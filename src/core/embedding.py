"""
Embedding interface for Moroccan Legal RAG.

Provides a unified interface for generating embeddings,
supporting both local (in-process) and remote (Colab GPU) backends.

Usage:
    # Local mode (default)
    embedder = LocalEmbedder()
    embeddings = embedder.embed(["المادة 147 من القانون الجنائي"])

    # Remote mode (Colab GPU via Cloudflare tunnel)
    embedder = RemoteEmbedder(service_url="https://xxx.trycloudflare.com")
    embeddings = embedder.embed(["المادة 147 من القانون الجنائي"])

    # Auto-detect from environment
    embedder = create_embedder()  # reads EMBEDDING_SERVICE_URL from .env
"""

from abc import ABC, abstractmethod
import os
import time
import logging
from typing import List, Union
import requests
import numpy as np

from src.utils.config import get_embedding_config

logger = logging.getLogger(__name__)


# ============================================
# Abstract Interface
# ============================================

class BaseEmbedder(ABC):
    """Abstract interface for embedding generators."""

    @abstractmethod
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Generate embeddings for one or more texts.

        Args:
            texts: Single string or list of strings.

        Returns:
            Numpy array of shape (n_texts, dimension).
        """
        pass

    @abstractmethod
    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Input text string.

        Returns:
            1D numpy array of shape (dimension,).
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension (e.g., 1024 for e5-large)."""
        pass

    @property
    @abstractmethod
    def mode(self) -> str:
        """Return 'local' or 'remote'."""
        pass


# ============================================
# Local Implementation
# ============================================

class LocalEmbedder(BaseEmbedder):
    """Embed texts using a locally-loaded SentenceTransformer model.

    Slow on CPU (~10 texts/second). Fast on GPU if available.
    """

    def __init__(
        self,
        model_name: str = None,
        device: str = None,
    ):
        if model_name is None:
            embed_config = get_embedding_config()
            model_name = embed_config.get(
                "model_name", "BAAI/bge-m3"
            )

        self._model_name = model_name
        self._device = device
        self._model = None  # Lazy load
        self._dimension = None

    def _load_model(self):
        """Lazy-load the model on first use."""
        if self._model is not None:
            return

        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading embedding model: {self._model_name}")
        start = time.time()

        self._model = SentenceTransformer(
            self._model_name, device=self._device)
        self._dimension = self._model.get_embedding_dimension()

        elapsed = time.time() - start
        logger.info(
            f"Model loaded in {elapsed:.1f}s | "
            f"Device: {self._model.device} | "
            f"Dimension: {self._dimension}"
        )

    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        self._load_model()

        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.array([])

        start = time.time()
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 10,
            convert_to_numpy=True,
        )
        elapsed = time.time() - start

        logger.debug(f"Embedded {len(texts)} texts in {elapsed:.2f}s "
                     f"({len(texts)/elapsed:.0f} texts/s)")

        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._load_model()
        return self._dimension

    @property
    def mode(self) -> str:
        return "local"


# ============================================
# Remote Implementation
# ============================================

class RemoteEmbedder(BaseEmbedder):
    """Embed texts by calling a remote embedding service (Colab GPU).

    The remote service must expose:
        GET  /health  → {"status": "ok", "dimension": 1024, ...}
        POST /embed   → {"embeddings": [...], "dimension": 1024, ...}
    """

    def __init__(self, service_url: str, timeout: int = 300):
        self._service_url = service_url.rstrip("/")
        self._timeout = timeout
        self._dimension = None

        # Verify connection on init
        self._health_check()

    def _health_check(self):
        """Call /health to verify service is reachable and get dimension."""
        import requests

        try:
            resp = requests.get(
                f"{self._service_url}/health",
                timeout=10,
            )
            resp.raise_for_status()
            health = resp.json()

            self._dimension = health.get("dimension", 1024)
            logger.info(
                f"Connected to embedding service: {self._service_url}\n"
                f"  Model: {health.get('model', 'unknown')}\n"
                f"  Device: {health.get('device', 'unknown')}\n"
                f"  Dimension: {self._dimension}"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Cannot reach embedding service: {e}")
            raise ConnectionError(
                f"Embedding service unreachable at {self._service_url}. "
                f"Is the Colab notebook running?"
            ) from e

    def embed(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        import requests

        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.array([])

        logger.info(f"Sending {len(texts)} texts to remote embedder...")
        start = time.time()

        try:
            resp = requests.post(
                f"{self._service_url}/embed",
                json={"texts": texts, "batch_size": batch_size},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            elapsed = time.time() - start
            server_time = data.get("time_ms", 0)
            network_time = (elapsed * 1000) - server_time

            logger.info(
                f"Remote embedding complete: {data['count']} texts "
                f"in {elapsed:.1f}s "
                f"(server: {server_time:.0f}ms, network: {network_time:.0f}ms)"
            )

            return np.array(data["embeddings"], dtype=np.float32)

        except requests.exceptions.RequestException as e:
            logger.error(f"Remote embedding failed: {e}")
            raise ConnectionError(
                f"Embedding request failed. Is the Colab runtime still active?"
            ) from e

    def embed_single(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return self._dimension or 1024

    @property
    def mode(self) -> str:
        return "remote"


# ============================================
# Factory Function
# ============================================
def create_embedder(
    service_url: str = None,
    model_name: str = None,
) -> BaseEmbedder:
    embed_config = get_embedding_config()

    # Determine service URL
    service_url = (
        service_url
        or os.getenv("EMBEDDING_SERVICE_URL")
        or embed_config.get("service_url")
    )

    if service_url and service_url.strip():
        logger.info(f"Attempting remote embedder at {service_url}")
        try:
            remote = RemoteEmbedder(service_url=service_url)
            logger.info("✓ Remote embedder connected successfully")
            return remote
        except ConnectionError as e:
            logger.warning(f"✗ Remote embedder unavailable: {e}")
            logger.warning("  → Falling back to local embedder.")
    else:
        logger.info("No EMBEDDING_SERVICE_URL set. Using local embedder.")

    # Local fallback
    model_name = model_name or embed_config.get(
        "model_name", "intfloat/multilingual-e5-large"
    )
    logger.info(f"Using local embedder with model: {model_name}")
    return LocalEmbedder(model_name=model_name)
