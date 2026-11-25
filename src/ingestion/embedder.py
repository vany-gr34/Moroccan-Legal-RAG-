"""Convenience wrapper for embedding during ingestion."""
import time
import logging
import numpy as np
from src.core.embedding import create_embedder, BaseEmbedder

logger = logging.getLogger(__name__)

# Default max characters per article for embedding.
# Models like intfloat/multilingual-e5-large cap at 512 tokens (~2000 Arabic chars).
# BAAI/bge-m3 handles up to 8192 tokens (~32000 Arabic chars).
# Set conservatively to avoid OOM on the remote GPU server.
DEFAULT_MAX_CHARS = 2000


class IngestionEmbedder:
    """Wrapper that provides batch embedding with progress and error handling."""

    def __init__(self, embedder: BaseEmbedder = None):
        if embedder is None:
            embedder = create_embedder()  # auto-detect remote/local
        self.embedder = embedder
        logger.info(
            f"Ingestion embedder: {embedder.mode} mode, dim={embedder.dimension}")

    def embed_articles(
        self,
        texts: list,
        batch_size: int = 32,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> np.ndarray:
        """
        Embed a list of texts in batches with progress.

        Args:
            texts: List of text strings to embed.
            batch_size: Number of texts per batch sent to the embedder.
            max_chars: Truncate each text to this many characters before
                embedding. Prevents VRAM OOM on the remote server when
                articles are excessively long due to parsing artefacts.
                Set to 0 or None to disable truncation.

        Returns:
            Numpy array of shape (N, dimension).
        """
        # Truncate overly long texts to avoid VRAM OOM
        if max_chars:
            truncated_count = 0
            processed_texts = []
            for t in texts:
                if len(t) > max_chars:
                    processed_texts.append(t[:max_chars])
                    truncated_count += 1
                else:
                    processed_texts.append(t)
            if truncated_count:
                logger.warning(
                    "Truncated %d/%d texts to %d chars to avoid OOM.",
                    truncated_count, len(texts), max_chars,
                )
            texts = processed_texts

        all_embeddings = []
        total = len(texts)
        for i in range(0, total, batch_size):
            batch = texts[i:i+batch_size]
            logger.info(
                f"Embedding batch {i//batch_size + 1}/{(total+batch_size-1)//batch_size} ({len(batch)} texts)")
            start = time.time()
            embeddings = self.embedder.embed(batch)
            elapsed = time.time() - start
            logger.info(f"  Batch embedded in {elapsed:.1f}s")
            all_embeddings.append(embeddings)
        return np.concatenate(all_embeddings, axis=0)
