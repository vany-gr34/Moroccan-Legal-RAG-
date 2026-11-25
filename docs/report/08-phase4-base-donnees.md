# 8. Phase 4 -- Infrastructure Base de Donnees

---

## 8.1 Choix de PostgreSQL + pgvector

### Comparaison avec les alternatives

```
+------------------+     +------------------+     +------------------+
|   PostgreSQL      |     |    ChromaDB      |     |     Qdrant       |
|   + pgvector      |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
|                    VS                          VS                    |
+------------------+     +------------------+     +------------------+
| Transactions ACID |     | Pas de transactions|    | Pas de transactions|
| SQL standard      |     | API proprietaire   |    | API proprietaire   |
| Maturite 30+ ans  |     | Projet recent      |    | Projet recent      |
| Full-text search  |     | Pas de FTS         |    | Pas de FTS         |
+------------------+     +------------------+     +------------------+
```

### Critere de decision

| Critere                     | PostgreSQL+pgvector | ChromaDB | Qdrant |
|-----------------------------|---------------------|----------|--------|
| Recherche vectorielle       | HNSW, IVFFlat       | Oui      | Oui    |
| Full-text search            | tsvector (arabe)    | Non      | Non    |
| Transactions ACID           | Oui                 | Non      | Non    |
| Jointures SQL               | Oui                 | Non      | Non    |
| Maturite                    | 30+ ans            | < 3 ans  | < 5 ans|
| Support arabe (UTF-8)       | Excellent           | Bon      | Bon    |
| Outils d'admin (pgAdmin)    | Oui                 | Non      | Non    |
| Backup / Restore            | pg_dump natif       | Manuel   | Manuel |

**Choix : PostgreSQL 16 + pgvector 0.7.4**

## 8.2 Schema de Base de Donnees

```
+====================================================================+
|                    SCHEMA legal_rag                                |
+====================================================================+
|                                                                    |
|  +--------------------------+     +---------------------------+    |
|  |       legal_chunks       |     |       conversations        |    |
|  +--------------------------+     +---------------------------+    |
|  | id (SERIAL PK)           |     | id (SERIAL PK)            |    |
|  | article_number (VARCHAR) |     | session_id (UUID)         |    |
|  | law_name (VARCHAR)       |     | question (TEXT)           |    |
|  | domain (VARCHAR)         |     | answer (TEXT)             |    |
|  | chapter_title (VARCHAR)  |     | sources (JSONB)           |    |
|  | section_title (VARCHAR)  |     | created_at (TIMESTAMPTZ)  |    |
|  | chunk_text (TEXT)        |     +---------------------------+    |
|  | chunk_text_normalized    |                                      |
|  | source_file (VARCHAR)    |     +---------------------------+    |
|  | embedding (vector(1024)) |     |      search_log           |    |
|  | search_vector (tsvector) |     +---------------------------+    |
|  | is_active (BOOLEAN)      |     | id (SERIAL PK)            |    |
|  | created_at (TIMESTAMPTZ) |     | query (TEXT)              |    |
|  +--------------------------+     | domain (VARCHAR)          |    |
|           |                       | strategy (VARCHAR)        |    |
|           |                       | results_count (INT)       |    |
|           v                       | time_ms (FLOAT)           |    |
|  +--------------------------+     | created_at (TIMESTAMPTZ)  |    |
|  |  INDEXES                 |     +---------------------------+    |
|  +--------------------------+                                      |
|  | embedding_idx (HNSW)     |                                      |
|  |   USING hnsw             |                                      |
|  |   WITH (m=16, ef=64)     |                                      |
|  |                          |                                      |
|  | search_vector_idx (GIN)  |                                      |
|  | domain_idx (BTREE)       |                                      |
|  | article_number_idx (BTREE)|                                     |
|  | is_active_idx (BTREE)    |                                      |
|  +--------------------------+                                      |
+====================================================================+
```

## 8.3 Indexation pgvector

### Configuration HNSW

```sql
CREATE INDEX embedding_idx ON legal_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);

-- Pour la recherche : SET hnsw.ef_search = 100;
```

| Parametre     | Valeur | Description                               |
|---------------|--------|--------------------------------------------|
| m             | 16     | Nombre de connexions par noeud             |
| ef_construction| 200   | Taille de la liste dynamique a la construction |
| ef_search     | 100    | Taille de la liste dynamique a la recherche    |
| ops           | cosine | Operateur de similarite cosinus            |

### Performance attendue

| Metrique            | Sans index (seq scan) | Avec HNSW   |
|---------------------|-----------------------|-------------|
| Recherche top-5     | ~50 ms                | ~2 ms       |
| Recherche top-50    | ~200 ms               | ~5 ms       |
| Insertion (batch)   | 100/s                 | 50/s        |
| Taille index        | 0                     | ~15 Mo      |

## 8.4 Full-Text Search Arabe

### Configuration PostgreSQL

```sql
-- Creation de la colonne tsvector
ALTER TABLE legal_chunks
ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('arabic', COALESCE(chunk_text_normalized, chunk_text))
) STORED;

CREATE INDEX search_vector_idx ON legal_chunks USING GIN (search_vector);

-- Requete de recherche plein-texte
SELECT * FROM legal_chunks
WHERE is_active = TRUE
  AND search_vector @@ plainto_tsquery('arabic', 'عقوبة السرقة')
ORDER BY ts_rank(search_vector, plainto_tsquery('arabic', 'عقوبة السرقة')) DESC
LIMIT 5;
```

### Limite du FTS arabe PostgreSQL

Le dictionnaire `arabic` de PostgreSQL est basique (pas de racination
morphologique avancee). Pour compenser, nous utilisons egalement
**rank-bm25** (Python) pour le BM25 lexical avec un meilleur tokenizer.

## 8.5 Deploiement Docker

```yaml
# Extrait de docker-compose.yaml
services:
  postgres:
    build:
      dockerfile: docker/Dockerfile.postgres
      args:
        PG_MAJOR: 16
        PGVECTOR_VERSION: 0.7.4
    image: moroccan-legal-rag-db:latest
    container_name: legal-rag-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: legal_rag
      POSTGRES_USER: legal_rag_user
      POSTGRES_PASSWORD: legal_rag_pass
      POSTGRES_INITDB_ARGS: "--locale=C.UTF-8 --encoding=UTF8"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init_db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U legal_rag_user -d legal_rag"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2'
```
