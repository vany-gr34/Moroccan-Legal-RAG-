"""
Core business logic for Moroccan Legal RAG.

Contains pure business logic with no framework or IO dependencies:
  - cleaning:    Arabic legal text cleaning and noise removal
  - normalizing: Arabic character-level normalization
  - structure:   Text-level structure parsing (headings, articles, footnotes)
  - block_parser: PDF block-level article detection
  - embedding:   Embedding generation (local + remote backends)
"""

from .cleaning import LegalTextCleaner, CleanedResult, CleanedPage
from .normalizing import ArabicNormalizer
from .structure import LegalStructureParser, parse_normalized_text_to_json
from .block_parser import PDFBlockParser, PDFContentAnalyzer, DigitalLegalExtractor
from .embedding import (
    BaseEmbedder,
    LocalEmbedder,
    RemoteEmbedder,
    create_embedder,
)

__all__ = [
    "LegalTextCleaner",
    "CleanedResult",
    "CleanedPage",
    "ArabicNormalizer",
    "LegalStructureParser",
    "parse_normalized_text_to_json",
    "PDFBlockParser",
    "PDFContentAnalyzer",
    "DigitalLegalExtractor",
    "BaseEmbedder",
    "LocalEmbedder",
    "RemoteEmbedder",
    "create_embedder",
]
