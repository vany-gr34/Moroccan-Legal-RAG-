"""
Debug: test vector search with Arabic legal queries.

Usage:
    python scripts/debug_vector_search.py
"""

from src.core.embedding import create_embedder
from src.db.session import get_connection
from dotenv import load_dotenv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


def search(embedder, conn, query: str, top_k: int = 3, domain: str = None):
    """Vector similarity search."""
    query_embedding = embedder.embed_single(query)

    cur = conn.cursor()

    if domain:
        cur.execute(
            """
            SELECT 
                id, chunk_text, domain, law_name, article_number,
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
            SELECT 
                id, chunk_text, domain, law_name, article_number,
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
    conn = get_db_connection()
    embedder = create_embedder()

    print(f"Embedder: {embedder.mode} | Dimension: {embedder.dimension}\n")

    # Check data exists
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM legal_chunks WHERE source_file = 'seed_test_data'")
    count = cur.fetchone()[0]
    cur.close()

    if count == 0:
        print("No test data found. Run: python scripts/seed_test_data.py")
        conn.close()
        return

    print(f"Database has {count} test chunks.\n")

    # Test queries
    queries = [
        ("ما هي عقوبة السرقة في القانون المغربي؟", "criminal"),
        ("ما هي مخالفات تجاوز السرعة؟", "traffic"),
        ("كيف يتم الطلاق حسب مدونة الأسرة؟", "family"),
        ("ما هي شروط صحة العقد؟", "civil"),
        ("كيف يتم التسجيل في السجل التجاري؟", "commercial"),
        ("كيف يتم تقديم الاستئناف؟", "judicial"),
        ("ما هي أنواع المخالفات والغرامات؟", "violations"),
    ]

    passed = 0

    for query, expected_domain in queries:
        print(f"Query: {query}")
        start = time.time()
        results = search(embedder, conn, query, top_k=3)
        elapsed = time.time() - start

        top_domain = results[0][2] if results else "N/A"
        correct = top_domain == expected_domain

        if correct:
            passed += 1
            print(
                f"  ✅ Top result: [{top_domain}] (expected: {expected_domain})")
        else:
            print(
                f"  ❌ Top result: [{top_domain}] (expected: {expected_domain})")

        for i, row in enumerate(results, 1):
            text_preview = row[1][:100].replace("\n", " ")
            print(f"     {i}. [{row[2]}] {text_preview}... ({row[5]:.4f})")

        print(f"     Search time: {elapsed*1000:.0f}ms\n")

    print(f"Result: {passed}/{len(queries)} queries returned correct domain")

    # Domain-filtered search
    print("-" * 50)
    print("Domain-filtered search: 'السرقة' in criminal law only")
    results = search(embedder, conn, "السرقة والعقوبات",
                     top_k=3, domain="criminal")
    all_criminal = all(r[2] == "criminal" for r in results)
    print(f"  All results in criminal domain: {'✅' if all_criminal else '❌'}")
    for i, row in enumerate(results, 1):
        print(f"     {i}. [{row[2]}] {row[1][:100]}...")

    conn.close()


if __name__ == "__main__":
    main()
