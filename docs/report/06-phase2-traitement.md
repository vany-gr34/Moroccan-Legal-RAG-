# 6. Phase 2 -- Traitement et Validation des Donnees

---

## 6.1 Pipeline de Nettoyage

```
+------------+     +------------+     +------------+     +------------+
| TEXTE BRUT | --> | CLEANING   | --> |NORMALISATION| --> | VALIDATION | --> CORPUS
| (OCR/VLM)  |     |            |     |             |     |            |     PROPRE
+------------+     +------------+     +------------+     +------------+
                         |                  |                  |
                         v                  v                  v
                  +------------+     +------------+     +------------+
                  | cleaning   |     |normalization|     | structure  |
                  | .yaml      |     | .yaml       |     | parser     |
                  +------------+     +------------+     +------------+
```

## 6.2 Module de Nettoyage (LegalTextCleaner)

### Regles appliquees

| Regle                      | Exemple avant                    | Exemple apres             |
|----------------------------|----------------------------------|---------------------------|
| Suppression headers/footers| `Page 12 - Code Penal`          | (supprime)                |
| Normalisation espaces      | `المادة    513`                  | `المادة 513`             |
| Suppression lignes vides   | `\n\n\n`                        | `\n`                      |
| Correction retours a la ligne| `الماد\nة`                     | `المادة`                 |
| Suppression caracteres parasites| `~~~article 1~~~`          | `article 1`               |

### Configuration (cleaning.yaml)

```yaml
cleaning:
  remove_headers: true
  remove_footers: true
  normalize_spaces: true
  remove_empty_lines: true
  fix_line_breaks: true
  remove_special_chars: false  # preserve Arabic diacritics
  
  patterns:
    header_patterns:
      - "Page \\d+"
      - "الجريدة الرسمية"
    footer_patterns:
      - "\\d+$"
```

## 6.3 Module de Normalisation Arabe (ArabicNormalizer)

### Regles appliquees

| Regle                      | Exemple avant       | Exemple apres         |
|----------------------------|---------------------|-----------------------|
| Unification alef           | إ, أ, آ -> ا        | امن -> امن            |
| Unification taa marbouta   | ة -> ه               | مادة -> ماده          |
| Suppression tatweel        | المــــادة          | المادة                |
| Normalisation chiffres     | ١٢٣ -> 123          | ١٢٣ -> 123            |
| Unification ponctuation    | ؛ -> ,               | نص؛ نص -> نص, نص      |

### Configuration (normalization.yaml)

```yaml
normalization:
  unify_alef: true
  unify_taa_marbouta: true
  remove_tatweel: true
  normalize_digits: true
  unify_punctuation: true
  
  preserve:
    - shadda
    - diacritics_in_quran_verses
```

## 6.4 Module de Structuration (LegalStructureParser)

```
+-------------------------------------------------+
|                STRUCTURE PARSER                  |
|                                                 |
|  Texte Brut --> Detection des motifs :          |
|                                                 |
|  +------------------------------------------+   |
|  | "المادة X"  -> debut article              |   |
|  | "الباب Y"   -> debut chapitre             |   |
|  | "القسم Z"   -> debut section               |   |
|  | "الكتاب W"  -> debut livre                 |   |
|  +------------------------------------------+   |
|                                                 |
|  --> Sortie : articles structures avec          |
|      hierarchie (livre > chapitre > section)     |
+-------------------------------------------------+
```

## 6.5 Defis Rencontres et Solutions

| Probleme                          | Solution appliquee                          |
|-----------------------------------|----------------------------------------------|
| Bruit OCR (caracteres incorrects) | Correction VLM + regles de cleaning          |
| Texte duplique                    | Detection par hash MD5 + similarite cosinus  |
| Melange Arabe/Francais            | Segmentation par detection de script Unicode |
| Metadonnees manquantes            | Inference par heuristiques (motifs dans texte)|
| Formatage irregulier              | Normalisation configurable via YAML          |
| Pages manquantes                  | Log + re-extraction                          |

## 6.6 Validation du Corpus

### Controles qualite

```
+------------------+     +------------------+     +------------------+
| COHERENCE        |     | COMPLETUDE       |     | CONSISTANCE      |
+------------------+     +------------------+     +------------------+
| - Numero article |     | - Articles       |     | - Format JSON    |
|   unique par loi |     |   attendus       |     |   valide         |
| - Sequence       |     |   presents       |     | - Tous les champs|
|   continue       |     | - Pas de trous   |     |   obligatoires   |
+------------------+     +------------------+     +------------------+
```

### Rapports de validation

```json
{
  "law_name": "code penal maroc ar",
  "total_articles": 790,
  "missing_articles": [],
  "duplicate_articles": [],
  "articles_with_empty_text": 0,
  "sequence_gaps": [],
  "validation_passed": true
}
```
