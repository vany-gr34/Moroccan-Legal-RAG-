# PostgreSQL + pgvector dans le RAG Juridique Marocain

> Pourquoi PostgreSQL, comment le schéma est conçu, et comment le déployer
> pour le système de Recherche-Juridique-Intelligent Marocain.

---

## 1. Pourquoi PostgreSQL ?

### 1.1 Le Problème

Un système RAG juridique a besoin de **quatre capacités** de stockage distinctes :

| Besoin | Exemple |
|--------|---------|
| **Documents structurés** | Articles de loi, métadonnées (domaine, chapitre, source) |
| **Texte intégral** | Recherche full-text en arabe (`tsvector`) |
| **Vecteurs sémantiques** | Embeddings 1024d pour la recherche par similarité |
| **JSON flexible** | Annotations, métadonnées variables par article |

Sans PostgreSQL, il faudrait **trois systèmes spécialisés** :
- Une base relationnelle (MySQL, SQLite) pour les métadonnées
- Un index vectoriel (FAISS, ChromaDB, Qdrant) pour les embeddings
- Un moteur full-text (Elasticsearch) pour la recherche lexicale

PostgreSQL + pgvector **unifie** tout cela en un seul système.

### 1.2 Comparaison avec les Alternatives

```
Critère              PostgreSQL+pgvector    ChromaDB/Qdrant    Elasticsearch
──────               ───────────────────    ───────────────    ─────────────
ACID transactions    ✅ Oui                 ❌ Non             ⚠️ Partiel
Full-text arabe      ✅ tsvector + pg_trgm  ❌ Non             ✅ Oui
Vector search        ✅ HNSW (pgvector)     ✅ Oui             ⚠️ Limité
JSON natif           ✅ JSONB               ❌ Non             ✅ Oui
Jointures SQL        ✅ Oui                 ❌ Non             ❌ Partiel
Maturité             ⭐ 30+ ans             ⭐ 5 ans           ⭐ 15 ans
Licence              Open Source (BSD)      Open Source        SSPL (restrictif)
Support UTF-8 arabe  ✅ Excellent           ✅ Bon             ✅ Excellent
```

### 1.3 Avantages Clés

| Avantage | Détail |
|----------|--------|
| **Unification** | Une seule base → un seul backup, une seule connexion, pas de synchro inter-systèmes |
| **Jointures hybrides** | Filtre par domaine SQL puis recherche vectorielle dans la même requête |
| **ACID** | Garantie que les embeddings et les métadonnées restent cohérents |
| **Maturité** | 30+ ans de développement, utilisé en production critique dans le monde entier |
| **Extensions** | pgvector, pg_trgm, unaccent — tout dans le même processus |
| **Performance** | HNSW index pour la recherche approximate nearest neighbor en < 10ms |

---

## 2. Architecture de la Base de Données

```
┌──────────────────────────────────────────────────────────────────┐
│                MOROCCAN LEGAL RAG — STACK DONNÉES                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL 16                          │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │              Extensions activées                    │  │   │
│  │  │                                                    │  │   │
│  │  │  vector     → embeddings 1024d + HNSW index        │  │   │
│  │  │  pg_trgm    → fuzzy text matching pour l'arabe     │  │   │
│  │  │  unaccent   → recherche sans diacritiques          │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │           Table unique : legal_chunks               │  │   │
│  │  │                                                    │  │   │
│  │  │  id               SERIAL PRIMARY KEY               │  │   │
│  │  │  chunk_text       TEXT                             │  │   │
│  │  │  chunk_text_norm  TEXT (normalisé)                 │  │   │
│  │  │  embedding        vector(1024)  ◄── pgvector       │  │   │
│  │  │  domain           VARCHAR(50)   ◄── CHECK          │  │   │
│  │  │  law_name         VARCHAR(255)                     │  │   │
│  │  │  article_number   VARCHAR(20)                      │  │   │
│  │  │  search_vector    tsvector      ◄── full-text      │  │   │
│  │  │  metadata         JSONB         ◄── flexible       │  │   │
│  │  │  ...                                                │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │                  Indexes                            │  │   │
│  │  │                                                    │  │   │
│  │  │  idx_embedding     HNSW (vector_cosine_ops)        │  │   │
│  │  │  idx_domain        B-tree                          │  │   │
│  │  │  idx_article       B-tree                          │  │   │
│  │  │  idx_search        GIN (tsvector)                  │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────┐     ┌────────────────┐     ┌──────────────┐ │
│  │   Python App    │────▶│  psycopg2      │────▶│  PostgreSQL  │ │
│  │   (src/db/)     │     │  get_connection │     │  + pgvector  │ │
│  └────────────────┘     └────────────────┘     └──────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Schéma Détaillé

### 3.1 Table `legal_chunks`

```sql
CREATE TABLE IF NOT EXISTS legal_chunks (
    id                   SERIAL PRIMARY KEY,
    chunk_text           TEXT NOT NULL,
    chunk_text_normalized TEXT NOT NULL,
    embedding            vector(1024),
    domain               VARCHAR(50) NOT NULL CHECK (domain IN (
        'traffic', 'criminal', 'family', 'civil',
        'commercial', 'judicial', 'violations', 'companies'
    )),
    law_name             VARCHAR(255),
    law_number           VARCHAR(50),
    article_number       VARCHAR(20),
    chapter_title        TEXT,
    section_title        TEXT,
    source_file          VARCHAR(500) NOT NULL,
    source_page          INTEGER,
    extraction_method    VARCHAR(50) CHECK (extraction_method IN (
        'digital', 'ocr', 'manual',
        'pymupdf', 'pdfplumber', 'pipeline'
    )),
    search_vector        tsvector
                         GENERATED ALWAYS AS (
                             to_tsvector('arabic', chunk_text_normalized)
                         ) STORED,
    ocr_confidence       FLOAT,
    metadata             JSONB DEFAULT '{}',
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW(),
    is_active            BOOLEAN DEFAULT TRUE
);
```

### 3.2 Indexes

```sql
-- HNSW index : recherche ANN (approximate nearest neighbor) en < 10ms
CREATE INDEX idx_legal_chunks_embedding
    ON legal_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- Filtres rapides par domaine, article, source
CREATE INDEX idx_legal_chunks_domain ON legal_chunks(domain);
CREATE INDEX idx_legal_chunks_article ON legal_chunks(article_number);
CREATE INDEX idx_legal_chunks_source ON legal_chunks(source_file);
CREATE INDEX idx_legal_chunks_active ON legal_chunks(is_active);

-- Full-text search en arabe
CREATE INDEX idx_legal_chunks_search
    ON legal_chunks USING GIN(search_vector);
```

### 3.3 Relations Conceptuelles

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MODÈLE DE DONNÉES CONCEPTUEL                      │
│                                                                     │
│  Un article de loi est représenté par UN enregistrement dans        │
│  legal_chunks, avec :                                               │
│                                                                     │
│  ┌────────────┐                                                     │
│  │  Domaine   │──── law_name, domain                                │
│  │  Juridique │                                                     │
│  └────────────┘                                                     │
│        │                                                            │
│        ▼                                                            │
│  ┌────────────────┐                                                 │
│  │   law_number   │── Loi numéro X (ex: 1-78 pour DOC)              │
│  └────────────────┘                                                 │
│        │                                                            │
│        ├──────────────────────┬──────────────────┐                  │
│        ▼                      ▼                  ▼                  │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐          │
│  │ section_title │   │ chapter_title│   │ article_number │          │
│  └──────────────┘   └──────────────┘   └────────────────┘          │
│        │                      │                  │                  │
│        └──────────────────────┴──────────────────┘                  │
│                               │                                     │
│                               ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      chunk_text                               │  │
│  │  Texte intégral de l'article en arabe                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                               │                                     │
│                               ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      embedding (vector 1024d)                 │  │
│  │  Généré par E5-large, stocké dans pgvector                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.4 Workflow d'Insertion

```
Document Brut ──► NLP Pipeline ──► Chunk ──► Embedding ──► PostgreSQL
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │  INSERT INTO     │
                                            │  legal_chunks    │
                                            │  (chunk_text,    │
                                            │   embedding,     │
                                            │   domain,        │
                                            │   article_number,│
                                            │   ...)           │
                                            └──────────────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │  HNSW index      │
                                            │  rebuilt auto    │
                                            └──────────────────┘
```

---

## 4. Recherche : Comment pgvector Fonctionne

### 4.1 Requête Vectorielle

```sql
-- Trouver les 5 articles les plus proches sémantiquement
SELECT
    id, chunk_text, article_number, law_name,
    1 - (embedding <=> '[0.01, -0.03, ...]'::vector) AS similarity
FROM legal_chunks
WHERE is_active = TRUE
  AND domain = 'criminal'
ORDER BY embedding <=> '[0.01, -0.03, ...]'::vector
LIMIT 5;
```

L'opérateur `<=>` calcule la **distance cosinus** entre le vecteur de la requête
et chaque embedding stocké. L'index HNSW accélère cette recherche de O(n) à O(log n).

### 4.2 Recherche Hybride (avec le code Python)

```python
def hybrid_search(query_embedding, domain=None, top_k=10, alpha=0.7):
    """Hybride : vectoriel (pgvector) + lexical (tsvector)."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            # Partie vectorielle
            cur.execute("""
                SELECT id, chunk_text, article_number, domain,
                       1 - (embedding <=> %s::vector) AS vector_score
                FROM legal_chunks
                WHERE is_active = TRUE
                  AND (%s IS NULL OR domain = %s)
                ORDER BY embedding <=> %s::vector
                LIMIT 20
            """, (query_embedding, domain, domain, query_embedding))
            dense_results = cur.fetchall()

            # Partie BM25 (via PostgreSQL tsvector)
            cur.execute("""
                SELECT id, chunk_text, article_number, domain,
                       ts_rank(search_vector, plainto_tsquery('arabic', %s))
                       AS bm25_score
                FROM legal_chunks
                WHERE search_vector @@ plainto_tsquery('arabic', %s)
                  AND (%s IS NULL OR domain = %s)
                ORDER BY bm25_score DESC
                LIMIT 20
            """, (query_text, query_text, domain, domain))
            bm25_results = cur.fetchall()

            # Fusion pondérée (alpha)
            return fuse_hybrid(dense_results, bm25_results, alpha, top_k)
```

### 4.3 HNSW Index — Paramètres

| Paramètre | Valeur | Rôle |
|-----------|--------|------|
| `m` | 16 | Degré du graphe (connexions par nœud) |
| `ef_construction` | 200 | Taille de la liste dynamique à la construction |
| `ef_search` | 100 | Taille de la liste dynamique à la recherche (config PostgreSQL) |

Ces valeurs offrent un bon équilibre **précision ~ vs ~ vitesse** pour un corpus
de taille petite à moyenne (< 100k documents).

---

## 5. Déploiement

### 5.1 Avec Docker (Production / Développement)

```yaml
# docker-compose.yaml (extrait)
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
      start_period: 15s
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2'
```

### 5.2 Image Docker Personnalisée

```dockerfile
# docker/Dockerfile.postgres (extrait)
FROM postgres:16

# Installation de pgvector depuis les sources
RUN apt-get update && apt-get install -y \
    build-essential postgresql-server-dev-16 git \
    && git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git \
    && cd pgvector && make && make install

# Locales arabes et françaises
RUN echo "ar_SA.UTF-8 UTF-8" >> /etc/locale.gen \
    && echo "fr_FR.UTF-8 UTF-8" >> /etc/locale.gen \
    && locale-gen
```

### 5.3 Configuration PostgreSQL

```ini
# docker/config/postgresql.conf (extrait)
shared_buffers = 256MB            # Mémoire pour le cache de données
work_mem = 64MB                   # Mémoire par opération de tri
maintenance_work_mem = 128MB      # Mémoire pour VACUUM, CREATE INDEX
effective_cache_size = 1GB        # Estimation du cache OS
random_page_cost = 1.1            # SSD → coût faible
effective_io_concurrency = 200    # I/O parallèle
max_connections = 50              # Suffisant pour le RAG
hnsw.ef_search = 100              # Qualité de recherche HNSW
```

---

## 6. Connexion depuis Python

```python
from src.db import get_connection

# Connexion (utilise les variables d'environnement POSTGRES_*)
conn = get_connection()

# Exemple : insérer un chunk avec son embedding
with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO legal_chunks
            (chunk_text, chunk_text_normalized, embedding,
             domain, law_name, article_number, source_file)
        VALUES (%s, %s, %s::vector, %s, %s, %s, %s)
    """, (
        article_text,
        normalized_text,
        embedding.tolist(),       # Liste Python → pgvector
        "criminal",
        "القانون الجنائي",
        "147",
        "data/processed/criminal/penal_law.pdf"
    ))
conn.commit()
```

### Variables d'Environnement

```bash
# .env (ou export)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=legal_rag
POSTGRES_USER=legal_rag_user
POSTGRES_PASSWORD=legal_rag_pass
```

---

## 7. Commandes Essentielles

```bash
# ─── Démarrer ──────────────────────────────────
docker compose up -d postgres

# ─── Vérifier que PostgreSQL est prêt ──────────
docker compose logs postgres          # Attendre "database system is ready"
docker compose ps                      # legal-rag-postgres: Up (healthy)

# ─── Connexion interactive ─────────────────────
docker exec -it legal-rag-postgres \
    psql -U legal_rag_user -d legal_rag

# ─── Tester pgvector ───────────────────────────
docker exec -it legal-rag-postgres \
    psql -U legal_rag_user -d legal_rag -c "SELECT '[1,2,3]'::vector;"

# ─── Compter les articles indexés ──────────────
docker exec -it legal-rag-postgres \
    psql -U legal_rag_user -d legal_rag \
    -c "SELECT domain, COUNT(*) FROM legal_chunks GROUP BY domain;"

# ─── Voir les indexes ──────────────────────────
docker exec -it legal-rag-postgres \
    psql -U legal_rag_user -d legal_rag \
    -c "\di"

# ─── Backup / Restore ──────────────────────────
docker exec -t legal-rag-postgres \
    pg_dump -U legal_rag_user legal_rag > backup.sql
docker exec -i legal-rag-postgres \
    psql -U legal_rag_user legal_rag < backup.sql

# ─── Arrêter (données persistées) ──────────────
docker compose down

# ─── Arrêter et tout effacer ───────────────────
docker compose down -v
```

### Makefile Helpers

```bash
make test-database   # Teste la connexion et les opérations DB
```

---

## 8. Points d'Attention

| Point | Explication |
|-------|-------------|
| **Locale UTF-8** | PostgreSQL 16 utilise `C.UTF-8` pour l'init — l'arabe fonctionne car c'est de l'UTF-8, mais le tri alphabétique arabe n'est pas utilisé |
| **Dimensions du vecteur** | `vector(1024)` correspond exactement à la sortie de `E5-large` (1024d). Si vous changez de modèle, mettez à jour la table via `ALTER TABLE ... ALTER COLUMN embedding TYPE vector(N)`. |
| **HNSW vs IVFFlat** | HNSW est plus rapide et plus précis à la recherche, mais consomme plus de mémoire et prend plus de temps à construire. Pour les corpus < 100k, HNSW est le meilleur choix. |
| **psycopg2** | La bibliothèque Python `psycopg2` gère nativement les conversions `list ↔ vector` via le protocol binaire de PostgreSQL. |
| **is_active** | Le flag `is_active` permet de désactiver des chunks sans les supprimer — utile pour les mises à jour de corpus sans downtime. |

---

## 9. Références

| Ressource | Lien |
|-----------|------|
| pgvector GitHub | [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) |
| PostgreSQL 16 docs | [postgresql.org/docs/16](https://www.postgresql.org/docs/16/) |
| HNSW paper (Malkov & Yashunin) | arXiv:1603.09320 |
| Module connexion Python | `src/db/session.py` |
| Schéma SQL | `database/init_db.sql` |
| Dockerfile PostgreSQL | `docker/Dockerfile.postgres` |
| Configuration | `docker/config/postgresql.conf` |
