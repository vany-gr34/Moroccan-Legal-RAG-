"""Retrieval orchestrator - factory and unified search interface."""

import logging
from typing import Optional
from .strategies.base import SearchResponse
from .strategies.dense import DenseRetrieval
from .strategies.bm25 import BM25Retrieval
from .strategies.rrf import RRFRetrieval

logger = logging.getLogger(__name__)


def create_retrieval_strategy(strategy_name: str = "rrf", **kwargs):
    """Factory for retrieval strategies.

    Args:
        strategy_name: One of "dense", "bm25", "rrf".
        kwargs: Additional arguments for the strategy (e.g., k_rrf for RRF).

    Returns:
        A BaseRetrievalStrategy instance.
    """
    strategy_name = strategy_name.lower()

    if strategy_name == "dense":
        return DenseRetrieval()
    elif strategy_name == "bm25":
        return BM25Retrieval()
    elif strategy_name == "rrf":
        k_rrf = kwargs.get("k_rrf", 60)
        return RRFRetrieval(k_rrf=k_rrf)
    else:
        raise ValueError(f"Unknown retrieval strategy: {strategy_name}")


# Default strategy (can be overridden by config)
_default_strategy = None


def search(
    query: str,
    domain: Optional[str] = None,
    top_k: int = 5,
    strategy: Optional[str] = None,
) -> SearchResponse:
    """Execute retrieval with the configured strategy.

    Args:
        query: Arabic legal question.
        domain: Optional domain filter.
        top_k: Number of results to return.
        strategy: Override default strategy.

    Returns:
        SearchResponse with ranked results.
    """
    global _default_strategy

    strategy_name = strategy or "rrf"

    if _default_strategy is None or _default_strategy.name != strategy_name:
        _default_strategy = create_retrieval_strategy(strategy_name)

    return _default_strategy.search(query=query, domain=domain, top_k=top_k)
