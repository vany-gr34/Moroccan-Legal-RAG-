"""Abstract base for all PDF text extractors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import time


@dataclass
class PageData:
    """Represents extracted text from a single page."""
    page_number: int
    text: str
    confidence: Optional[float] = None          # OCR/VLM confidence 0-100
    extraction_time_ms: Optional[float] = None  # time taken for this page
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Unified result from any extractor."""
    file_path: Path
    extractor_name: str
    total_pages: int
    pages: List[PageData]
    total_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseExtractor(ABC):
    """Abstract extractor for Moroccan legal PDFs."""

    @abstractmethod
    def extract(self, pdf_path: Path) -> ExtractionResult:
        """Extract text from a PDF, returning a unified result.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            ExtractionResult containing page-wise text and metadata.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the extractor."""
        ...
