"""Dense (vector similarity) retrieval strategy."""

import time
import logging
from typing import Optional, List
from .base import BaseRetrievalStrategy, SearchResult, SearchResponse
from src.core.embedding import create_embedder

logger = logging.getLogger(__name__)


class DenseRetrieval(BaseRetrievalStrategy):
    """Pure vector similarity search using pgvector."""

    def __init__(self):
        self.embedder = create_embedder()
        logger.info(f"Dense retrieval using: {self.embedder.mode} embedder")

    @property
    def name(self) -> str:
        return "dense"

    def _get_connection(self):
        from src.db.session import get_connection
        return get_connection()

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> SearchResponse:
        start_time = time.time()

        # Generate query embedding
        query_embedding = self.embedder.embed_single(query)

        conn = self._get_connection()
        cur = conn.cursor()

        if domain:
            cur.execute(
                """
                SELECT id, article_number, chunk_text, law_name, domain,
                       chapter_title, section_title, source_file,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM legal_chunks
                WHERE is_active = TRUE AND domain = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding.tolist(), domain,
                 query_embedding.tolist(), top_k),
            )
        else:
            cur.execute(
                """
                SELECT id, article_number, chunk_text, law_name, domain,
                       chapter_title, section_title, source_file,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM legal_chunks
                WHERE is_active = TRUE
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding.tolist(), query_embedding.tolist(), top_k),
            )

        results = []
        for row in cur.fetchall():
            results.append(SearchResult(
                id=row[0],
                article_number=row[1],
                text=row[2],
                law_name=row[3],
                domain=row[4],
                chapter_title=row[5],
                section_title=row[6],
                source_file=row[7],
                similarity=round(row[8], 4),
            ))

        cur.close()
        conn.close()

        elapsed = (time.time() - start_time) * 1000
        return SearchResponse(
            query=query,
            strategy=self.name,
            results=results,
            total_results=len(results),
            search_time_ms=round(elapsed, 2),
        )
