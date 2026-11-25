"""
Custom exceptions for the Moroccan Legal RAG project.

Provides a consistent error hierarchy so that API handlers and
callers can catch specific failure types rather than raw Exception.
"""


class LegalRAGError(Exception):
    """Base exception for all project-specific errors."""
    pass


class ConfigError(LegalRAGError):
    """Raised when configuration loading fails."""
    pass


class DatabaseError(LegalRAGError):
    """Raised when a database operation fails."""
    pass


class ExtractionError(LegalRAGError):
    """Raised when PDF text extraction fails."""
    pass


class EmbeddingError(LegalRAGError):
    """Raised when embedding generation fails."""
    pass


class RetrievalError(LegalRAGError):
    """Raised when the retrieval engine fails."""
    pass


class LLMConnectionError(LegalRAGError):
    """Raised when the remote LLM service is unreachable."""
    pass


class LLMGenerationError(LegalRAGError):
    """Raised when LLM response generation fails."""
    pass


class IngestionError(LegalRAGError):
    """Raised when the ingestion pipeline fails."""
    pass


class OCRServiceError(LegalRAGError):
    """Raised when the OCR service is unreachable or returns an error."""
    pass
