# 5. Phase 1 -- Collecte et Constitution du Corpus

---

## 5.1 Sources de Donnees

```
+----------------------------+     +---------------------------+
|         SOURCES             |     |        EXTRACTION         |
+----------------------------+     +---------------------------+
|                            |     |                           |
| Bulletin Officiel (PDF)    | --> | PyMuPDF -> PNG            |
| Sites gouvernementaux      |     | EasyOCR -> Texte brut     |
| Recueils juridiques prives |     | VLM -> Correction         |
| Textes numerises (scans)   |     |                           |
|                            |     |                           |
+----------------------------+     +---------------------------+
```

### Types de documents sources

| Type             | Format          | Traitement              |
|------------------|-----------------|--------------------------|
| PDF scanne       | Image brute     | OCR EasyOCR + VLM        |
| PDF texte        | Texte integre   | Extraction PyMuPDF directe |
| Documents web    | HTML            | Parsing + nettoyage      |
| Textes structures| TXT/JSON        | Import direct             |

## 5.2 Processus d'Extraction

### Pipeline complet

```
+--------+     +----------+     +----------+     +-----------+     +----------+
|  PDF   | --> | PyMuPDF  | --> |  Images  | --> |  EasyOCR  | --> |  TEXTE   |
| SCANNE |     | (render) |     |  (PNG)   |     | (arabe)   |     |  BRUT    |
+--------+     +----------+     +----------+     +-----------+     +----------+
                                                                        |
                                                                        v
+--------+     +----------+     +----------+     +-----------+     +----------+
|  JSON  | <-- | Structure| <-- |  TEXTE   | <-- |  VLM       | <-- |  TEXTE   |
| FINAL  |     | Parser   |     |  NETTOYE |     |  Gemma 4   |     |  BRUT    |
+--------+     +----------+     +----------+     +-----------+     +----------+
```

### Etapes detaillees

| Etape             | Outil              | Description                                    |
|-------------------|--------------------|------------------------------------------------|
| 1. Rendu PDF      | PyMuPDF (fitz)     | Conversion PDF -> images PNG par page          |
| 2. OCR            | EasyOCR            | Reconnaissance de texte arabe sur les images   |
| 3. Correction      | Gemma 4 (VLM)      | Correction des erreurs OCR par modele de vision |
| 4. Nettoyage       | LegalTextCleaner   | Suppression des artefacts, retours a la ligne  |
| 5. Normalisation   | ArabicNormalizer   | Normalisation de l'orthographe arabe           |
| 6. Structuration   | StructureParser    | Extraction des numeros d'article, chapitres    |
| 7. Export          | JSON schema        | Format structure avec metadonnees              |

### Prompt VLM de correction

```
Tu es un correcteur de texte juridique marocain en arabe.
Corrige UNIQUEMENT les erreurs de reconnaissance optique.
NE TRADUIS PAS.
NE RESUMES PAS.
Texte original :
{texte_brut}
Texte corrige :
```

## 5.3 Structure du Corpus Final

```
+------------------------------------------------------------------+
|                     STRUCTURE DU CORPUS                           |
+------------------------------------------------------------------+
|                                                                  |
|  corpus/                                                         |
|  |-- penal/                                                      |
|  |   |-- code-penal-maroc-ar.articles.json   (513 articles)      |
|  |   |-- sanction-code-penal-marocain-ar.articles.json (29 arts)|
|  |                                                               |
|  |-- circulation/                                                |
|  |   |-- code-de-la-route-marocain-ar.articles.json (228 arts)  |
|  |                                                               |
|  |-- civil/                                                      |
|  |   |-- code-civil-marocain-ar.articles.json     (494 arts)    |
|  |   |-- code-general-impots-2024.articles.json   (211 arts)    |
|  |                                                               |
|  |-- commercial/                                                 |
|  |   |-- registre-commerce.articles.json           (317 arts)    |
|  |   |-- loi-societes.articles.json                (42 arts)    |
|  |                                                               |
|  |-- judiciaire/                                                 |
|  |   |-- organisation-judiciaire-38-15.articles.json (32 arts)  |
|  |                                                               |
|  |-- fiscal/                                                     |
|  |   |-- code-general-impots-2024.articles.json    (211 arts)   |
|  |                                                               |
+------------------------------------------------------------------+
```

### Format d'un article (JSON)

```json
{
  "article_number": "513",
  "law_name": "code penal maroc ar",
  "domain": "criminal",
  "chapter_title": "حماية الاحداث",
  "section_title": "التدابير الوقائية",
  "text": "يعتبر الحدث البالغ من العمر اقل من 16 سنة...",
  "source_file": "code-penal-maroc-ar.pdf",
  "page_number": 145
}
```

## 5.4 Metadonnees Associees

| Champ           | Description                                      |
|------------------|--------------------------------------------------|
| article_number   | Numero officiel de l'article                     |
| law_name         | Nom normalise de la loi source                   |
| domain           | Domaine juridique (criminal, civil, ...)         |
| chapter_title    | Titre du chapitre (si disponible)                |
| section_title    | Titre de la section (si disponible)              |
| source_file      | Fichier PDF d'origine                            |
| page_number      | Page dans le document source                     |

## 5.5 Statistiques du Corpus

| Domaine                    | Articles | Taille approx. |
|----------------------------|----------|-----------------|
| Droit Penal                | 822      | ~1.2 Mo         |
| Circulation                | 228      | ~350 Ko         |
| Droit Civil                | 705      | ~1.0 Mo         |
| Droit Commercial           | 359      | ~550 Ko         |
| Organisation Judiciaire    | 32       | ~80 Ko          |
| Droit Fiscal               | 211      | ~400 Ko         |
| **Total**                  | **~2357**| **~3.6 Mo**     |
