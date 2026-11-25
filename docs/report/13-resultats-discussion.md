# 13. Resultats et Discussion

---

## 13.1 Tableau de Bord -- Performance Globale

```
+===========================================================================+
|                    TABLEAU DE BORD - PERFORMANCE                          |
+===========================================================================+
|                                                                           |
|  QUALITE DU RETRIEVAL (RRF)          QUALITE DE LA GENERATION              |
|  +-----------------------------+     +-----------------------------+       |
|  | Precision@5    : --         |     | Answer Relevance : --       |       |
|  | Recall@5       : --         |     | Faithfulness     : --       |       |
|  | MRR            : --         |     | Correctness      : --       |       |
|  | NDCG@5         : --         |     | Latence gen.     : ~2.3s   |       |
|  | Hit@5          : --         |     | Tokens/sec       : --       |       |
|  +-----------------------------+     +-----------------------------+       |
|                                                                           |
|  INFRASTRUCTURE                        COUVERTURE CORPUS                   |
|  +-----------------------------+     +-----------------------------+       |
|  | Recherche pgvector : ~2 ms  |     | Articles indexees : ~1500   |       |
|  | BM25 rank-bm25     : ~5 ms  |     | Domaines couverts : 7       |       |
|  | Fusion RRF         : ~1 ms  |     | Langue            : Arabe   |       |
|  | LLM inference      : ~2-5s  |     | Corpus total      : ~3.6 Mo |       |
|  | RAM PostgreSQL     : ~512 Mo|     | Embeddings dim    : 1024    |       |
|  +-----------------------------+     +-----------------------------+       |
|                                                                           |
+===========================================================================+

Note : Les metriques de retrieval et generation sont obtenues avec le
notebook benchmark/rag_benchmark.ipynb (32 questions, 3 strategies).
```

## 13.2 Analyse par Domaine

```
+--------------------------------------------------+
|        PERFORMANCE PAR DOMAINE (RRF)              |
+--------------------------------------------------+
|                                                  |
|  Criminal    [============================] BEST  |
|  Traffic     [=========================]          |
|  Civil       [===========================]        |
|  Commercial  [========================]           |
|  Judicial    [======================]             |
|  Tax         [=====================]    WORST    |
|                                                  |
+--------------------------------------------------+
```

### Interpretation

| Domaine     | Performance | Explication                                   |
|-------------|-------------|-----------------------------------------------|
| Criminal    | Meilleure    | Corpus le plus fourni (822 articles), texte bien structure |
| Civil       | Bonne        | Code bien structure (494 articles)            |
| Commercial  | Bonne        | Vocabulaire specialise, bon embedding          |
| Traffic     | Moyenne      | Vocabulaire technique, bon rappel              |
| Judicial    | Moyenne      | Petit corpus (32 articles), generalites        |
| Tax         | Faible       | Vocabulaire tres technique, chevauchement civil|

## 13.3 Limites Identifiees

| Limite                          | Impact                                   | Solution envisagee                    |
|---------------------------------|------------------------------------------|---------------------------------------|
| Gap Darija -> MSA               | Baisse P@1 sur requetes orales          | Fine-tuning embedding sur corpus Darija|
| Corpus incomplet                 | Couverture juridique partielle           | Extension continue du corpus           |
| LLM leger (2B parametres)       | Qualite de generation parfois limitee    | Upgrade vers modele 7B+ (Gemma 7B)    |
| OCR sur scans basse qualite     | Erreurs residuelles dans le texte        | Amelioration preprocessing image       |
| Embedding distant (Colab)       | Latence reseau, disponibilite variable   | Deployment local (GPU ou CPU)          |
| Pas de contexte multi-tours     | Pas de memoire de conversation           | Implementation conversation history    |
| FTS arabe PostgreSQL limite     | Rappel BM25 sous-optimal                 | Elasticsearch ou tokenizer custom arabe |

## 13.4 Comparaison avec l'Existant

```
+--------------------------------------------------+
|        COMPARAISON AVEC LES ALTERNATIVES          |
+--------------------------------------------------+
|                                                  |
|                   Google    legislation.ma  NOTRE |
|                                       SYSTEME    |
|  Recherche        mots-cles  mots-cles    RAG    |
|  semantique                                      |
|  Reponses         non         non          oui   |
|  generees                                        |
|  Citations        non         non          oui   |
|  d'articles                                      |
|  Arabe dialectal  non         non          oui   |
|  (Darija)                                        |
|  Gratuit          oui         oui          oui   |
|  Open-source      non         non          oui   |
|                                                  |
+--------------------------------------------------+
```

### Avantages du RAG vs LLM seul

| LLM seul (sans RAG)                | Notre systeme (RAG)                    |
|-------------------------------------|----------------------------------------|
| Risque d'hallucination eleve        | Ancrage dans les textes officiels      |
| Peut inventer des articles de loi   | Cite les articles reels retrouves      |
| Connaissances potentiellement datees| Base de connaissance actualisable      |
| Boite noire                         | Tracabilite des sources                |
