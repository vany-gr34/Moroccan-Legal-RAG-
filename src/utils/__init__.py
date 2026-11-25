"""
Utilities for the Moroccan Legal RAG project.

Provides:
  - config:     YAML configuration loading (main, cleaning, normalization, OCR, retrieval)
  - exceptions: Custom exception hierarchy
"""

from .config import (
    load_config,
    load_config_optional,
    get_pdf_classifier_config,
    get_embedding_config,
    get_cleaning_config,
    get_normalization_config,
    get_ocr_config,
    get_retrieval_config,
)
from .exceptions import (
    LegalRAGError,
    ConfigError,
    DatabaseError,
    ExtractionError,
    EmbeddingError,
    RetrievalError,
    LLMConnectionError,
    LLMGenerationError,
    IngestionError,
    OCRServiceError,
)

__all__ = [
    # Config
    "load_config",
    "load_config_optional",
    "get_pdf_classifier_config",
    "get_embedding_config",
    "get_cleaning_config",
    "get_normalization_config",
    "get_ocr_config",
    "get_retrieval_config",
    # Exceptions
    "LegalRAGError",
    "ConfigError",
    "DatabaseError",
    "ExtractionError",
    "EmbeddingError",
    "RetrievalError",
    "LLMConnectionError",
    "LLMGenerationError",
    "IngestionError",
    "OCRServiceError",
]
