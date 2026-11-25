# 4. Architecture Globale du Systeme

---

## 4.1 Vue d'Ensemble

```
+===========================================================================+
|                MOROCCAN LEGAL RAG - ARCHITECTURE GLOBALE                  |
+===========================================================================+
|                                                                           |
|  +-----------------+     +------------------+     +-------------------+   |
|  |    SOURCES      |     |    INGESTION     |     |     STOCKAGE      |   |
|  |                 |     |                  |     |                   |   |
|  |  PDF Scannes    | --> |  EasyOCR + VLM   | --> |  PostgreSQL 16    |   |
|  |  PDF Texte      |     |  Correction      |     |  + pgvector 0.7   |   |
|  |  Textes Web     |     |  Nettoyage       |     |  + indices HNSW   |   |
|  +-----------------+     +------------------+     +--------+----------+   |
|                                                           |              |
|  +--------------------------------------------------------+              |
|  |                                                                        |
|  |  +------------------+     +-------------------+                        |
|  |  |    RECHERCHE     |     |    GENERATION     |                        |
|  |  |                  |     |                   |                        |
|  |  |  [Dense]         |     |  Prompt Builder   |                        |
|  |  |  [BM25]          | --> |  Gemma 4 (2B)     | --> REPONSE JURIDIQUE  |
|  |  |  [RRF Hybride]   |     |  llama.cpp        |                        |
|  |  +------------------+     +-------------------+                        |
|  |                                                                        |
|  +-------------------- CONTROLE QUALITE ---------------------------------+ |
|  |  Nettoyage . Normalisation . Validation . Benchmarks . Tests          | |
|  +-----------------------------------------------------------------------+ |
|                                                                           |
|  +-------------------- INTERFACES ----------------------------------------+ |
|  |  +----------------+   +----------------+   +----------------+          | |
|  |  |   API REST     |   |   Interface    |   |   TUI & CLI    |          | |
|  |  |   FastAPI      |   |   SvelteKit    |   |   Textual      |          | |
|  |  +----------------+   +----------------+   +----------------+          | |
|  +-----------------------------------------------------------------------+ |
|                                                                           |
+===========================================================================+
```

## 4.2 Stack Technique Detaillee

```
+----------------------------------------------+
|              COUCHE PRESENTATION              |
|  +-------------------+  +------------------+  |
|  | SvelteKit 5       |  | TUI (Textual)    |  |
|  | Tailwind CSS 4    |  | CLI (scripts/)   |  |
|  | TypeScript 6      |  | Python           |  |
|  +--------+----------+  +--------+---------+  |
|           |                      |            |
+-----------+----------------------+------------+
            |                      |
+-----------v----------------------v------------+
|              COUCHE API (FastAPI)              |
|  /ask  /search  /laws  /upload  /health       |
|  Pydantic v2  CORS  async/await               |
+-----------------------+-----------------------+
                        |
        +---------------+---------------+
        |                               |
+-------v--------+            +--------v--------+
|  RECHERCHE     |            |  GENERATION     |
|  Hybride/Dense |            |  Gemma 4 (2B)   |
|  BM25 / RRF    |            |  llama.cpp      |
|  Embedder E5   |            |  Remote/OpenAI  |
+-------+--------+            +--------+--------+
        |                               |
+-------v-------------------------------v--------+
|          COUCHE DONNEES (PostgreSQL 16)         |
|  pgvector 0.7.4  HNSW  Full-text  Arabic UTF8 |
+-----------------------+-----------------------+
                        |
+-----------------------v-----------------------+
|              COUCHE INGESTION                   |
|  PyMuPDF  EasyOCR  VLM  Camel-Tools           |
|  Cleaning  Normalization  Structure Parser     |
+-----------------------------------------------+
```

## 4.3 Flux de Donnees Principal

```
                         UTILISATEUR
                              |
                    Question en arabe
                              |
                              v
              +-------------------------------+
              |         API FastAPI            |
              |   POST /api/v1/ask            |
              +-------------------------------+ 
                              |
              +---------------+---------------+
              |                               |
              v                               v
    +------------------+          +-----------------------+
    | Embedder E5-large|          |   BM25 (rank-bm25)    |
    | (Cloudflare       |          |   Chargement corpus   |
    |  Tunnel -> Colab) |          |   en memoire          |
    +--------+---------+          +-----------+-----------+
             |                                |
             v                                v
    +------------------+          +-----------------------+
    | pgvector cosine  |          | ts_rank + normalise   |
    | similarity       |          | PostgreSQL FTS        |
    +--------+---------+          +-----------+-----------+
             |                                |
             +---------------+----------------+
                             |
                             v
              +-------------------------------+
              |   Fusion RRF (k=60)           |
              |   Reciprocal Rank Fusion      |
              +-------------------------------+
                             |
                             v
              +-------------------------------+
              |        Top-K Articles         |
              |   (K=5, avec scores)          |
              +-------------------------------+
                             |
                             v
              +-------------------------------+
              |      Prompt Construction      |
              |  System: assistant juridique  |
              |  Context: [articles retrouves]|
              |  Question: [query utilisateur]|
              +-------------------------------+
                             |
                             v
              +-------------------------------+
              |     LLM Gemma 4 (2B)          |
              |     llama.cpp / OpenAI API    |
              |     temperature=0.3           |
              +-------------------------------+
                             |
                             v
              +-------------------------------+
              |     Reponse + Sources         |
              |  - reponse en arabe           |
              |  - articles cites             |
              |  - disclaimer                 |
              +-------------------------------+
```

## 4.4 Services et Communication

```
+------------------+        +------------------+        +------------------+
|  Machine Locale  |        |  Cloudflare       |        |  Google Colab    |
|                  |        |  Tunnel           |        |  (GPU T4)        |
|  +------------+  |  HTTP  |  +------------+   |  HTTP  |  +------------+  |
|  | FastAPI    +----------->| trycloudflare+------------>| Embedding   |  |
|  | PostgreSQL |  |        |  .com        |   |        |  Service     |  |
|  | llama.cpp  |  |        +------------+   |        |  (E5-large)  |  |
|  +------------+  |                         |        +------------+  |
+------------------+                         +-------------------------+

+------------------------------------------------------------------+
|                DEPLOIEMENT DOCKER COMPOSE                         |
|                                                                  |
|  +------------------+   +------------------+   +--------------+  |
|  | legal-rag-postgres|   | pgadmin         |   | api (FastAPI) |  |
|  | postgres:16       |   | (dpage/pgadmin4)|   | custom image  |  |
|  | pgvector:0.7.4    |   | port 5050       |   | port 8000     |  |
|  +------------------+   +------------------+   +--------------+  |
|                                                                  |
+------------------------------------------------------------------+
```
