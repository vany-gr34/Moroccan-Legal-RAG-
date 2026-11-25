#!/usr/bin/env python3
"""
extract_legal.py — Universal Arabic Legal Code Extractor (LiteParse Edition)
=============================================================================

Extracts the full hierarchy of an Arabic legal PDF into structured JSON/JSONL/TXT.

Uses LiteParse for fast, local PDF parsing with:
- Spatial text layout preservation
- Built-in OCR support for scanned documents  
- Bounding box extraction for each text line
- No cloud dependencies, no API keys

Hierarchy levels supported (ordered from highest to lowest):
  الكتاب   (Book)
  الجزء    (Part)
  القسم    (Section)
  الباب    (Chapter)
  الفصل   (Title/Division) — used in Penal Code instead of مادة
  الفرع    (Sub-chapter)
  القسم الفرعي  (Sub-section)
  المادة / الفصل (Article)

Each article node carries the full breadcrumb of its ancestor headings.

Requires: 
    pip install liteparse

Usage:
    python extract_legal.py --pdf code_route.pdf
    python extract_legal.py --pdf code_route.pdf --format jsonl --out articles.jsonl
    python extract_legal.py --pdf code_route.pdf --format txt
    python extract_legal.py --pdf code_route.pdf --start-page 10 --end-page 80 --verbose
    python extract_legal.py --pdf scanned_penal_code.pdf --ocr --verbose

Outputs (JSON):
    [
      {
        "article": "1",
        "page": 3,
        "breadcrumb": {
          "book":        "الكتاب الأول — شروط السير على الطريق العمومية",
          "section":     "القسم الأول — رخصة السياقة", 
          "chapter":     "الباب الأول — إلزامية رخصة السياقة"
        },
        "text": "لا يجوز لأي شخص …",
        "bbox": {"x": 120, "y": 450, "width": 380, "height": 24}  # optional
      },
      …
    ]
"""

import re
import json
import argparse
import sys
from pathlib import Path
from copy import deepcopy

# ─────────────────────────────────────────────────────────────
# Dependency check: LiteParse
# ─────────────────────────────────────────────────────────────
try:
    from liteparse import LiteParse
except ImportError:
    sys.exit(
        "❌  'liteparse' not found.\n"
        "    Install with: pip install liteparse\n"
        "    Or see: https://github.com/liteparse/liteparse"
    )


# ─────────────────────────────────────────────────────────────
# Unicode bidi cleanup & Normalization
# ─────────────────────────────────────────────────────────────
_BIDI = '\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff'
_BIDI_TABLE = str.maketrans('', '', _BIDI)

# Map Eastern Arabic Numerals to Western for consistent parsing
EASTERN_TO_WESTERN = {
    ord('٠'): '0', ord('١'): '1', ord('٢'): '2', ord('٣'): '3', ord('٤'): '4',
    ord('٥'): '5', ord('٦'): '6', ord('٧'): '7', ord('٨'): '8', ord('٩'): '9',
    ord('٫'): '.', ord('٬'): ',',
}


def normalize_digits(text: str) -> str:
    """Convert Eastern Arabic Numerals to Western."""
    return text.translate(EASTERN_TO_WESTERN)


def strip_bidi(text: str) -> str:
    """Remove bidirectional control characters."""
    return text.translate(_BIDI_TABLE)


def clean(line: str) -> str:
    """Clean a line of text: strip bidi, normalize digits, collapse whitespace."""
    line = strip_bidi(line)
    line = normalize_digits(line)
    return re.sub(r'[ \t]+', ' ', line).strip()


# ─────────────────────────────────────────────────────────────
# Arabic ordinal → integer (for sorting headers)
# ─────────────────────────────────────────────────────────────
AR_ORDINAL = {
    'الأول': 1,   'الاول': 1,   'أول': 1,
    'الثاني': 2,  'الثانى': 2,  'ثاني': 2,
    'الثالث': 3,  'ثالث': 3,
    'الرابع': 4,  'رابع': 4,
    'الخامس': 5,  'خامس': 5,
    'السادس': 6,  'سادس': 6,
    'السابع': 7,  'سابع': 7,
    'الثامن': 8,  'ثامن': 8,
    'التاسع': 9,  'تاسع': 9,
    'العاشر': 10, 'عاشر': 10,
    'الحادي عشر': 11, 'الحادى عشر': 11,
    'الثاني عشر': 12, 'الثانى عشر': 12,

    # Feminine forms (common in legal Arabic)
    'الأولى': 1,  'الاولى': 1,
    'الثانية': 2, 'الثانيه': 2,
    'الثالثة': 3, 'الثالثه': 3,
    'الرابعة': 4, 'الرابعه': 4,
    'الخامسة': 5, 'الخامسه': 5,
    'السادسة': 6, 'السادسه': 6,
    'السابعة': 7, 'السابعه': 7,
    'الثامنة': 8, 'الثامنه': 8,
    'التاسعة': 9, 'التاسعه': 9,
    'العاشرة': 10, 'العاشرة': 10,
}


def ordinal_sort_key(ordinal: str) -> int:
    """Return an integer sort key for an Arabic ordinal string."""
    ordinal = ordinal.strip()
    if ordinal in AR_ORDINAL:
        return AR_ORDINAL[ordinal]

    # Check for compound ordinals
    for key, val in AR_ORDINAL.items():
        if key in ordinal:
            return val

    # Try digits
    m = re.search(r'\d+', ordinal)
    return int(m.group()) if m else 99


# ─────────────────────────────────────────────────────────────
# Hierarchy definition
# ─────────────────────────────────────────────────────────────
# Order matters: Longer/more specific phrases first.
# Levels: 6 (Book) > 5 (Part) > 4 (Title/Section) > 3 (Chapter) > 2 (Sub-chapter) > 0 (Article)

HIERARCHY_TOKENS = [
    ('الكتاب',        6, 'book'),
    ('الجزء',         5, 'part'),
    # Common in Moroccan codes between Part and Chapter
    ('العنوان',       4, 'title'),
    ('القسم',         4, 'section'),
    ('الباب',         3, 'chapter'),
    # In Penal Code, 'Fasl' is often a division, NOT an article
    ('الفصل',         2, 'sub_chapter'),
    # The actual Article (with definite article)
    ('المادة',        0, 'article'),
    ('املادة',        0, 'article'),     # Ligature variant
    # Bare form (common in Moroccan Penal Code)
    ('مادة',          0, 'article'),
]

# Regex to detect structural headers (Keyword + Ordinal Number/Word)
STRUCTURAL_HEADER_RE = re.compile(
    r'^(الكتاب|الجزء|العنوان|القسم|الباب|الفصل)\s+'
    r'(?:'
    r'(?:الأول|الاول|الأولى|الثاني|الثانى|الثانية|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|الحادي عشر|الثاني عشر)'
    r'|'
    r'(?:\d+)'
    r')'
)


# ─────────────────────────────────────────────────────────────
# Article number parsing
# ─────────────────────────────────────────────────────────────
MAX_ARTICLE_NUM = 1000


def parse_article_number(token: str) -> tuple[int | None, str | None]:
    """
    Parse the number portion after 'المادة'.
    Handles: plain integers, hyphenated sub-articles, footnote-concatenated numbers.
    Returns (None, None) if not parseable.
    """
    token = token.strip()
    if not token:
        return None, None

    # Remove common suffixes
    token = token.rstrip(':').rstrip('-').strip()

    # Try direct integer conversion
    try:
        n = int(token)
        if 1 <= n <= MAX_ARTICLE_NUM:
            return n, token
    except ValueError:
        pass

    # Handle "Mada X bis" variants - extract digit
    m = re.search(r'(\d+)', token)
    if m:
        n = int(m.group(1))
        if 1 <= n <= MAX_ARTICLE_NUM:
            return n, token

    return None, None


# ─────────────────────────────────────────────────────────────
# Line classifier
# ─────────────────────────────────────────────────────────────
NOISE_FRAGMENTS = [
    'وحدة الدراسات', 'رئاسة النيابة', 'اململكة', 'المملكة المغربية',
    'وحدة التوئتق', 'توئتق', 'الأمانة العامة للحكومة', 'امانة عامة',
    'الأمانة العامة', 'الامانة العامة', 'الجريدة الرسمية', 'عدد',
    'مرسوم', 'ظهير شريف', 'قانون رقم', 'صفحة', 'ص', '١', '٢', '٣'
]


def is_noise(line: str) -> bool:
    """Check if a line is noise (headers, footers, page numbers)."""
    if not line or len(line.strip()) < 3:
        return True
    # Ignore pure page numbers
    if re.match(r'^\d+$', line.strip()):
        return True
    for frag in NOISE_FRAGMENTS:
        if frag in line:
            return True
    return False


def classify_line(line: str) -> tuple[str | None, int, str | None, str | None]:
    """
    Classify a cleaned line.
    Returns: (keyword, level, json_key, remainder_text)
    Returns (None, -1, None, None) if not a hierarchy line.
    """
    if is_noise(line):
        return None, -1, None, None

    # 1. Check for Structural Headers (Book, Part, Chapter, etc.)
    m_struct = STRUCTURAL_HEADER_RE.match(line)
    if m_struct:
        keyword = m_struct.group(1)
        for k, lvl, key in HIERARCHY_TOKENS:
            if k == keyword:
                remainder = line[len(keyword):].strip()
                return keyword, lvl, key, remainder

    # 2. Check for Articles (المادة / مادة)
    if line.startswith('المادة') or line.startswith('املادة') or line.startswith('مادة'):
        if line.startswith('مادة') and not line.startswith('المادة'):
            keyword = 'مادة'
        elif line.startswith('املادة'):
            keyword = 'املادة'
        else:
            keyword = 'المادة'
        remainder = line[len(keyword):].strip()

        # Verify remainder looks like a number or ordinal
        if remainder and (remainder[0].isdigit() or remainder.startswith(('الأول', 'الثاني'))):
            return keyword, 0, 'article', remainder

    # 3. Fallback for simple tokens
    for token, level, key in HIERARCHY_TOKENS:
        if line == token:
            return token, level, key, ""

    return None, -1, None, None


# ─────────────────────────────────────────────────────────────
# PDF extraction using LiteParse
# ─────────────────────────────────────────────────────────────
def extract_text_liteparse(pdf_path: str | bytes, first_page: int = 1,
                           last_page: int | None = None, use_ocr: bool = False,
                           verbose: bool = False) -> str:
    """
    Extract text from PDF using LiteParse with spatial layout preservation.

    Args:
        pdf_path: Path to the PDF file or bytes content
        first_page: First page to parse (1-indexed)
        last_page: Last page to parse (None for end)
        use_ocr: Enable OCR for scanned documents
        verbose: Print progress information

    Returns:
        Raw text with page separators for downstream processing
    """
    try:
        # Configure parser
        parser = LiteParse(
            ocr_enabled=use_ocr,
            ocr_language='ara',  # Arabic language for OCR
            dpi=300,
        )

        if verbose:
            print(
                f"🔍  Parsing with LiteParse: {pdf_path if isinstance(pdf_path, str) else '<bytes>'}")
            if use_ocr:
                print("📷  OCR enabled for scanned document support")

        # Parse the document (handles both path and bytes)
        result = parser.parse(pdf_path)

        # Build text output with page markers (form-feed style for compatibility)
        output_lines = []

        for page in result.pages:
            # Skip pages outside requested range
            if page.page_num < first_page:
                continue
            if last_page and page.page_num > last_page:
                break

            # Add page separator (form-feed character for pdftotext compatibility)
            if page.page_num > first_page:
                output_lines.append('\f')

            # Extract text items sorted by vertical position (top-to-bottom reading order)
            # LiteParse returns text_items with spatial info; we sort by y-coordinate
            text_items = sorted(
                page.text_items,
                key=lambda item: (item.bbox.y if hasattr(item, 'bbox') else 0,
                                  item.bbox.x if hasattr(item, 'bbox') else 0)
            )

            for item in text_items:
                text = item.text.strip() if hasattr(item, 'text') else str(item).strip()
                if text:  # Skip empty items
                    output_lines.append(text)

        if verbose:
            total_lines = len(output_lines)
            print(
                f"📝  Extracted ~{total_lines:,} lines from {len(result.pages)} pages")

        return '\n'.join(output_lines)

    except Exception as e:
        error_msg = str(e)
        if "OCR" in error_msg and not use_ocr:
            print(f"⚠️  Warning: Document may contain scanned images.")
            print(f"    Try re-running with --ocr flag to enable OCR.")
        sys.exit(f"❌  LiteParse error:\n{error_msg}")


# ─────────────────────────────────────────────────────────────
# Breadcrumb state tracker
# ─────────────────────────────────────────────────────────────
class BreadcrumbTracker:
    """Tracks the current position in the document hierarchy."""

    def __init__(self):
        # level → (json_key, label)
        self._crumbs: dict[int, tuple[str, str]] = {}

    def update(self, level: int, json_key: str, label: str):
        """Set the breadcrumb for `level` and clear all lower structural levels."""
        self._crumbs[level] = (json_key, label)
        # Clear everything at strictly lower levels (children)
        keys_to_delete = [l for l in self._crumbs.keys() if l < level]
        for l in keys_to_delete:
            del self._crumbs[l]

    def snapshot(self) -> dict[str, str]:
        """Return current breadcrumb dict (key → label), excluding the article level."""
        result = {}
        # Sort by level descending so Book comes first
        for level in sorted(self._crumbs.keys(), reverse=True):
            json_key, label = self._crumbs[level]
            if level > 0:   # skip the article itself
                result[json_key] = label
        return result


# ─────────────────────────────────────────────────────────────
# Core parser
# ─────────────────────────────────────────────────────────────
def parse(raw_text: str, verbose: bool = False) -> list[dict]:
    """
    Walk through the raw text and build a list of article dicts,
    each carrying a breadcrumb snapshot of the surrounding hierarchy.
    """
    articles: dict[int, dict] = {}
    breadcrumb = BreadcrumbTracker()

    current_key:   int | None = None
    current_label: str | None = None
    current_body:  list[str] = []
    current_page:  int = 1
    current_crumb: dict = {}

    # State machine for headers that span two lines
    pending_header: tuple | None = None

    def flush_article():
        nonlocal current_key, current_label, current_body, current_crumb
        if current_key is None:
            return

        text = '\n'.join(l for l in current_body if l).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)

        if not text:
            if verbose:
                print(f"  ⚠️ Empty article {current_label}")
            return

        if current_key in articles:
            # Append if duplicate key found
            articles[current_key]['text'] += '\n' + text
        else:
            articles[current_key] = {
                'article':    current_label,
                '_sort_key':  current_key,
                'page':       current_page,
                'breadcrumb': current_crumb,
                'text':       text,
            }
            if verbose:
                bc_str = ' > '.join(
                    articles[current_key]['breadcrumb'].values())
                print(
                    f'  ✅ المادة {current_label:>6} (p.{current_page}) [{bc_str}]')

    lines = raw_text.splitlines()
    for i, raw_line in enumerate(lines):
        # Track pages via form-feed character
        if '\f' in raw_line:
            current_page += raw_line.count('\f')
            raw_line = raw_line.replace('\f', '')

        line = clean(raw_line)

        # Skip noise
        if is_noise(line):
            continue

        kw, level, json_key, remainder = classify_line(line)

        if kw is None:
            # --- Body Text ---
            if pending_header is not None:
                # The previous line was a header keyword, this line is its Title
                ph_level, ph_key, ph_base_label = pending_header
                full_label = f'{ph_base_label} : {line}'
                breadcrumb.update(ph_level, ph_key, full_label)
                pending_header = None
            elif current_key is not None:
                # Add to current article body
                current_body.append(line)
            continue

        # --- Structural Element Found ---

        if level == 0:
            # It's an Article (المادة)
            sort_key, label = parse_article_number(remainder)

            if sort_key is None:
                # Failed to parse number - might be ordinal
                ord_key = ordinal_sort_key(remainder)
                if ord_key != 99:
                    sort_key = ord_key
                    label = remainder
                else:
                    # Not an article number, treat as body text if inside an article
                    if current_key is not None:
                        current_body.append(line)
                    continue

            # Flush previous article
            flush_article()

            # Start new article
            current_key = sort_key
            current_label = label
            current_body = []
            current_crumb = breadcrumb.snapshot()
            pending_header = None

        else:
            # It's a Header (Book, Chapter, etc.)
            flush_article()
            current_key = None
            current_body = []

            base_label = f'{kw} {remainder}'.strip()

            # Check if the title is on the same line
            if ':' in remainder or ' - ' in remainder or len(remainder.split()) > 2:
                # Likely inline title
                breadcrumb.update(level, json_key, base_label)
                pending_header = None
            else:
                # Title likely on next line
                pending_header = (level, json_key, base_label)

    # Flush last article
    flush_article()

    return sorted(articles.values(), key=lambda a: a['_sort_key'])


# ─────────────────────────────────────────────────────────────
# Post-processing
# ─────────────────────────────────────────────────────────────
def post_process(articles: list[dict]) -> list[dict]:
    """Clean and finalize article extraction results."""
    result = []
    for art in articles:
        text = art['text']
        if text:
            # Strip isolated footnote numbers at line ends
            text = re.sub(r'(?<!\d)(\d{1,2})(?!\d)\s*$',
                          '', text, flags=re.MULTILINE)
            text = re.sub(r'\n{3,}', '\n\n', text).strip()

            out = {
                'article':    art['article'],
                'page':       art['page'],
                'breadcrumb': art['breadcrumb'],
                'text':       text,
            }
            result.append(out)
    return result


# ─────────────────────────────────────────────────────────────
# Output writers
# ─────────────────────────────────────────────────────────────
def write_json(articles: list[dict], out_path: str):
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f'✅  Saved {len(articles)} articles  →  {out_path}')


def write_jsonl(articles: list[dict], out_path: str):
    with open(out_path, 'w', encoding='utf-8') as f:
        for art in articles:
            f.write(json.dumps(art, ensure_ascii=False) + '\n')
    print(f'✅  Saved {len(articles)} articles (JSONL)  →  {out_path}')


def write_txt(articles: list[dict], out_path: str):
    sep = '═' * 70
    with open(out_path, 'w', encoding='utf-8') as f:
        for art in articles:
            f.write(f'{sep}\n')
            bc = art['breadcrumb']
            for key in ['book', 'part', 'title', 'section', 'chapter', 'sub_chapter']:
                if key in bc:
                    f.write(f'  {bc[key]}\n')
            f.write(f'  المادة {art["article"]}   (صفحة {art["page"]})\n')
            f.write(f'{sep}\n')
            f.write(art['text'] + '\n\n')
    print(f'✅  Saved {len(articles)} articles (TXT)  →  {out_path}')


def print_hierarchy_tree(articles: list[dict]):
    """Print a compact tree view of the document structure."""
    print('\n📂  Document hierarchy tree (structural nodes only):')
    seen = []
    for art in articles:
        bc = art['breadcrumb']
        crumb_vals = list(bc.values())
        for depth, val in enumerate(crumb_vals):
            if val not in seen:
                seen.append(val)
                indent = '  ' + '  ' * depth
                marker = '├─' if depth < len(crumb_vals) - 1 else '└─'
                print(f'{indent}{marker} {val}')
    print()


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Extract hierarchical legal articles from Arabic PDFs using LiteParse'
    )
    parser.add_argument('--pdf',        required=True, help='Input PDF path')
    parser.add_argument(
        '--out',        default='articles.json', help='Output file path')
    parser.add_argument('--format',     choices=['json', 'jsonl', 'txt'], default='json',
                        help='Output format: json | jsonl | txt  (default: json)')
    parser.add_argument('--start-page', type=int,
                        default=1, help='First page to parse')
    parser.add_argument('--end-page',   type=int,
                        default=None, help='Last page to parse')
    parser.add_argument('--verbose',    action='store_true',
                        help='Print progress')
    parser.add_argument('--tree',       action='store_true',
                        help='Print hierarchy tree')
    parser.add_argument('--ocr',        action='store_true',
                        help='Enable OCR for scanned/image-based PDFs')
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(f'❌  PDF not found: {pdf_path}')

    print(f'🔍  Processing: {pdf_path.name}')
    print(f'    Pages: {args.start_page} – {args.end_page or "end"}')
    if args.ocr:
        print('📷  OCR mode enabled')

    # Extract text using LiteParse
    raw = extract_text_liteparse(
        str(pdf_path),
        first_page=args.start_page,
        last_page=args.end_page,
        use_ocr=args.ocr,
        verbose=args.verbose
    )

    if not raw.strip():
        sys.exit(
            "❌  Extracted text is empty. Check if PDF is valid or try --ocr flag.")

    # Parse articles
    articles = parse(raw, verbose=args.verbose)
    print(f'🔎  Found {len(articles)} articles (pre-cleanup)')

    articles = post_process(articles)
    print(f'✨  Final clean articles: {len(articles)}')

    if not articles:
        print('⚠️  No articles found. Try checking:')
        print('    • Is the PDF text-based or scanned? (try --ocr)')
        print('    • Does the document use "المادة" for articles?')
        print('    • Check the first 20 lines of raw output:')
        for l in raw.splitlines()[:20]:
            print(f'      {repr(l)[:100]}')
        sys.exit(1)

    # Sample output
    if args.verbose:
        print('\n─── Sample (first 3 articles) ──────────────────────────────────────')
        for art in articles[:3]:
            bc = ' > '.join(art['breadcrumb'].values())
            preview = art['text'][:120].replace('\n', ' ')
            print(f'  [{bc}]')
            print(f'  المادة {art["article"]} (p.{art["page"]}): {preview}…')
            print()
        print('────────────────────────────────────────────────────────────────────\n')

    if args.tree:
        print_hierarchy_tree(articles)

    # Write output
    if args.format == 'json':
        write_json(articles, args.out)
    elif args.format == 'jsonl':
        write_jsonl(articles, args.out)
    else:
        write_txt(articles, args.out)


if __name__ == '__main__':
    main()
