# 1. Resume Executif

> Synthese en 1 page du projet **Analyse des Lois -- Justice Maroc**

---

## Problematique

L'acces a l'information juridique marocaine en langue arabe est limite pour le citoyen.
Les textes de loi sont disperses, souvent au format PDF scanne, et l'arabe juridique
est complexe. Il n'existe pas de systeme de question-reponse juridique fonde
exclusivement sur les textes officiels marocains.

## Solution

Un assistant juridique intelligent base sur l'architecture **Retrieval-Augmented Generation (RAG)** :

```
+-------------------+       +------------------+       +------------------+
|   QUESTION ARABE  | ----> | RECHERCHE HYBRIDE | ----> | GENERATION LLM   |
| (utilisateur)     |       | Dense + BM25+ RRF |       | Gemma 4 (2B)     |
+-------------------+       +------------------+       +------------------+
                                      |                          |
                                      v                          v
                             +------------------+       +------------------+
                             | PostgreSQL+pgvector|       | REPONSE JURIDIQUE|
                             | ~1500 articles    |       | avec sources     |
                             +------------------+       +------------------+
```

## Technologies Cles

| Composant           | Technologie                              |
|---------------------|------------------------------------------|
| Extraction Texte    | EasyOCR + PyMuPDF + correction VLM        |
| Embedding           | intfloat/multilingual-e5-large (1024d)    |
| Base de donnees     | PostgreSQL 16 + pgvector 0.7.4            |
| Recherche           | Dense (cosine) + BM25 + RRF (hybride)     |
| Generation          | Gemma 4 2B (Q4_K_XL GGUF) via llama.cpp   |
| API                 | FastAPI (Python)                          |
| Interface Web       | SvelteKit 5 + Tailwind CSS 4              |
| Infrastructure      | Docker Compose + Cloudflare Tunnel         |

## Domaines Juridiques Couverts

- Droit Penal (Code Penal Marocain)
- Code de la Route (Circulation)
- Droit de la Famille (Moudawana)
- Droit Civil (Code des Obligations et Contrats)
- Droit Commercial (Registre du Commerce, Societes)
- Procedures Judiciaires (Organisation Judiciaire)
- Droit Fiscal (Code General des Impots)
- Contraventions et Sanctions

## Resultats Principaux

| Metrique               | Valeur                                  |
|------------------------|-----------------------------------------|
| Articles indexees       | ~1500                                   |
| Domaines couverts       | 7                                       |
| Strategies retrieval    | 3 (Dense, BM25, RRF)                    |
| Modeles embedding eval  | 5                                       |
| Taille LLM              | ~1.1 GB (quantifie Q4_K_XL)             |
| Latence recherche       | < 100 ms (pgvector)                     |
| Latence generation      | < 5 s (GPU T4 Colab)                    |

## Impact

- Premiere base de connaissance juridique marocaine interrogeable en arabe
- Reduction des hallucinations via l'ancrage dans les textes officiels
- Architecture legere et deployable localement (Docker)
- Pipeline reproductible de bout en bout (PDF -> OCR -> Embedding -> RAG)
