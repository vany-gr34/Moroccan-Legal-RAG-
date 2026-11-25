# Rapport — Système RAG Juridique Marocain

> Structure du rapport final pour le projet **Analyse des Lois — Justice Maroc**.
> Ce document sert de plan de rédaction ; chaque section référence les artefacts existants
> (notebooks, modules, documentation) à intégrer.

---

## Table des Matières

1. [Résumé Exécutif](#1-résumé-exécutif)
2. [Introduction et Contexte](#2-introduction-et-contexte)
3. [État de l'Art](#3-état-de-lart)
4. [Architecture Globale du Système](#4-architecture-globale-du-système)
5. [Phase 1 — Collecte et Constitution du Corpus](#5-phase-1--collecte-et-constitution-du-corpus)
6. [Phase 2 — Traitement et Validation des Données](#6-phase-2--traitement-et-validation-des-données)
7. [Phase 3 — Pipeline NLP](#7-phase-3--pipeline-nlp)
8. [Phase 4 — Infrastructure Base de Données](#8-phase-4--infrastructure-base-de-données)
9. [Phase 5 — Système RAG Complet](#9-phase-5--système-rag-complet)
10. [Recherche et Expérimentations](#10-recherche-et-expérimentations)
11. [Interface Utilisateur](#11-interface-utilisateur)
12. [Tests et Qualité](#12-tests-et-qualité)
13. [Résultats et Discussion](#13-résultats-et-discussion)
14. [Conclusion et Perspectives](#14-conclusion-et-perspectives)
15. [Annexes](#15-annexes)

---

## 1. Résumé Exécutif

```
┌─────────────────────────────────────────────────────────────────┐
│                      RÉSUMÉ EXÉCUTIF                             │
│                                                                 │
│  • Problématique : Accès limité à l'information juridique        │
│    marocaine en langue arabe                                     │
│  • Solution : Assistant juridique intelligent basé sur RAG       │
│  • Technologies clés : pgvector, E5-large, Gemma 4, llama.cpp   │
│  • Domaines couverts : Pénal, Famille, Circulation, Civil,       │
│    Commercial                                                    │
│  • Résultat principal : Système fonctionnel de Q&A juridique     │
│    avec récupération hybride et génération contextualisée        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Contenu attendu :**
- Synthèse en 1 page (français + arabe)
- Problème, solution, résultats clés, impact
- Schéma global simplifié du pipeline

**Sources à intégrer :**
- `README.md` — objectifs et features
- Résultats des benchmarks (embedding + retrieval)

---

## 2. Introduction et Contexte

### 2.1 Problématique Juridique au Maroc
- Difficulté d'accès aux textes de loi pour le citoyen
- Barrière linguistique (arabe juridique complexe, mélange arabe/français)
- Dispersion des sources légales

### 2.2 Objectifs du Projet
- Constituer un corpus juridique marocain structuré
- Permettre la recherche sémantique en arabe, darija, et français
- Générer des réponses juridiques fondées sur les textes officiels
- Réduire les hallucinations via l'approche RAG

### 2.3 Périmètre
- 6 domaines juridiques : Pénal, Circulation, Famille, Civil, Commercial, Contraventions
- Formats sources : PDF scannés, textes OCRisés, documents structurés

**Sources à intégrer :**
- `README.md`
- `docs/Architecture/01-DataGathering-Corpus-Construction.md`

---

## 3. État de l'Art

### 3.1 Recherche d'Information Juridique
- Systèmes existants (international et monde arabe)
- Limites des approches par mots-clés

### 3.2 NLP pour l'Arabe
- Défis spécifiques : morphologie riche, diglossie (Darija vs MSA), code-switching
- Modèles multilingues vs modèles arabes spécialisés

### 3.3 Retrieval-Augmented Generation (RAG)
- Architecture générale
- Variantes : RAG séquentiel, RAG agentique, RAG hybride

### 3.4 Quantification et Optimisation Mémoire
- Formats GGUF, GPTQ, AWQ
- Solutions légères : llama.cpp, ollama

**Sources à intégrer :**
- `docs/llm_serving_quantized_models.md`
- Références académiques externes

---

## 4. Architecture Globale du Système

```
┌──────────────────────────────────────────────────────────────────────────┐
│                 MOROCCAN LEGAL RAG — ARCHITECTURE GLOBALE                 │
│                                                                          │
│  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │ SOURCES │   │ INGESTION│   │ STOCKAGE │   │ RECHERCHE│   │  Q&A    │ │
│  │         │   │          │   │          │   │          │   │         │ │
│  │ PDF     │──▶│ OCR      │──▶│PostgreSQL│◀──│ Hybride  │──▶│  LLM    │ │
│  │ Scans   │   │ EasyOCR  │   │+pgvector │   │ Dense+   │   │ Gemma 4 │ │
│  │ Textes  │   │ VLM      │   │          │   │ BM25+RRF │   │         │ │
│  └─────────┘   └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│                     │               │               │              │      │
│                     ▼               ▼               ▼              ▼      │
│              ┌──────────────────────────────────────────────────────┐     │
│              │                    CONTRÔLE QUALITÉ                   │     │
│              │   Nettoyage · Normalisation · Validation · Tests    │     │
│              └──────────────────────────────────────────────────────┘     │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                        INTERFACES                                  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                        │    │
│  │  │  API     │  │  Web     │  │   TUI    │                        │    │
│  │  │ FastAPI  │  │ Svelte   │  │ Textual  │                        │    │
│  │  └──────────┘  └──────────┘  └──────────┘                        │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Stack Technique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Ingestion | EasyOCR, PyMuPDF, VLM (Gemma 4) | Extraction texte arabe depuis PDF |
| NLP | E5-large (1024d), LaBSE, BGE-M3 | Embedding, normalisation |
| Base de données | PostgreSQL 16 + pgvector 0.7.4 | Stockage documents + vecteurs |
| Recherche | Dense (cosine), BM25, Hybride, RRF | Retrieval multi-stratégie |
| Génération | Gemma 4 (Q4_K_XL GGUF), llama.cpp | Réponses juridiques contextualisées |
| API | FastAPI (Python) | Endpoints REST |
| Frontend | Svelte + TypeScript | Interface web |
| TUI | Textual (Python) | Gestion du corpus en terminal |
| Infra | Docker Compose, Cloudflare Tunnel | Déploiement local + GPU distant |

### 4.2 Flux de Données Principal

```
Utilisateur (Question)
    │
    ▼
API Gateway (FastAPI)
    │
    ▼
Embedding (E5-large) ──► pgvector (cosine similarity)
    │                         │
    │                    BM25 (lexical)
    │                         │
    └─────────┬───────────────┘
              │
              ▼
        Fusion (Hybride / RRF)
              │
              ▼
        Top-K Articles
              │
              ▼
        Prompt Construction
              │
              ▼
        LLM (Gemma 4 via llama.cpp)
              │
              ▼
        Réponse Juridique
```

**Sources à intégrer :**
- `docs/Architecture/` (les 5 documents de phase)
- `docs/Services/Embedding-Service.md`
- `docker-compose.yaml`

---

## 5. Phase 1 — Collecte et Constitution du Corpus

### 5.1 Sources de Données
- Bulletins officiels (format PDF)
- Textes de loi numérisés
- Sources web gouvernementales

### 5.2 Processus d'Extraction

```
PDF Scanné ──► PyMuPDF ──► Images (PNG) ──► EasyOCR ──► Texte Arabe Brut
                                  │
                                  ▼
                           VLM (Gemma 4)
                           Correction OCR
                                  │
                                  ▼
                           Texte Arabe Corrigé
```

### 5.3 Structure du Corpus

| Domaine | Articles | Format |
|---------|----------|--------|
| Pénal | ~500 | Texte + Métadonnées |
| Circulation | ~200 | Texte + Métadonnées |
| Famille | ~400 | Texte + Métadonnées |
| Civil (DOC) | ~500 | Texte + Métadonnées |
| Commercial | ~300 | Texte + Métadonnées |
| Contraventions | ~100 | Texte + Métadonnées |

### 5.4 Métadonnées Associées
- Numéro d'article
- Loi de référence
- Section / Chapitre
- Domaine juridique
- Source (PDF, URL)

**Sources à intégrer :**
- `docs/Architecture/01-DataGathering-Corpus-Construction.md`
- `notebooks/01_ocr_quality_research.ipynb`
- `notebooks/04_ocr_service_colab.ipynb`
- `notebooks/OCR__VLM_CORECTION(1).ipynb`
- `src/ingestion/`

---

## 6. Phase 2 — Traitement et Validation des Données

### 6.1 Pipeline de Nettoyage

```
Texte Brut OCR ──► Cleaning ──► Normalisation ──► Validation ──► Corpus Propre
                   (config)     (config)           (structure)
```

### 6.2 Défis Rencontrés

| Problème | Solution |
|----------|----------|
| Bruit OCR (caractères incorrects) | Correction VLM + règles de cleaning |
| Texte dupliqué | Détection par hash + similarité |
| Mélange Arabe/Français | Segmentation par langue |
| Métadonnées manquantes | Inférence par heuristiques |
| Formatage irrégulier | Normalisation configurable (YAML) |

### 6.3 Configuration
- `config/cleaning.yaml` — règles de nettoyage
- `config/normalization.yaml` — normalisation arabe
- `config/config.yaml` — configuration générale

**Sources à intégrer :**
- `docs/Architecture/02-Processing-Validation-Raw-Legal-Data.md`
- `src/core/cleaning.py`
- `src/core/normalizing.py`
- `src/core/structure.py`
- `src/core/block_parser.py`
- `config/`

---

## 7. Phase 3 — Pipeline NLP

### 7.1 Segmentation et Chunking
- Découpage par article juridique
- Regroupement par domaine
- Fenêtres contextuelles (article + contexte législatif)

### 7.2 Embedding

```
Article Arabe ──► E5-large ──► Vecteur 1024d ──► pgvector
                   (GPU T4
                   Colab)
```

### 7.3 Modèles d'Embedding Évalués

| Modèle | Dimension | Performance | Utilisation |
|--------|-----------|-------------|-------------|
| E5-large | 1024 | ★ Meilleur | Production |
| BGE-M3 | 1024 | ★★ | Alternative |
| LaBSE | 768 | ★★★ | Fallback rapide |
| E5-base | 768 | ★★★ | CPU-only |
| MPNet | 768 | ★★★★ | Non retenu |

### 7.4 Service d'Embedding Distant

```
Machine Locale ──HTTP──► Cloudflare Tunnel ──HTTP──► Google Colab (T4)
                             │
                        trycloudflare.com     FastAPI :8000
                                              E5-large sur GPU
```

**Sources à intégrer :**
- `docs/Architecture/03-NLP-Pipeline-Construction.md`
- `docs/Services/Embedding-Service.md`
- `docs/embedding_model_benchmark.md`
- `notebooks/02_embedding_colab_api.ipynb`
- `notebooks/03_embedding_models_benchmark.ipynb`
- `src/core/embedding.py`
- `src/ingestion/embedder.py`

---

## 8. Phase 4 — Infrastructure Base de Données

### 8.1 Choix de PostgreSQL + pgvector

| Critère | PostgreSQL | Alternative | Verdict |
|---------|------------|-------------|---------|
| Recherche vectorielle | pgvector (IVFFlat, HNSW) | ChromaDB, Qdrant | pgvector : intégré |
| Support arabe | UTF-8, ICU | — | OK |
| Full-text search | tsvector (arabe limité) | Elasticsearch | BM25 externe |
| Transactions ACID | Oui | Non (vector DBs) | PostgreSQL gagne |
| Maturité | 30+ ans | Variable | PostgreSQL gagne |

### 8.2 Schéma de Base de Données

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   articles   │────▶│   chunks     │────▶│  embeddings  │
│              │     │              │     │  (pgvector)  │
│ id           │     │ id           │     │ id           │
│ article_num  │     │ article_id   │     │ chunk_id     │
│ law_name     │     │ text         │     │ embedding    │
│ domain       │     │ context      │     │ model_name   │
│ text         │     │              │     │ created_at   │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 8.3 Déploiement Docker

```yaml
# docker-compose.yaml
services:
  postgres:
    image: moroccan-legal-rag-db:latest
    environment:
      POSTGRES_DB: legal_rag
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init_db.sql:/docker-entrypoint-initdb.d/01-init.sql
```

**Sources à intégrer :**
- `docs/Architecture/04-PostgreSQL-Chosen-Moroccan-Legal-RAG-System.md`
- `docker-compose.yaml`
- `docker/`
- `database/init_db.sql`

---

## 9. Phase 5 — Système RAG Complet

### 9.1 Architecture RAG

```
┌──────────────────────────────────────────────────────────────────┐
│                        RAG PIPELINE                               │
│                                                                  │
│  Question ──► Embedding ──► pgvector ──┐                         │
│                     │                  │                         │
│                     ▼                  ▼                         │
│                BM25 Index ──► Fusion ──► Top-K ──► LLM ──► Réponse│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 9.2 Stratégies de Recherche

| Stratégie | Score MRR | Avantage |
|-----------|-----------|----------|
| Dense seul | — | Sémantique pure |
| BM25 seul | — | Mots-clés exacts |
| Hybride (α=0.7) | — | Meilleur équilibre |
| RRF | — | Sans paramètre |

### 9.3 Service de Génération (LLM)

```
Articles Récupérés ──► Prompt Template ──► Gemma 4 ──► Réponse
                             │              (Q4_K_XL)
                             │              llama.cpp
                             ▼
                 ┌─────────────────────┐
                 │ System: Tu es un    │
                 │ assistant juridique │
                 │ marocain...         │
                 │                     │
                 │ Context: [articles] │
                 │ Question: [user]    │
                 └─────────────────────┘
```

### 9.4 Optimisation Mémoire LLM

| Paramètre | Valeur | Impact |
|-----------|--------|--------|
| Quantification | Q4_K_XL (GGUF) | ~1.1 GB au lieu de ~4 GB |
| GPU Layers | -1 (tous sur GPU) | Débit maximal |
| Contexte | 16384 tokens | Article complet + prompt |
| Température | 0.0 | Déterministe (juridique) |

### 9.5 API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/search` | Recherche juridique |
| POST | `/ask` | Question-réponse juridique |
| GET | `/articles/{id}` | Récupération d'un article |
| GET | `/domains` | Liste des domaines |
| GET | `/health` | Statut du système |

**Sources à intégrer :**
- `docs/Architecture/05-Implementation-Retrieval-Augmented.md`
- `docs/llm_serving_quantized_models.md`
- `docs/retrieval_strategies_benchmark.md`
- `notebooks/06_benchmark_retreiving_strategies.ipynb`
- `notebooks/07_llm_api_colab_qwen2_5.ipynb`
- `src/retrieval/`
- `src/generation/`
- `src/api/`

---

## 10. Recherche et Expérimentations

### 10.1 Benchmark Embedding

> Voir `docs/embedding_model_benchmark.md` pour le détail complet.

- 5 modèles testés (E5-large, E5-base, MPNet, LaBSE, BGE-M3)
- 26 articles × 5 domaines juridiques
- 65 variantes de requêtes : Arabe formel, Darija, Mots-clés, Français, Anglais
- Métriques : P@K, MRR, NDCG, Domain Accuracy
- **Résultat** : E5-large recommandé pour la production

![Figure 1 — Comparaison globale](images/embedding_benchmark_fig1_overall.png)
![Figure 2 — Difficulté des requêtes](images/embedding_benchmark_fig2_difficulty.png)
![Figure 3 — Cross-lingual](images/embedding_benchmark_fig3_crosslingual.png)
![Figure 4 — Vitesse vs Qualité](images/embedding_benchmark_fig4_speed_quality.png)

### 10.2 Benchmark Stratégies de Recherche

> Voir `docs/retrieval_strategies_benchmark.md` pour le détail complet.

- 4 stratégies : Dense, BM25, Hybride (α), RRF
- 7 requêtes avec jugements de pertinence
- Tuning du paramètre α ∈ {0.3, 0.5, 0.7, 0.9}
- **Résultat** : RRF recommandé (pas de paramètre à régler)

![Figure 1 — Comparaison stratégies](images/retrieval_benchmark_fig1_comparison.png)
![Figure 2 — Tuning alpha](images/retrieval_benchmark_fig2_alpha.png)
![Figure 3 — MRR par requête](images/retrieval_benchmark_fig3_per_query.png)
![Figure 4 — Tableau récapitulatif](images/retrieval_benchmark_fig4_summary.png)

### 10.3 Expérimentation VLM pour Correction OCR

> Voir `notebooks/OCR__VLM_CORECTION(1).ipynb` et `docs/llm_serving_quantized_models.md`.

- Gemma 4 (2B, Q4_K_XL) utilisé pour corriger les erreurs OCR
- Approche article par article avec checkpoint/resume
- Prompt spécialisé : ne pas résumer, ne pas traduire, corriger uniquement

### 10.4 Service Embedding via Colab

- GPU T4 gratuit via Google Colab
- Exposition via Cloudflare Tunnel (trycloudflare.com)
- Fallback CPU local si tunnel indisponible

**Sources à intégrer :**
- `notebooks/01` à `07`
- `docs/embedding_model_benchmark.md`
- `docs/retrieval_strategies_benchmark.md`
- `docs/llm_serving_quantized_models.md`

---

## 11. Interface Utilisateur

### 11.1 Interface Web (Svelte)

```
┌──────────────────────────────────────────┐
│  🔍 Recherche Juridique Marocaine         │
│  ┌──────────────────────────────────────┐ │
│  │  Posez votre question en arabe...    │ │
│  └──────────────────────────────────────┘ │
│  [Rechercher]                             │
│                                           │
│  Résultats :                              │
│  ┌──────────────────────────────────────┐ │
│  │ المادة 147 — القانون الجنائي         │ │
│  │ كل من ارتكب جريمة السرقة يعاقب...    │ │
│  └──────────────────────────────────────┘ │
│  ┌──────────────────────────────────────┐ │
│  │ Réponse générée :                    │ │
│  │ حسب المادة 147 من القانون الجنائي... │ │
│  └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

- Frontend Svelte + TypeScript
- Vite pour le build
- Appels à l'API FastAPI

### 11.2 TUI (Terminal User Interface)

- Gestion de la base de connaissances en terminal
- Navigation par domaines juridiques
- Visualisation des articles et métadonnées
- Raccourcis clavier

### 11.3 Scripts CLI

| Script | Fonction |
|--------|----------|
| `embed_all_articles.py` | Indexation complète du corpus |
| `batch_process_pdfs.py` | Traitement par lots de PDF |
| `run_preprocessing_pipeline.py` | Pipeline complet de preprocessing |
| `seed_test_data.py` | Peuplement de la base de test |
| `check_retrieval_quality.py` | Vérification qualité retrieval |

**Sources à intégrer :**
- `web/`
- `tui/`
- `scripts/`

---

## 12. Tests et Qualité

### 12.1 Stratégie de Test

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Unitaires  │  │ Intégration │  │  Benchmarks │  │  Validation │
│             │  │             │  │             │  │  Manuelle    │
│ pytest      │  │ DB + API    │  │ Notebooks   │  │ Qualité OCR │
│ conftest.py │  │ Docker      │  │ Métriques   │  │ VLM output  │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### 12.2 Couverture

| Module | Tests |
|--------|-------|
| `test_config.py` | Chargement configuration |
| `test_database.py` | Connexion et opérations DB |
| `test_embedder.py` | Embedding local + mock distant |
| `test_extractor.py` | Extraction articles |
| `test_pdf_classifier.py` | Classification PDF |
| `test_pdf_to_text_extractor.py` | Extraction texte PDF |

### 12.3 Fixtures

- `tests/fixtures/` — PDF et textes de test
- `conftest.py` — Configuration pytest partagée

**Sources à intégrer :**
- `tests/`
- `pytest.ini`
- `makefile` (cibles test)

---

## 13. Résultats et Discussion

### 13.1 Performance du Système

```
┌─────────────────────────────────────────────────────────────────┐
│                   TABLEAU DE BORD — PERFORMANCE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUALITÉ RETRIEVAL          GÉNÉRATION LLM                      │
│  ┌──────────────────┐       ┌──────────────────┐               │
│  │ MRR    : —       │       │ Cohérence : —    │               │
│  │ Recall : —       │       │ Fidélité  : —    │               │
│  │ NDCG   : —       │       │ Latence   : —    │               │
│  └──────────────────┘       └──────────────────┘               │
│                                                                 │
│  INFRASTRUCTURE              COUVERTURE CORPUS                  │
│  ┌──────────────────┐       ┌──────────────────┐               │
│  │ PG Vector : — ms │       │ Articles  : —    │               │
│  │ LLM Inf.  : — s  │       │ Domaines  : 6    │               │
│  │ RAM       : — GB │       │ Langues   : AR   │               │
│  └──────────────────┘       └──────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

_À remplir avec les résultats des benchmarks._

### 13.2 Limites Identifiées

| Limite | Impact | Solution envisagée |
|--------|--------|-------------------|
| Darija → MSA gap | Baisse P@1 sur requêtes orales | Fine-tuning embedding darija |
| Corpus incomplet | Couverture juridique partielle | Extension continue du corpus |
| LLM léger (2B) | Qualité de génération limitée | Upgrade vers modèle 7B+ |
| OCR sur scans basse qualité | Erreurs résiduelles | Amélioration préprocessing image |

### 13.3 Comparaison avec l'Existant
- Avantages par rapport à une recherche Google/legislation.ma
- Plus-value du RAG vs LLM seul

---

## 14. Conclusion et Perspectives

### 14.1 Résumé des Contributions
1. Constitution d'un corpus juridique marocain structuré en arabe
2. Pipeline complet d'ingestion : OCR → VLM → Nettoyage → Embedding
3. Benchmark systématique des modèles d'embedding pour l'arabe juridique
4. Comparaison de 4 stratégies de retrieval (dense, BM25, hybride, RRF)
5. Déploiement léger de LLM quantifié avec llama.cpp
6. Service d'embedding GPU distant via Colab + Cloudflare Tunnel

### 14.2 Perspectives

```
Court terme (1-3 mois)          Moyen terme (3-6 mois)         Long terme (6-12 mois)
─────────────────────────       ────────────────────────       ──────────────────────
• Extension corpus              • Fine-tuning embedding        • Modèle juridique
  (plus de domaines)              sur données juridiques         spécialisé (fine-tune
• Interface web complète        • RAG multi-tours                LLM)
• Évaluation humaine            • Citations automatiques       • API publique
• Support audio (Darija)        • Résumé de lois               • Mise à jour automatique
                                                               • Plateforme multi-pays
```

---

## 15. Annexes

### Annexe A — Structure du Projet

```
Analyse-des-lois-justice-Maroc/
├── config/            # Fichiers YAML de configuration
├── data/              # Données brutes, intermédiaires, processed
├── database/          # Scripts SQL d'initialisation
├── docker/            # Dockerfiles et configuration
├── docs/              # Documentation
│   ├── Architecture/  # 5 documents de phase
│   ├── Services/      # Documentation des services
│   └── *.md           # Rapports de benchmark
├── notebooks/         # Notebooks Jupyter de recherche
├── scripts/           # Scripts CLI utilitaires
├── src/               # Code source principal
│   ├── api/           # API FastAPI
│   ├── core/          # NLP, cleaning, structure
│   ├── db/            # Accès base de données
│   ├── generation/    # LLM (factory, remote, base)
│   ├── ingestion/     # OCR, classification, extraction
│   ├── retrieval/     # Recherche hybride, stratégies
│   └── utils/         # Utilitaires
├── tests/             # Tests unitaires et fixtures
├── tui/               # Interface terminal (Textual)
├── web/               # Frontend Svelte
├── docker-compose.yaml
├── makefile
├── requirements.txt
└── README.md
```

### Annexe B — Modèles Utilisés

| Modèle | Tâche | Taille | Format |
|--------|-------|--------|--------|
| `intfloat/multilingual-e5-large` | Embedding | 560M params | FP16 |
| `unsloth/gemma-4-E2B-it-qat-GGUF` | Génération | 2B params | Q4_K_XL GGUF |
| EasyOCR | OCR arabe | — | ONNX |

### Annexe C — Références

- Documents d'architecture internes (`docs/Architecture/`)
- Benchmarks internes (`docs/*.md`)
- Bibliographie académique (à compléter)

### Annexe D — Guide de Reproduction

```bash
# 1. Cloner le projet
git clone <repo>
cd Analyse-des-lois-justice-Maroc

# 2. Environnement
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Base de données
docker-compose up -d

# 4. Indexation
python scripts/seed_test_data.py
python scripts/embed_all_articles.py

# 5. API
uvicorn src.main:app --reload

# 6. Frontend (optionnel)
cd web && npm install && npm run dev
```
