# 9. Phase 5 -- Systeme RAG Complet

---

## 9.1 Architecture RAG

```
+===========================================================================+
|                          RAG PIPELINE COMPLET                             |
+===========================================================================+
|                                                                           |
|  +------------------+                                                     |
|  | QUESTION UTILIS. |  "ما هي عقوبة السرقة في القانون المغربي؟"           |
|  +--------+---------+                                                     |
|           |                                                               |
|           v                                                               |
|  +------------------+     +------------------+     +------------------+   |
|  |    EMBEDDING     |     |      BM25        |     |                  |   |
|  |    E5-large      |     |    rank-bm25     |     |                  |   |
|  |    (1024d)       |     |    (lexical)     |     |                  |   |
|  +--------+---------+     +--------+---------+     |                  |   |
|           |                        |               |                  |   |
|           v                        v               |                  |   |
|  +------------------+     +------------------+     |                  |   |
|  | pgvector cosine  |     | token overlap    |     |                  |   |
|  | top-20 ids+ranks |     | top-20 ids+ranks |     |                  |   |
|  +--------+---------+     +--------+---------+     |                  |   |
|           |                        |               |                  |   |
|           +------------+-----------+               |                  |   |
|                        |                           |                  |   |
|                        v                           |                  |   |
|  +------------------------------------------------+                  |   |
|  |              FUSION RRF (k=60)                                    |   |
|  |                                                                  |   |
|  |  RRF(d) = SUM(1 / (k + rank_i(d)))                              |   |
|  |                                                                  |   |
|  |  pour chaque document d, sur les strategies i                    |   |
|  +-------------------------------+----------------------------------+   |
|                                  |                                      |
|                                  v                                      |
|  +-------------------------------+----------------------------------+   |
|  |                        TOP-K = 5                                   |   |
|  |  +----------------------------------------------------------+    |   |
|  |  | #1 | Art 513 | Code Penal    | score=0.92 | "يعتبر الحدث..."|    |   |
|  |  | #2 | Art 508 | Code Penal    | score=0.87 | "يعاقب على الس..."|   |   |
|  |  | #3 | Art 509 | Code Penal    | score=0.81 | "ترفع العقوبة..." |   |   |
|  |  | #4 | Art 514 | Code Penal    | score=0.76 | "يتخذ قاضي..."   |   |   |
|  |  | #5 | Art 512 | Code Penal    | score=0.73 | "يقصد بالحدث..." |   |   |
|  |  +----------------------------------------------------------+    |   |
|  +-------------------------------+----------------------------------+   |
|                                  |                                      |
|                                  v                                      |
|  +-------------------------------+----------------------------------+   |
|  |                     PROMPT CONSTRUCTION                             |   |
|  |                                                                     |   |
|  |  System: انت مساعد قانوني متخصص في القانون المغربي                  |   |
|  |          اجب فقط بناء على النصوص المسترجعة                          |   |
|  |                                                                     |   |
|  |  Context: [1] المادة 513 من القانون الجنائي:                       |   |
|  |           يعتبر الحدث البالغ من العمر اقل من 16 سنة...              |   |
|  |           [2] المادة 508 من القانون الجنائي:                       |   |
|  |           يعاقب على السرقة الموصوفة بالسجن...                       |   |
|  |                                                                     |   |
|  |  Question: ما هي عقوبة السرقة في القانون المغربي؟                   |   |
|  +-------------------------------+----------------------------------+   |
|                                  |                                      |
|                                  v                                      |
|  +-------------------------------+----------------------------------+   |
|  |                     LLM GENERATION                                   |   |
|  |                                                                     |   |
|  |  Gemma 4 2B (Q4_K_XL GGUF) via llama.cpp                            |   |
|  |  temperature=0.3  max_tokens=512                                    |   |
|  +-------------------------------+----------------------------------+   |
|                                  |                                      |
|                                  v                                      |
|  +-------------------------------+----------------------------------+   |
|  |                     REPONSE FINALE                                   |   |
|  |                                                                     |   |
|  |  حسب المادتين 508 و 509 من القانون الجنائي المغربي،                 |   |
|  |  يعاقب على السرقة الموصوفة بالسجن من 5 الى 10 سنوات...             |   |
|  |                                                                     |   |
|  |  المصادر:                                                           |   |
|  |  - المادة 508 من القانون الجنائي                                   |   |
|  |  - المادة 509 من القانون الجنائي                                   |   |
|  |                                                                     |   |
|  |  تنبيه: هذه الاجابة مولدة اليا، يرجى مراجعة النصوص الاصلية.         |   |
|  +------------------------------------------------------------------+   |   |
|                                                                           |
+===========================================================================+
```

## 9.2 Strategies de Recherche

### Implementation

| Strategie   | Classe                        | Description                              |
|-------------|-------------------------------|------------------------------------------|
| Dense       | `DenseRetrieval`              | Cosine similarity via pgvector            |
| BM25        | `BM25Retrieval`              | PostgreSQL tsvector + rank-bm25 Python    |
| RRF         | `RRFRetrieval`               | Fusion Dense + BM25 via Reciprocal Rank   |

### Code de la factory

```python
def create_retrieval_strategy(strategy_name: str = "rrf", **kwargs):
    if strategy_name == "dense":
        return DenseRetrieval()
    elif strategy_name == "bm25":
        return BM25Retrieval()
    elif strategy_name == "rrf":
        return RRFRetrieval(k_rrf=kwargs.get("k_rrf", 60))
```

### Formule RRF (Reciprocal Rank Fusion)

```
RRF(d) = SUM over strategies i [ 1 / (k + rank_i(d)) ]

ou :
  d     = document (article juridique)
  i     = strategie (dense, bm25)
  k     = constante de lissage (60 par defaut)
  rank  = position du document dans les resultats de la strategie i
```

## 9.3 Service de Generation (LLM)

### Configuration Gemma 4

```
+--------------------------------------------------+
|           CONFIGURATION LLM (llama.cpp)            |
+--------------------------------------------------+
|                                                  |
|  Modele : unsloth/gemma-4-E2B-it-qat-GGUF        |
|  Taille : 2B parametres                           |
|  Quantification : Q4_K_XL (GGUF)                  |
|  Taille fichier : ~1.1 Go                         |
|  Contexte max : 16384 tokens                      |
|  GPU Layers : -1 (tous sur GPU si dispo)          |
|  Temperature : 0.3                                |
|  Top-P : 0.9                                      |
|  Max tokens : 512                                 |
|                                                  |
+--------------------------------------------------+
```

### Strategie de prompt

```
+--------------------------------------------------+
|              PROMPT SYSTEM (francais)              |
+--------------------------------------------------+
| Tu es un assistant juridique specialise dans le   |
| droit marocain. Tu reponds UNIQUEMENT en arabe.   |
| Base ta reponse EXCLUSIVEMENT sur les articles    |
| de loi fournis ci-dessous.                        |
| Si les articles ne permettent pas de repondre,    |
| dis-le clairement.                                |
| N'invente JAMAIS d'article de loi.                 |
| Cite TOUJOURS les numeros d'article utilises.     |
+--------------------------------------------------+
```

## 9.4 API Endpoints

| Methode | Endpoint           | Description                              |
|---------|--------------------|------------------------------------------|
| GET     | `/api/v1/health`   | Etat du systeme                          |
| POST    | `/api/v1/search`   | Recherche juridique (retrieval seul)     |
| POST    | `/api/v1/ask`      | Question-reponse juridique (RAG complet) |
| GET     | `/api/v1/laws`     | Liste des lois disponibles               |
| POST    | `/api/v1/upload`   | Upload de nouveaux PDF juridiques        |
| GET     | `/api/v1/conversations` | Historique des conversations        |

### Format requete/reponse `/ask`

```json
// Requete
{
  "query": "ما هي عقوبة السرقة في القانون المغربي؟",
  "domain": "criminal",
  "top_k": 5,
  "strategy": "rrf"
}

// Reponse
{
  "query": "ما هي عقوبة السرقة في القانون المغربي؟",
  "short_answer": "حسب المادتين 508 و 509 من القانون الجنائي...",
  "long_answer": "يعاقب على السرقة الموصوفة بالسجن من 5 الى 10 سنوات...",
  "sources": [
    {
      "article_number": "508",
      "law_name": "code penal maroc ar",
      "domain": "criminal",
      "relevance_score": 0.92
    }
  ],
  "disclaimer": "هذه الاجابة مولدة اليا...",
  "session_id": "uuid",
  "search_time_ms": 12.5,
  "generation_time_ms": 2340.0,
  "total_time_ms": 2352.5,
  "model_name": "Gemma 4 2B"
}
```
