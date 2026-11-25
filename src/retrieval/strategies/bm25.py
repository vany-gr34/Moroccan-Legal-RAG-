"""BM25 lexical retrieval using rank-bm25 with Arabic-aware tokenization.

PostgreSQL's Arabic FTS dictionary is too basic for legal Arabic.
This module uses the Python rank-bm25 library with proper Arabic
word segmentation, stop-word removal, and the project's existing
text normalization pipeline.
"""

import time
import logging
from typing import Optional, List

import numpy as np
from rank_bm25 import BM25Okapi

from .base import BaseRetrievalStrategy, SearchResult, SearchResponse
from .arabic_tokenizer import tokenize_for_bm25, normalize_and_tokenize

logger = logging.getLogger(__name__)


class BM25Retrieval(BaseRetrievalStrategy):
    """Keyword-based retrieval using Python rank-bm25 with Arabic tokenizer.

    Loads all active legal chunks into memory once, tokenizes them
    with Arabic-aware word segmentation, and builds a BM25Okapi index.
    """

    def __init__(self):
        self._bm25: Optional[BM25Okapi] = None
        self._doc_ids: List[int] = []
        self._doc_articles: List[str] = []
        self._doc_laws: List[str] = []
        self._doc_domains: List[str] = []
        self._doc_texts: List[str] = []
        self._loaded = False

    @property
    def name(self) -> str:
        return "bm25"

    def _get_connection(self):
        from src.db.session import get_connection
        return get_connection()

    def _load_index(self):
        """Load all documents and build BM25 index (once, lazily)."""
        if self._loaded:
            return

        logger.info("Loading documents for BM25 (Arabic tokenizer)...")
        start = time.time()

        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, article_number, chunk_text, law_name, domain
            FROM legal_chunks
            WHERE is_active = TRUE
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Use a shared normalizer for consistency
        from src.core.normalizing import ArabicNormalizer
        normalizer = ArabicNormalizer()

        tokenized_docs = []
        for row in rows:
            doc_id, article, text, law, domain = row
            self._doc_ids.append(doc_id)
            self._doc_articles.append(article or "")
            self._doc_laws.append(law or "")
            self._doc_domains.append(domain or "")
            self._doc_texts.append(text or "")
            tokens = normalize_and_tokenize(text or "", normalizer=normalizer)
            tokenized_docs.append(tokens)

        self._bm25 = BM25Okapi(tokenized_docs)
        self._loaded = True

        logger.info(
            f"BM25 index ready: {len(rows)} docs in {time.time() - start:.1f}s "
            f"(avg tokens/doc: {sum(len(t) for t in tokenized_docs) / max(len(tokenized_docs), 1):.0f})"
        )

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> SearchResponse:
        start_time = time.time()

        # Build index on first call
        self._load_index()

        if self._bm25 is None or not self._doc_ids:
            elapsed = (time.time() - start_time) * 1000
            return SearchResponse(
                query=query,
                strategy=self.name,
                results=[],
                total_results=0,
                search_time_ms=round(elapsed, 2),
            )

        # Tokenize the query with the same Arabic tokenizer
        tokenized_query = tokenize_for_bm25(query)

        if not tokenized_query:
            elapsed = (time.time() - start_time) * 1000
            return SearchResponse(
                query=query,
                strategy=self.name,
                results=[],
                total_results=0,
                search_time_ms=round(elapsed, 2),
            )

        # Get BM25 scores for all documents
        scores = self._bm25.get_scores(tokenized_query)

        # Build (index, score) pairs, optionally filter by domain
        indexed_scores = []
        for i, score in enumerate(scores):
            if score <= 0:
                continue
            if domain and self._doc_domains[i] != domain:
                continue
            indexed_scores.append((i, score))

        # Sort by score descending
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        top = indexed_scores[:top_k]

        # Build results
        results = []
        for idx, score in top:
            results.append(SearchResult(
                id=self._doc_ids[idx],
                article_number=self._doc_articles[idx],
                text=self._doc_texts[idx],
                law_name=self._doc_laws[idx],
                domain=self._doc_domains[idx],
                chapter_title=None,
                section_title=None,
                source_file="",
                similarity=round(float(score), 4),
            ))

        elapsed = (time.time() - start_time) * 1000
        logger.info(
            f"BM25 search: query='{query[:50]}...' "
            f"domain={domain or 'all'} → {len(results)} results "
            f"in {elapsed:.1f}ms"
        )

        return SearchResponse(
            query=query,
            strategy=self.name,
            results=results,
            total_results=len(results),
            search_time_ms=round(elapsed, 2),
        )
