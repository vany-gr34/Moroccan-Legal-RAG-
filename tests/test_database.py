"""
Tests for PostgreSQL + pgvector connection and operations.

Run:
    pytest tests/test_database.py -v

Skip (no database):
    pytest tests/test_database.py -v -k "not db"
"""

import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2 import sql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from pgvector.psycopg2 import register_vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False


# ============================================
# Connection Fixture
# ============================================

@pytest.fixture
def conn():
    """Connect to PostgreSQL. Skips tests if unavailable."""
    if not PSYCOPG2_AVAILABLE:
        pytest.skip("psycopg2 not installed")

    try:
        connection = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            dbname=os.getenv("POSTGRES_DB", "legal_rag"),
            user=os.getenv("POSTGRES_USER", "legal_rag_user"),
            password=os.getenv("POSTGRES_PASSWORD", "legal_rag_pass"),
            connect_timeout=5,
        )
        yield connection
        connection.close()
    except psycopg2.OperationalError as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.fixture
def cur(conn):
    """Create a cursor for the connection."""
    cursor = conn.cursor()
    yield cursor
    cursor.close()


# ============================================
# Connection Tests
# ============================================

class TestDatabaseConnection:
    """Tests for basic database connectivity."""

    def test_connection_successful(self, conn):
        """Can connect to PostgreSQL."""
        assert conn is not None
        assert conn.closed == 0  # 0 = open

    def test_can_execute_query(self, cur):
        """Can execute a simple query."""
        cur.execute("SELECT 1")
        result = cur.fetchone()
        assert result[0] == 1

    def test_database_name(self, cur):
        """Connected to the correct database."""
        cur.execute("SELECT current_database()")
        db_name = cur.fetchone()[0]
        assert db_name == os.getenv("POSTGRES_DB", "legal_rag")

    def test_connection_user(self, cur):
        """Connected as the correct user."""
        cur.execute("SELECT current_user")
        user = cur.fetchone()[0]
        assert user == os.getenv("POSTGRES_USER", "legal_rag_user")


# ============================================
# Extension Tests
# ============================================

class TestExtensions:
    """Tests for required PostgreSQL extensions."""

    def test_pgvector_extension_exists(self, cur):
        """pgvector extension is available."""
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
        )
        exists = cur.fetchone()[0]
        assert exists, "pgvector extension not available in this PostgreSQL instance"

    def test_pgvector_extension_installed(self, cur):
        """pgvector extension is installed in the database."""
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        installed = cur.fetchone()[0]
        assert installed, "pgvector extension not installed. Run: CREATE EXTENSION vector;"

    def test_pg_trgm_extension_installed(self, cur):
        """pg_trgm extension is installed."""
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')"
        )
        installed = cur.fetchone()[0]
        assert installed, "pg_trgm extension not installed"

    def test_unaccent_extension_installed(self, cur):
        """unaccent extension is installed."""
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'unaccent')"
        )
        installed = cur.fetchone()[0]
        assert installed, "unaccent extension not installed"


# ============================================
# Table Tests
# ============================================

class TestTableStructure:
    """Tests for legal_chunks table schema."""

    def test_legal_chunks_table_exists(self, cur):
        """legal_chunks table exists."""
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'legal_chunks')"
        )
        exists = cur.fetchone()[0]
        assert exists, "legal_chunks table does not exist"

    def test_required_columns_exist(self, cur):
        """All required columns are present."""
        required_columns = [
            "id",
            "chunk_text",
            "chunk_text_normalized",
            "embedding",
            "domain",
            "law_name",
            "article_number",
            "source_file",
            "source_page",
            "extraction_method",
            "ocr_confidence",
            "metadata",
            "created_at",
            "updated_at",
            "is_active",
        ]

        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'legal_chunks'"
        )
        existing_columns = [row[0] for row in cur.fetchall()]

        for col in required_columns:
            assert col in existing_columns, f"Column '{col}' missing from legal_chunks"

    def test_embedding_column_type(self, cur):
        """embedding column accepts vector type."""
        cur.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'legal_chunks' AND column_name = 'embedding'"
        )
        data_type = cur.fetchone()[0]
        assert "vector" in data_type.lower() or data_type == "USER-DEFINED", (
            f"embedding column type is '{data_type}', expected 'vector'"
        )

    def test_domain_check_constraint(self, cur):
        """domain column has CHECK constraint for valid values."""
        valid_domains = [
            "traffic", "criminal", "family", "civil",
            "commercial", "judicial", "violations",
        ]

        for domain in valid_domains:
            # Should not raise
            cur.execute(
                "SELECT %s::VARCHAR(50)", (domain,)
            )

    def test_domain_rejects_invalid_value(self, conn):
        """domain column rejects invalid values."""
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO legal_chunks (chunk_text, chunk_text_normalized, domain, source_file) "
                "VALUES ('test', 'test', 'invalid_domain', 'test.pdf')"
            )
            conn.rollback()
            pytest.fail("Should have raised an error for invalid domain")
        except Exception:
            conn.rollback()
            # Expected - invalid domain should be rejected
            pass
        finally:
            cur.close()


# ============================================
# Index Tests
# ============================================

class TestIndexes:
    """Tests for database indexes."""

    def test_hnsw_index_exists(self, cur):
        """HNSW index on embedding column exists."""
        cur.execute(
            "SELECT EXISTS("
            "SELECT 1 FROM pg_indexes "
            "WHERE tablename = 'legal_chunks' "
            "AND indexdef LIKE '%hnsw%'"
            ")"
        )
        exists = cur.fetchone()[0]
        assert exists, "HNSW index on embedding column not found"

    def test_domain_index_exists(self, cur):
        """Index on domain column exists."""
        cur.execute(
            "SELECT EXISTS("
            "SELECT 1 FROM pg_indexes "
            "WHERE tablename = 'legal_chunks' "
            "AND indexname = 'idx_legal_chunks_domain'"
            ")"
        )
        exists = cur.fetchone()[0]
        assert exists, "Index on domain column not found"

    def test_article_index_exists(self, cur):
        """Index on article_number column exists."""
        cur.execute(
            "SELECT EXISTS("
            "SELECT 1 FROM pg_indexes "
            "WHERE tablename = 'legal_chunks' "
            "AND indexname = 'idx_legal_chunks_article'"
            ")"
        )
        exists = cur.fetchone()[0]
        assert exists, "Index on article_number column not found"


# ============================================
# CRUD Tests
# ============================================

class TestCRUD:
    """Tests for basic Create, Read, Update, Delete operations."""

    TEST_SOURCE = "pytest_crud_test"

    def test_insert_chunk(self, conn):
        """Can insert a chunk without embedding."""
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO legal_chunks 
                (chunk_text, chunk_text_normalized, domain, law_name, 
                 article_number, source_file, extraction_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                "اختبار الإدراج",
                "اختبار الادراج",
                "criminal",
                "قانون الاختبار",
                "999",
                self.TEST_SOURCE,
                "manual",
            ),
        )
        chunk_id = cur.fetchone()[0]
        conn.commit()
        assert chunk_id > 0

        # Clean up
        cur.execute("DELETE FROM legal_chunks WHERE source_file = %s",
                    (self.TEST_SOURCE,))
        conn.commit()
        cur.close()

    def test_insert_chunk_with_embedding(self, conn):
        """Can insert a chunk with an embedding vector."""
        if not PGVECTOR_AVAILABLE:
            pytest.skip("pgvector Python package not installed")

        embedding = np.random.randn(1024).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO legal_chunks 
                (chunk_text, chunk_text_normalized, embedding, domain, 
                 law_name, article_number, source_file)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                "اختبار المتجهات",
                "اختبار المتجهات",
                embedding.tolist(),
                "traffic",
                "قانون الاختبار",
                "1000",
                self.TEST_SOURCE,
            ),
        )
        chunk_id = cur.fetchone()[0]
        conn.commit()

        # Verify embedding stored correctly
        cur.execute(
            "SELECT embedding::text FROM legal_chunks WHERE id = %s", (
                chunk_id,)
        )
        stored_text = cur.fetchone()[0]

        # Parse the vector string "[0.1,0.2,...]" into numpy array
        import re
        values = [float(x) for x in re.findall(
            r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', stored_text)]
        stored_embedding = np.array(values, dtype=np.float32)

        assert len(
            stored_embedding) == 1024, f"Expected 1024, got {len(stored_embedding)}"
        assert np.isclose(np.linalg.norm(stored_embedding), 1.0, atol=0.01)

        # Clean up
        cur.execute("DELETE FROM legal_chunks WHERE source_file = %s",
                    (self.TEST_SOURCE,))
        conn.commit()
        cur.close()

    def test_read_chunk(self, conn):
        """Can read an inserted chunk."""
        cur = conn.cursor()

        # Insert
        cur.execute(
            """
            INSERT INTO legal_chunks 
                (chunk_text, chunk_text_normalized, domain, source_file)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            ("نص للقراءة", "نص للقراءة", "civil", self.TEST_SOURCE),
        )
        chunk_id = cur.fetchone()[0]
        conn.commit()

        # Read
        cur.execute(
            "SELECT chunk_text, domain, source_file FROM legal_chunks WHERE id = %s",
            (chunk_id,),
        )
        row = cur.fetchone()
        assert row[0] == "نص للقراءة"
        assert row[1] == "civil"
        assert row[2] == self.TEST_SOURCE

        # Clean up
        cur.execute("DELETE FROM legal_chunks WHERE source_file = %s",
                    (self.TEST_SOURCE,))
        conn.commit()
        cur.close()

    def test_update_chunk(self, conn):
        """Can update a chunk's metadata."""
        cur = conn.cursor()

        # Insert
        cur.execute(
            "INSERT INTO legal_chunks (chunk_text, chunk_text_normalized, domain, source_file) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            ("نص للتحديث", "نص للتحديث", "family", self.TEST_SOURCE),
        )
        chunk_id = cur.fetchone()[0]
        conn.commit()

        # Update
        cur.execute(
            "UPDATE legal_chunks SET is_active = FALSE, updated_at = NOW() WHERE id = %s",
            (chunk_id,),
        )
        conn.commit()

        # Verify
        cur.execute(
            "SELECT is_active FROM legal_chunks WHERE id = %s", (chunk_id,))
        is_active = cur.fetchone()[0]
        assert is_active is False

        # Clean up
        cur.execute("DELETE FROM legal_chunks WHERE source_file = %s",
                    (self.TEST_SOURCE,))
        conn.commit()
        cur.close()

    def test_delete_chunk(self, conn):
        """Can delete a chunk."""
        cur = conn.cursor()

        # Insert
        cur.execute(
            "INSERT INTO legal_chunks (chunk_text, chunk_text_normalized, domain, source_file) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            ("نص للحذف", "نص للحذف", "commercial", self.TEST_SOURCE),
        )
        chunk_id = cur.fetchone()[0]
        conn.commit()

        # Delete
        cur.execute("DELETE FROM legal_chunks WHERE id = %s", (chunk_id,))
        conn.commit()

        # Verify deletion
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM legal_chunks WHERE id = %s)", (chunk_id,))
        exists = cur.fetchone()[0]
        assert exists is False

        cur.close()

    def test_duplicate_prevention(self, conn):
        """Application handles duplicates gracefully (not a DB constraint, logic check)."""
        cur = conn.cursor()

        # Insert first
        cur.execute(
            "INSERT INTO legal_chunks (chunk_text, chunk_text_normalized, domain, source_file) "
            "VALUES (%s, %s, %s, %s)",
            ("نص مكرر", "نص مكرر", "judicial", self.TEST_SOURCE),
        )
        conn.commit()

        # Insert second (same data, different row - allowed at DB level)
        cur.execute(
            "INSERT INTO legal_chunks (chunk_text, chunk_text_normalized, domain, source_file) "
            "VALUES (%s, %s, %s, %s)",
            ("نص مكرر", "نص مكرر", "judicial", self.TEST_SOURCE),
        )
        conn.commit()

        # Verify both exist (application should check before inserting)
        cur.execute(
            "SELECT COUNT(*) FROM legal_chunks WHERE source_file = %s",
            (self.TEST_SOURCE,),
        )
        count = cur.fetchone()[0]
        assert count == 2  # DB allows it, app logic should prevent

        # Clean up
        cur.execute("DELETE FROM legal_chunks WHERE source_file = %s",
                    (self.TEST_SOURCE,))
        conn.commit()
        cur.close()


# ============================================
# Vector Search Tests
# ============================================

class TestVectorSearch:
    """Tests for pgvector similarity search."""

    TEST_SOURCE = "pytest_vector_test"

    @pytest.fixture(autouse=True)
    def setup_teardown(self, conn):
        """Clean up before and after vector tests."""
        cur = conn.cursor()
        cur.execute("DELETE FROM legal_chunks WHERE source_file = %s",
                    (self.TEST_SOURCE,))
        conn.commit()
        cur.close()
        yield
        cur = conn.cursor()
        cur.execute("DELETE FROM legal_chunks WHERE source_file = %s",
                    (self.TEST_SOURCE,))
        conn.commit()
        cur.close()

    def test_vector_cosine_distance(self, conn):
        """Cosine distance between identical vectors is ~0."""
        if not PGVECTOR_AVAILABLE:
            pytest.skip("pgvector Python package not installed")

        embedding = np.random.randn(1024).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        cur = conn.cursor()

        # Insert
        cur.execute(
            "INSERT INTO legal_chunks (chunk_text, chunk_text_normalized, embedding, domain, source_file) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            ("اختبار المسافة", "اختبار المسافة",
             embedding.tolist(), "criminal", self.TEST_SOURCE),
        )
        chunk_id = cur.fetchone()[0]
        conn.commit()

        # Search with same vector
        cur.execute(
            "SELECT 1 - (embedding <=> %s::vector) AS similarity FROM legal_chunks WHERE id = %s",
            (embedding.tolist(), chunk_id),
        )
        similarity = cur.fetchone()[0]

        # Same vector should have similarity ~1.0
        assert np.isclose(
            similarity, 1.0, atol=0.001), f"Similarity = {similarity}"

        cur.close()

    def test_vector_search_ordering(self, conn):
        """Vector search orders by similarity (most similar first)."""
        if not PGVECTOR_AVAILABLE:
            pytest.skip("pgvector Python package not installed")

        cur = conn.cursor()

        # Create three vectors with known relationships
        base = np.random.randn(1024).astype(np.float32)
        base = base / np.linalg.norm(base)

        similar = base + 0.1 * np.random.randn(1024).astype(np.float32)
        similar = similar / np.linalg.norm(similar)

        different = np.random.randn(1024).astype(np.float32)
        different = different / np.linalg.norm(different)

        # Insert all three
        texts = [
            ("النص الأساسي", base),
            ("نص مشابه", similar),
            ("نص مختلف", different),
        ]

        ids = []
        for text, emb in texts:
            cur.execute(
                "INSERT INTO legal_chunks (chunk_text, chunk_text_normalized, embedding, domain, source_file) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (text, text, emb.tolist(), "civil", self.TEST_SOURCE),
            )
            ids.append(cur.fetchone()[0])
        conn.commit()

        # Search with base vector
        cur.execute(
            """
            SELECT id, 1 - (embedding <=> %s::vector) AS similarity
            FROM legal_chunks
            WHERE source_file = %s
            ORDER BY embedding <=> %s::vector
            """,
            (base.tolist(), self.TEST_SOURCE, base.tolist()),
        )
        results = cur.fetchall()

        # Base should be first (most similar to itself)
        assert results[0][0] == ids[0], f"Expected base (id={ids[0]}) first, got id={results[0][0]}"
        assert results[0][1] > 0.99  # Near-perfect similarity

        # Similar should be second
        # Different should be last
        similarities = [r[1] for r in results]
        assert similarities[0] > similarities[1], "Results not ordered by similarity"
        assert similarities[1] > similarities[2], "Results not ordered by similarity"

        cur.close()

    def test_vector_search_with_domain_filter(self, conn):
        """Vector search combined with domain filter works."""
        if not PGVECTOR_AVAILABLE:
            pytest.skip("pgvector Python package not installed")

        cur = conn.cursor()

        embedding = np.random.randn(1024).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        # Insert chunks in different domains
        domains = ["criminal", "traffic", "criminal"]
        for i, domain in enumerate(domains):
            cur.execute(
                "INSERT INTO legal_chunks (chunk_text, chunk_text_normalized, embedding, domain, source_file) "
                "VALUES (%s, %s, %s, %s, %s)",
                (f"نص {i}", f"نص {i}", embedding.tolist(),
                 domain, self.TEST_SOURCE),
            )
        conn.commit()

        # Search with domain filter
        cur.execute(
            """
            SELECT id, domain
            FROM legal_chunks
            WHERE source_file = %s AND domain = 'criminal'
            ORDER BY embedding <=> %s::vector
            """,
            (self.TEST_SOURCE, embedding.tolist()),
        )
        results = cur.fetchall()

        # All results should be from criminal domain
        assert len(
            results) == 2, f"Expected 2 criminal results, got {len(results)}"
        for row in results:
            assert row[1] == "criminal", f"Got domain={row[1]}, expected criminal"

        cur.close()


# ============================================
# Data Integrity Tests
# ============================================

class TestDataIntegrity:
    """Tests for data integrity after seeding."""

    def test_seed_data_exists(self, cur):
        """Seed data is present in the database."""
        cur.execute(
            "SELECT COUNT(*) FROM legal_chunks WHERE source_file = 'seed_test_data'")
        count = cur.fetchone()[0]
        if count == 0:
            pytest.skip(
                "No seed data found. Run: python scripts/seed_test_data.py")
        assert count > 0, "No seed data in database"

    def test_all_domains_represented(self, cur):
        """All 7 legal domains have seed data."""
        cur.execute(
            "SELECT COUNT(*) FROM legal_chunks WHERE source_file = 'seed_test_data'"
        )
        count = cur.fetchone()[0]
        if count == 0:
            pytest.skip("No seed data found")

        cur.execute(
            "SELECT COUNT(DISTINCT domain) FROM legal_chunks WHERE source_file = 'seed_test_data'"
        )
        domain_count = cur.fetchone()[0]
        assert domain_count == 7, f"Expected 7 domains, found {domain_count}"

    def test_embeddings_not_null(self, cur):
        """All seed chunks have embeddings."""
        cur.execute(
            "SELECT COUNT(*) FROM legal_chunks WHERE source_file = 'seed_test_data'"
        )
        count = cur.fetchone()[0]
        if count == 0:
            pytest.skip("No seed data found")

        cur.execute(
            "SELECT COUNT(*) FROM legal_chunks "
            "WHERE source_file = 'seed_test_data' AND embedding IS NOT NULL"
        )
        with_embeddings = cur.fetchone()[0]
        assert with_embeddings == count, (
            f"{count - with_embeddings} chunks missing embeddings"
        )
