"""API dependencies - singleton instances."""

import logging
from src.retrieval.hybrid_search import create_retrieval_strategy
from src.db.session import get_connection

logger = logging.getLogger(__name__)

# Singleton retrieval strategy - loaded once at startup
_retrieval_strategy = None


def get_retrieval_strategy(strategy_name: str = "rrf"):
    """Get or create the retrieval strategy singleton."""
    global _retrieval_strategy
    if _retrieval_strategy is None:
        logger.info(f"Initializing retrieval strategy: {strategy_name}")
        _retrieval_strategy = create_retrieval_strategy(strategy_name)
        # Force BM25 index to build now, not on first request
        if hasattr(_retrieval_strategy, '_load_bm25'):
            _retrieval_strategy._load_bm25()
            logger.info("BM25 index pre-loaded")
    return _retrieval_strategy
