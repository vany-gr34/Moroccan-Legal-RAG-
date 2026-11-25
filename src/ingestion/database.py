"""Database operations for legal chunks."""
import logging
from typing import List, Dict
import psycopg2
from psycopg2.extras import execute_values

from src.db.session import get_connection

logger = logging.getLogger(__name__)


def delete_chunks_for_source(conn, source_file: str):
    """Remove existing chunks for a given source file (re-ingestion)."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM legal_chunks WHERE source_file = %s", (source_file,))
    conn.commit()
    logger.info(f"Deleted existing chunks for source: {source_file}")


def insert_chunks_batch(conn, chunks_data: List[Dict]):
    """
    Insert multiple chunks efficiently.
    Each dict must have:
        chunk_text, chunk_text_normalized, embedding (list of floats),
        domain, law_name, article_number, source_file,
        chapter_title, section_title, source_page, extraction_method,
        metadata (JSON-serializable dict)
    """
    if not chunks_data:
        return

    columns = [
        "chunk_text", "chunk_text_normalized", "embedding",
        "domain", "law_name", "article_number", "source_file",
        "chapter_title", "section_title", "source_page",
        "extraction_method", "metadata"
    ]

    values = []
    for chunk in chunks_data:
        values.append((
            chunk["chunk_text"],
            chunk["chunk_text_normalized"],
            chunk["embedding"],
            chunk["domain"],
            chunk["law_name"],
            chunk["article_number"],
            chunk["source_file"],
            chunk.get("chapter_title"),
            chunk.get("section_title"),
            chunk.get("source_page"),
            chunk.get("extraction_method", "pipeline"),
            psycopg2.extras.Json(chunk.get("metadata", {})),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            f"""
            INSERT INTO legal_chunks ({', '.join(columns)})
            VALUES %s
            """,
            values,
            template=None
        )
    conn.commit()
    logger.info(f"Inserted {len(values)} chunks")
