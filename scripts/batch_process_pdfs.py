#!/usr/bin/env python3
"""
Batch-process all PDFs in data/raw/ through the full pipeline.

Output structure:
    data/processed/{domain}/
        {stem}.txt              # Preprocessed / normalized text
        {stem}.articles.json    # Parsed structured articles
    data/metadata/
        processing_summary.csv  # Overview of all processed files

Usage:
    python scripts/batch_process_pdfs.py
    python scripts/batch_process_pdfs.py --skip-existing
"""

from src.ingestion.extractors.pdf_text import PdfToTextExtractor
from src.core.structure import parse_normalized_text_to_json
from src.core.cleaning import LegalTextCleaner
from src.core.normalizing import ArabicNormalizer
import json
import sys
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("BatchProcess")

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
METADATA_DIR = Path("data/metadata")


def _output_paths(pdf_path: Path, domain: str):
    """Get output paths organized by domain."""
    stem = pdf_path.stem
    domain_dir = PROCESSED_DIR / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    return (
        domain_dir / f"{stem}.txt",
        domain_dir / f"{stem}.articles.json",
    )


def process_pdf(pdf_path: Path, skip_existing: bool = False):
    """Run extraction → cleaning → normalization → structure parsing on one PDF."""
    stem = pdf_path.stem
    domain = infer_domain(pdf_path)
    txt_path, json_path = _output_paths(pdf_path, domain)

    if skip_existing and txt_path.exists() and json_path.exists():
        articles_count = 0
        try:
            with open(json_path) as f:
                articles_count = len(json.load(f))
        except Exception:
            pass
        logger.info(
            f"  SKIP {stem} ({articles_count} articles, domain={domain})")
        return {
            "file": stem,
            "domain": domain,
            "method": "cached",
            "chars": 0,
            "articles": articles_count,
            "law_name": infer_law_name(pdf_path),
        }

    logger.info(f"  Processing {stem} (domain={domain})...")

    # Step 1: Extract raw text
    extractor = PdfToTextExtractor(use_ocr=False)
    extraction_result = extractor.extract(pdf_path)
    method = extraction_result.metadata.get("method", "unknown")
    total_raw_chars = sum(len(p.text) for p in extraction_result.pages)

    # Step 2: Clean
    cleaner = LegalTextCleaner()
    cleaned_result = cleaner.clean_extraction_result(extraction_result)

    # Step 3: Normalize
    normalizer = ArabicNormalizer({
        'unify_alef': True,
        'remove_tatweel': True,
        'remove_diacritics': True,
        'preserve_shadda': False,
        'unify_digits': True,
    })
    normalized_text = normalizer.normalize(cleaned_result.full_text)

    # Step 4: Save normalized text
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(normalized_text)

    # Step 5: Parse structure → JSON
    law_name = infer_law_name(pdf_path)
    articles = parse_normalized_text_to_json(
        normalized_text,
        domain=domain,
        law_name=law_name,
        output_path=str(json_path),
    )

    logger.info(
        f"  DONE {stem} | method={method} | chars={total_raw_chars} "
        f"| articles={len(articles)} | domain={domain}"
    )

    return {
        "file": stem,
        "domain": domain,
        "method": method,
        "chars": total_raw_chars,
        "articles": len(articles),
        "law_name": law_name,
    }


def infer_domain(pdf_path: Path) -> str:
    """Try to infer legal domain from filename."""
    name = pdf_path.stem
    if "trade" in name.lower() or "تجارة" in name or "5.96" in name:
        return "commercial"
    if "civil" in name.lower() or "مدني" in name:
        return "civil"
    if "penal" in name.lower() or "جنائي" in name:
        return "criminal"
    if "route" in name.lower() or "سير" in name:
        return "traffic"
    if "constitution" in name.lower() or "دستور" in name:
        return "civil"
    if "قضائي" in name:
        return "judicial"
    if "ضري" in name or "ضرا" in name or "tax" in name.lower():
        return "tax"
    if "شغل" in name:
        return "civil"
    if "sanction" in name.lower() or "عقوب" in name:
        return "violations"
    return "civil"


def infer_law_name(pdf_path: Path) -> str:
    """Try to infer a readable law name from filename."""
    name = pdf_path.stem
    return name.replace("-", " ").replace("_", " ").strip()


def write_summary(results: list):
    """Write a CSV summary of all processing results."""
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    import csv

    csv_path = METADATA_DIR / "processing_summary.csv"
    fieldnames = ["file", "domain", "articles", "chars", "method", "law_name"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            if row:
                writer.writerow(row)

    logger.info(f"Summary saved to {csv_path}")

    # Also print a human-readable summary
    print("\n" + "=" * 70)
    print(f"{'File':<40} {'Domain':<15} {'Articles':<10}")
    print("=" * 70)
    total_articles = 0
    for row in results:
        if row:
            print(f"{row['file']:<40} {row['domain']:<15} {row['articles']:<10}")
            total_articles += row['articles']
    print("=" * 70)
    print(f"{'TOTAL':<40} {'':<15} {total_articles:<10}")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Batch process all PDFs in data/raw/")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip PDFs that already have output files")
    args = parser.parse_args()

    pdf_files = sorted(RAW_DIR.glob("*.pdf"))

    if not pdf_files:
        logger.error(f"No PDFs found in {RAW_DIR}")
        sys.exit(1)

    logger.info(f"Found {len(pdf_files)} PDFs to process")

    results = []
    for pdf_path in pdf_files:
        result = process_pdf(pdf_path, skip_existing=args.skip_existing)
        results.append(result)

    write_summary(results)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
