"""
PDF Block Parser — extracts structured articles from PDF page blocks.

This module works at the PDF level: it takes PyMuPDF page blocks and
identifies article boundaries, headings, footers, and structural elements
using font heuristics and spatial analysis.

Use AFTER PdfToTextExtractor and BEFORE LegalTextCleaner.

It contains:
  - PDFBlockParser:       Static methods for article detection from page blocks
  - PDFContentAnalyzer:   Analyzes PyMuPDF output with noise filtering
  - DigitalLegalExtractor: Orchestrator for batch processing digital PDFs
"""

import fitz  # PyMuPDF
import json
import logging
import pandas as pd
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional

# ----------------------------------------------------------------------
# Configuration & Constants
# ----------------------------------------------------------------------

# Regex patterns for Moroccan legal structure (Universal Alif & Word Numbers)
ARTICLE_PATTERNS = [
    r"(?:[اأإآ]لمادة|[اأإآ]لفصل|م\.)\s*[:\-\.]?\s*(?:\d+|[اأإآ]لأولى|[اأإآ]لثانية|[اأإآ]لثالثة|[اأإآ]لرابعة|[اأإآ]لخامسة)",
    r"(?:\d+|[اأإآ]لأولى|[اأإآ]لثانية)\s*(?:[اأإآ]لمادة|[اأإآ]لفصل|م\.)",
    r"(?:[اأإآ]لباب|[اأإآ]لقسم)\s*(?:\d+|[اأإآ]لأولى|[اأإآ]لثانية|[اأإآ]لثالثة|[اأإآ]لرابعة|[اأإآ]لخامسة|[اأإآ]لأول|[اأإآ]لثاني|[اأإآ]لثالث)",
    r"قانون\s+رقم\s+[\d\.]+",
    r"ظهير\s+شريف\s+رقم\s+[\d\.]+",
]

HEADER_FOOTER_MARGIN = 60  # Points from top/bottom to look for noise
REPETITION_THRESHOLD = 0.6  # If text appears on >60% of pages, it's noise
HEADING_FONT_RATIO = 1.10  # Ratio vs median font size to detect headings

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# PDFBlockParser (was LegalStructureParser in old data_preprocessing/)
# ----------------------------------------------------------------------

class PDFBlockParser:
    """Detects legal entities like articles and headings in PDF page blocks.

    This parser works on structured page blocks from PyMuPDF, using
    spatial analysis (font sizes, positions) to identify articles.
    """

    _ARABIC_WORD_RE = re.compile(r"^[\u0600-\u06FF]+$")
    _NON_ATTACHABLE_SHORT_WORDS = {
        "في", "من", "عن", "على", "الى", "إلى", "أو", "ثم", "قد", "لن", "لم",
        "أن", "إن", "كل", "مع", "بين", "بعد", "قبل", "هذا", "هذه", "ذلك", "تلك",
        "هو", "هي", "هم", "هن", "ما", "لا", "أجل",
    }
    _COMMON_SUFFIX_FRAGMENTS = {"ان", "ين", "ون", "ات",
                                "ية", "ه", "ها", "هم", "هن", "نا", "كما", "كم"}
    _ARTICLE_NUMBERS = (
        r"(?:\d+|الأولى|الأول|الثانية|الثاني|الثالثة|الثالث|الرابعة|الرابع|الخامسة|الخامس)"
    )
    _ARTICLE_PREFIX = r"(?:المادة|الفصل|م\.|الباب|القسم|الكتاب)"
    _ARTICLE_FORWARD_RE = re.compile(
        r"^" + _ARTICLE_PREFIX + r"\s*[:\-–\.]?\s*" + _ARTICLE_NUMBERS + r"\b"
    )
    _ARTICLE_REVERSE_RE = re.compile(
        r"^" + _ARTICLE_NUMBERS + r"\s*" + _ARTICLE_PREFIX + r"\b"
    )

    @staticmethod
    def _is_arabic_word(token: str) -> bool:
        return bool(token) and bool(PDFBlockParser._ARABIC_WORD_RE.match(token))

    @staticmethod
    def _should_merge_tokens(current: str, nxt: str) -> bool:
        """Determine whether two Arabic tokens should be merged (split-word artifact)."""
        if not PDFBlockParser._is_arabic_word(current) or not PDFBlockParser._is_arabic_word(nxt):
            return False
        if current in PDFBlockParser._NON_ATTACHABLE_SHORT_WORDS:
            return False
        if nxt in PDFBlockParser._NON_ATTACHABLE_SHORT_WORDS:
            return False
        if len(current) == 1 and current not in {"و", "ف", "ب", "ك", "ل"}:
            return True
        if len(nxt) == 1:
            return True
        if len(current) <= 2 and len(nxt) >= 4:
            return True
        if len(current) >= 3 and nxt in PDFBlockParser._COMMON_SUFFIX_FRAGMENTS:
            return True
        return False

    @staticmethod
    def _merge_fragmented_arabic_words(text: str) -> str:
        """Rejoin Arabic words that were split across spans during PDF extraction."""
        tokens = text.split()
        if len(tokens) < 2:
            return text

        merged_tokens = []
        i = 0
        while i < len(tokens):
            current = tokens[i]
            while i + 1 < len(tokens) and PDFBlockParser._should_merge_tokens(current, tokens[i + 1]):
                current += tokens[i + 1]
                i += 1
            merged_tokens.append(current)
            i += 1

        return " ".join(merged_tokens)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize Arabic text: NFKC, alef unification, spacing fixes."""
        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)
        text = re.sub(
            r"[\u0640\u200b-\u200f\u202a-\u202e\u2066-\u2069]", "", text)
        text = re.sub(r"\b[اأإآ]ملادة\b", "المادة", text)
        text = re.sub(r"\b[اأإآ]لفلص\b", "الفصل", text)
        text = re.sub(r"\bاأل", "الأ", text)
        text = re.sub(r"\bاإل", "الإ", text)
        text = re.sub(r"\bاآل", "الآ", text)
        text = re.sub(
            r"\b(المادة|الفصل|الباب|القسم|الكتاب)(\d+)\b", r"\1 \2", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+([،؛:,.!?])", r"\1", text)
        text = re.sub(r"([(\[«])\s+", r"\1", text)
        text = re.sub(r"\s+([)\]»])", r"\1", text)

        text = PDFBlockParser._merge_fragmented_arabic_words(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def extract_article_id(text: str) -> Optional[str]:
        """Extract article ID from a text line (e.g., 'المادة 147')."""
        if not text:
            return None

        clean = PDFBlockParser.normalize_text(text)
        clean = re.sub(r'^[«"\(\[\{]+', "", clean).strip()
        if re.match(r"^\d+\s*[-–]", clean):
            return None

        match = PDFBlockParser._ARTICLE_FORWARD_RE.match(clean)
        if not match:
            match = PDFBlockParser._ARTICLE_REVERSE_RE.match(clean)
        if not match:
            return None
        return match.group(0).strip(" -:.،؛")

    @staticmethod
    def is_article_start(text: str) -> bool:
        """Check if a text block starts with an article marker."""
        return PDFBlockParser.extract_article_id(text) is not None

    @staticmethod
    def _looks_like_page_number_or_rule(text: str) -> bool:
        stripped = text.strip()
        return bool(
            re.fullmatch(r"-?\s*\d+\s*-?", stripped)
            or re.fullmatch(r"-{3,}", stripped)
        )

    @staticmethod
    def _looks_like_toc_entry(text: str) -> bool:
        return bool(re.search(r"\.{3,}\s*\d+\s*$", text))

    @staticmethod
    def build_articles(pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build structured articles from flattened page blocks.

        Args:
            pages_data: List of pages, each with page_number and blocks.

        Returns:
            List of articles with id, page, and text fields.
        """
        flattened_blocks: List[Dict[str, Any]] = []
        for page in pages_data:
            page_number = page["page_number"]
            for block in page["blocks"]:
                flattened_blocks.append({
                    "page": page_number,
                    "text": block["text"],
                    "type": block["type"],
                })

        start_indexes = [
            idx for idx, block in enumerate(flattened_blocks)
            if PDFBlockParser.is_article_start(block["text"])
            and not PDFBlockParser._looks_like_toc_entry(block["text"])
        ]

        articles = []
        for pos, start_idx in enumerate(start_indexes):
            start_block = flattened_blocks[start_idx]
            article_id = PDFBlockParser.extract_article_id(start_block["text"])
            if not article_id:
                continue

            end_idx = start_indexes[pos + 1] if pos + \
                1 < len(start_indexes) else len(flattened_blocks)
            article_parts = []

            for idx in range(start_idx, end_idx):
                block = flattened_blocks[idx]
                block_text = PDFBlockParser.normalize_text(
                    block["text"]).strip()
                if not block_text or PDFBlockParser._looks_like_page_number_or_rule(block_text):
                    continue
                if idx > start_idx and block["type"] == "heading" and not PDFBlockParser.is_article_start(block_text):
                    break
                article_parts.append(block_text)

            if not article_parts:
                continue

            articles.append({
                "id": article_id,
                "page": start_block["page"],
                "text": " ".join(article_parts).strip(),
            })

        return articles

    @staticmethod
    def is_heading(span: Dict[str, Any], median_font_size: float) -> bool:
        """Heuristic to detect headings based on font size and weight."""
        flags = span.get("flags", 0)
        is_bold = bool(flags & 2) or bool(flags & 16)
        size_ratio = span.get("size", 0) / \
            median_font_size if median_font_size > 0 else 1

        if size_ratio >= HEADING_FONT_RATIO:
            return True
        if is_bold and size_ratio >= 1.02:
            return True
        return False


# ----------------------------------------------------------------------
# PDFContentAnalyzer
# ----------------------------------------------------------------------

class PDFContentAnalyzer:
    """Handles PyMuPDF extraction and spatial noise filtering."""

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.noise_map = {}
        self.median_font_size = self._calculate_median_font_size()
        self.noise_blocks = self._detect_headers_footers()

    def _calculate_median_font_size(self) -> float:
        """Determine the most common font size to use as a baseline for body text."""
        sizes = []
        for page in self.doc[:5]:
            dict_data = page.get_text("dict")
            for block in dict_data.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        sizes.append(round(span["size"], 1))

        if not sizes:
            return 12.0
        return Counter(sizes).most_common(1)[0][0]

    def _detect_headers_footers(self) -> List[str]:
        """Identify repeated text blocks at top/bottom of pages (potential noise)."""
        if len(self.doc) < 3:
            return []

        y_positions = {}
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            height = page.rect.height
            dict_data = page.get_text("dict")

            for block in dict_data.get("blocks", []):
                if block["type"] != 0:
                    continue

                y0, y1 = block["bbox"][1], block["bbox"][3]
                if y0 < HEADER_FOOTER_MARGIN or y1 > (height - HEADER_FOOTER_MARGIN):
                    text = "".join(
                        s["text"] for l in block.get("lines", [])
                        for s in l.get("spans", [])
                    ).strip()
                    text = PDFBlockParser.normalize_text(text)
                    if not text:
                        continue

                    if "الجريدة الرسمية" in text:
                        pos_key = (round(y0, 0), "GAZETTE_HEADER")
                    else:
                        text_no_digits = re.sub(r'\d+', '', text).strip()
                        pos_key = (round(y0, 0), text_no_digits)

                    y_positions[pos_key] = y_positions.get(pos_key, 0) + 1
                    if pos_key not in self.noise_map:
                        self.noise_map[pos_key] = text

        noise = [self.noise_map[key] for key, count in y_positions.items()
                 if count > (len(self.doc) * REPETITION_THRESHOLD)]
        return noise

    def extract_structured_data(self) -> Dict[str, Any]:
        """Extract cleaned text and structural info from all pages."""
        pages_data = []

        for page_num, page in enumerate(self.doc, start=1):
            page_blocks = []
            dict_data = page.get_text("dict")

            blocks = sorted(dict_data.get("blocks", []),
                            key=lambda b: (b["bbox"][1], b["bbox"][0]))

            for block_idx, block in enumerate(blocks):
                if block["type"] != 0:
                    continue

                line_text_parts = []
                is_heading = False

                for line in block.get("lines", []):
                    span_text_parts = []
                    for span in line.get("spans", []):
                        text = span["text"].strip()
                        normalized_text = PDFBlockParser.normalize_text(text)
                        if not normalized_text or normalized_text in self.noise_blocks:
                            continue
                        span_text_parts.append(normalized_text)
                        if PDFBlockParser.is_heading(span, self.median_font_size):
                            is_heading = True

                    line_text = "".join(span_text_parts).strip()
                    line_text = PDFBlockParser.normalize_text(line_text)
                    if line_text:
                        line_text_parts.append(line_text)

                full_text = " ".join(line_text_parts).strip()
                if not full_text:
                    continue

                full_text = PDFBlockParser.normalize_text(full_text)

                page_blocks.append({
                    "index": block_idx,
                    "text": full_text,
                    "type": "heading" if is_heading else "text",
                    "bbox": block["bbox"]
                })

            pages_data.append({
                "page_number": page_num,
                "blocks": page_blocks
            })

        articles = PDFBlockParser.build_articles(pages_data)
        self.doc.close()
        return {
            "pages": pages_data,
            "detected_articles": articles
        }


# ----------------------------------------------------------------------
# DigitalLegalExtractor — batch orchestrator
# ----------------------------------------------------------------------

class DigitalLegalExtractor:
    """Orchestrates the extraction process for all digital PDFs."""

    def __init__(self, raw_dir: str = "data/raw", interim_dir: str = "data/interim"):
        self.raw_dir = Path(raw_dir)
        self.interim_dir = Path(interim_dir)
        self.output_dir = self.interim_dir / "extracted"
        self.classification_file = self.interim_dir / "pdf_classification.csv"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger("DigitalLegalExtractor")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s"))
            self.logger.addHandler(handler)

    def load_queue(self) -> List[Path]:
        """Load list of digital PDFs from classification CSV."""
        if not self.classification_file.exists():
            self.logger.error(
                f"Classification file not found at {self.classification_file}")
            return []

        df = pd.read_csv(self.classification_file)
        digital_files = df[df["classification"] == "digital"]["file"].tolist()
        return [Path(f) for f in digital_files]

    def process_all(self):
        """Process each file in the queue."""
        queue = self.load_queue()
        self.logger.info(f"Found {len(queue)} digital PDFs to process.")

        for pdf_path in queue:
            try:
                self.logger.info(f"Processing: {pdf_path.name}")
                analyzer = PDFContentAnalyzer(pdf_path)
                data = analyzer.extract_structured_data()

                final_output = {
                    "file": str(pdf_path),
                    "extraction_date": pd.Timestamp.now().isoformat(),
                    "total_pages": len(data["pages"]),
                    "articles_count": len(data["detected_articles"]),
                    **data
                }

                output_path = self.output_dir / \
                    f"{pdf_path.stem}_extracted.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(final_output, f, ensure_ascii=False, indent=2)

                self.logger.info(
                    f"Successfully saved {output_path.name} ({len(data['detected_articles'])} articles)")

            except Exception as e:
                self.logger.error(f"Failed to process {pdf_path.name}: {e}")
