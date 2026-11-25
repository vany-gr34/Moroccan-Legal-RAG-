#!/usr/bin/env python3
"""
embed_all_articles.py — Embed all parsed legal articles into the vector database.

Scans data/processed/{domain}/ for all .articles.json files,
infers the legal domain from the directory name, and ingests each file
into the legal_chunks table with embeddings.

Usage:
    # Embed everything (default: skip already-ingested sources)
    python scripts/embed_all_articles.py

    # Force re-ingest all sources (delete existing chunks first)
    python scripts/embed_all_articles.py --clear-existing

    # Dry run — show what would be done without inserting
    python scripts/embed_all_articles.py --dry-run

    # Only specific domains
    python scripts/embed_all_articles.py --domains civil commercial

    # Custom batch size for embedding (lower if memory-constrained)
    python scripts/embed_all_articles.py --batch-size 16

    # Skip files with 0 articles (empty/broken parses)
    python scripts/embed_all_articles.py --skip-empty
"""

import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Make sure the project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from src.ingestion.pipeline import ingest_articles  # noqa: E402

logger = logging.getLogger(__name__)

# ─── Domain directory → DB domain mapping ─────────────────────────────────────
# Key = directory name under data/processed/
# Value = domain string accepted by legal_chunks.domain CHECK constraint
DIRECTORY_TO_DOMAIN = {
    "civil": "civil",
    "commercial": "commercial",
    "criminal": "criminal",
    "judicial": "judicial",
    # Tax codes stored as civil (not a separate DB domain)
    "tax": "civil",
    "traffic": "traffic",
    "violations": "violations",
    "companies": "companies",
    "family": "family",
}

VALID_DOMAINS = set(DIRECTORY_TO_DOMAIN.values())

PROCESSED_DIR = Path("data/processed")


def discover_article_files(
    processed_dir: Path,
    domains: list[str] | None = None,
) -> list[tuple[Path, str]]:
    """Discover all .articles.json files and their inferred domains.

    Returns:
        List of (json_path, domain) tuples.
    """
    results: list[tuple[Path, str]] = []

    if domains:
        dirs_to_scan = [
            processed_dir / d for d in domains
            if (processed_dir / d).is_dir()
        ]
    else:
        dirs_to_scan = sorted(processed_dir.iterdir())

    for dir_path in dirs_to_scan:
        if not dir_path.is_dir():
            continue

        domain = DIRECTORY_TO_DOMAIN.get(dir_path.name)
        if domain is None:
            logger.warning(
                "Skipping unknown directory '%s' — no domain mapping.",
                dir_path,
            )
            continue

        json_files = sorted(dir_path.glob("*.articles.json"))
        for jf in json_files:
            results.append((jf, domain))

    return results


def should_skip_file(json_path: Path, skip_empty: bool = False) -> str | None:
    """Return a skip reason string, or None if the file should be processed."""
    if json_path.stat().st_size == 0:
        return "empty file"

    if skip_empty:
        try:
            import json  # noqa: F811
            with open(json_path, "r", encoding="utf-8") as f:
                articles = json.load(f)
            if not articles:
                return "0 articles"
        except (json.JSONDecodeError, Exception) as e:
            return f"unreadable ({e})"

    return None


def print_summary(results: list[dict]):
    """Print a summary table of all processed files."""
    total_articles = 0
    ok_count = 0
    skip_count = 0
    fail_count = 0

    print("\n" + "=" * 80)
    print(f"{'File':<42} {'Domain':<14} {'Articles':<10} Status")
    print("=" * 80)

    for r in results:
        status = r.get("status", "?")
        articles = r.get("articles", 0)
        file_stem = r.get("file", "")
        domain = r.get("domain", "")

        if status == "ok":
            ok_count += 1
            total_articles += articles
        elif status == "skipped":
            skip_count += 1
        else:
            fail_count += 1

        print(
            f"{file_stem:<42} {domain:<14} {articles:<10} {status}"
        )

    print("=" * 80)
    print(f"  OK: {ok_count}  |  Skipped: {skip_count}  |  Failed: {fail_count}")
    print(f"  Total articles embedded: {total_articles}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Embed all parsed legal articles into the vector database.",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=None,
        help="Only process these domains (e.g. civil commercial). "
             f"Valid: {', '.join(sorted(VALID_DOMAINS))}",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size (default: 32).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Truncate articles to N chars before embedding "
             "(prevents VRAM OOM on remote server; default: 2000).",
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Delete existing chunks for each source before inserting.",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Never delete existing chunks (overrides --clear-existing for safety).",
    )
    parser.add_argument(
        "--skip-empty",
        action="store_true",
        help="Skip JSON files that contain 0 articles.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually inserting.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO).",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )

    processed_dir = Path(PROCESSED_DIR)
    if not processed_dir.is_dir():
        logger.error("Processed data directory not found: %s", processed_dir)
        sys.exit(1)

    # Resolve clear_existing flag
    if args.no_clear:
        clear_existing = False
    else:
        clear_existing = args.clear_existing

    # Discover article files
    files = discover_article_files(processed_dir, domains=args.domains)

    if not files:
        logger.warning("No .articles.json files found in %s", processed_dir)
        print("No article files to process.")
        return

    logger.info(
        "Found %d article file(s) across %d domain(s).",
        len(files),
        len({d for _, d in files}),
    )

    # ── Dry-run ──────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n[DRY RUN] Would process the following files:\n")
        print(f"{'#':<4} {'File':<50} {'Domain':<14} {'Articles':<10}")
        print("-" * 80)
        for idx, (jf, domain) in enumerate(files, 1):
            # Quick article count
            try:
                import json
                with open(jf, "r", encoding="utf-8") as f:
                    articles = json.load(f)
                count = len(articles)
            except Exception:
                count = 0
            print(f"{idx:<4} {jf.name:<50} {domain:<14} {count:<10}")
        print(f"\nWould embed {len(files)} file(s) "
              f"(clear_existing={clear_existing}, "
              f"batch_size={args.batch_size}, "
              f"max_chars={args.max_chars or 2000})")
        return

    # ── Process each file ────────────────────────────────────────────────────
    results: list[dict] = []

    for idx, (json_path, domain) in enumerate(files, 1):
        reason = should_skip_file(json_path, skip_empty=args.skip_empty)
        if reason:
            logger.info("[%d/%d] SKIP %s — %s", idx,
                        len(files), json_path.name, reason)
            results.append({
                "file": json_path.stem,
                "domain": domain,
                "articles": 0,
                "status": f"skipped ({reason})",
            })
            continue

        logger.info(
            "[%d/%d] Ingesting %s (domain=%s) …",
            idx, len(files), json_path.name, domain,
        )

        try:
            n = ingest_articles(
                json_path=json_path,
                domain=domain,
                source_file=json_path.stem,
                law_name=None,
                extraction_method="pipeline",
                batch_size=args.batch_size,
                max_chars=args.max_chars,
                clear_existing=clear_existing,
            )
            results.append({
                "file": json_path.stem,
                "domain": domain,
                "articles": n,
                "status": "ok",
            })
            logger.info("  ✓ %d articles ingested.", n)

        except Exception as e:
            logger.exception("  ✗ Failed to ingest %s", json_path.name)
            results.append({
                "file": json_path.stem,
                "domain": domain,
                "articles": 0,
                "status": f"failed: {e}",
            })

    print_summary(results)


if __name__ == "__main__":
    main()
