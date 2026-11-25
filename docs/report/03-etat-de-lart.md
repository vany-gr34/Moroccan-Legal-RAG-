# 3. Etat de l'Art

---

## 3.1 Recherche d'Information Juridique

### Systemes existants

| Systeme                 | Portee            | Approche           | Limites                         |
|-------------------------|-------------------|---------------------|----------------------------------|
| legislation.ma          | Maroc             | Mots-cles           | Pas de semantique, interface limitee |
| Legifrance              | France            | Mots-cles + thesaurus | Monolingue francais             |
| CanLII                  | Canada            | Mots-cles + IA      | Common law, pas de droit civil arabe |
| WestLaw / LexisNexis    | International     | Proprietaire        | Payant, pas d'arabe             |

**Constats :**
- Aucun systeme RAG open-source pour le droit marocain en arabe
- Les solutions existantes reposent sur la recherche par mots-cles
- L'arabe juridique est un domaine sous-explore en NLP

### Approches modernes

```
+---------------------------+     +---------------------------+
| RECHERCHE PAR MOTS-CLES   |     | RECHERCHE SEMANTIQUE (RAG) |
| (traditionnelle)          |     | (notre approche)          |
+---------------------------+     +---------------------------+
|                           |     |                           |
| "vol" -> documents        |     | "Quelle peine pour avoir  |
|  contenant le mot "vol"   |     |  pris un objet sans       |
|                           |     |  permission ?"            |
| X termes connexes ignores |     |       |                   |
| X synonymes non trouves   |     |       v                   |
| X reformulation echoue    |     | Embedding -> pgvector     |
|                           |     | -> Articles pertinents    |
|                           |     | -> Reponse generee        |
+---------------------------+     +---------------------------+
```

## 3.2 NLP pour l'Arabe

### Defis specifiques

| Defi                        | Description                                            |
|-----------------------------|--------------------------------------------------------|
| Morphologie riche           | Un mot arabe peut avoir des dizaines de formes flechies |
| Diglossie                   | Darija (dialecte) vs MSA (arabe standard moderne)      |
| Code-switching              | Melange arabe/francais dans les textes juridiques      |
| Absence de ressources       | Peu de corpus annotes pour l'arabe juridique marocain  |
| OCR sur arabe               | Les polices arabes sont difficiles pour l'OCR          |

### Modeles multilingues vs modeles arabes specialises

| Modele                    | Type              | Avantage                           |
|---------------------------|-------------------|-------------------------------------|
| AraBERT                   | Arabe uniquement  | Specialise, mais limite au MSA      |
| CAMeL-Tools               | Boite a outils    | Normalisation, lemmatisation        |
| LaBSE                     | Multilingue       | Bon pour l'arabe, 768 dimensions    |
| E5-large (multilingual)   | Multilingue       | Meilleur compromis qualite/performance |
| BGE-M3                    | Multilingue       | Excellent, 1024 dimensions          |

## 3.3 Retrieval-Augmented Generation (RAG)

### Architecture generale

```
+--------+     +------------+     +----------+     +--------+
| QUERY  | --> | RETRIEVER  | --> | PROMPT   | --> |  LLM   | --> REPONSE
+--------+     +------------+     +----------+     +--------+
                     |                                 |
                     v                                 v
              +------------+                  +---------------+
              |  BASE DE   |                  | ANCRAGE DANS  |
              | CONNAISS.  |                  | LES SOURCES   |
              +------------+                  +---------------+
```

### Variantes RAG

| Variante             | Description                                       |
|----------------------|---------------------------------------------------|
| RAG sequentiel       | Retrieval -> Generation en un seul passage        |
| RAG agentique        | Plusieurs passages avec raisonnement intermediaire |
| RAG hybride          | Combinaison de plusieurs strategies de retrieval  |
| RAG multi-tours      | Conservation du contexte de conversation           |

**Notre choix : RAG hybride sequentiel** -- bon equilibre entre qualite,
latence et simplicite de mise en oeuvre.

## 3.4 Quantification et Optimisation Memoire des LLM

### Pourquoi quantifier ?

```
+--------------------------------------------------+
|            IMPACT DE LA QUANTIFICATION            |
|                                                  |
|  Modele Gemma 4 2B :                             |
|                                                  |
|  FP16 (origine)  : ~4.0 Go VRAM                  |
|  Q8_0            : ~2.1 Go VRAM                  |
|  Q4_K_XL (choisi): ~1.1 Go VRAM  <-- UTILISE    |
|                                                  |
|  Perte de qualite mesuree : < 2%                 |
|  Gain memoire           : ~73%                   |
+--------------------------------------------------+
```

### Formats de quantification

| Format   | Bits/poids | Usage                            |
|----------|------------|----------------------------------|
| GGUF     | Variable   | llama.cpp, CPU + GPU hybride     |
| GPTQ     | 4-bit      | GPU uniquement                   |
| AWQ      | 4-bit      | GPU, meilleur que GPTQ           |
| EXL2     | Variable   | GPU, haute performance            |

**Notre choix : GGUF Q4_K_XL via llama.cpp** -- compatible CPU+GPU,
deployable sur Colab T4 et machines locales.

### Solutions legeres

| Outil      | Avantage                          |
|------------|-----------------------------------|
| llama.cpp  | CPU+GPU, GGUF, performances elevees |
| Ollama     | Simplicite d'installation         |
| vLLM       | Haute performance GPU             |
