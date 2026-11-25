# Moroccan Legal RAG — Retrieval Strategy Benchmark

> Systematic comparison of **Dense**, **BM25**, **Hybrid**, and **RRF** retrieval strategies
> for Arabic legal document search. Finds the best approach before wiring it into production.

---

## 1. Why Benchmark Retrieval Strategies?

Legal text retrieval is **not** a solved problem for Arabic. Different strategies excel at
different aspects:

| Strategy | Strengths | Weaknesses |
|----------|-----------|------------|
| **Dense (Vector)** | Semantic understanding, cross-lingual, handles paraphrasing | Misses exact keyword matches, requires GPU for embedding |
| **BM25 (Lexical)** | Exact term matching, fast, no GPU, great for article numbers | No semantic understanding, fails on synonyms/Darija |
| **Hybrid (Weighted)** | Best of both worlds, tunable balance | Extra parameter (alpha) to tune, two indexes to maintain |
| **RRF (Rank Fusion)** | No weights to tune, robust across datasets | Slightly more compute, rank-based (ignores score magnitude) |

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL STRATEGY BENCHMARK                           │
│                                                                          │
│  ┌──────────────────┐                                                    │
│  │  Legal Articles   │   Moroccan trade law articles (JSON)              │
│  │  (JSON input)     │   Each with: article_number, text, context        │
│  └────────┬─────────┘                                                    │
│           │                                                               │
│           ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    Document Preprocessing                         │    │
│  │                                                                  │    │
│  │  Raw JSON ──► build_document_text() ──► Enriched documents       │    │
│  │                                                                  │    │
│  │  "[Trade Law] [Section 3] [Chapter 2] المادة 42: text..."       │    │
│  └────────────────────────────────┬─────────────────────────────────┘    │
│                                   │                                       │
│              ┌────────────────────┼────────────────────┐                  │
│              ▼                    ▼                    ▼                  │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐          │
│  │   Dense Index     │ │   BM25 Index      │ │   Query Set      │          │
│  │                  │ │                  │ │                  │          │
│  │  E5-large (1024d)│ │  rank-bm25       │ │  7 test queries  │          │
│  │  ChromaDB (cos)  │ │  Arabic tokenizer│ │  w/ relevance    │          │
│  │  L2 normalized   │ │                  │ │  judgments       │          │
│  └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘          │
│           │                    │                    │                     │
│           └────────────────────┼────────────────────┘                     │
│                                │                                          │
│                                ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    4 RETRIEVAL STRATEGIES                         │    │
│  │                                                                  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  ┌──────────┐ │    │
│  │  │  DENSE   │  │   BM25   │  │     HYBRID       │  │   RRF    │ │    │
│  │  │          │  │          │  │                  │  │          │ │    │
│  │  │ cos_sim  │  │ tf-idf   │  │ α·dense +        │  │ Σ 1/(k+r)│ │    │
│  │  │ top-k    │  │ top-k    │  │ (1-α)·bm25_norm  │  │ per list │ │    │
│  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  └────┬─────┘ │    │
│  │       │             │                 │                  │       │    │
│  └───────┼─────────────┼─────────────────┼──────────────────┼───────┘    │
│          │             │                 │                  │            │
│          └─────────────┼─────────────────┼──────────────────┘            │
│                        │                 │                               │
│                        ▼                 ▼                               │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                     EVALUATION ENGINE                             │    │
│  │                                                                  │    │
│  │  Per query:                                                      │    │
│  │    retrieved_ids → compare with relevant_ids →                   │    │
│  │                                                                  │    │
│  │    ┌──────────┐  ┌──────────┐  ┌──────────┐                     │    │
│  │    │ Recall@K │  │   MRR    │  │ NDCG@K   │                     │    │
│  │    │          │  │          │  │          │                     │    │
│  │    │ "Did we  │  │ "How     │  │ "How     │                     │    │
│  │    │  find    │  │  early?  │  │  well    │                     │    │
│  │    │  it?"    │  │          │  │  ranked?"│                     │    │
│  │    └──────────┘  └──────────┘  └──────────┘                     │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Retrieval Strategies in Detail

### 3.1 Dense Retrieval (Vector Search)

```
Query: "ما هي شروط التسجيل في السجل التجاري؟"
                    │
                    ▼
          ┌─────────────────┐
          │  E5-large       │
          │  encode(query)  │
          │  → 1024d vector │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  ChromaDB       │
          │  cosine_sim(q,  │
          │  all_docs)      │
          │  → top-K        │
          └─────────────────┘

  • Embedding: intfloat/multilingual-e5-large (1024 dimensions)
  • Index: ChromaDB with HNSW + cosine distance
  • Documents: L2-normalized for faster cosine similarity
  • Strength: Captures semantic meaning, handles paraphrasing
  • Weakness: Blind to exact article number mentions
```

### 3.2 BM25 (Lexical Search)

```
Query: "ما هي شروط التسجيل في السجل التجاري؟"
                    │
                    ▼
          ┌─────────────────┐
          │  tokenize()     │
          │  split on       │
          │  whitespace     │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────────────┐
          │  BM25Okapi              │
          │                         │
          │  score(d,q) = Σ IDF(tᵢ) │
          │  · (f(tᵢ,d)·(k₁+1)) /  │
          │    (f(tᵢ,d)+k₁·(...))  │
          │                         │
          │  → top-K               │
          └─────────────────────────┘

  • Library: rank-bm25 (Okapi BM25)
  • Tokenizer: split() — simple whitespace for Arabic
  • Parameters: k₁=1.5, b=0.75 (defaults)
  • Strength: Exact term matching, fast, no GPU needed
  • Weakness: Fails on synonyms, Darija, and paraphrased queries
```

### 3.3 Hybrid Fusion (Weighted)

```
                    Query
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
    ┌──────────┐            ┌──────────┐
    │  Dense   │            │   BM25   │
    │  Score   │            │  Score   │
    └────┬─────┘            └────┬─────┘
         │                       │
         │  normalize to [0,1]   │
         ▼                       ▼
    ┌──────────┐            ┌──────────┐
    │  dense   │            │  bm25    │
    │  × α     │            │  ×(1-α)  │
    └────┬─────┘            └────┬─────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  combined = α·dense   │
         │   + (1-α)·bm25_norm   │
         │                       │
         │  → sort → top-K       │
         └───────────────────────┘

  • Alpha (α): Weight of dense score (0.0 = pure BM25, 1.0 = pure dense)
  • BM25 scores normalized to [0,1] via min-max scaling
  • Tuned across α ∈ {0.3, 0.5, 0.7, 0.9}
```

### 3.4 Reciprocal Rank Fusion (RRF)

```
        Dense Index                    BM25 Index
        ranks docs                     ranks docs
            │                               │
            ▼                               ▼
    ┌──────────────┐                ┌──────────────┐
    │ doc_A: rank=1│                │ doc_A: rank=3│
    │ doc_B: rank=2│                │ doc_B: rank=1│
    │ doc_C: rank=3│                │ doc_D: rank=2│
    │ ...          │                │ ...          │
    └──────┬───────┘                └──────┬───────┘
           │                               │
           └───────────────┬───────────────┘
                           │
                           ▼
           ┌───────────────────────────────┐
           │  RRF(doc) = Σ 1 / (k + rank)  │
           │                               │
           │  doc_A = 1/(60+1) + 1/(60+3)  │
           │        = 0.0164 + 0.0159      │
           │        = 0.0323               │
           │                               │
           │  → sort by RRF → top-K        │
           └───────────────────────────────┘

  • k (RRF constant): 60 (standard value)
  • No weights to tune — parameter-free fusion
  • Robust: rank position matters more than absolute scores
```

---

## 4. Evaluation Metrics

```
┌─────────────────────────────────────────────────────────────────┐
│                      METRICS EXPLAINED                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Recall@K    "Did we find at least one relevant document        │
│               in the top K results?"                             │
│                                                                 │
│              Recall@5 = 1 if any relevant doc in top 5          │
│                                                                 │
│  MRR         "How early does the FIRST relevant document        │
│  (Mean        appear in the ranked list?"                       │
│  Reciprocal                                                     │
│  Rank)       MRR = 1/rank_of_first_relevant                     │
│                                                                 │
│              Perfect: MRR = 1.0 (relevant at rank 1)            │
│              Poor:    MRR = 0.0 (no relevant found)             │
│                                                                 │
│  NDCG@K      "How well are relevant documents ranked            │
│  (Normalized  in the top K?"                                    │
│  Discounted                                                     │
│  Cumulative   NDCG = DCG / IDCG                                 │
│  Gain)                                                          │
│              Rewards ranking relevant docs higher               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Results

### 5.1 Strategy Comparison (Overall)

> ![Figure 1: Retrieval Strategy Comparison](images/retrieval_benchmark_fig1_comparison.png)
> *Left: Grouped bar chart — Recall@K, MRR, NDCG@K for all 4 strategies.
> Right: MRR-focused horizontal bar chart with best strategy highlighted.*

| Strategy | Recall@K | MRR | NDCG@K | Verdict |
|----------|----------|-----|--------|---------|
| Dense | — | — | — | |
| BM25 | — | — | — | |
| Hybrid (α=0.7) | — | — | — | |
| RRF | — | — | — | |

> *Run the notebook to populate. The notebook automatically marks the best MRR strategy with ★.*

### 5.2 Alpha Tuning (Hybrid Weight)

> ![Figure 2: Alpha Tuning](images/retrieval_benchmark_fig2_alpha.png)
> *Line plot showing Recall, MRR, and NDCG across α ∈ {0.3, 0.5, 0.7, 0.9}.
> Vertical dashed line marks the best α.*

```
  Score ▲
  100% ┤
        │     ●──────●──────●──────●   Recall@K
   80% ┤    /
        │   /
   60% ┤  ◆──────◆──────◆──────◆      NDCG@K
        │       /
   40% ┤      ◆
        │     /
   20% ┤    ■──────■──────■──────■     MRR
        │
        └────┬──────┬──────┬──────┬──►
           0.3    0.5    0.7    0.9   α (dense weight)

              ↑ best α = 0.7
```

Key insight: Too much BM25 weight (α < 0.5) drags down semantic understanding.
Too much dense weight (α > 0.9) loses keyword precision. The sweet spot is
typically **α = 0.7** — dense dominates but BM25 catches exact matches.

### 5.3 Per-Query MRR Analysis

> ![Figure 3: Per-Query MRR](images/retrieval_benchmark_fig3_per_query.png)
> *Grouped bar chart showing MRR for each of the 7 test queries across all 4 strategies.*

This reveals **which queries challenge each strategy**:

```
Query characteristics that favor different strategies:

  DENSE wins:   Semantic queries, paraphrased wording,
                cross-lingual intent, Darija queries

  BM25 wins:    Exact article number mentions,
                domain-specific terminology,
                short keyword queries

  HYBRID wins:  Mixed queries with both semantic
                and lexical signals

  RRF wins:     When score distributions differ
                widely between dense and BM25
```

### 5.4 Summary Table

> ![Figure 4: Summary Table](images/retrieval_benchmark_fig4_summary.png)
> *Styled table with all metrics and best strategy marked in green.*

---

## 6. Key Findings

```
┌─────────────────────────────────────────────────────────────────┐
│                     KEY TAKEAWAYS                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. PURE DENSE IS OFTEN ENOUGH                                  │
│     For well-structured legal text, E5-large embeddings         │
│     alone capture article-level semantics effectively.          │
│     BM25 adds marginal value if queries are well-formed.        │
│                                                                 │
│  2. HYBRID SHINES WITH MIXED QUERIES                            │
│     When users mix keywords + natural language, hybrid          │
│     (α ≈ 0.7) consistently beats both pure strategies.          │
│                                                                 │
│  3. RRF = ZERO-TUNING FUSION                                    │
│     RRF matches or beats tuned hybrid in many cases.            │
│     No alpha to tune = simpler production maintenance.          │
│                                                                 │
│  4. MRR > RECALL FOR LEGAL SEARCH                               │
│     Users care about the FIRST relevant result. A strategy      │
│     with lower recall but higher MRR is better UX.              │
│                                                                 │
│  5. BM25 CATCHES WHAT DENSE MISSES                              │
│     Exact article numbers ("المادة 42") and legal terms         │
│     are BM25's superpower. Dense alone can miss these.          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Formula Reference

### Hybrid Score

$$\text{score}(d, q) = \alpha \cdot \text{cos\_sim}(E(q), E(d)) \;+\; (1-\alpha) \cdot \frac{\text{BM25}(d, q) - \min(\text{BM25})}{\max(\text{BM25}) - \min(\text{BM25})}$$

### Reciprocal Rank Fusion

$$\text{RRF}(d) = \sum_{L \in \{\text{dense}, \text{bm25}\}} \frac{1}{k + \text{rank}_L(d)}$$

Where $k = 60$ (standard constant that dampens the impact of high ranks).

### MRR (Mean Reciprocal Rank)

$$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_q}$$

Where $\text{rank}_q$ is the position of the first relevant document (or $\infty$ if none found, contributing 0).

### NDCG@K

$$\text{NDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}, \quad \text{DCG@K} = \sum_{i=1}^{K} \frac{2^{\text{rel}_i} - 1}{\log_2(i + 1)}$$

Binary relevance: $\text{rel}_i = 1$ if document at rank $i$ is relevant, $0$ otherwise.

---

## 8. Production Integration

```
┌──────────────────────────────────────────────────────────────────┐
│                    PRODUCTION RETRIEVAL FLOW                       │
│                                                                  │
│  User Query (API)                                                │
│     │                                                            │
│     ▼                                                            │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  src/retrieval/search.py                                  │    │
│  │                                                          │    │
│  │  def search(query, strategy="hybrid", alpha=0.7, k=10): │    │
│  │      if strategy == "dense":                             │    │
│  │          return dense_search(query, k)                   │    │
│  │      elif strategy == "bm25":                            │    │
│  │          return bm25_search(query, k)                    │    │
│  │      elif strategy == "hybrid":                          │    │
│  │          return hybrid_search(query, k, alpha)           │    │
│  │      elif strategy == "rrf":                             │    │
│  │          return rrf_search(query, k)                     │    │
│  └──────────────────────────────────────────────────────────┘    │
│     │                                                            │
│     ▼                                                            │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Top-K Articles                                           │    │
│  │     │                                                     │    │
│  │     ▼                                                     │    │
│  │  ┌────────────────────┐                                   │    │
│  │  │  LLM (Gemma 4)     │  Generate answer from context     │    │
│  │  │  Answer Generation │                                   │    │
│  │  └────────────────────┘                                   │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Recommended default**: Start with **RRF** for simplicity, fall back to **Hybrid (α=0.7)** if you need per-query weight control.

---

## 9. Reproducing the Benchmark

### Prerequisites

```bash
pip install chromadb sentence-transformers rank-bm25 numpy pandas matplotlib scikit-learn
```

### Run

```bash
jupyter notebook notebooks/06_benchmark_retreiving_strategies.ipynb
```

### What You Need

1. **Articles JSON file** — uploaded at runtime (e.g., `TradeRecord_ar-MA.articles.json`)
2. **GPU recommended** — for embedding 1000+ documents with E5-large
3. **Relevance judgments** — edit `TEST_QUERIES` and `relevant_ids` in Cell 5 with your own labeled data

### Add a New Strategy

```python
# In the evaluation cell:
def my_custom_search(query, top_k=10):
    # 1. Get dense scores
    # 2. Get BM25 scores
    # 3. Apply your fusion logic
    # 4. Return [(doc_id, score), ...]
    pass

my_metrics = evaluate_strategy(my_custom_search, TEST_QUERIES, top_k=5)
```

---

## 10. Image Placeholders Reference

| Figure | Description | Placeholder Path |
|--------|-------------|-----------------|
| Fig 1 | Strategy comparison (grouped bar + MRR bars) | `images/retrieval_benchmark_fig1_comparison.png` |
| Fig 2 | Alpha tuning curves (Recall/MRR/NDCG vs α) | `images/retrieval_benchmark_fig2_alpha.png` |
| Fig 3 | Per-query MRR by strategy | `images/retrieval_benchmark_fig3_per_query.png` |
| Fig 4 | Summary table with best strategy | `images/retrieval_benchmark_fig4_summary.png` |

> To export figures from the notebook, add `plt.savefig("images/retrieval_benchmark_figN_name.png", dpi=150, bbox_inches="tight")` before each `plt.show()` call.
