# 7. Phase 3 -- Pipeline NLP

---

## 7.1 Segmentation et Chunking

### Strategie de decoupage

```
+----------------------------------------------------+
|               STRATEGIE DE CHUNKING                  |
|                                                    |
|  Document complet (loi)                             |
|       |                                            |
|       v                                            |
|  Decoupage par article juridique                    |
|  (un article = un chunk)                            |
|       |                                            |
|       v                                            |
|  Chaque article recoit :                            |
|  - Son texte integral                               |
|  - Son numero d'article                             |
|  - Le nom de la loi                                 |
|  - Le domaine juridique                             |
|  - Le titre du chapitre (contexte)                  |
|  - Le titre de la section (contexte)                |
|       |                                            |
|       v                                            |
|  Embedding individuel + stockage pgvector           |
+----------------------------------------------------+
```

### Pourquoi chunker par article ?

| Approche              | Avantage                         | Inconvenient                    |
|-----------------------|----------------------------------|---------------------------------|
| Par article           | Precision juridique, tracabilite | Articles tres longs rares       |
| Fenetre fixe (512 tok)| Uniformite                       | Casse les articles en deux      |
| Fenetre glissante     | Contexte continu                 | Duplication, bruit              |

**Notre choix : chunking par article** -- adapte a la nature des textes
juridiques ou chaque article est une unite de sens autonome.

## 7.2 Pipeline d'Embedding

```
+------------------+     +------------------+     +------------------+
|  ARTICLE ARABE   | --> |   E5-large       | --> |   VECTEUR 1024d  |
|  (texte nettoye) |     |   (GPU T4 Colab) |     |   (float32)      |
+------------------+     +------------------+     +------------------+
                                                          |
                                                          v
+------------------+     +------------------+     +------------------+
|  INDEX HNSW      | <-- |   pgvector       | <-- |   INSERT INTO    |
|  (recherche       |     |   (cosine)       |     |   legal_chunks   |
|   rapide)        |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
```

## 7.3 Modeles d'Embedding Evalues

| Modele                     | Dim  | Taille    | P@5 Moy | MRR    | Dom. Acc |
|----------------------------|------|-----------|---------|--------|----------|
| intfloat/multilingual-e5-large | 1024 | 560M    | 0.72   | 0.81   | 0.89     |
| BAAI/bge-m3               | 1024 | 568M     | 0.69   | 0.78   | 0.85     |
| sentence-transformers/LaBSE| 768  | 470M     | 0.61   | 0.70   | 0.78     |
| intfloat/multilingual-e5-base | 768  | 278M    | 0.58   | 0.67   | 0.74     |
| paraphrase-multilingual-mpnet | 768  | 278M    | 0.52   | 0.61   | 0.68     |

**Modele retenu : E5-large (meilleur compromis qualite/ressources)**

### Criteres de selection

1. **Performance sur l'arabe juridique** : E5-large et BGE-M3 dominent
2. **Dimension** : 1024d offre une meilleure expressivite que 768d
3. **Support multilingue** : Gestion du melange arabe/francais
4. **Stabilite** : E5-large est plus mature que BGE-M3
5. **Disponibilite GPU** : 560M params tient sur un T4 Colab (16 Go)

## 7.4 Service d'Embedding Distant

### Architecture

```
+------------------+        +------------------+        +------------------+
| MACHINE LOCALE   |        | CLOUDFLARE TUNNEL|        | GOOGLE COLAB T4  |
|                  |        |                  |        |                  |
| src/core/        |  HTTP  | trycloudflare    |  HTTP  | FastAPI :8000    |
| embedding.py     +--------> .com             +--------> E5-large GPU     |
|                  |        | (tunnel gratuit) |        | (16 Go VRAM)     |
+------------------+        +------------------+        +------------------+
        |                                                       |
        |  Fallback si tunnel down                              |
        +-------------------------------------------------------+
                   Embedding CPU local (E5-base)
```

### Endpoint du service distant

```
POST /embed
Content-Type: application/json

{
  "texts": ["المادة 513 من القانون الجنائي ..."],
  "model": "intfloat/multilingual-e5-large"
}

Response:
{
  "embeddings": [[0.123, -0.456, ...]],
  "model": "intfloat/multilingual-e5-large",
  "dimension": 1024,
  "time_ms": 45.2
}
```

### Avantages de l'approche distante

| Avantage                    | Description                                     |
|-----------------------------|-------------------------------------------------|
| GPU gratuit                 | Colab T4 gratuit, pas de cout d'infrastructure  |
| Latence acceptable          | ~50 ms par embedding via Cloudflare Tunnel       |
| Scalabilite                 | Indexation par lots (batch processing)           |
| Fallback local              | Repli sur CPU si le service est indisponible     |
