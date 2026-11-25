#!/usr/bin/env python3
"""Parse a normalized legal text file into structured JSON articles."""

from src.core.structure import parse_normalized_text_to_json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/parse_legal_structure.py <normalized.txt> [--domain DOMAIN] [--law-name 'Law Name']")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    # Optional domain and law name from command line
    domain = None
    law_name = None
    for i, arg in enumerate(sys.argv):
        if arg == '--domain' and i + 1 < len(sys.argv):
            domain = sys.argv[i + 1]
        if arg == '--law-name' and i + 1 < len(sys.argv):
            law_name = sys.argv[i + 1]

    text = input_path.read_text(encoding='utf-8')
    output_path = input_path.with_suffix('.articles.json')

    articles = parse_normalized_text_to_json(
        text,
        domain=domain,
        law_name=law_name,
        output_path=str(output_path)
    )

    print(f"Extracted {len(articles)} articles.")
    print(f"Saved to: {output_path}")

    # Print a sample
    if articles:
        print("\nFirst article:")
        print(json.dumps(articles[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import json
    main()
