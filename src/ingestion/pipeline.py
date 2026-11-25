"""Main ingestion pipeline: JSON → embed → store."""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

from .database import get_connection, delete_chunks_for_source, insert_chunks_batch
from .embedder import IngestionEmbedder

logger = logging.getLogger(__name__)


def build_article_text(article: Dict) -> str:
    """Create a contextualized text for embedding.
    Includes law, chapter, section, and article number as prefix.
    """
    context = article.get("context", {})
    law = article.get("law_name", "")
    chapter = context.get("chapter", "")
    section = context.get("section", "")
    article_num = article.get("article_number", "")

    prefix_parts = []
    if law:
        prefix_parts.append(f"[{law}]")
    if section:
        prefix_parts.append(f"[{section}]")
    if chapter:
        prefix_parts.append(f"[{chapter}]")
    if article_num:
        prefix_parts.append(f"المادة {article_num}:")

    prefix = " ".join(prefix_parts)
    return f"{prefix} {article['text']}".strip()


def ingest_articles(
    json_path: Path,
    domain: str,
    source_file: Optional[str] = None,
    law_name: Optional[str] = None,
    extraction_method: str = "pymupdf",
    batch_size: int = 32,
    clear_existing: bool = True,
    max_chars: Optional[int] = None,
) -> int:
    """
    Ingest articles from a JSON file into the vector database.

    Args:
        json_path: Path to the articles JSON file.
        domain: Legal domain (e.g., 'commercial').
        source_file: Original PDF filename for traceability.
        law_name: Override law name (otherwise taken from articles).
        extraction_method: How the text was extracted.
        batch_size: Embedding batch size.
        clear_existing: Whether to delete existing chunks for this source before inserting.
        max_chars: Truncate article text to this many chars before embedding.
            Prevents VRAM OOM on remote GPU server. Defaults to 2000 if not set.

    Returns:
        Number of articles ingested.
    """
    # Load articles
    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    if not articles:
        logger.warning("No articles found in JSON.")
        return 0

    # Determine source file
    if source_file is None:
        source_file = json_path.stem  # fallback

    # Override law name if provided
    if law_name:
        for art in articles:
            art["law_name"] = law_name

    # Connect to DB
    conn = get_connection()
    try:
        if clear_existing:
            delete_chunks_for_source(conn, source_file)

        # Build embedding texts
        embed_texts = [build_article_text(art) for art in articles]

        # Create embedder and embed all
        embedder = IngestionEmbedder()  # will use remote if configured
        embeddings = embedder.embed_articles(
            embed_texts, batch_size=batch_size, max_chars=max_chars)

        # Prepare chunk data for insertion
        chunks = []
        for art, emb in zip(articles, embeddings):
            # Use article text as stored text, but normalized text from the article
            chunk_text = art["text"]
            # already normalized in pipeline
            chunk_text_normalized = art["text"]
            context = art.get("context", {})
            metadata = {
                "footnotes": art.get("footnotes", []),
                "context": context,
            }

            chunks.append({
                "chunk_text": chunk_text,
                "chunk_text_normalized": chunk_text_normalized,
                "embedding": emb.tolist(),
                "domain": domain,
                "law_name": art.get("law_name", ""),
                "article_number": art.get("article_number", ""),
                "source_file": source_file,
                "chapter_title": context.get("chapter"),
                "section_title": context.get("section"),
                "source_page": None,  # could be extracted from context if available
                "extraction_method": extraction_method,
                "metadata": metadata,
            })

        insert_chunks_batch(conn, chunks)
        logger.info(
            f"Successfully ingested {len(chunks)} articles from {json_path}")
        return len(chunks)

    finally:
        conn.close()
