# 10. Recherche et Experimentations

---

## 10.1 Benchmark Embedding Models

### Protocole

- **5 modeles** testes : E5-large, E5-base, MPNet, LaBSE, BGE-M3
- **26 articles** x 5 domaines juridiques
- **65 variantes** de requetes : Arabe formel, Darija, Mots-cles, Francais, Anglais
- **Metriques** : Precision@5, MRR, NDCG, Domain Accuracy

### Resultats

```
+--------------------------------------------------+
|         COMPARAISON DES MODELES D'EMBEDDING       |
+--------------------------------------------------+
|                                                  |
|  E5-large   [============================] 0.89  |
|  BGE-M3     [==========================]   0.85  |
|  LaBSE      [======================]       0.78  |
|  E5-base    [====================]         0.74  |
|  MPNet      [=================]            0.68  |
|                                                  |
|  (score = moyenne P@5, MRR, NDCG normalise)      |
+--------------------------------------------------+
```

### Analyse par type de requete

| Type de requete    | E5-large | BGE-M3  | LaBSE   |
|--------------------|----------|---------|---------|
| Arabe formel       | 0.91     | 0.88    | 0.82    |
| Darija (dialecte)  | 0.65     | 0.61    | 0.55    |
| Mots-cles          | 0.72     | 0.69    | 0.63    |
| Francais           | 0.78     | 0.75    | 0.80    |
| Anglais            | 0.81     | 0.79    | 0.77    |

**Constats :**
- E5-large domine sur l'arabe formel (langue des textes de loi)
- BGE-M3 est un excellent second choix
- Tous les modeles peinent sur le Darija (gap dialectal)
- LaBSE est le meilleur pour le francais

## 10.2 Benchmark Strategies de Recherche

### Protocole

- **3 strategies** : Dense seule, BM25 seule, RRF (fusion)
- **32 questions** du benchmark `retrieval_benchmark.json` v2.0
- **6 domaines** juridiques
- **Metriques** : Precision@5, Recall@5, MRR, NDCG@5, Hit@5

### Resultats (a obtenir avec le notebook `rag_benchmark.ipynb`)

```
+--------------------------------------------------+
|     COMPARAISON DES STRATEGIES DE RECHERCHE        |
+--------------------------------------------------+
|                                                  |
|           Precision@5  Recall@5   MRR     NDCG    |
|  Dense      [===]       [===]     [===]   [===]   |
|  BM25       [===]       [===]     [===]   [===]   |
|  RRF        [====]      [====]    [====]  [====]  |
|                                                  |
+--------------------------------------------------+
```

### Analyse par domaine

| Domaine      | Meilleure strategie | Score |
|--------------|---------------------|-------|
| Criminal     | RRF                 | --    |
| Traffic      | BM25                | --    |
| Civil        | RRF                 | --    |
| Commercial   | RRF                 | --    |
| Judicial     | Dense               | --    |
| Tax          | RRF                 | --    |

## 10.3 Experimentation VLM pour Correction OCR

### Protocole

- Modele : Gemma 4 (2B, Q4_K_XL)
- Prompt specialise : corriger sans traduire ni resumer
- Traitement article par article avec checkpoint/resume

### Exemple de correction

```
AVANT (OCR brut) :
"يعتﻼ الحدث البالغ من العمر اقل نم 61 سنة
يف وضعية صعبة اذا كا'ت سالمنه البدهية
او الدهنية او النفسية او الخلقية..."

APRES (VLM corrige) :
"يعتبر الحدث البالغ من العمر اقل من 16 سنة
في وضعية صعبة اذا كانت سلامته البدنية
او الذهنية او النفسية او الخلقية..."
```

## 10.4 Service Embedding via Colab

### Architecture du tunnel

```
+------------------+     +-------------------+     +------------------+
| Script local     |     | Cloudflare         |     | Notebook Colab   |
| embed_all.py     | --> | Tunnel (gratuit)   | --> | 02_embedding...  |
|                  |     |                    |     | E5-large GPU     |
+------------------+     +-------------------+     +------------------+
```

### Debit mesure

| Mode              | Articles/s | Latence/article |
|-------------------|------------|-----------------|
| GPU Colab (T4)   | ~20        | ~50 ms          |
| CPU local (E5-base)| ~3        | ~300 ms         |

## 10.5 Notebooks de Recherche

| Notebook                                       | Sujet                              |
|------------------------------------------------|------------------------------------|
| `01_ocr_quality_research.ipynb`                | Qualite de l'OCR sur PDF arabes    |
| `02_embedding_colab_api.ipynb`                 | Service d'embedding distant Colab  |
| `03_embedding_models_benchmark.ipynb`          | Benchmark des modeles d'embedding  |
| `04_ocr_service_colab.ipynb`                   | Service OCR sur Colab              |
| `05_reasearch_VLM.ipynb`                       | Correction OCR par VLM             |
| `06_benchmark_retreiving_strategies.ipynb`     | Benchmark strategies de recherche  |
| `07_llm_api_colab_qwen2_5.ipynb`              | Service LLM distant Colab          |
| `benchmark/rag_benchmark.ipynb`               | Benchmark RAG complet (5 metriques)|
