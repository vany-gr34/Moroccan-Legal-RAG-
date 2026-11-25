#!/usr/bin/env python3
"""Run the full preprocessing pipeline: Extract → Clean → Normalize."""

from src.core.normalizing import ArabicNormalizer
from src.core.cleaning import LegalTextCleaner
from src.ingestion.extractors.pdf_text import PdfToTextExtractor
import sys
from pathlib import Path

# Make sure the project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/run_preprocessing_pipeline.py <pdf_path> [--ocr]")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    use_ocr = "--ocr" in sys.argv

    # Step 1: Extract raw text
    print("=" * 60)
    print("1. Extraction")
    print("=" * 60)
    extractor = PdfToTextExtractor(use_ocr=use_ocr)
    extraction_result = extractor.extract(pdf_path)
    print(f"   Method: {extraction_result.metadata.get('method', 'unknown')}")
    print(f"   Pages: {extraction_result.total_pages}")
    total_raw_chars = sum(len(p.text) for p in extraction_result.pages)
    print(f"   Characters: {total_raw_chars}")

    # Step 2: Clean
    print("\n" + "=" * 60)
    print("2. Cleaning")
    print("=" * 60)
    cleaner = LegalTextCleaner()
    cleaned_result = cleaner.clean_extraction_result(extraction_result)
    print(f"   Original chars: {cleaned_result.stats['original_chars']}")
    print(f"   Cleaned chars:  {cleaned_result.stats['cleaned_chars']}")
    print(f"   Reduction:      {cleaned_result.stats['reduction_percent']}%")

    # Step 3: Normalize
    print("\n" + "=" * 60)
    print("3. Normalization")
    print("=" * 60)
    normalizer = ArabicNormalizer({
        'unify_alef': True,
        'remove_tatweel': True,
        'remove_diacritics': True,
        'preserve_shadda': False,
        'unify_digits': True,
    })
    normalized_text = normalizer.normalize(cleaned_result.full_text)
    print(f"   Final characters: {len(normalized_text)}")

    # Step 4: Save output
    output_path = pdf_path.with_suffix(".preprocessed.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(normalized_text)

    print("\n" + "=" * 60)
    print(f"Preprocessed text saved to: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
