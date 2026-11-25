#!/bin/bash
# ============================================
# PostgreSQL Database Inspection Script
# ============================================
# Usage:
#   chmod +x scripts/inspect_db.sh
#   ./scripts/inspect_db.sh
#   ./scripts/inspect_db.sh --extensions
#   ./scripts/inspect_db.sh --tables
#   ./scripts/inspect_db.sh --indexes
#   ./scripts/inspect_db.sh --chunks
#   ./scripts/inspect_db.sh --domains
#   ./scripts/inspect_db.sh --all
# ============================================

set -e

# Load .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Connection details (defaults if .env not set)
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-legal_rag}"
DB_USER="${POSTGRES_USER:-legal_rag_user}"
DB_PASS="${POSTGRES_PASSWORD:-legal_rag_pass}"

# psql connection string
CONN="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
PSQL="docker exec -i legal-rag-postgres psql -U ${DB_USER} -d ${DB_NAME}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# Helper functions
# ============================================

header() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

query() {
    echo -e "${YELLOW}→ $1${NC}"
    echo ""
}

# ============================================
# Inspection commands
# ============================================

show_extensions() {
    header "Installed Extensions"
    query "Check pgvector, pg_trgm, unaccent are installed"
    $PSQL <<EOF
SELECT 
    extname AS extension,
    extversion AS version,
    extowner::regrole AS owner
FROM pg_extension
ORDER BY extname;
EOF
}

show_tables() {
    header "Database Tables"
    query "Show all tables with row counts"
    $PSQL <<EOF
SELECT 
    schemaname AS schema,
    tablename AS table,
    n_live_tup AS estimated_rows
FROM pg_stat_user_tables
ORDER BY tablename;
EOF
}

show_table_structure() {
    header "Table: legal_chunks"
    query "Column names, types, and constraints"
    $PSQL <<EOF
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'legal_chunks'
ORDER BY ordinal_position;
EOF
}

show_indexes() {
    header "Indexes"
    query "All indexes on legal_chunks table"
    $PSQL <<EOF
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'legal_chunks'
ORDER BY indexname;
EOF
}

show_chunks_summary() {
    header "Chunks Summary"
    query "Total chunks, active/inactive, extraction methods"
    $PSQL <<EOF
SELECT 
    COUNT(*) AS total_chunks,
    COUNT(CASE WHEN is_active THEN 1 END) AS active,
    COUNT(CASE WHEN NOT is_active THEN 1 END) AS inactive,
    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) AS with_embedding,
    COUNT(CASE WHEN embedding IS NULL THEN 1 END) AS without_embedding
FROM legal_chunks;
EOF

    echo ""
    query "By extraction method"
    $PSQL <<EOF
SELECT 
    COALESCE(extraction_method, 'unknown') AS method,
    COUNT(*) AS count
FROM legal_chunks
GROUP BY extraction_method
ORDER BY count DESC;
EOF
}

show_domains() {
    header "Legal Domains"
    query "Chunks per domain"
    $PSQL <<EOF
SELECT 
    domain,
    COUNT(*) AS total,
    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) AS with_embedding,
    COUNT(CASE WHEN embedding IS NULL THEN 1 END) AS without_embedding
FROM legal_chunks
WHERE is_active = TRUE
GROUP BY domain
ORDER BY domain;
EOF
}

show_recent_chunks() {
    header "Recent Chunks (last 10 inserted)"
    query "Most recently added legal chunks"
    $PSQL <<EOF
SELECT 
    id,
    domain,
    law_name,
    article_number,
    LEFT(chunk_text, 80) AS preview,
    created_at
FROM legal_chunks
ORDER BY created_at DESC
LIMIT 10;
EOF
}

show_vector_stats() {
    header "Vector Embedding Statistics"
    query "Min, max, avg dimension of stored vectors"
    $PSQL <<EOF
SELECT 
    COUNT(*) AS total_vectors,
    MIN(vector_dims(embedding)) AS min_dim,
    MAX(vector_dims(embedding)) AS max_dim,
    ROUND(AVG(vector_dims(embedding)), 0) AS avg_dim
FROM legal_chunks
WHERE embedding IS NOT NULL;
EOF
}

show_full_text_search() {
    header "Full-Text Search Test"
    query "Search for 'عقوبة' (penalty) using tsvector"
    $PSQL <<EOF
SELECT 
    id,
    domain,
    LEFT(chunk_text, 100) AS preview,
    ts_rank(search_vector, query) AS rank
FROM legal_chunks, plainto_tsquery('arabic', 'عقوبة') query
WHERE search_vector @@ query
ORDER BY rank DESC
LIMIT 5;
EOF
}

show_vector_search_test() {
    header "Vector Search Test"
    query "Find chunks similar to a criminal law query (limit 5)"
    echo -e "${YELLOW}Note: This requires at least one chunk with an embedding${NC}"
    echo ""
    $PSQL <<EOF
WITH query_embedding AS (
    SELECT embedding 
    FROM legal_chunks 
    WHERE domain = 'criminal' AND embedding IS NOT NULL 
    LIMIT 1
)
SELECT 
    lc.id,
    lc.domain,
    LEFT(lc.chunk_text, 80) AS preview,
    1 - (lc.embedding <=> qe.embedding) AS similarity
FROM legal_chunks lc, query_embedding qe
WHERE lc.embedding IS NOT NULL
ORDER BY lc.embedding <=> qe.embedding
LIMIT 5;
EOF
}

show_source_files() {
    header "Source Files"
    query "Documents that have been ingested"
    $PSQL <<EOF
SELECT 
    source_file,
    COUNT(*) AS chunks,
    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) AS with_vectors,
    MIN(created_at) AS first_added,
    MAX(created_at) AS last_added
FROM legal_chunks
GROUP BY source_file
ORDER BY last_added DESC;
EOF
}

# ============================================
# Main
# ============================================

echo -e "${GREEN}Moroccan Legal RAG - Database Inspector${NC}"
echo -e "Connection: ${DB_HOST}:${DB_PORT}/${DB_NAME} as ${DB_USER}"
echo ""

# Check if PostgreSQL is running
if ! docker ps --format '{{.Names}}' | grep -q "legal-rag-postgres"; then
    echo -e "${YELLOW}⚠ PostgreSQL container not running.${NC}"
    echo "Start it with: docker-compose up -d"
    exit 1
fi

# Parse arguments
if [ $# -eq 0 ]; then
    # Default: show summary
    show_extensions
    show_tables
    show_chunks_summary
    show_domains
else
    for arg in "$@"; do
        case $arg in
            --extensions|-e)
                show_extensions
                ;;
            --tables|-t)
                show_tables
                show_table_structure
                ;;
            --indexes|-i)
                show_indexes
                ;;
            --chunks|-c)
                show_chunks_summary
                show_recent_chunks
                ;;
            --domains|-d)
                show_domains
                ;;
            --vectors|-v)
                show_vector_stats
                show_vector_search_test
                ;;
            --search|-s)
                show_full_text_search
                ;;
            --sources)
                show_source_files
                ;;
            --all|-a)
                show_extensions
                show_tables
                show_table_structure
                show_indexes
                show_chunks_summary
                show_domains
                show_recent_chunks
                show_vector_stats
                show_source_files
                show_full_text_search
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --extensions, -e    Show installed extensions"
                echo "  --tables, -t        Show table structures"
                echo "  --indexes, -i       Show indexes"
                echo "  --chunks, -c        Show chunks summary"
                echo "  --domains, -d       Show domain distribution"
                echo "  --vectors, -v       Show vector statistics + test search"
                echo "  --search, -s        Test full-text search"
                echo "  --sources           Show source files"
                echo "  --all, -a           Show everything"
                echo "  --help, -h          Show this help"
                exit 0
                ;;
            *)
                echo "Unknown option: $arg"
                echo "Use --help for usage"
                exit 1
                ;;
        esac
    done
fi

echo ""
echo -e "${GREEN}Done.${NC}"