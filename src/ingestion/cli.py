"""CLI for ingestion module."""
from dotenv import load_dotenv
from src.ingestion.pipeline import ingest_articles
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Ingest structured legal articles into the vector database"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to articles JSON file"
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Legal domain (e.g., commercial, traffic, criminal)"
    )
    parser.add_argument(
        "--source-file",
        type=str,
        default=None,
        help="Original PDF filename for traceability (defaults to JSON stem)"
    )
    parser.add_argument(
        "--law-name",
        type=str,
        default=None,
        help="Override law name"
    )
    parser.add_argument(
        "--extraction-method",
        type=str,
        default="pymupdf",
        help="Method used for text extraction (e.g., pymupdf, ocr)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size"
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Truncate articles to N chars before embedding "
             "(prevents VRAM OOM; default: 2000)"
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear existing chunks for this source before inserting"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)-8s | %(message)s"
    )

    json_path = Path(args.input)
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)

    n = ingest_articles(
        json_path=json_path,
        domain=args.domain,
        source_file=args.source_file,
        law_name=args.law_name,
        extraction_method=args.extraction_method,
        batch_size=args.batch_size,
        max_chars=args.max_chars,
        clear_existing=not args.no_clear,
    )

    print(f"Ingested {n} articles.")


if __name__ == "__main__":
    main()
