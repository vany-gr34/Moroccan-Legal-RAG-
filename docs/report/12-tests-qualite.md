# 12. Tests et Qualite

---

## 12.1 Strategie de Test

```
+====================================================================+
|                      PYRAMIDE DE TESTS                              |
+====================================================================+
|                                                                    |
|                        +-----------+                                |
|                        |  E2E      |  Playwright (web)              |
|                        +-----------+                                |
|                      +---------------+                              |
|                      |  Integration  |  DB + API + Retrieval        |
|                      +---------------+                              |
|                    +---------------------+                          |
|                    |    Unitaires         |   pytest                |
|                    +---------------------+                          |
|                  +---------------------------+                      |
|                  |    Benchmarks              |  Notebooks eval     |
|                  +---------------------------+                      |
|                                                                    |
+====================================================================+
```

## 12.2 Tests Unitaires (pytest)

### Modules testes

| Fichier de test                        | Module teste                  |
|----------------------------------------|-------------------------------|
| `tests/test_config.py`                 | Chargement configuration YAML |
| `tests/test_database.py`               | Connexion et operations DB    |
| `tests/test_embedder.py`               | Embedding local + mock distant|
| `tests/test_extractor.py`              | Extraction articles           |
| `tests/test_pdf_classifier.py`         | Classification PDF            |
| `tests/test_pdf_to_text_extractor.py`  | Extraction texte PDF          |

### Configuration pytest (`pytest.ini`)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
```

### Execution

```bash
# Tous les tests
make test

# Tests rapides uniquement
pytest -m "not slow"

# Tests d'integration
pytest -m integration

# Avec couverture
pytest --cov=src --cov-report=html
```

## 12.3 Tests d'Integration

### Base de donnees

```
+------------------+     +------------------+     +------------------+
| test_database.py | --> | PostgreSQL       | --> | Verification     |
+------------------+     | (Docker)         |     +------------------+
                         |                  |     | - Connexion      |
                         | - init_db.sql    |     | - CRUD articles  |
                         | - pgvector       |     | - Recherche      |
                         +------------------+     | - Embedding      |
                                                  +------------------+
```

### API

| Endpoint    | Test                                      |
|-------------|-------------------------------------------|
| `/health`   | Verification etat du service              |
| `/search`   | Recherche avec requete valide             |
| `/ask`      | Q&A avec reponse attendue                  |
| `/laws`     | Liste des lois disponibles                |

## 12.4 Fixtures de Test

```
tests/
+-- fixtures/
|   +-- sample_civil.pdf           # PDF civil valide
|   +-- sample_criminal.pdf        # PDF penal valide
|   +-- sample_empty.pdf           # PDF vide (cas d'erreur)
|   +-- sample_scanned.pdf         # PDF scanne (test OCR)
+-- conftest.py                    # Configuration partagee
```

### Fixture example (conftest.py)

```python
@pytest.fixture
def db_connection():
    """Fournit une connexion a la base de test."""
    conn = get_connection()
    yield conn
    conn.close()

@pytest.fixture
def sample_article():
    """Fournit un article juridique de test."""
    return {
        "article_number": "513",
        "law_name": "code penal maroc ar",
        "domain": "criminal",
        "text": "يعتبر الحدث البالغ من العمر اقل من 16 سنة..."
    }
```

## 12.5 Benchmarks (Notebooks)

| Benchmark                                | Metriques                                   |
|------------------------------------------|---------------------------------------------|
| Embedding models                         | P@5, MRR, NDCG, Domain Accuracy             |
| Strategies de recherche                  | P@5, R@5, MRR, NDCG, Hit@5                  |
| RAG complet                              | Context P/R, Relevance, Faithfulness, Correctness |
| OCR + VLM correction                     | CER (Character Error Rate), WER (Word ER)   |

## 12.6 Qualite du Code

### Convention de nommage

| Element       | Convention              | Exemple                    |
|---------------|-------------------------|----------------------------|
| Modules       | snake_case              | `pdf_classifier.py`        |
| Classes       | PascalCase              | `DenseRetrieval`           |
| Fonctions     | snake_case              | `compute_faithfulness`     |
| Variables     | snake_case              | `query_embedding`          |
| Constantes    | UPPER_SNAKE             | `TOP_K`, `STRATEGIES`      |

### Outils recommandes

| Outil     | Usage                        |
|-----------|------------------------------|
| ruff      | Linting + formatting (Python)|
| mypy      | Typage statique              |
| prettier  | Formatting (Svelte/TS)       |
| eslint    | Linting (Svelte/TS)          |
