# 15. Annexes

---

## Annexe A -- Structure Complete du Projet

```
Analyse-des-lois-justice-Maroc/
|
+-- benchmark/
|   +-- retrieval_benchmark.json       # Donnees de benchmark (32 questions)
|   +-- rag_benchmark.ipynb            # Notebook benchmark RAG complet
|   +-- output/                        # Resultats CSV + figures
|
+-- config/
|   +-- config.yaml                    # Configuration generale
|   +-- cleaning.yaml                  # Regles de nettoyage texte
|   +-- normalization.yaml             # Normalisation arabe
|   +-- ocr_config.yml                 # Configuration OCR
|   +-- retrieval_config.yml           # Configuration retrieval
|
+-- data/
|   +-- raw/                           # PDF bruts
|   +-- interim/                       # Donnees intermediaires (CSV)
|   +-- processed/                     # Corpus final (JSON par domaine)
|   |   +-- criminal/                  # Code penal, sanctions
|   |   +-- civil/                     # Code civil, procedure
|   |   +-- commercial/               # Registre commerce, societes
|   |   +-- traffic/                  # Code de la route
|   |   +-- judicial/                 # Organisation judiciaire
|   |   +-- tax/                      # Code general des impots
|   +-- raw_text/                      # Texte brut extrait
|   +-- uploaded/                      # Uploads utilisateur
|
+-- database/
|   +-- init_db.sql                    # Schema + indexation
|
+-- docker/
|   +-- Dockerfile.api                 # Image API FastAPI
|   +-- Dockerfile.postgres            # Image PostgreSQL + pgvector
|   +-- Dockerfile.web                 # Image frontend Svelte
|   +-- config/
|       +-- postgresql.conf            # Configuration PostgreSQL
|
+-- docs/
|   +-- Architecture/                  # Documents d'architecture (5 phases)
|   +-- Services/                      # Documentation des services
|   +-- report/                        # Rapport final (15 sections)
|   +-- embedding_model_benchmark.md   # Benchmark embedding
|   +-- retrieval_strategies_benchmark.md # Benchmark retrieval
|   +-- llm_serving_quantized_models.md# Guide LLM quantifie
|   +-- postgresql_legal_rag.md        # Guide PostgreSQL+pgvector
|
+-- notebooks/
|   +-- 01_ocr_quality_research.ipynb
|   +-- 02_embedding_colab_api.ipynb
|   +-- 03_embedding_models_benchmark.ipynb
|   +-- 04_ocr_service_colab.ipynb
|   +-- 05_reasearch_VLM.ipynb
|   +-- 06_benchmark_retreiving_strategies.ipynb
|   +-- 07_llm_api_colab_qwen2_5.ipynb
|
+-- scripts/
|   +-- embed_all_articles.py
|   +-- batch_process_pdfs.py
|   +-- run_preprocessing_pipeline.py
|   +-- seed_test_data.py
|   +-- check_retrieval_quality.py
|   +-- parse_legal_structure.py
|   +-- extract_raw_text.py
|   +-- debug_vector_search.py
|   +-- debug_cleaner.py
|   +-- generate_pdf_fixtures.py
|   +-- inspect_raw_text.py
|
+-- src/
|   +-- __init__.py
|   +-- main.py                        # Point d'entree FastAPI
|   +-- api/                           # Couche API
|   |   +-- dependencies.py
|   |   +-- routers/                   # health, search, laws, ask, upload
|   |   +-- schemas/
|   |   +-- middleware/
|   +-- core/                          # NLP et traitement
|   |   +-- embedding.py               # Embedder (local + distant)
|   |   +-- cleaning.py                # Nettoyage texte juridique
|   |   +-- normalizing.py             # Normalisation arabe
|   |   +-- structure.py               # Parsing structure articles
|   |   +-- block_parser.py            # Parsing blocs PDF
|   +-- db/                            # Acces base de donnees
|   |   +-- session.py                 # Gestion connexions
|   |   +-- conversations.py           # Historique conversations
|   +-- extraction/                    # Extraction PDF
|   |   +-- base.py                    # Interface abstraite
|   |   +-- factory.py                 # Factory extracteurs
|   |   +-- pdf_to_text_extractor.py  # Extraction PyMuPDF
|   +-- generation/                    # Generation LLM
|   |   +-- base.py                    # Interface abstraite
|   |   +-- factory.py                 # Factory LLM
|   |   +-- remote_llm.py             # Client LLM distant
|   +-- ingestion/                     # Pipeline ingestion
|   |   +-- pipeline.py                # Orchestrateur
|   |   +-- database.py                # Stockage DB
|   |   +-- embedder.py                # Embedding batch
|   |   +-- cli.py                     # CLI ingestion
|   |   +-- classifiers/
|   +-- ocr/                           # OCR
|   |   +-- easyocr_client.py          # Client EasyOCR
|   +-- preprocessing/                 # Preprocessing
|   |   +-- cleaner.py                 # LegalTextCleaner
|   |   +-- normalizer.py              # ArabicNormalizer
|   |   +-- structure_parser.py        # LegalStructureParser
|   +-- retrieval/                     # Recherche
|   |   +-- hybrid_search.py           # Factory + interface unifiee
|   |   +-- strategies/
|   |       +-- base.py                # Interface abstraite
|   |       +-- dense.py               # Dense (pgvector)
|   |       +-- bm25.py               # BM25 (rank-bm25)
|   |       +-- rrf.py                # RRF (fusion hybride)
|   +-- utils/
|       +-- config.py                  # Gestion configuration YAML
|
+-- tests/
|   +-- conftest.py
|   +-- test_config.py
|   +-- test_database.py
|   +-- test_embedder.py
|   +-- test_extractor.py
|   +-- test_pdf_classifier.py
|   +-- test_pdf_to_text_extractor.py
|   +-- fixtures/
|
+-- tui/
|   +-- __init__.py
|   +-- app.py                         # Interface terminal Textual
|
+-- web/                               # Frontend SvelteKit
|   +-- package.json
|   +-- svelte.config.js
|   +-- tsconfig.json
|   +-- vite.config.ts
|   +-- src/
|   +-- static/
|   +-- template/
|
+-- docker-compose.yaml
+-- makefile
+-- pytest.ini
+-- requirements.txt
+-- setup.py
+-- README.md
+-- SETUP.md
+-- REFACTORING_PLAN.md
```

---

## Annexe B -- Modeles Utilises

| Modele                                   | Tache       | Params   | Format        | Taille disque |
|------------------------------------------|-------------|----------|---------------|---------------|
| `intfloat/multilingual-e5-large`         | Embedding   | 560M     | FP16 (PyTorch)| ~1.1 Go       |
| `unsloth/gemma-4-E2B-it-qat-GGUF`       | Generation  | 2B       | Q4_K_XL (GGUF)| ~1.1 Go       |
| `BAAI/bge-m3`                            | Embedding   | 568M     | FP16 (PyTorch)| ~1.1 Go       |
| `sentence-transformers/LaBSE`           | Embedding   | 470M     | FP16 (PyTorch)| ~940 Mo       |
| EasyOCR                                  | OCR         | --       | ONNX          | ~200 Mo       |

---

## Annexe C -- Configuration Docker Compose

```yaml
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

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    restart: unless-stopped
    ports:
      - "5050:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin123
    volumes:
      - pgadmin_data:/var/lib/pgadmin

volumes:
  postgres_data:
  pgadmin_data:
```

---

## Annexe D -- Guide de Reproduction

```bash
# 1. Cloner le projet
git clone <repo-url>
cd Analyse-des-lois-justice-Maroc

# 2. Creer l'environnement virtuel
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configurer les variables d'environnement
cp .env.example .env
# Editer .env : DB credentials, LLM_SERVICE_URL, OPENAI_API_KEY...

# 4. Demarrer PostgreSQL
docker compose up -d postgres

# 5. Initialiser la base de donnees
# (automatique via init_db.sql au premier demarrage)

# 6. Indexer le corpus
python scripts/embed_all_articles.py

# 7. Lancer l'API
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 8. Lancer le frontend (optionnel)
cd web
npm install
npm run dev -- --open

# 9. Executer les tests
make test

# 10. Executer le benchmark RAG
jupyter notebook benchmark/rag_benchmark.ipynb
```

---

## Annexe E -- References

### Documentation interne

| Document                                                 | Sujet                           |
|----------------------------------------------------------|---------------------------------|
| `docs/Architecture/01-DataGathering-Corpus-Construction.md` | Collecte et constitution        |
| `docs/Architecture/02-Processing-Validation-Raw-Legal-Data.md` | Traitement et validation       |
| `docs/Architecture/03-NLP-Pipeline-Construction.md`     | Pipeline NLP (a completer)      |
| `docs/Architecture/04-PostgreSQL-Chosen-Moroccan-Legal-RAG-System.md` | Infrastructure DB     |
| `docs/Architecture/05-Implementation-Retrieval-Augmented.md` | Implementation RAG            |
| `docs/embedding_model_benchmark.md`                      | Benchmark embedding             |
| `docs/retrieval_strategies_benchmark.md`                 | Benchmark retrieval             |
| `docs/llm_serving_quantized_models.md`                   | Guide LLM quantifie             |
| `docs/postgresql_legal_rag.md`                           | Guide PostgreSQL+pgvector       |
| `docs/colab_microservice_architecture.md`                | Architecture microservices      |

### References academiques (a completer)

- Lewis, P., et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." NeurIPS 2020.
- Wang, L., et al. (2024). "A Survey on Retrieval-Augmented Generation."
- Es, S., et al. (2023). "RAGAS: Automated Evaluation of Retrieval Augmented Generation."
