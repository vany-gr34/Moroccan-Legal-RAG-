"""
Arabic-aware tokenizer for BM25 retrieval.

Provides proper Arabic word segmentation that goes beyond naive
split-on-spaces.  Uses the project's existing ArabicNormalizer
for character-level standardization and adds:
  - Stop-word removal
  - Minimum token length filtering
  - Digit normalization
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# ── Common Arabic stop words (legal domain) ────────────────────────────────

ARABIC_STOP_WORDS = {
    # Articles & particles
    "ال", "في", "من", "على", "الى", "عن", "او", "ام", "ثم",
    "حتى", "لا", "ما", "لم", "لن", "قد", "هل", "هو", "هي",
    "هم", "هن", "هذا", "هذه", "هؤلاء", "ذلك", "تلك",
    "الذي", "التي", "الذين", "اللواتي", "اللذان", "اللتان",
    "الذوات", "اللوائي",
    # Prepositions & conjunctions
    "مع", "بين", "بعد", "قبل", "عند", "دون", "خلال", "اثناء",
    "حول", "نحو", "ضد", "فوق", "تحت", "امام", "خلف",
    "ك", "ب", "ل", "ف", "و",
    # Negation & condition
    "غير", "اذا", "ان", "كل", "بعض", "اي", "اية",
    # Common legal words (too frequent to be discriminative)
    "المادة", "المواد", "القانون", "القوانين", "الفصل", "الفصول",
    "الباب", "الكتاب", "القسم", "البند",
    "منها", "فيها", "عليها", "بها", "لها", "فيه",
    "يكون", "تكون", "كان", "كانت", "يتم",
}

# ── Simple Arabic tokenizer ─────────────────────────────────────────────────

# Arabic word characters (includes Arabic letters, digits, hamza variants)
_ARABIC_WORD = re.compile(r"[\u0621-\u063A\u0641-\u064A\u0660-\u0669]+")


def tokenize_arabic(
    text: str,
    remove_stop_words: bool = True,
    min_token_len: int = 2,
) -> List[str]:
    """Tokenize Arabic text for BM25 indexing.

    Steps:
    1. Extract Arabic word tokens (skip punctuation, Latin, numbers)
    2. Optionally remove common stop words
    3. Filter short tokens (< min_token_len)

    Args:
        text: Raw Arabic text (should already be normalized).
        remove_stop_words: If True, drop common Arabic stop words.
        min_token_len: Minimum token length to keep.

    Returns:
        List of Arabic word tokens ready for BM25 indexing.
    """
    if not text:
        return []

    tokens = _ARABIC_WORD.findall(text)

    if remove_stop_words:
        tokens = [t for t in tokens if t not in ARABIC_STOP_WORDS]

    if min_token_len > 1:
        tokens = [t for t in tokens if len(t) >= min_token_len]

    return tokens


def tokenize_for_bm25(text: str) -> List[str]:
    """Quick tokenize without heavy normalization (assumes pre-normalized text)."""
    return tokenize_arabic(text, remove_stop_words=True, min_token_len=2)


def normalize_and_tokenize(
    text: str,
    normalizer=None,
) -> List[str]:
    """Normalize then tokenize Arabic text.

    Args:
        text: Raw text (may contain noise, mixed scripts).
        normalizer: An ArabicNormalizer instance (created lazily if None).

    Returns:
        Tokenized word list.
    """
    if normalizer is None:
        from src.core.normalizing import ArabicNormalizer
        normalizer = ArabicNormalizer()

    normalized = normalizer.normalize(text)
    return tokenize_for_bm25(normalized)
