-- ============================================
-- Moroccan Legal RAG - Database Initialization
-- ============================================

-- Enable pgvector for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pg_trgm for fuzzy text matching (useful for Arabic)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable unaccent for diacritic-insensitive search
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ============================================
-- Core table: legal chunks with embeddings
-- ============================================
CREATE TABLE IF NOT EXISTS legal_chunks (
    id              SERIAL PRIMARY KEY,
    chunk_text      TEXT NOT NULL,
    chunk_text_normalized TEXT NOT NULL,
    embedding       vector(1024),
    domain VARCHAR(50) NOT NULL CHECK (domain IN (
    'traffic', 'criminal', 'family', 'civil',
    'commercial', 'judicial', 'violations', 'companies'
)),
    law_name        VARCHAR(255),
    law_number      VARCHAR(50),
    article_number  VARCHAR(20),
    chapter_title   TEXT,
    section_title   TEXT,
    source_file     VARCHAR(500) NOT NULL,
    source_page     INTEGER,
    extraction_method VARCHAR(50) CHECK (extraction_method IN (
    'digital', 'ocr', 'manual',
    'pymupdf', 'pdfplumber', 'pipeline'
    )),
    search_vector   tsvector GENERATED ALWAYS AS (to_tsvector('arabic', chunk_text_normalized)) STORED,
    ocr_confidence  FLOAT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE
);

-- ============================================
-- Indexes
-- ============================================

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_legal_chunks_embedding
    ON legal_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- B-tree indexes for metadata filtering
CREATE INDEX IF NOT EXISTS idx_legal_chunks_domain ON legal_chunks(domain);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_article ON legal_chunks(article_number);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_source ON legal_chunks(source_file);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_active ON legal_chunks(is_active);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_search ON legal_chunks USING GIN(search_vector);

-- ============================================
-- Conversations table (LLM chat history)
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id          SERIAL PRIMARY KEY,
    session_id  VARCHAR(64) NOT NULL,
    role        VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL,
    sources     JSONB,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);

-- ============================================
-- Verification
-- ============================================
DO $$
BEGIN
    RAISE NOTICE 'Database initialization complete. Extensions: vector, pg_trgm, unaccent.';
    RAISE NOTICE 'Table legal_chunks created with HNSW index.';
    RAISE NOTICE 'Table conversations created with session index.';
END $$;