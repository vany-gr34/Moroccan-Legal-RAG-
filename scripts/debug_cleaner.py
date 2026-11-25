#!/usr/bin/env python3
"""Debug: run the text cleaner on a PDF and inspect the output."""
from src.ingestion.extractors.pdf_text import PdfToTextExtractor
from src.core.cleaning import LegalTextCleaner
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_cleaner.py <pdf_path>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    # Extract raw text
    extractor = PdfToTextExtractor()
    result = extractor.extract(pdf_path)

    # Clean
    cleaner = LegalTextCleaner()
    cleaned = cleaner.clean_extraction_result(result)

    # Save cleaned text
    output_path = pdf_path.with_suffix(".cleaned.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned.full_text)

    print(f"Cleaned text saved to: {output_path}")
    print(f"Original chars: {cleaned.stats['original_chars']}")
    print(f"Cleaned chars:  {cleaned.stats['cleaned_chars']}")
    print(f"Reduction:      {cleaned.stats['reduction_percent']}%")
    print(f"Pages:          {cleaned.total_pages}")


if __name__ == "__main__":
    main()
