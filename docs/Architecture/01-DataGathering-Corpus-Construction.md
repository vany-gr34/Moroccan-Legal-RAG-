# Phase 1 — Data Gathering and Corpus Construction

## 1. Introduction

The first phase of the project focuses on building a structured Arabic legal corpus for the Moroccan legal assistant system. This phase is considered the foundation of the entire NLP and RAG pipeline because the quality of the generated responses depends directly on the quality of the collected legal data.

The objective is to gather legal documents related to Moroccan law from multiple sources, transform them into machine-readable Arabic text, and organize them into a reusable and searchable dataset.

The corpus will support several legal domains including:

- Moroccan Traffic Law
- Criminal Law
- Family Law
- Civil and Commercial Law
- Court Procedures
- Violations and Penalties

---

# 2. Objectives of the Data Gathering Phase

The main goals of this phase are:

- Collect legal documents from different formats
- Extract Arabic text from documents
- Normalize and clean extracted text
- Organize the legal corpus into structured datasets
- Attach metadata for future retrieval and classification
- Prepare data for NLP preprocessing and vectorization

---

# 3. Data Sources

The system accepts multiple document formats in order to maximize compatibility with Moroccan legal resources.

## Supported Sources

| Source Type | Description |
|---|---|
| PDF Documents | Official legal texts and scanned laws |
| Images | Scanned legal pages and screenshots |
| DOCX Files | Editable legal documents |
| Web Sources | Government legal publications |
| Simulated Cases | Artificially generated legal examples |

---

# 4. Data Gathering Architecture

```mermaid
flowchart TD

A[Legal Documents] --> B[PDF Files]
A --> C[Images]
A --> D[DOCX Files]

B --> E[PDF Text Extraction]
C --> F[OCR Processing]
D --> G[Document Parser]

E --> H[Raw Arabic Text]
F --> H
G --> H

H --> I[Text Cleaning]
I --> J[Normalization]
J --> K[Metadata Extraction]

K --> L[Structured JSON Dataset]
K --> M[CSV Dataset]
````

---

# 5. OCR and Text Extraction

Many Moroccan legal documents are available only as scanned PDFs or images. Therefore, Optical Character Recognition (OCR) is an essential component of the system.

## OCR Objectives

* Convert scanned Arabic legal documents into text
* Preserve article structure and numbering
* Minimize Arabic recognition errors
* Support multi-format ingestion

## Candidate OCR Technologies

| Tool              | Purpose                   |
| ----------------- | ------------------------- |
| Tesseract OCR     | Open-source OCR engine    |
| EasyOCR           | Deep-learning OCR         |
| PaddleOCR         | Advanced multilingual OCR |
| Google Vision OCR | High-accuracy cloud OCR   |

---

# 6. Arabic Text Cleaning

The extracted Arabic text may contain OCR noise, encoding issues, duplicated symbols, or inconsistent formatting.

The preprocessing stage aims to standardize the legal corpus before storage.

## Cleaning Operations

* Remove unnecessary spaces
* Remove OCR artifacts
* Normalize Arabic characters
* Remove repeated symbols
* Preserve legal article numbering
* Detect corrupted text segments

---

# 7. Arabic Normalization

Arabic normalization is necessary for semantic consistency during retrieval.

## Examples

| Original  | Normalized   |
| --------- | ------------ |
| أ / إ / آ | ا            |
| ـــــ     | removed      |
| ة         | standardized |
| ي / ى     | unified      |

---

# 8. Metadata Construction

Each legal entry must include metadata to improve filtering and semantic retrieval.

## Metadata Fields

| Field          | Description             |
| -------------- | ----------------------- |
| id             | Unique identifier       |
| title          | Legal topic             |
| law_type       | Domain category         |
| source         | Original document       |
| language       | Arabic / French         |
| article_number | Legal article reference |
| date           | Publication date        |
| tags           | Legal keywords          |

---

# 9. Dataset Structure

The legal corpus will be stored in structured JSON format.

## Example Structure

```json
{
  "id": "LAW_001",
  "title": "تجاوز السرعة",
  "law_type": "قانون السير",
  "legal_text": "يعاقب القانون المغربي...",
  "simple_explanation": "تجاوز السرعة يعتبر مخالفة...",
  "example_case": "قام السائق بتجاوز السرعة...",
  "source": "مدونة السير المغربية"
}
```

---

# 10. Data Storage Strategy

The collected legal data will be stored in two formats:

## JSON Storage

Used for:

* NLP pipelines
* embeddings
* semantic retrieval
* vector databases

## CSV Storage

Used for:

* manual review
* dataset inspection
* annotation tasks
* evaluation

---

# 11. Modular Ingestion Pipeline

The ingestion system is designed as a reusable pipeline.

```mermaid
flowchart LR

A[Upload Document]
--> B[Document Type Detection]
--> C[OCR or Parsing]
--> D[Arabic Cleaning]
--> E[Normalization]
--> F[Metadata Extraction]
--> G[Structured Storage]
```

---

# 12. Challenges of Arabic Legal Data

The project faces several challenges related to Arabic legal NLP.

## Main Challenges

* OCR errors in Arabic scans
* Complex legal terminology
* Long legal articles
* Mixed Arabic and French text
* Inconsistent formatting
* Lack of open Moroccan legal datasets

---

# 13. Expected Output of Phase 1

At the end of this phase, the system should produce:

* Structured Arabic legal corpus
* Cleaned legal documents
* Metadata-enriched datasets
* Reusable ingestion pipeline
* JSON and CSV exports
* OCR processing workflow

---

# 14. Conclusion

The data gathering phase is the most critical stage of the Moroccan Legal RAG system. A well-structured Arabic legal corpus improves semantic retrieval, reduces hallucinations, and increases the reliability of generated legal answers.

This phase establishes the foundation for later stages including NLP preprocessing, vector embeddings, retrieval systems, reranking, and LLM-based legal response generation.
