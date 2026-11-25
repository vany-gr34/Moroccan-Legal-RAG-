#!/usr/bin/env python3
"""Extract raw text from a single PDF and save to a .txt file for cleaning analysis."""

from src.ingestion.extractors.pdf_text import PdfToTextExtractor
import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(
        description="Extract raw text from one PDF and save to a .txt file."
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output .txt file path (default: same name with .txt extension)",
    )
    parser.add_argument(
        "--use-ocr",
        action="store_true",
        help="Attempt OCR fallback if no text layer is found",
    )
    parser.add_argument(
        "--ocr-lang",
        default="ara",
        help="OCR language code (default: ara)",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    output_path = args.output or pdf_path.with_suffix(".txt")
    output_path = Path(output_path)

    extractor = PdfToTextExtractor(
        use_ocr=args.use_ocr,
        ocr_lang=args.ocr_lang,
    )

    print(f"Extracting: {pdf_path}")
    result = extractor.extract(pdf_path)

    print(f"Pages: {result.total_pages}")
    print(f"Method used: {result.metadata.get('method', 'unknown')}")

    with open(output_path, "w", encoding="utf-8") as f:
        for page in result.pages:
            f.write(f"===== Page {page.page_number} =====\n")
            f.write(page.text + "\n\n")

    print(f"Saved raw text to: {output_path}")
    print(f"Total characters: {sum(len(p.text) for p in result.pages)}")


if __name__ == "__main__":
    main()
