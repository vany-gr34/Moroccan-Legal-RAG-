"""Reciprocal Rank Fusion retrieval strategy."""

import time
import logging
from typing import Optional, Dict, List
import numpy as np
from rank_bm25 import BM25Okapi
from .base import BaseRetrievalStrategy, SearchResult, SearchResponse
from .arabic_tokenizer import tokenize_for_bm25, normalize_and_tokenize
from src.core.embedding import create_embedder

logger = logging.getLogger(__name__)


class RRFRetrieval(BaseRetrievalStrategy):
    """Hybrid retrieval using Reciprocal Rank Fusion.

    Dense: pgvector cosine similarity
    BM25: Python rank-bm25 (PostgreSQL's Arabic text search doesn't work)
    """

    def __init__(self, k_rrf: int = 60):
        self.k_rrf = k_rrf
        self.embedder = create_embedder()
        self._bm25 = None
        self._bm25_ids = None
        self._loaded = False
        logger.info(f"RRF retrieval: k={k_rrf}, embedder={self.embedder.mode}")

    @property
    def name(self) -> str:
        return "rrf"

    def _get_connection(self):
        from src.db.session import get_connection
        return get_connection()

    def _load_bm25(self):
        """Load all document texts into memory for BM25 (only once)."""
        if self._loaded:
            return

        logger.info("Loading documents for BM25 index (Arabic tokenizer)...")
        start = time.time()

        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, chunk_text FROM legal_chunks WHERE is_active = TRUE"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Use the shared Arabic normalizer for consistent preprocessing
        from src.core.normalizing import ArabicNormalizer
        normalizer = ArabicNormalizer()

        self._bm25_ids = [row[0] for row in rows]
        tokenized_docs = [
            normalize_and_tokenize(row[1] or "", normalizer=normalizer)
            for row in rows
        ]
        self._bm25 = BM25Okapi(tokenized_docs)
        self._loaded = True

        logger.info(
            f"BM25 index ready: {len(rows)} docs in {time.time() - start:.1f}s"
            f" (avg tokens/doc: {sum(len(t) for t in tokenized_docs) / max(len(tokenized_docs), 1):.0f})"
        )

    def _dense_ranks(self, query: str, domain: Optional[str], top_n: int = 20) -> Dict[int, int]:
        """Get dense retrieval ranks for top-N results."""
        query_embedding = self.embedder.embed_single(query)
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            if domain:
                cur.execute(
                    """
                    SELECT id FROM legal_chunks
                    WHERE is_active = TRUE AND domain = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (domain, query_embedding.tolist(), top_n),
                )
            else:
                cur.execute(
                    """
                    SELECT id FROM legal_chunks
                    WHERE is_active = TRUE
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query_embedding.tolist(), top_n),
                )

            ranks = {}
            for rank, row in enumerate(cur.fetchall(), start=1):
                ranks[row[0]] = rank
            return ranks
        finally:
            cur.close()
            conn.close()

    def _bm25_ranks(self, query: str, domain: Optional[str], top_n: int = 20) -> Dict[int, int]:
        """Get BM25 ranks using Python rank-bm25 with Arabic tokenizer."""
        self._load_bm25()

        tokenized_query = tokenize_for_bm25(query)

        if not tokenized_query:
            logger.warning(
                f"BM25: query tokenized to empty list: '{query[:60]}'")
            return {}

        scores = self._bm25.get_scores(tokenized_query)

        # If domain filter, only rank documents in that domain
        if domain:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM legal_chunks WHERE is_active = TRUE AND domain = %s",
                (domain,)
            )
            domain_ids = {row[0] for row in cur.fetchall()}
            cur.close()
            conn.close()

            # Filter scores to domain only
            filtered = [(i, scores[i]) for i in range(len(scores))
                        if self._bm25_ids[i] in domain_ids]
        else:
            filtered = [(i, scores[i]) for i in range(len(scores))]

        # Sort by score descending, take top_n
        filtered.sort(key=lambda x: x[1], reverse=True)
        top_indices = filtered[:top_n]

        ranks = {}
        for rank, (idx, _) in enumerate(top_indices, start=1):
            ranks[self._bm25_ids[idx]] = rank

        return ranks

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> SearchResponse:
        start_time = time.time()

        # Get ranks from both strategies
        dense_ranks = self._dense_ranks(query, domain, top_n=20)
        bm25_ranks = self._bm25_ranks(query, domain, top_n=20)

        # Compute RRF scores
        rrf_scores = {}
        all_ids = set(dense_ranks.keys()) | set(bm25_ranks.keys())
        penalty_rank = 21  # top_n + 1

        for doc_id in all_ids:
            dense_rank = dense_ranks.get(doc_id, penalty_rank)
            bm25_rank = bm25_ranks.get(doc_id, penalty_rank)
            rrf_scores[doc_id] = (
                1.0 / (self.k_rrf + dense_rank) +
                1.0 / (self.k_rrf + bm25_rank)
            )

        # Sort by RRF score descending
        sorted_ids = sorted(rrf_scores.items(),
                            key=lambda x: x[1], reverse=True)[:top_k]

        # Fetch full document data in a single query
        ids_to_fetch = [doc_id for doc_id, _ in sorted_ids]
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT id, article_number, chunk_text, law_name, domain,
                       chapter_title, section_title, source_file
                FROM legal_chunks
                WHERE id = ANY(%s)
                """,
                (ids_to_fetch,),
            )
            rows = {row[0]: row for row in cur.fetchall()}
        finally:
            cur.close()
            conn.close()

        # Build results preserving RRF order
        results = []
        for doc_id, rrf_score in sorted_ids:
            row = rows.get(doc_id)
            if row:
                results.append(SearchResult(
                    id=row[0],
                    article_number=row[1],
                    text=row[2],
                    law_name=row[3],
                    domain=row[4],
                    chapter_title=row[5],
                    section_title=row[6],
                    source_file=row[7],
                    similarity=round(rrf_score, 4),
                    dense_rank=dense_ranks.get(doc_id),
                    bm25_rank=bm25_ranks.get(doc_id),
                    rrf_score=round(rrf_score, 4),
                ))

        elapsed = (time.time() - start_time) * 1000
        return SearchResponse(
            query=query,
            strategy=self.name,
            results=results,
            total_results=len(results),
            search_time_ms=round(elapsed, 2),
        )
