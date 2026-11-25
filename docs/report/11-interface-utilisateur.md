# 11. Interface Utilisateur

---

## 11.1 Interface Web (SvelteKit)

### Stack Frontend

| Technologie      | Version | Role                        |
|------------------|---------|-----------------------------|
| SvelteKit        | 5       | Framework frontend          |
| Svelte           | 5       | UI reactive                 |
| Tailwind CSS     | 4       | Styling utilitaire          |
| TypeScript       | 6       | Typage statique             |
| Vite             | 8       | Bundler / Dev server        |
| Lucide Icons     | 1       | Icones                      |
| marked           | 18      | Rendu Markdown              |
| DOMPurify        | 3       | Sanitization HTML           |
| Playwright       | 1.59    | Tests E2E                   |

### Pages principales

```
+--------------------------------------------------+
|                INTERFACE WEB                      |
+--------------------------------------------------+
|  +------------------------------------------+    |
|  |  [Logo]  Recherche Juridique Marocaine    |    |
|  +------------------------------------------+    |
|                                                  |
|  +------------------------------------------+    |
|  |                                          |    |
|  |  Posez votre question juridique...       |    |
|  |  [_____________________________] [Chercher]   |
|  |                                          |    |
|  |  Domaine: [Tous ▼]  Strategie: [RRF ▼]   |    |
|  +------------------------------------------+    |
|                                                  |
|  +------------------------------------------+    |
|  |  RESULTATS                               |    |
|  |                                          |    |
|  |  +----------------------------------+    |    |
|  |  | المادة 513 | Code Penal | 0.92  |    |    |
|  |  | يعتبر الحدث البالغ من العمر...  |    |    |
|  |  +----------------------------------+    |    |
|  |                                          |    |
|  |  +----------------------------------+    |    |
|  |  | المادة 508 | Code Penal | 0.87  |    |    |
|  |  | يعاقب على السرقة الموصوفة...   |    |    |
|  |  +----------------------------------+    |    |
|  +------------------------------------------+    |
|                                                  |
|  +------------------------------------------+    |
|  |  REPONSE GENERE (Gemma 4)               |    |
|  |                                          |    |
|  |  حسب المادتين 508 و 509 من القانون      |    |
|  |  الجنائي المغربي، يعاقب على السرقة       |    |
|  |  الموصوفة بالسجن من 5 الى 10 سنوات...   |    |
|  |                                          |    |
|  |  المصادر: المادة 508, 509               |    |
|  |  [Disclaimer]                            |    |
|  +------------------------------------------+    |
+--------------------------------------------------+
```

## 11.2 TUI (Terminal User Interface)

```
+--------------------------------------------------+
| Moroccan Legal RAG - Knowledge Base Manager       |
+--------------------------------------------------+
|                                                  |
|  [1] Droit Penal         (822 articles)          |
|  [2] Code de la Route    (228 articles)          |
|  [3] Droit Civil         (705 articles)          |
|  [4] Droit Commercial    (359 articles)          |
|  [5] Organisation Judic. (32 articles)           |
|  [6] Droit Fiscal        (211 articles)          |
|                                                  |
|  [S] Rechercher    [U] Uploader    [Q] Quitter   |
+--------------------------------------------------+
```

### Fonctionnalites TUI

| Touche  | Action                       |
|---------|------------------------------|
| 1-6     | Naviguer par domaine         |
| S       | Rechercher un article        |
| U       | Uploader un nouveau PDF      |
| Enter   | Voir le detail d'un article  |
| Q       | Quitter                      |

## 11.3 Scripts CLI

| Script                              | Fonction                                  |
|-------------------------------------|-------------------------------------------|
| `scripts/embed_all_articles.py`    | Indexation complete du corpus             |
| `scripts/batch_process_pdfs.py`    | Traitement par lots de PDF                |
| `scripts/run_preprocessing_pipeline.py` | Pipeline complet de preprocessing     |
| `scripts/seed_test_data.py`        | Peuplement de la base de test             |
| `scripts/check_retrieval_quality.py`| Verification qualite du retrieval         |
| `scripts/parse_legal_structure.py` | Parsing structure des lois                |
| `scripts/extract_raw_text.py`      | Extraction texte brut des PDF             |
| `scripts/debug_vector_search.py`   | Debug de la recherche vectorielle         |
| `scripts/generate_pdf_fixtures.py` | Generation de PDF de test                 |

### Exemple d'utilisation

```bash
# Indexer tout le corpus
python scripts/embed_all_articles.py --domain criminal --batch-size 50

# Traiter un nouveau PDF
python scripts/batch_process_pdfs.py --input data/raw/new_law.pdf --domain civil

# Verifier la qualite du retrieval
python scripts/check_retrieval_quality.py --domain criminal --top-k 5
```
