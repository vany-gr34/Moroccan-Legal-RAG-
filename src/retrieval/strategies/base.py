"""Abstract base for retrieval strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class SearchResult:
    """A single retrieved legal chunk."""
    id: int
    article_number: str
    text: str
    law_name: str
    domain: str
    chapter_title: Optional[str]
    section_title: Optional[str]
    source_file: str
    similarity: float
    dense_rank: Optional[int] = None
    bm25_rank: Optional[int] = None
    rrf_score: Optional[float] = None


@dataclass
class SearchResponse:
    """Complete search response."""
    query: str
    strategy: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float


class BaseRetrievalStrategy(ABC):
    """Abstract retrieval strategy."""

    @abstractmethod
    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> SearchResponse:
        """Execute retrieval and return ranked results.

        Args:
            query: Arabic legal question.
            domain: Optional domain filter.
            top_k: Number of results to return.

        Returns:
            SearchResponse with ranked results and metadata.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name."""
        pass
