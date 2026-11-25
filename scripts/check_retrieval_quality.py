#!/usr/bin/env python3
"""Check retrieval quality on the ingested commercial law articles."""

from src.core.embedding import create_embedder
from src.db.session import get_connection
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


# Test queries – should retrieve specific articles from your trade law
TEST_QUERIES = [
    {
        "query": "ما هي شروط التسجيل في السجل التجاري؟",
        "expected_articles": ["1", "2244", "42"],   # loosely expected numbers
    },
    {
        "query": "كيف يتم تحديد أجل الأداء بين التجار؟",
        "expected_articles": ["1-78", "2-78", "3-78"],
    },
    {
        "query": "ما هي البيانات التي يجب التصريح بها للشركات التجارية؟",
        "expected_articles": ["2244", "42"],
    },
    {
        "query": "ما هو التعويض عن التأخير في أداء المبالغ المستحقة؟",
        "expected_articles": ["3-78"],
    },
]


def search(embedder, conn, query: str, top_k: int = 5, domain: str = None):
    """Embed query and return top-k articles from the database."""
    query_embedding = embedder.embed_single(query)
    cur = conn.cursor()
    if domain:
        cur.execute(
            """
            SELECT article_number, chapter_title, section_title,
                   chunk_text,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM legal_chunks
            WHERE is_active = TRUE AND domain = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding.tolist(), domain, query_embedding.tolist(), top_k),
        )
    else:
        cur.execute(
            """
            SELECT article_number, chapter_title, section_title,
                   chunk_text,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM legal_chunks
            WHERE is_active = TRUE
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding.tolist(), query_embedding.tolist(), top_k),
        )
    results = cur.fetchall()
    cur.close()
    return results


def main():
    # Connect to DB
    conn = get_connection()

    embedder = create_embedder()
    print(f"Embedder: {embedder.mode} | Dimension: {embedder.dimension}\n")

    for item in TEST_QUERIES:
        query = item["query"]
        expected = set(item["expected_articles"])
        print(f"Query: {query}")
        results = search(embedder, conn, query, top_k=5, domain="commercial")
        found_articles = []
        for row in results:
            art_num, chapter, section, text, sim = row
            found_articles.append(art_num)
            snippet = text[:100].replace('\n', ' ')
            print(f"  {art_num} (sim={sim:.3f}): {snippet}...")
        # Check if any expected article appears in top-5
        hit = set(found_articles) & expected
        if hit:
            print(f"  ✓ Found expected articles: {hit}")
        else:
            print(
                f"  ✗ None of the expected {expected} found. Got: {found_articles}")
        print()

    conn.close()


if __name__ == "__main__":
    main()
