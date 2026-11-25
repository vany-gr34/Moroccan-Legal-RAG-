"""Structure Parser for Moroccan Legal Texts.

Extracts hierarchical structure (books, sections, chapters, articles)
from normalized Arabic legal text.

Falls back to heading-level chunking when no individual articles are found.
"""

import re
from typing import List, Dict, Optional
import json


def _extract_heading_number(heading_text: str) -> str:
    """Extract a numeric or ordinal identifier from a heading like 'الباب الاول' or 'الفصل 18'."""
    text = heading_text.strip()
    # Try Arabic ordinals (الاول → 1, الثاني → 2, etc.)
    arabic_ordinals = {
        'الاول': '1', 'الأول': '1', 'اول': '1', 'أول': '1',
        'الثاني': '2', 'الثانى': '2', 'ثاني': '2', 'ثانى': '2',
        'الثالث': '3', 'ثالث': '3',
        'الرابع': '4', 'رابع': '4',
        'الخامس': '5', 'خامس': '5',
        'السادس': '6', 'سادس': '6',
        'السابع': '7', 'سابع': '7',
        'الثامن': '8', 'ثامن': '8',
        'التاسع': '9', 'تاسع': '9',
        'العاشر': '10', 'عاشر': '10',
    }
    # Try to find a digit first
    digit_match = re.search(r'(\d+)', text)
    if digit_match:
        return digit_match.group(1)
    # Try Arabic ordinal words
    for word, num in arabic_ordinals.items():
        if word in text:
            return num
    # Fallback: hash the text for a short identifier
    return str(hash(text) % 10000)


class LegalStructureParser:
    """Parses normalized legal text into structured articles with hierarchy.

    Strategy:
        1. Try to extract individual articles (المادة / مادة / الفصل as article).
        2. If none found, fall back to heading-level chunks (one per الباب/الفصل/الفرع/etc).
        3. If no headings either, create one chunk from the entire text.
    """

    # Heading patterns (must appear at START of a line)
    HEADING_PATTERNS = [
        (re.compile(r'^(?:الكتاب)\s+(\w+)?\s*(?::|\.)?\s*(.*)'), 'book'),
        (re.compile(r'^(?:الباب)\s+(\w+)?\s*(?::|\.)?\s*(.*)'), 'section'),
        (re.compile(r'^(?:القسم)\s+(\w+)?\s*(?::|\.)?\s*(.*)'), 'subsection'),
        (re.compile(r'^(?:الفصل)\s+(\w+)?\s*(?::|\.)?\s*(.*)'), 'chapter'),
        (re.compile(r'^(?:الفرع)\s+(\w+)?\s*(?::|\.)?\s*(.*)'), 'branch'),
    ]

    # Article patterns — expanded to catch more variants
    _ARTICLE_PREFIX = r'(?:المادة|مادة|م\.|الفصل)'
    _ARTICLE_NUMBER = r'(?:\d+(?:[-\u2013]\d+(?:/\d+)?)?)'

    ARTICLE_PATTERN = re.compile(
        r'^' + _ARTICLE_PREFIX + r'\s*[:\-–\.]?\s*' + _ARTICLE_NUMBER + r'\b'
    )

    # Also match reversed order: "1-المادة"
    ARTICLE_REVERSE_PATTERN = re.compile(
        r'^' + _ARTICLE_NUMBER + r'\s*[:\-–\.]?\s*' + _ARTICLE_PREFIX + r'\b'
    )

    # Footnote pattern
    FOOTNOTE_PATTERN = re.compile(
        r'^[-–]\d{1,3}\s+تم\s+|^\(?\d+\)\s*(?:تم|المادة|انظر)')

    def __init__(self, domain: str = None, law_name: str = None):
        self.domain = domain
        self.law_name = law_name

    def _extract_article_number(self, stripped: str) -> Optional[str]:
        """Extract article number from a line like 'المادة 147' or 'مادة 1-42'."""
        for pattern in [self.ARTICLE_PATTERN, self.ARTICLE_REVERSE_PATTERN]:
            match = pattern.match(stripped)
            if match:
                nums = re.findall(
                    r'\d+(?:[-\u2013]\d+(?:/\d+)?)?', match.group(0))
                return nums[0] if nums else match.group(0)
        return None

    def _extract_law_name_from_text(self, text: str) -> Optional[str]:
        """Try to extract the law name from the beginning of the text."""
        patterns = [
            r'(القانون رقم [\d\.]+ .+?)(?:\n|\.)',
            r'(مدونة [\u0600-\u06FF]+)',
            r'(ظهير شريف رقم [\d\.]+ .+?)(?:\n|\.)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text[:2000])
            if match:
                return match.group(1).strip()
        return None

    # ── Detect heading type for a line ────────────────────────────────────

    def _match_heading(self, stripped: str) -> tuple[Optional[str], Optional[str]]:
        """Return (heading_type, full_heading_text) or (None, None)."""
        if len(stripped) > 150:
            return None, None
        for pattern, htype in self.HEADING_PATTERNS:
            if pattern.match(stripped):
                return htype, stripped
        return None, None

    # ── Article-level parsing ─────────────────────────────────────────────

    def _parse_articles(self, lines: list[str]) -> List[Dict]:
        """Parse individual articles (المادة / مادة). Returns list of article dicts."""
        articles = []
        current_context = {
            'book': None, 'section': None, 'subsection': None,
            'chapter': None, 'branch': None
        }
        current_article_num = None
        current_article_lines = []
        current_footnotes = []

        def flush():
            nonlocal current_article_num, current_article_lines, current_footnotes
            if current_article_num is not None and current_article_lines:
                article_text = ' '.join(current_article_lines).strip()
                articles.append({
                    'article_number': current_article_num,
                    'text': article_text,
                    'footnotes': current_footnotes if current_footnotes else [],
                    'context': dict(current_context),
                    'law_name': self.law_name,
                    'domain': self.domain,
                })
            current_article_num = None
            current_article_lines = []
            current_footnotes = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if self.FOOTNOTE_PATTERN.match(stripped):
                current_footnotes.append(stripped)
                continue

            heading_type, heading_text = self._match_heading(stripped)
            if heading_type:
                flush()
                current_context[heading_type] = heading_text
                levels = ['book', 'section', 'subsection', 'chapter', 'branch']
                idx = levels.index(heading_type)
                for lower in levels[idx + 1:]:
                    current_context[lower] = None
                continue

            art_num = self._extract_article_number(stripped)
            if art_num:
                flush()
                current_article_num = art_num
                rest = self.ARTICLE_PATTERN.sub('', stripped, count=1).strip()
                rest = self.ARTICLE_REVERSE_PATTERN.sub(
                    '', rest, count=1).strip()
                if rest:
                    current_article_lines.append(rest)
                continue

            if current_article_num is not None:
                current_article_lines.append(stripped)

        flush()

        # Merge adjacent duplicates
        merged = []
        for art in articles:
            if merged and merged[-1]['article_number'] == art['article_number']:
                merged[-1]['text'] += ' ' + art['text']
                merged[-1]['footnotes'].extend(art['footnotes'])
            else:
                merged.append(art)
        return merged

    # ── Heading-level fallback ────────────────────────────────────────────

    def _parse_heading_chunks(self, lines: list[str]) -> List[Dict]:
        """Create one chunk per heading with all text under it."""
        chunks = []
        current_context = {
            'book': None, 'section': None, 'subsection': None,
            'chapter': None, 'branch': None
        }
        current_lines: list[str] = []
        current_heading_type: Optional[str] = None
        current_heading_text: Optional[str] = None
        chunk_idx = 0

        def flush_chunk():
            nonlocal current_lines, chunk_idx
            text = ' '.join(current_lines).strip()
            if text:
                # Build a meaningful article_number from the context
                if current_heading_type and current_heading_text:
                    num = _extract_heading_number(current_heading_text)
                    art_num = f"{current_heading_type}-{num}"
                else:
                    chunk_idx += 1
                    art_num = f"chunk-{chunk_idx}"

                chunks.append({
                    'article_number': art_num,
                    'text': text,
                    'footnotes': [],
                    'context': dict(current_context),
                    'law_name': self.law_name,
                    'domain': self.domain,
                })
            current_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if self.FOOTNOTE_PATTERN.match(stripped):
                continue

            heading_type, heading_text = self._match_heading(stripped)
            if heading_type:
                flush_chunk()
                current_heading_type = heading_type
                current_heading_text = heading_text
                current_context[heading_type] = heading_text
                levels = ['book', 'section', 'subsection', 'chapter', 'branch']
                idx = levels.index(heading_type)
                for lower in levels[idx + 1:]:
                    current_context[lower] = None
                continue

            # Regular content line
            current_lines.append(stripped)

        flush_chunk()
        return chunks

    # ── Main parse ────────────────────────────────────────────────────────

    def parse(self, full_text: str) -> List[Dict]:
        """Parse text into structured articles with heading-level fallback."""
        if not full_text:
            return []

        if not self.law_name:
            self.law_name = self._extract_law_name_from_text(full_text)

        lines = full_text.splitlines()

        # Strategy 1: Try article-level parsing
        articles = self._parse_articles(lines)

        if articles:
            return articles

        # Strategy 2: Heading-level chunks
        chunks = self._parse_heading_chunks(lines)
        if chunks:
            return chunks

        # Strategy 3: One big chunk for the entire text
        clean = ' '.join(
            l.strip() for l in lines if l.strip()
            and not self.FOOTNOTE_PATTERN.match(l.strip())
        )
        if clean:
            return [{
                'article_number': 'full-text',
                'text': clean,
                'footnotes': [],
                'context': {
                    'book': None, 'section': None, 'subsection': None,
                    'chapter': None, 'branch': None,
                },
                'law_name': self.law_name,
                'domain': self.domain,
            }]

        return []


def parse_normalized_text_to_json(
    normalized_text: str,
    domain: str = None,
    law_name: str = None,
    output_path: str = None
) -> List[Dict]:
    parser = LegalStructureParser(domain=domain, law_name=law_name)
    articles = parser.parse(normalized_text)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
    return articles
