"""LLM factory - creates the appropriate LLM instance."""

import os
import logging
from .base import BaseLLM
from .remote_llm import RemoteLLM
from ..services.openai_llm import OpenAILLM

logger = logging.getLogger(__name__)

_llm_instance = None


def create_llm(service_url: str = None) -> BaseLLM:
    """Create an LLM instance based on configuration.

    Resolution order:
        1. If `LLM_BACKEND=openai` is set → OpenAILLM (uses openai SDK)
        2. If `OPENAI_API_KEY` is set without LLM_SERVICE_URL → OpenAILLM
        3. If `service_url` or `LLM_SERVICE_URL` is set → RemoteLLM
        4. Raise error

    Args:
        service_url: URL of remote LLM service (optional).

    Returns:
        BaseLLM instance.
    """
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    backend = os.getenv("LLM_BACKEND", "").lower()

    # OpenAI-compatible backend (DeepSeek, OpenAI, etc.)
    if backend == "openai" or (os.getenv("OPENAI_API_KEY") and not os.getenv("LLM_SERVICE_URL")):
        logger.info("Using OpenAI-compatible LLM backend")
        _llm_instance = OpenAILLM()
        return _llm_instance

    # Legacy remote service backend (custom /generate endpoint)
    service_url = service_url or os.getenv("LLM_SERVICE_URL")
    if service_url:
        logger.info(f"Connecting to remote LLM at {service_url}")
        _llm_instance = RemoteLLM(service_url=service_url)
        return _llm_instance

    raise ValueError(
        "No LLM backend configured. Set one of:\n"
        "  - LLM_BACKEND=openai + OPENAI_API_KEY (OpenAI/DeepSeek)\n"
        "  - LLM_SERVICE_URL (remote /generate endpoint)\n"
        "  - OPENAI_API_KEY (auto-detected as OpenAI backend)\n"
        "Or pass service_url to create_llm()."
    )


def get_llm() -> BaseLLM:
    """Get the singleton LLM instance (must call create_llm first)."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = create_llm()
    return _llm_instance
