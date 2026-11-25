"""PDF to Text extractor – pdfplumber + PyMuPDF (layout‑aware) + optional OCR with Arabic RTL fixing."""
import re
from pathlib import Path
import time
import logging
from typing import Optional, List, Tuple

from .base import BaseExtractor, ExtractionResult, PageData

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import fitz
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

ARABIC_RANGE = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
)
ARABIC_THRESHOLD = 0.3


def bidi_visual_to_logical(text: str) -> str:
    """
    Convert a line from visual order (as rendered by some PDF engines)
    to logical order while preserving numbers and Latin words intact.
    """
    tokens = re.split(r'(\s+)', text)
    processed = []
    for tok in tokens:
        if tok.isspace() or not tok:
            processed.append(tok)
            continue
        if ARABIC_RANGE.search(tok):
            processed.append(tok[::-1])
        else:
            processed.append(tok)

    processed.reverse()
    return ''.join(processed)


class PdfToTextExtractor(BaseExtractor):
    """Extract text from PDFs using best available method (pdfplumber > PyMuPDF layout > OCR)."""

    def __init__(
        self,
        use_ocr: bool = False,
        ocr_dpi: int = 200,
        ocr_lang: str = "ara",
    ):
        self.use_ocr = use_ocr
        self.ocr_dpi = ocr_dpi
        self.ocr_lang = ocr_lang

    @property
    def name(self) -> str:
        methods = ["pdfplumber", "PyMuPDF"]
        if self.use_ocr:
            methods.append("OCR")
        return f"PdfToText ({'+'.join(methods)})"

    # ------------------------------------------------------------------
    # Arabic helpers
    # ------------------------------------------------------------------
    @staticmethod
    def is_arabic_line(text: str, threshold: float = ARABIC_THRESHOLD) -> bool:
        if not text:
            return False
        arabic_chars = len(ARABIC_RANGE.findall(text))
        total = len(text)
        return (arabic_chars / total) >= threshold if total > 0 else False

    @staticmethod
    def reverse_arabic_text(text: str) -> str:
        """Reverse Arabic text that was extracted in reversed visual order."""
        return bidi_visual_to_logical(text)

    @classmethod
    def fix_arabic_line(cls, line: str) -> str:
        if cls.is_arabic_line(line):
            return bidi_visual_to_logical(line)
        return line

    @classmethod
    def fix_arabic_text(cls, text: str) -> str:
        lines = text.splitlines()
        fixed = [cls.fix_arabic_line(line) for line in lines]
        return "\n".join(fixed)

    # ------------------------------------------------------------------
    # Layout‑aware extraction using PyMuPDF “dict” mode
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_pymupdf_layout(doc: fitz.Document) -> List[str]:
        """
        Layout‑aware extraction that handles two‑column pages.
        Blocks are assigned to left/right column based on their horizontal centre,
        then each column is read top‑to‑bottom and columns are concatenated left‑to‑right.
        """
        page_texts = []
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            text_blocks = []
            for b in blocks:
                if b["type"] != 0:
                    continue
                block_text = ""
                for line in b["lines"]:
                    line_text = "".join([span["text"]
                                        for span in line["spans"]])
                    block_text += line_text + "\n"
                block_text = block_text.strip()
                if block_text:
                    x0, y0, x1, y1 = b["bbox"]
                    text_blocks.append((x0, y0, x1, y1, block_text))

            if not text_blocks:
                page_texts.append("")
                continue

            # ----- Column detection (two‑column pages) -----
            # Use the median of x‑centres to split into left/right
            x_centres = [(b[0] + b[2]) / 2 for b in text_blocks]
            median_x = sorted(x_centres)[len(x_centres) // 2]

            left_col = []
            right_col = []
            for b in text_blocks:
                x0, y0, x1, y1, txt = b
                cx = (x0 + x1) / 2
                if cx < median_x:
                    left_col.append((y0, txt))
                else:
                    right_col.append((y0, txt))

            # If one column is empty (single‑column page), keep simple order
            if not left_col or not right_col:
                # Single column – sort by y and join
                text_blocks.sort(key=lambda b: b[1])
                page_text = "\n".join([b[4] for b in text_blocks])
                page_texts.append(page_text)
                continue

            # Sort each column by vertical position
            left_col.sort(key=lambda t: t[0])
            right_col.sort(key=lambda t: t[0])

            # Merge columns: left column first, then right column
            left_text = "\n".join([t[1] for t in left_col])
            right_text = "\n".join([t[1] for t in right_col])
            page_text = left_text + "\n\n" + right_text

            page_texts.append(page_text)

        return page_texts

    # ------------------------------------------------------------------
    # Extraction methods (per page) – updated PyMuPDF path
    # ------------------------------------------------------------------
    def _extract_pdfplumber(self, pdf_path: Path):
        if pdfplumber is None:
            return None
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        yield page_num, self.fix_arabic_text(text)
        except Exception as e:
            logger.warning(f"pdfplumber error: {e}")

    def _extract_pymupdf(self, pdf_path: Path):
        """
        Use layout‑aware dict extraction when possible.
        Falls back to plain text if dict mode fails.
        """
        if fitz is None:
            return None
        try:
            doc = fitz.open(pdf_path)
            # First try layout extraction
            try:
                page_texts = self._extract_pymupdf_layout(doc)
                for i, text in enumerate(page_texts, start=1):
                    if text.strip():
                        yield i, self.fix_arabic_text(text)
                    else:
                        # Fallback for empty pages
                        page = doc[i-1]
                        plain = page.get_text("text")
                        if plain.strip():
                            yield i, self.fix_arabic_text(plain)
            except Exception as e:
                logger.warning(
                    f"Layout extraction failed, falling back to plain text: {e}")
                # Fallback: original plain text extraction
                for page_num, page in enumerate(doc, start=1):
                    text = page.get_text("text")
                    if text:
                        yield page_num, self.fix_arabic_text(text)
            doc.close()
        except Exception as e:
            logger.warning(f"PyMuPDF error: {e}")

    def _extract_ocr(self, pdf_path: Path):
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            logger.error("OCR libraries not available (pillow, pytesseract)")
            return None
        if fitz is None:
            return None
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc, start=1):
                pix = page.get_pixmap(dpi=self.ocr_dpi)
                img = Image.frombytes(
                    "RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img, lang=self.ocr_lang)
                if text:
                    yield page_num, self.fix_arabic_text(text)
            doc.close()
        except Exception as e:
            logger.warning(f"OCR error: {e}")

    # ------------------------------------------------------------------
    # Main extraction
    # ------------------------------------------------------------------
    def extract(self, pdf_path: Path) -> ExtractionResult:
        pages: list[PageData] = []
        total_start = time.time()
        used_method = ""

        # Try pdfplumber first
        method = "pdfplumber"
        for page_num, text in self._extract_pdfplumber(pdf_path):
            pages.append(PageData(page_number=page_num, text=text.strip()))
            used_method = method

        if pages:
            total_time = (time.time() - total_start) * 1000
            return ExtractionResult(
                file_path=pdf_path,
                extractor_name=self.name,
                total_pages=len(pages),
                pages=pages,
                total_time_ms=total_time,
                metadata={"method": used_method},
            )

        # Fallback to PyMuPDF with layout detection
        method = "PyMuPDF"
        for page_num, text in self._extract_pymupdf(pdf_path):
            pages.append(PageData(page_number=page_num, text=text.strip()))
            used_method = method

        if pages:
            total_time = (time.time() - total_start) * 1000
            return ExtractionResult(
                file_path=pdf_path,
                extractor_name=self.name,
                total_pages=len(pages),
                pages=pages,
                total_time_ms=total_time,
                metadata={"method": used_method},
            )

        # Optional OCR
        if self.use_ocr:
            method = "OCR"
            for page_num, text in self._extract_ocr(pdf_path):
                pages.append(PageData(page_number=page_num, text=text.strip()))
                used_method = method

        total_time = (time.time() - total_start) * 1000
        return ExtractionResult(
            file_path=pdf_path,
            extractor_name=self.name,
            total_pages=len(pages),
            pages=pages,
            total_time_ms=total_time,
            metadata={"method": used_method or "none"},
        )
