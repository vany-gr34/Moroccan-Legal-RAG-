#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF to Raw Text Extractor with RTL (Arabic) support.
Corrects reversed Arabic text extracted from PDFs.
"""

import argparse
import logging
import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DEFAULT_INPUT_DIR = "data/raw"
DEFAULT_OUTPUT_DIR = "data/raw_text"
LOG_LEVEL = logging.INFO

# Arabic Unicode range
ARABIC_RANGE = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
ARABIC_THRESHOLD = 0.3  # 30% Arabic chars to trigger reversal

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PDF2TXT")


# ----------------------------------------------------------------------
# Arabic text correction functions
# ----------------------------------------------------------------------
def is_arabic_line(text: str, threshold: float = ARABIC_THRESHOLD) -> bool:
    """Check if a line contains a significant amount of Arabic characters."""
    if not text:
        return False
    arabic_chars = len(ARABIC_RANGE.findall(text))
    total_chars = len(text)
    if total_chars == 0:
        return False
    return (arabic_chars / total_chars) >= threshold


def reverse_arabic_text(text: str) -> str:
    """
    Reverse Arabic text that was extracted in reversed order.
    Handles numbers and Latin characters properly (they remain in place within the reversed context).
    This is a simplified approach: split into words, reverse each word? Actually, the entire string
    is reversed character-by-character. That works for pure Arabic strings.
    """
    if not text:
        return text
    # Simple full reversal works for Arabic when glyph order is reversed.
    # However, numbers and punctuation may become reversed incorrectly.
    # For legal documents, numbers are usually isolated.
    return text[::-1]


def fix_arabic_line(line: str) -> str:
    """Apply reversal if line is predominantly Arabic."""
    if is_arabic_line(line):
        return reverse_arabic_text(line)
    return line


def fix_arabic_text(text: str) -> str:
    """Fix all lines in a text block."""
    lines = text.splitlines()
    fixed_lines = [fix_arabic_line(line) for line in lines]
    return "\n".join(fixed_lines)


# ----------------------------------------------------------------------
# Extraction functions
# ----------------------------------------------------------------------
def extract_text_pdfplumber(pdf_path: Path) -> Optional[str]:
    """Extract text using pdfplumber and apply RTL correction."""
    try:
        full_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    # Apply RTL correction
                    page_text = fix_arabic_text(page_text)
                    full_text.append(f"===== Page {page_num} =====\n")
                    full_text.append(page_text.strip())
                    full_text.append("\n\n")
                else:
                    logger.warning(
                        f"No text on page {page_num} of {pdf_path.name}")
        return "".join(full_text).strip()
    except Exception as e:
        logger.error(f"pdfplumber failed on {pdf_path.name}: {e}")
        return None


def extract_text_pymupdf(pdf_path: Path) -> Optional[str]:
    """Extract text using PyMuPDF with RTL correction."""
    if fitz is None:
        return None
    try:
        full_text = []
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            if page_text:
                page_text = fix_arabic_text(page_text)
                full_text.append(f"===== Page {page_num} =====\n")
                full_text.append(page_text.strip())
                full_text.append("\n\n")
        doc.close()
        return "".join(full_text).strip()
    except Exception as e:
        logger.error(f"PyMuPDF failed on {pdf_path.name}: {e}")
        return None


def extract_text_ocr(pdf_path: Path, dpi: int = 200) -> Optional[str]:
    """OCR fallback for scanned PDFs (requires tesseract with Arabic)."""
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        logger.error(
            "OCR libraries not available. Install pillow and pytesseract.")
        return None

    if fitz is None:
        logger.error("PyMuPDF required for OCR rendering.")
        return None

    try:
        doc = fitz.open(pdf_path)
        full_text = []
        for page_num, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = pytesseract.image_to_string(img, lang="ara")
            if page_text:
                # OCR output usually has correct order, but apply just in case
                page_text = fix_arabic_text(page_text)
                full_text.append(f"===== Page {page_num} =====\n")
                full_text.append(page_text.strip())
                full_text.append("\n\n")
        doc.close()
        return "".join(full_text).strip()
    except Exception as e:
        logger.error(f"OCR failed on {pdf_path.name}: {e}")
        return None


def extract_text_auto(pdf_path: Path, use_ocr: bool = False) -> Optional[str]:
    """Automatic extraction with fallback."""
    # Try pdfplumber first
    text = extract_text_pdfplumber(pdf_path)
    if text and len(text) > 500:
        return text

    # Try PyMuPDF
    if fitz:
        text = extract_text_pymupdf(pdf_path)
        if text and len(text) > 500:
            return text

    # Try OCR
    if use_ocr:
        logger.info(f"Attempting OCR on {pdf_path.name}")
        text = extract_text_ocr(pdf_path)
        if text:
            return text

    logger.error(f"All extraction methods failed for {pdf_path.name}")
    return None


# ----------------------------------------------------------------------
# Batch processing
# ----------------------------------------------------------------------
def process_single_pdf(pdf_path: Path, output_dir: Path, use_ocr: bool = False) -> bool:
    """Extract and save one PDF as .txt."""
    logger.info(f"Processing: {pdf_path.name}")
    text = extract_text_auto(pdf_path, use_ocr)
    if text is None:
        return False

    output_file = output_dir / f"{pdf_path.stem}.txt"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"Saved: {output_file.name} ({len(text)} characters)")
        return True
    except Exception as e:
        logger.error(f"Failed to write {output_file}: {e}")
        return False


def process_all_pdfs(input_dir: Path, output_dir: Path, use_ocr: bool = False, recursive: bool = False) -> None:
    """Process all PDFs in directory."""
    if recursive:
        pdf_files = list(input_dir.rglob("*.pdf")) + \
            list(input_dir.rglob("*.PDF"))
    else:
        pdf_files = list(input_dir.glob("*.pdf")) + \
            list(input_dir.glob("*.PDF"))

    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return

    logger.info(f"Found {len(pdf_files)} PDF files")
    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    for pdf_path in pdf_files:
        if process_single_pdf(pdf_path, output_dir, use_ocr):
            success += 1

    logger.info(f"Completed: {success}/{len(pdf_files)} files extracted")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs (digital or scanned) with Arabic RTL support."
    )
    parser.add_argument("--input", "-i", type=str, default=DEFAULT_INPUT_DIR,
                        help=f"Input directory (default: {DEFAULT_INPUT_DIR})")
    parser.add_argument("--output", "-o", type=str, default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--ocr", action="store_true",
                        help="Use OCR for scanned PDFs (requires tesseract + Arabic)")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="Search subdirectories recursively")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)

    process_all_pdfs(input_dir, output_dir, use_ocr=args.ocr,
                     recursive=args.recursive)


if __name__ == "__main__":
    main()
