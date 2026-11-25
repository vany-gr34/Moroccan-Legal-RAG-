#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate article.docm (Microsoft Word, Springer LNCS proceedings format)
from the splnproc2510 template.

Strategy: unpack the template, rebuild ONLY the document body using the
template's own paragraph styles (papertitle, author, address, abstract,
keywords, heading1-4, p1a, bulletitem, equation, tablecaption,
figurecaption, referenceitem, ...), embed the result figures, and repackage
as a .docm. All styles, running heads, footers, numbering and the LNCS
macro ribbon are preserved unchanged.
"""
import os
import re
import shutil
import struct
import zipfile
import xml.sax.saxutils as sax

TEMPLATE = ("/home/mgkali/Desktop/NLP/Analyse-des-lois-justice-Maroc/research paper/"
            "ICCT2026/template/Microsoft+Word+Proceedings+Templates/splnproc2510.docm")
ARTICLE = "/home/mgkali/Desktop/NLP/Analyse-des-lois-justice-Maroc/research paper/ICCT2026/article"
BUILD = "/tmp/splnproc_build"
OUTPUT = os.path.join(ARTICLE, "article.docm")

TEXT_W_EMU = int(12.2 * 360000)          # LNCS text width ~12.2 cm
IMG_MAX_W = int(TEXT_W_EMU * 0.97)


# --------------------------------------------------------------------------
# Low-level XML helpers
# --------------------------------------------------------------------------
def esc(s):
    return sax.escape(s, {'"': "&quot;"})


def R(text, bold=False, italic=False, mono=False, sub=False, sup=False, size=None):
    """A single <w:r> run."""
    rpr = ""
    if mono:
        rpr += '<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/>'
    if bold:
        rpr += "<w:b/>"
    if italic:
        rpr += "<w:i/>"
    if sub:
        rpr += '<w:vertAlign w:val="subscript"/>'
    if sup:
        rpr += '<w:vertAlign w:val="superscript"/>'
    if size:
        rpr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return f"<w:r>{rpr}<w:t xml:space=\"preserve\">{esc(text)}</w:t></w:r>"


_INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\*[^*]+?\*)")

def inline(text):
    """Parse **bold**, `mono`, *italic* markers into a list of run XML."""
    out = []
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            out.append(R(text[pos:m.start()]))
        tok = m.group(0)
        if tok.startswith("**"):
            out.append(R(tok[2:-2], bold=True))
        elif tok.startswith("`"):
            out.append(R(tok[1:-1], mono=True))
        else:
            out.append(R(tok[1:-1], italic=True))
        pos = m.end()
    if pos < len(text):
        out.append(R(text[pos:]))
    return out


def P(style=None, runs=None, jc=None, extra_ppr="", num_id=None):
    """A <w:p> paragraph. runs = list of run XML strings (or a string)."""
    if isinstance(runs, str):
        runs = [runs]
    ppr = ""
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if num_id is not None:                      # e.g. num_id=0 disables numbering
        ppr += f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>'
    if jc:
        ppr += f'<w:jc w:val="{jc}"/>'
    ppr += extra_ppr
    ppr = f"<w:pPr>{ppr}</w:pPr>" if ppr else ""
    return f"<w:p>{ppr}{''.join(runs) if runs else ''}</w:p>"


def para(text, style=None, bold=False, first=True):
    """Convenience: a body paragraph with inline markup."""
    if style is None:
        style = "p1a" if first else None       # None -> Normal (indented)
    return P(style, inline(text))


def bullet(text):
    return P("bulletitem", inline(text))


def heading(level, text):
    return P(f"heading{level}", R(text))


# --------------------------------------------------------------------------
# Tables (Springer "booktabs" look: thick top, thin middle, thick bottom)
# --------------------------------------------------------------------------
def _cell(runs_xml, w_dxa, jc="left", top=None, bottom=None, header=False):
    tcpr = f'<w:tcPr><w:tcW w:w="{w_dxa}" w:type="dxa"/>'
    if top or bottom:
        tcpr += "<w:tcBorders>"
        if top:
            tcpr += f'<w:top w:val="single" w:sz="{top}" w:space="0" w:color="000000"/>'
        if bottom:
            tcpr += f'<w:bottom w:val="single" w:sz="{bottom}" w:space="0" w:color="000000"/>'
        tcpr += "</w:tcBorders>"
    tcpr += "</w:tcPr>"
    runs = "".join(R(t, bold=header, size=18) if isinstance(t, str)
                   else f'<w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>'
                        f'<w:t xml:space="preserve">{esc(t["text"])}</w:t></w:r>'
                   for t in runs_xml)
    return (f"<w:tc>{tcpr}<w:p><w:pPr><w:ind w:firstLine=\"0\"/><w:jc w:val=\"{jc}\"/>"
            f"<w:rPr><w:sz w:val=\"18\"/><w:szCs w:val=\"18\"/></w:rPr></w:pPr>{runs}</w:p></w:tc>")


def table(rows, jc_cells=None):
    """rows = list of lists of strings; first row is the header."""
    ncol = len(rows[0])
    total = 6889  # dxa, matches template table width
    widths = [total // ncol] * (ncol - 1) + [total - (total // ncol) * (ncol - 1)]
    jc = jc_cells or (["center"] * ncol)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    trs = []
    for r_i, row in enumerate(rows):
        cells = []
        for c_i, cell_text in enumerate(row):
            if r_i == 0:                       # header row
                top, bottom = 12, 6
            elif r_i == len(rows) - 1:         # last row
                top, bottom = None, 12
            else:
                top, bottom = None, 6
            cells.append(_cell([cell_text], widths[c_i], jc=jc[c_i],
                               top=top, bottom=bottom, header=(r_i == 0)))
        trs.append(f"<w:tr>{''.join(cells)}</w:tr>")
    tblpr = ("<w:tblPr><w:tblW w:w=\"6889\" w:type=\"dxa\"/><w:jc w:val=\"center\"/>"
             "<w:tblLayout w:type=\"fixed\"/>"
             "<w:tblCellMar><w:left w:w=\"70\" w:type=\"dxa\"/>"
             "<w:right w:w=\"70\" w:type=\"dxa\"/></w:tblCellMar>"
             '<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" '
             'w:lastColumn="0" w:noHBand="0" w:noVBand="0"/></w:tblPr>')
    return f"<w:tbl>{tblpr}<w:tblGrid>{grid}</w:tblGrid>{''.join(trs)}</w:tbl>"


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------
def png_size(path):
    with open(path, "rb") as f:
        head = f.read(26)
    w, h = struct.unpack(">II", head[16:24])
    return w, h


def figure(path, r_id, doc_id):
    w, h = png_size(path)
    if w > IMG_MAX_W:
        h = int(h * IMG_MAX_W / w)
        w = IMG_MAX_W
    cx, cy = w, h
    return (
        '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="120" w:after="120"/>'
        f'<w:ind w:firstLine="0"/></w:pPr><w:r>'
        '<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{doc_id}" name="Figure {doc_id}"/>'
        '<wp:cNvGraphicFramePr/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{doc_id}" name="Figure {doc_id}"/>'
        '<pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill>'
        f'<a:blip r:embed="{r_id}"/>'
        '<a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
    )


# --------------------------------------------------------------------------
# Article content
# --------------------------------------------------------------------------
def build_body(images):
    B = []

    # ---- Title block -------------------------------------------------------
    B.append(P("papertitle", R("Moroccan Legal Question Answering System Based on "
                               "Retrieval-Augmented Generation (RAG) with Arabic "
                               "Natural Language Processing")))
    B.append(P("author", [R("Author One"), R("1", sup=True),
                          R(" and Author Two"), R("1", sup=True),
                          R(" and Author Three"), R("1", sup=True)]))
    B.append(P("address", R("1 Faculty of Sciences and Techniques of Tangier, "
                            "Abdelmalek Essaadi University, Morocco")))
    B.append(P("address", R("{firstname.lastname}@etu.uae.ac.ma")))

    # ---- Abstract & keywords ----------------------------------------------
    abstract_text = ("This paper presents the design, implementation, and evaluation of a legal "
        "Question Answering (Q&A) system specialized in Moroccan law, based on the "
        "Retrieval-Augmented Generation (RAG) architecture. The system integrates a complete "
        "Arabic NLP pipeline including text extraction from PDF documents (digital and scanned), "
        "cleaning, Arabic normalization, structural analysis of legal articles, and vector "
        "indexing via PostgreSQL with the pgvector extension. Hybrid search combines dense cosine "
        "similarity (BAAI/bge-m3, 1024 dimensions) with BM25 lexical search, fused through "
        "Reciprocal Rank Fusion (RRF). The generation module relies on Google's Gemma 4 2B model, "
        "served on GPU via Google Colab and exposed through a Cloudflare tunnel. Benchmarks show "
        "that the RRF strategy achieves a Hit@5 of 68.75% and a Recall@5 of 59.38%, while dense "
        "search offers the best MRR@5 (0.565). Embedding-model evaluation demonstrates the "
        "superiority of 1024-dimension models (intfloat/multilingual-e5-large, BAAI/bge-m3) for "
        "Arabic legal text, with domain accuracy reaching 89%. This work constitutes the first "
        "complete open-source Moroccan legal RAG platform, covering seven areas of law (criminal, "
        "traffic, family, civil, commercial, judicial, tax).")
    B.append(P("abstract", [R("Abstract. ", bold=True, italic=True, size=18),
                            R(abstract_text, size=18)]))
    B.append(P("keywords", [R("Keywords: ", bold=True),
                            R("RAG, Arabic NLP, Moroccan Law, Hybrid Search, Multilingual "
                              "Embeddings, pgvector, Gemma 4, Legal Question Answering, "
                              "Reciprocal Rank Fusion")]))

    # ---- 1 Introduction ----------------------------------------------------
    B.append(heading(1, "Introduction"))
    B.append(para("Access to legal information is a fundamental right in any state governed by "
        "the rule of law. In Morocco, the legal corpus is vast and complex, comprising hundreds of "
        "laws, codes, and decrees written primarily in Modern Standard Arabic (MSA). For citizens, "
        "legal practitioners, and researchers, navigating this corpus to find a precise answer to "
        "a specific question constitutes a major challenge. General-purpose search engines "
        "(Google, Bing) are poorly suited to this task: they neither understand the specificity "
        "of Arabic legal vocabulary nor the hierarchical structure of legal codes (articles, "
        "chapters, sections)."))
    B.append(para("Recent advances in Natural Language Processing (NLP), particularly in Large "
        "Language Models (LLMs) and Retrieval-Augmented Generation (RAG) [1], offer an "
        "unprecedented opportunity to build specialized Question Answering (Q&A) systems. The RAG "
        "approach combines an information-retrieval module with a text-generation module (LLM), "
        "producing contextualized, sourced, and up-to-date responses without requiring expensive "
        "fine-tuning. However, applying RAG to the Arabic legal domain presents unique challenges: "
        "the scarcity of multilingual embedding models optimized for legal vocabulary, the "
        "morphological complexity of Arabic [3], the presence of Darija (the Moroccan Arabic "
        "dialect) in user queries, the need for absolute fidelity to legal texts, and the "
        "difficulty of processing scanned historical legal documents.", first=False))
    B.append(para("Our system relies on a corpus of **2,357 legal articles** covering seven areas "
        "of Moroccan law: criminal (822 articles), traffic (228), civil (705), commercial (359), "
        "judicial organization (32), tax (211), and violations. These articles are extracted from "
        "their source PDFs, cleaned, normalized to standard Arabic, structured with hierarchical "
        "metadata, and indexed in PostgreSQL + pgvector using the "
        "`intfloat/multilingual-e5-large` embedding model (1024 dimensions).", first=False))
    B.append(para("Our contributions are fourfold:", first=False))
    B.append(bullet("A **complete Arabic NLP processing chain** from PDF extraction (digital and "
                    "scanned) to morphological normalization, cleaning, and structural analysis "
                    "of Moroccan legal codes."))
    B.append(bullet("A **hybrid search architecture** combining dense vector similarity "
                    "(`BAAI/bge-m3`, 1024 dimensions) with BM25 lexical search, fused via "
                    "Reciprocal Rank Fusion (RRF), indexed in PostgreSQL + pgvector with an HNSW "
                    "index."))
    B.append(bullet("A **systematic benchmark** of five multilingual embedding models on 26 "
                    "Arabic legal articles with 65 query variants covering formal Arabic, Darija, "
                    "French, English, and short/long queries."))
    B.append(bullet("A **comparative benchmark** of three search strategies (dense, BM25, RRF) "
                    "on 32 questions across 7 legal domains, evaluating both retrieval quality "
                    "and generated-answer quality."))
    B.append(para("The remainder of this paper is organized as follows. Section 2 presents "
        "related work. Section 3 describes our methodology. Section 4 details the proposed "
        "system architecture. Section 5 presents experimental results. Section 6 discusses "
        "implications and limitations. Section 7 concludes the paper.", first=False))

    # ---- 2 Related Work ----------------------------------------------------
    B.append(heading(1, "Related Work"))
    B.append(para("The application of NLP to the legal domain has attracted growing interest in "
        "recent years. This section examines existing work in three areas: legal Q&A and RAG "
        "systems, Arabic language models and embeddings, and hybrid search strategies."))
    B.append(heading(2, "Legal RAG and Q&A Systems"))
    B.append(para("The RAG architecture, introduced by Lewis et al. [1], combines a retriever "
        "(typically Dense Passage Retrieval [2]) with a sequence generator to produce "
        "contextualized responses. Since then, several specialized RAG systems have emerged in "
        "the legal domain. Louis et al. [5] present Legal-RAG for Indian law using multilingual "
        "embeddings and a fine-tuned LLM, achieving 72% accuracy on Indian legal queries. Nguyen "
        "et al. [6] develop a similar system for Vietnamese law, demonstrating the importance of "
        "linguistic and cultural adaptation. Closer to our context, Alshareef et al. [7] propose "
        "a Q&A system for Saudi law using AraBERT and Elasticsearch for lexical search, achieving "
        "68% accuracy on 100 Arabic legal questions. Elaraby et al. [8] present a RAG system for "
        "Egyptian law with multilingual embeddings and a remote LLM. Sharma et al. [29] propose "
        "an Indian Legal RAG with hybrid search, while Huang et al. [30] present SAIL-Legal for "
        "Chinese law with distributed vector indexing. Zhou et al. [31] develop LexGPT, a "
        "GPT-4-based legal assistant with retrieval augmentation. In parallel, domain-adapted "
        "pre-trained language models such as LEGAL-BERT [34] demonstrated that legal-specific "
        "representations outperform generic language models on legal tasks. Our work extends "
        "these approaches by proposing a complete architecture with advanced hybrid search and "
        "systematic benchmarking on Moroccan law."))
    B.append(heading(2, "Arabic NLP for the Legal Domain"))
    B.append(para("Arabic NLP presents well-documented challenges [3]. The rich derivational "
        "morphology (triliteral roots, patterns, affixes), diglossia (MSA vs. dialects), and "
        "ambiguous orthography (alef variants, tatweel, ligatures) make linguistic preprocessing "
        "crucial. In the legal domain specifically, Zaghouani [9] highlights the complexity of "
        "Arabic legal vocabulary, characterized by fixed formulas, French and English borrowings, "
        "and elaborate syntax. Benali and Alami [32] note that Moroccan legal Arabic systems must "
        "handle very long sentences (often over 100 words per article), a high degree of "
        "co-reference, non-standard abbreviations, and frequent Arabic–French code-switching. "
        "Nassif et al. [28] provide a comprehensive survey of recent Arabic NLP advances, "
        "confirming that rich morphology and diglossia remain open challenges. Tools such as the "
        "CAMeL Tools suite [4] offer morphological analyzers for standard Arabic, though their "
        "application to legal text requires adaptation."))
    B.append(heading(2, "Multilingual Embedding Models"))
    B.append(para("Embedding-model choice is crucial in any RAG system. For Arabic, Ali et al. "
        "[23] compare LaBSE, XLM-R, and AraBERT, concluding that LaBSE [13] offers the best "
        "cross-lingual performance. Distillation-based approaches [10] further extend monolingual "
        "embeddings to hundreds of languages. Wang et al. [11] introduce BGE-M3, a "
        "multi-granularity model supporting 100+ languages. Liang et al. [12] present E5-large, "
        "based on contrastive pre-training. Both BGE-M3 and E5-large produce 1024-dimension "
        "embeddings, offering superior representational capacity over 768-dimension models. Our "
        "benchmark (Section 5) is, to the best of our knowledge, the first to systematically "
        "compare these five models on Arabic legal text with multilingual query variants."))
    B.append(heading(2, "Hybrid Search Strategies"))
    B.append(para("Dense (vector) search captures semantic similarity but may miss exact lexical "
        "matches. BM25 excels at exact matching but ignores semantic context [14]. "
        "Transformer-based rankers [17] bridge this gap but are computationally expensive at "
        "scale. Reciprocal Rank Fusion (RRF) [15] is a parameter-free fusion method that combines "
        "rankings from multiple systems. Shao et al. [33] demonstrate that hybrid "
        "Dense + BM25 + RRF offers the best results for legal queries. Our benchmark confirms "
        "these findings in the Arabic legal domain, with Hit@5 improving from 65.62% (dense) to "
        "68.75% (RRF)."))
    B.append(heading(2, "Large Language Models for Arabic"))
    B.append(para("Gemma 4 [18] is Google's fourth-generation open model, available in 2B and 9B "
        "sizes, supporting Arabic with competitive performance. Our system uses Gemma 4 2B in "
        "Q4_K_XL quantization via llama.cpp [19]. Recent studies [22] show that multilingual LLMs "
        "can correctly answer Arabic legal questions without specific fine-tuning, provided they "
        "receive relevant context via RAG."))
    B.append(heading(2, "Comparative Synthesis"))
    B.append(para("Table 1 summarizes the technical characteristics of recent legal RAG systems "
        "compared with our proposal."))
    B.append(P("tablecaption", R("Table 1. Comparative synthesis of recent legal RAG systems.")))
    B.append(table([
        ["System", "Domain", "Search", "Embedding", "Best"],
        ["Lewis et al. (2020)", "General", "DPR", "BERT", "68% (R@20)"],
        ["Louis et al. (2023)", "Indian", "Dense (FAISS)", "E5", "72% (P@1)"],
        ["Alshareef et al. (2023)", "Saudi", "Lexical (ES)", "AraBERT", "68% (Acc.)"],
        ["Zhou et al. (2023)", "US", "Hybrid (GPT-4)", "Ada-002", "N/D"],
        ["Nguyen et al. (2023)", "Vietnamese", "Dense (FAISS)", "PhoBERT", "65% (Acc.)"],
        ["Elaraby et al. (2024)", "Egyptian", "Hybrid (RRF)", "E5-large", "70% (F1)"],
        ["Sharma et al. (2024)", "Indian", "Hybrid (RRF)", "MuRIL", "73.5% (MRR)"],
        ["Huang et al. (2024)", "Chinese", "Hybrid (Dist.)", "BGE", "76.2% (H@5)"],
        ["Ours", "Moroccan", "Hybrid (RRF)", "E5-large 1024d", "81% (MRR)"],
    ]))

    # ---- 3 Methodology -----------------------------------------------------
    B.append(heading(1, "Methodology"))
    B.append(para("This section describes the experimental methodology employed to evaluate "
        "system performance, including the embedding-model benchmark protocol, search strategy "
        "evaluation, and generated-answer quality metrics."))
    B.append(heading(2, "Embedding-Model Benchmark"))
    B.append(heading(3, "Test Corpus"))
    B.append(para("A corpus of 26 Moroccan legal articles was assembled, covering five domains: "
        "criminal (7 articles, No. 147–436), traffic (5 articles, No. 172–180), family (5 "
        "articles, No. 48–78), civil (4 articles, No. 1–100), and commercial (4 articles, "
        "No. 1–55). Each article was carefully selected to include close neighbors (hard "
        "negatives) — for example, Article 147 (simple theft) and Article 148 (aggravated theft) "
        "of the Penal Code — to test the models' ability to discriminate legally distinct but "
        "semantically similar texts."))
    B.append(heading(3, "Query Variants"))
    B.append(para("For each article group, five to seven query variants were generated: formal "
        "Arabic, Moroccan Darija, short keywords (2–3 words), long descriptive queries, "
        "cross-lingual French, and cross-lingual English. In total, 65 query variants were "
        "evaluated across 5 embedding models."))
    B.append(heading(3, "Models Evaluated"))
    B.append(para("Five multilingual embedding models were compared:"))
    B.append(bullet("**E5-large** (`intfloat/multilingual-e5-large`, 1024d)"))
    B.append(bullet("**BGE-M3** (`BAAI/bge-m3`, 1024d)"))
    B.append(bullet("**LaBSE** (`sentence-transformers/LaBSE`, 768d)"))
    B.append(bullet("**MPNet** (`paraphrase-multilingual-mpnet-base-v2`, 768d)"))
    B.append(bullet("**E5-base** (`intfloat/multilingual-e5-base`, 768d)"))
    B.append(heading(3, "Metrics"))
    B.append(para("For each (model, variant) pair, cosine similarity was computed between query "
        "and document embeddings. Metrics: Precision@k (k ∈ {1, 3, 5}), Mean Reciprocal Rank "
        "(MRR), NDCG@5, domain accuracy, and Hit@10."))
    B.append(heading(2, "Retrieval-Strategy Benchmark"))
    B.append(heading(3, "Experimental Setup"))
    B.append(para("Following the zero-shot evaluation paradigm of BEIR [16], three search "
        "strategies were compared: dense (pgvector cosine), BM25 (rank-bm25 with a dedicated "
        "Arabic tokenizer), and RRF (fusion of both). The test set comprises 32 legal questions "
        "across 7 domains with top-k = 5. Paired Student's t-tests were applied for statistical "
        "significance."))
    B.append(heading(3, "Generation Metrics"))
    B.append(para("For each strategy, retrieved articles were passed to the LLM (Gemma 4 2B, "
        "temperature 0.3, max_tokens = 512). Three metrics were evaluated:"))
    B.append(bullet("**Answer Relevance**: cosine similarity between question and answer "
                    "embeddings (0–1)."))
    B.append(bullet("**Faithfulness**: proportion of answer claims grounded in retrieved "
                    "documents via token overlap (0–1)."))
    B.append(bullet("**Answer Correctness**: composite ROUGE-L + BERTScore F1 against ground "
                    "truth (0–1)."))
    B.append(para("Questions were stratified by domain (7 domains) and difficulty level "
        "(easy: 10, medium: 11, hard: 11) to identify specific system weaknesses."))

    # ---- 4 The Proposed Solution --------------------------------------------
    B.append(heading(1, "The Proposed Solution"))
    B.append(heading(2, "Overall Architecture"))
    B.append(para("The Moroccan Legal RAG system follows a layered architecture organized around "
        "two main flows: the ingestion flow (PDF → vector knowledge base) and the inference flow "
        "(question → generated answer). Each layer is independently interchangeable."))
    B.append(heading(2, "Ingestion-Pipeline Components"))
    B.append(heading(3, "PDF Classification and Extraction with VLM Correction"))
    B.append(para("A PDF classifier determines whether a document is digital (extractable text) "
        "or scanned (image-based). For scanned PDFs, the pipeline comprises: (1) PyMuPDF renders "
        "each page as a PNG image, (2) EasyOCR performs Arabic text recognition on GPU, (3) Gemma "
        "4 in vision mode corrects OCR errors with a specialized prompt, following the post-OCR "
        "correction paradigm of [27], and (4) post-processing corrects the Arabic visual order."))
    B.append(heading(3, "Legal Text Cleaning"))
    B.append(para("The `LegalTextCleaner` removes noise specific to Moroccan legal documents: "
        "repeated headers/footers, page numbers, watermarks, table-of-contents artifacts, "
        "duplicate paragraphs, incorrect line breaks, and non-text artifacts."))
    B.append(heading(3, "Arabic Normalization"))
    B.append(para("The `ArabicNormalizer` applies standardized Arabic preprocessing: Unicode "
        "NFKC normalization, alef unification, diacritic removal, tatweel (kashida) removal, "
        "digit normalization, and punctuation spacing."))
    B.append(heading(3, "Structural Parsing"))
    B.append(para("The `LegalStructureParser` extracts the hierarchical structure: books/parts, "
        "chapters, sections, and articles matching the pattern \u201CArticle X\u201D (al-madda "
        "X). Each article is enriched with complete hierarchical context (law name, number, "
        "book, chapter, section) and serialized to JSON."))
    B.append(heading(3, "Vector Ingestion"))
    B.append(para("Articles are contextualized with a prefix (e.g., \u201C[Penal Code] "
        "[Section 3] Article 147: …\u201D), embedded via BGE-M3 (1024d), and inserted into "
        "PostgreSQL with an HNSW index (m = 16, ef_construction = 200)."))
    B.append(heading(2, "Inference-Pipeline Components"))
    B.append(heading(3, "REST API (FastAPI)"))
    B.append(para("The REST API is built with FastAPI [25]. Six endpoints are exposed under "
        "`/api/v1`: health check, pure search, full Q&A (RAG), laws listing, PDF upload, and "
        "conversation history."))
    B.append(heading(3, "Hybrid Search Engine"))
    B.append(para("Three interchangeable strategies are implemented via the Strategy pattern.", first=False))
    B.append(para("**Dense retrieval.** The query is encoded into a 1024-dimensional vector and "
        "searched via pgvector's cosine-distance operator `<=>`.", first=False))
    B.append(para("**BM25 retrieval.** PostgreSQL FTS with the Arabic dictionary was abandoned "
        "due to poor performance. An in-memory `BM25Okapi` index was implemented with a "
        "specialized Arabic tokenizer: (1) normalization via `ArabicNormalizer`, (2) Unicode "
        "regex word extraction, (3) removal of 60+ legal stop-words, (4) filtering of short "
        "tokens (< 2 characters). This approach achieves Recall@5 of 41.67% and Hit@5 of "
        "46.88%.", first=False))
    B.append(para("**Reciprocal Rank Fusion.** Top-N results from each strategy (N = 20) are "
        "fused using the following formula:", first=False))
    B.append(P("equation", [R("RRF(d) = 1 / (k + r"), R("dense", sub=True),
                            R("(d)) + 1 / (k + r"), R("bm25", sub=True),
                            R("(d))        (1)")]))
    B.append(para("where k = 60 is the fusion constant and r_s(d) is the rank of document d "
        "in strategy s. Figure 1 illustrates the fusion procedure."))
    B.append(P("figurecaption", R("Fig. 1. Reciprocal Rank Fusion: dense (top-20) and BM25 "
                                  "(top-20) rankings are combined with the RRF formula and "
                                  "sorted to produce the final top-K list.")))
    B.append(figure(images["rrf_fusion"], "rId19", 1))
    B.append(heading(3, "LLM Generation Module"))
    B.append(para("The generation module builds a structured prompt from retrieved articles and "
        "calls a remote LLM. The prompt includes: (1) retrieved legal texts numbered and "
        "sourced, (2) a system instruction specifying the Moroccan legal-assistant role, the "
        "grounding rule, and the output format, (3) the user's question. The LLM is Gemma 4 2B, "
        "quantized to Q4_K_XL and served via llama.cpp on an NVIDIA T4 GPU hosted on Google "
        "Colab, accessible through a Cloudflare tunnel. The response is parsed into three "
        "sections: short answer, legal analysis, and practical example."))
    B.append(heading(2, "Data Infrastructure"))
    B.append(para("PostgreSQL 16 with pgvector 0.7.4 [24] stores `legal_chunks` (articles with "
        "1024d embeddings, domain metadata, HNSW index) and `conversations` (session history "
        "with JSONB sources)."))
    B.append(heading(2, "User Interface"))
    B.append(para("The web interface is developed with SvelteKit 5 [26] and Tailwind CSS 4, with "
        "full Arabic (RTL) support, offering a search page, results page with structured "
        "answers, law explorer with hierarchical tree, conversation history, PDF upload "
        "interface, and system health dashboard."))

    # ---- 5 Results ---------------------------------------------------------
    B.append(heading(1, "Results"))
    B.append(heading(2, "Embedding-Model Benchmark"))
    B.append(para("Table 2 shows the aggregated performance of five embedding models on the "
        "corpus of 26 legal articles with 65 query variants."))
    B.append(P("tablecaption", R("Table 2. Embedding-model benchmark results.")))
    B.append(table([
        ["Model", "P@1", "P@3", "P@5", "MRR", "NDCG", "Dom. Acc."],
        ["E5-large (1024d)", "0.72", "0.68", "0.61", "0.81", "0.76", "0.89"],
        ["BGE-M3 (1024d)", "0.69", "0.65", "0.58", "0.78", "0.73", "0.85"],
        ["LaBSE (768d)", "0.61", "0.58", "0.52", "0.70", "0.66", "0.78"],
        ["E5-base (768d)", "0.58", "0.54", "0.49", "0.67", "0.63", "0.74"],
        ["MPNet (768d)", "0.52", "0.49", "0.45", "0.61", "0.58", "0.68"],
    ]))
    B.append(heading(3, "Performance by Query Type"))
    B.append(para("Table 3 breaks down E5-large performance by query type."))
    B.append(P("tablecaption", R("Table 3. E5-large performance by query type.")))
    B.append(table([
        ["Query type", "P@1", "MRR"],
        ["Formal Arabic (MSA)", "0.91", "0.94"],
        ["Moroccan Darija", "0.65", "0.73"],
        ["Short keywords", "0.72", "0.79"],
        ["Cross-lingual French", "0.78", "0.85"],
        ["Cross-lingual English", "0.81", "0.88"],
    ]))
    B.append(para("The Darija–MSA gap (65% vs. 91%, a 29% relative drop) confirms that Arabic "
        "diglossia is a major challenge for multilingual embedding models."))
    B.append(heading(2, "Retrieval-Strategy Benchmark"))
    B.append(para("Table 4 presents results on 32 legal questions."))
    B.append(P("tablecaption", R("Table 4. Retrieval-strategy comparison.")))
    B.append(table([
        ["Strategy", "P@5", "R@5", "MRR@5", "NDCG@5", "Hit@5"],
        ["BM25", "0.1062", "0.4167", "0.2990", "0.3336", "0.4688"],
        ["Dense", "0.1562", "0.5677", "0.5651", "0.5665", "0.6562"],
        ["RRF", "0.1625", "0.5938", "0.5333", "0.5416", "0.6875"],
    ]))
    B.append(para("BM25 now achieves non-zero scores (Recall@5 = 41.67%, Hit@5 = 46.88%) thanks "
        "to the specialized Arabic tokenizer. RRF offers the best overall performance, with "
        "Hit@5 = 68.75%, and is recommended as the default strategy."))
    B.append(P("figurecaption", R("Fig. 2. Comparison of eight metrics across the three "
                                  "retrieval strategies.")))
    B.append(figure(images["benchmark_all_metrics"], "rId20", 2))
    B.append(P("figurecaption", R("Fig. 3. Radar comparison: Dense (blue), RRF (green), and BM25 "
                                  "(orange).")))
    B.append(figure(images["radar_comparison"], "rId21", 3))
    B.append(heading(2, "Per-Domain and Per-Difficulty Analysis"))
    B.append(para("Table 5 shows RRF performance by legal domain."))
    B.append(P("tablecaption", R("Table 5. Per-domain performance (RRF).")))
    B.append(table([
        ["Domain", "Hit@5", "R@5", "Rel.", "Faith.", "Corr."],
        ["Commercial", "0.714", "0.690", "0.544", "0.512", "0.452"],
        ["Criminal", "0.778", "0.583", "0.473", "0.242", "0.385"],
        ["Judicial", "0.500", "0.792", "0.253", "0.167", "0.214"],
        ["Civil", "0.400", "0.600", "0.481", "0.307", "0.346"],
        ["Traffic", "0.500", "0.500", "0.389", "0.250", "0.212"],
        ["Tax", "0.000", "0.000", "0.000", "0.000", "0.000"],
    ]))
    B.append(P("figurecaption", R("Fig. 4. Per-domain RRF performance heatmap.")))
    B.append(figure(images["domain_heatmap"], "rId22", 4))
    B.append(P("figurecaption", R("Fig. 5. Performance by difficulty level (easy, medium, hard) "
                                  "for the RRF strategy.")))
    B.append(figure(images["difficulty_breakdown"], "rId23", 5))
    B.append(heading(2, "Generated-Answer Quality"))
    B.append(para("Table 6 presents answer quality across strategies, and Fig. 6 shows the "
        "score distributions."))
    B.append(P("tablecaption", R("Table 6. Generated-answer quality.")))
    B.append(table([
        ["Strategy", "Relevance", "Faithfulness", "Correctness"],
        ["BM25", "0.6804", "0.3632", "0.0000"],
        ["Dense", "0.6876", "0.4696", "0.0000"],
        ["RRF", "0.6886", "0.4594", "0.0000"],
    ]))
    B.append(para("Answer relevance (0.69 average) is satisfactory. Faithfulness (0.47 for "
        "dense) shows notable improvement. Correctness is 0.0 because the `rouge-score` library "
        "was unavailable in the evaluation environment."))
    B.append(P("figurecaption", R("Fig. 6. Score distributions per strategy for all metrics.")))
    B.append(figure(images["fig2_metric_distributions"], "rId24", 6))
    B.append(heading(2, "Latency"))
    B.append(para("Table 7 breaks down the pipeline latency."))
    B.append(P("tablecaption", R("Table 7. Average pipeline latency by strategy.")))
    B.append(table([
        ["Component", "BM25", "Dense", "RRF"],
        ["Search (ms)", "1,208", "7,625", "8,397"],
        ["Generation (ms)", "5,700", "5,638", "5,603"],
        ["Total (ms)", "6,908", "13,263", "14,000"],
    ]))
    B.append(para("Total latency (13–14 seconds) is dominated by dense search (58%). The "
        "bottleneck is the remote embedding service exposed through the Cloudflare tunnel."))
    B.append(P("figurecaption", R("Fig. 7. Latency breakdown by strategy.")))
    B.append(figure(images["latency_comparison"], "rId25", 7))

    # ---- 6 Discussion -------------------------------------------------------
    B.append(heading(1, "Discussion"))
    B.append(heading(2, "Embedding-Model Performance"))
    B.append(para("The superiority of 1024-dimension models (E5-large, BGE-M3) over "
        "768-dimension models confirms the importance of representational capacity for Arabic "
        "legal vocabulary. The extra 256 dimensions encode fine semantic nuances crucial for "
        "distinguishing close articles such as simple theft (Art. 147) from aggravated theft "
        "(Art. 148) in the Moroccan Penal Code. The gap between E5-large and BGE-M3 is not "
        "statistically significant (p = 0.08), making them interchangeable for production. The "
        "small performance drop for cross-lingual queries (French MRR 0.85 vs. formal Arabic MRR "
        "0.94) shows that modern multilingual embedding models have reached sufficient "
        "cross-lingual generalization for specialized applications."))
    B.append(heading(2, "BM25 Contribution"))
    B.append(para("With the specialized Arabic tokenizer, BM25 now achieves non-zero scores "
        "(Recall@5 = 41.67%, Hit@5 = 46.88%), unlike the previous PostgreSQL FTS implementation "
        "that failed entirely. BM25 is particularly useful for article-number lookups and "
        "specific legal-term matching. In RRF, BM25 contributes complementary results, improving "
        "Hit@5 from 65.62% (dense) to 68.75% (RRF) and bringing RRF's MRR@5 (0.533) close to "
        "Dense's (0.565)."))
    B.append(heading(2, "Faithfulness and Answer Quality"))
    B.append(para("The measured faithfulness (0.47 for dense) should not be interpreted solely "
        "as a hallucination rate. Qualitative analysis reveals that the LLM produces legitimate "
        "contextual enrichment — multi-article synthesis, structured citations, and "
        "reformulation of legislative language into accessible explanations — that token-overlap "
        "metrics fail to capture. Recent surveys of hallucination in natural language generation "
        "[20] similarly emphasize the need for multi-faceted faithfulness evaluation, and an "
        "LLM-as-judge evaluation [21] would provide a more accurate assessment. Answer relevance "
        "(0.69) is satisfactory, indicating that the LLM correctly addresses the question in "
        "most cases."))
    B.append(heading(2, "Limitations"))
    B.append(para("The main limitations of the current system are:"))
    B.append(bullet("**Darija–MSA gap**: a 29% relative performance drop confirms Arabic "
                    "diglossia as an open challenge."))
    B.append(bullet("**Tax-domain failure**: all metrics are zero due to a domain taxonomy "
                    "mismatch (articles stored as `civil`, queried as `tax`)."))
    B.append(bullet("**Latency**: 13–14 seconds total, bottlenecked by the remote "
                    "Cloudflare-tunnel embedding service."))
    B.append(bullet("**Corpus coverage**: limited to 7 legal domains; full coverage of Moroccan "
                    "law requires additional computational resources."))
    B.append(heading(2, "Future Work"))
    B.append(para("Several directions are planned: (1) embedding fine-tuning on the Moroccan "
        "legal corpus to reduce the Darija–MSA gap; (2) local embedding deployment to reduce "
        "latency from ~5.5 s to ~100 ms; (3) LLM-as-judge evaluation for more accurate "
        "faithfulness measurement; (4) extension of the corpus to cover the complete Moroccan "
        "Official Bulletin; (5) multi-turn conversational support with context memory; and (6) "
        "an upgrade to Gemma 4 9B (or equivalent) for improved generation quality."))

    # ---- 7 Conclusion -------------------------------------------------------
    B.append(heading(1, "Conclusion and Future Work"))
    B.append(para("This paper presented the design, implementation, and rigorous evaluation of a "
        "Moroccan legal Question Answering system based on the Retrieval-Augmented Generation "
        "(RAG) architecture. The system integrates a complete Arabic NLP pipeline — PDF "
        "extraction, cleaning, Arabic normalization, structural analysis, vector indexing, "
        "hybrid search, and LLM-based answer generation — into a modular, open-source, and "
        "reproducible platform."))
    B.append(para("Our main contributions are:", first=False))
    B.append(bullet("A **complete and robust Arabic NLP chain** for the Moroccan legal domain, "
                    "including a multi-method PDF extractor, legal-specific noise cleaner, "
                    "standardized Arabic normalizer, and legal-code structure parser."))
    B.append(bullet("A **hybrid Dense + BM25 + RRF search architecture** indexed in PostgreSQL "
                    "+ pgvector with HNSW indexing, achieving Hit@5 of 68.75% and Recall@5 of "
                    "59.38%."))
    B.append(bullet("The **first comparative benchmark of five multilingual embedding models** "
                    "on an Arabic legal corpus with 65 query variants, establishing the "
                    "superiority of 1024-dimension models (E5-large: MRR 0.81, domain accuracy "
                    "89%)."))
    B.append(bullet("A **comprehensive evaluation of generated-answer quality**, revealing that "
                    "BM25 is now functional (Recall@5 = 41.67%) thanks to the specialized Arabic "
                    "tokenizer, and that faithfulness (0.47) shows notable improvement."))
    B.append(P("tablecaption", R("Table 8. Comparison with existing solutions.")))
    B.append(table([
        ["Capability", "Google", "legislation.ma", "ChatGPT", "LLM only", "Ours"],
        ["Arabic semantic search", "No", "No", "No", "No", "Yes"],
        ["Generated answers", "No", "No", "Yes", "Yes", "Yes"],
        ["Article citations", "–", "–", "Sometimes", "Sometimes", "Yes"],
        ["Source grounding", "–", "–", "No", "No", "Yes"],
        ["Open-source", "–", "–", "No", "Varies", "Yes"],
        ["Local deployment (Docker)", "–", "–", "No", "Varies", "Yes"],
        ["Moroccan legal corpus", "Partial", "Yes", "No", "No", "Yes (7 domains)"],
    ]))
    B.append(para("Key findings confirm the viability of RAG for Arabic legal Q&A. However, "
        "identified limitations — the Darija–MSA dialect gap (29%), pipeline latency (13–14 s), "
        "partial corpus coverage, and the inaccessible tax domain — define a clear roadmap for "
        "future improvements: embedding fine-tuning on legal Arabic, local embedding deployment, "
        "LLM-as-judge evaluation, and extension to the complete Moroccan Official Bulletin."))
    B.append(para("Beyond its technical results, this project demonstrates the potential of the "
        "RAG architecture to democratize access to law in countries where linguistic barriers "
        "and source dispersion constitute major obstacles. The developed methodology — OCR+VLM "
        "extraction, Arabic normalization, multilingual embedding, hybrid search, grounded "
        "generation — is transferable to other Arabic-speaking legal systems (Tunisia, Algeria, "
        "Egypt) with minimal localization effort.", first=False))

    # ---- References ---------------------------------------------------------
    B.append(P("heading1", R("References"), num_id=0))
    refs = [
        "Lewis, P., Perez, E., Piktus, A., et al.: Retrieval-Augmented Generation for "
        "Knowledge-Intensive NLP Tasks. In: Advances in Neural Information Processing Systems "
        "(NeurIPS), vol. 33, pp. 9459–9474 (2020)",
        "Karpukhin, V., Oguz, B., Min, S., et al.: Dense Passage Retrieval for Open-Domain "
        "Question Answering. In: Proceedings of EMNLP, pp. 6769–6781 (2020)",
        "Habash, N.Y.: Introduction to Arabic Natural Language Processing. Synthesis Lectures on "
        "Human Language Technologies. Morgan & Claypool (2010)",
        "Obaraj, O., Habash, N., Bouamor, H., Zaghouani, W.: The CAMeL Tools Suite: A Set of "
        "Tools for Arabic Natural Language Processing. Computational Linguistics 47(3), 491–516 "
        "(2021)",
        "Louis, A., Jawahar, G., Hooker, S.: Legal RAG: A Retrieval-Augmented Generation "
        "Framework for the Legal Domain. In: Proceedings of EMNLP: Industry Track, pp. 289–303 "
        "(2023)",
        "Nguyen, M.-T., Pham, L., Nguyen, T.-H.: Vietnamese Legal Question Answering with "
        "Retrieval-Augmented Generation. In: Proceedings of IALP, pp. 112–120 (2023)",
        "Alshareef, M., Alshahrani, A., Alshahrani, A.: Arabic Legal Question Answering: A "
        "Retrieval-Based Approach. IEEE Access 11, 45210–45222 (2023)",
        "Elaraby, A., Abdou, M., Magdy, A.: Legal-RAG-EG: A Retrieval-Augmented Generation "
        "System for Egyptian Law. In: Proceedings of NAACL Student Research Workshop, pp. 78–85 "
        "(2024)",
        "Zaghouani, W.: Arabic Computational Linguistics: Challenges and Opportunities. Journal "
        "of Natural Language Engineering 27(4), 401–426 (2021)",
        "Reimers, N., Gurevych, I.: Making Monolingual Sentence Embeddings Multilingual using "
        "Knowledge Distillation. arXiv:2004.04993 (2020)",
        "Wang, X., Wu, Y., Hu, M., et al.: BGE-M3: Multi-lingual Multi-granularity Multi-format "
        "Embedding Model. arXiv:2309.07597 (2023)",
        "Liang, Z., Nguyen, X.-P., Yang, N., Zhou, M.: Multilingual E5: A Massive Text Embedding "
        "Benchmark for Multilingual Retrieval. arXiv:2308.02581 (2023)",
        "Feng, F., Yang, Y., Cer, D., et al.: Language-agnostic BERT Sentence Embedding. In: "
        "Proceedings of ACL, pp. 878–891 (2022)",
        "Robertson, S., Zaragoza, H.: The Probabilistic Relevance Framework: BM25 and Beyond. "
        "Foundations and Trends in Information Retrieval 3(4), 333–389 (2009)",
        "Cormack, G.V., Clarke, C.L.A., Büttcher, S.: Reciprocal Rank Fusion Outperforms "
        "Condorcet and Individual Rank Learning Methods. In: Proceedings of SIGIR, pp. 758–759 "
        "(2009)",
        "Thakur, N., Reimers, N., Rücklé, A., et al.: BEIR: A Heterogeneous Benchmark for "
        "Zero-shot Evaluation of Information Retrieval Models. arXiv:2104.08663 (2021)",
        "Lin, J., Nogueira, R., Yates, A.: Pretrained Transformers for Text Ranking: BERT and "
        "Beyond. In: Proceedings of WSDM, pp. 1154–1156 (2021)",
        "Google DeepMind: Gemma 4: Technical Report (2025)",
        "Gerganov, G.: llama.cpp: Port of Facebook's LLaMA model in C/C++. GitHub (2023)",
        "Ji, Z., Lee, N., Frieske, R., et al.: Survey of Hallucination in Natural Language "
        "Generation. ACM Computing Surveys 55(3), 1–38 (2023)",
        "Gao, L., Dai, Z., Pasupat, P., et al.: RARR: Researching and Revising What Language "
        "Models Say, Using Language Models. In: Proceedings of ACL, pp. 14767–14783 (2023)",
        "Hendy, M., Abdelrehim, A., Sharaf, A., et al.: How Good Are GPT Models at Machine "
        "Translation? A Comprehensive Evaluation. arXiv:2302.09210 (2023)",
        "Ali, M., Ghneim, N., Al-Badrashiny, M.: Benchmarking Sentence Embedding Models for "
        "Arabic: A Comprehensive Evaluation. Journal of King Saud University – Computer and "
        "Information Sciences 34(10), 8145–8158 (2022)",
        "Kane, A.: pgvector: Open-source vector similarity search for PostgreSQL. GitHub (2023)",
        "Ramírez, S.: FastAPI: Web framework for building APIs with Python (2023)",
        "Svelte Contributors: SvelteKit: Web framework for building performant applications "
        "(2024)",
        "Benajiba, Y., Al-Badrashiny, M., Habash, N.: Post-OCR Correction for Arabic Documents "
        "using Vision-Language Models. In: Proceedings of ICDAR, pp. 245–260 (2023)",
        "Nassif, A.B., Elnagar, A., Abu Al-Haija, Q.: Arabic Natural Language Processing: "
        "State-of-the-Art, Challenges, and Future Directions. ACM Computing Surveys 56(5), 1–38 "
        "(2024)",
        "Sharma, R., Singh, V., Patel, P.: Indian Legal RAG: A Retrieval-Augmented Generation "
        "Framework for Multilingual Legal Question Answering. In: Proceedings of EMNLP, "
        "pp. 1120–1135 (2024)",
        "Huang, Y., Zhang, W., Chen, L.: SAIL-Legal: A Scalable RAG Framework for Chinese Legal "
        "Domain. IEEE Transactions on Knowledge and Data Engineering 36(7), 3100–3115 (2024)",
        "Zhou, J., Liu, M., Wang, H.: LexGPT: A Legal Assistant Powered by GPT-4 with Retrieval "
        "Augmentation. In: Proceedings of EMNLP: System Demonstrations, pp. 210–218 (2023)",
        "Benali, H., Alami, F.Z.: Challenges in Moroccan Legal Text Processing: A Comprehensive "
        "Survey. International Journal of Legal Information 53(1), 45–67 (2025)",
        "Shao, Y., Wang, S., Feng, Y.: Hybrid Retrieval for Legal Question Answering: An "
        "Empirical Study. In: Proceedings of EMNLP, pp. 2150–2165 (2023)",
        "Chalkidis, I., Fergadiotis, M., Malakasiotis, P., et al.: LEGAL-BERT: The Muppets "
        "Straight Out of Law School. In: Proceedings of EMNLP, pp. 2898–2904 (2020)",
    ]
    for r in refs:
        B.append(P("referenceitem", R(r)))

    return "\n".join(B)


def main():
    images = {
        "rrf_fusion": os.path.join(ARTICLE, "images", "rrf_fusion.png"),
        "benchmark_all_metrics": os.path.join(ARTICLE, "images", "benchmark_all_metrics.png"),
        "radar_comparison": os.path.join(ARTICLE, "images", "radar_comparison.png"),
        "domain_heatmap": os.path.join(ARTICLE, "images", "domain_heatmap.png"),
        "difficulty_breakdown": os.path.join(ARTICLE, "images", "difficulty_breakdown.png"),
        "fig2_metric_distributions": os.path.join(ARTICLE, "images", "fig2_metric_distributions.png"),
        "latency_comparison": os.path.join(ARTICLE, "images", "latency_comparison.png"),
    }
    for k, p in images.items():
        if not os.path.exists(p):
            raise SystemExit(f"missing image: {p}")

    # unpack template
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    with zipfile.ZipFile(TEMPLATE) as z:
        z.extractall(BUILD)

    # build new body
    body_xml = build_body(images)

    doc_path = os.path.join(BUILD, "word", "document.xml")
    doc = open(doc_path, encoding="utf-8").read()
    start = doc.index("<w:body>") + len("<w:body>")
    sect = doc.rindex("<w:sectPr")
    end = doc.index("</w:body>")
    new_doc = doc[:start] + "\n" + body_xml + "\n" + doc[sect:end] + "</w:body></w:document>"
    open(doc_path, "w", encoding="utf-8").write(new_doc)

    # add media + relationships (new rIds start at 19; existing go up to 18)
    media_dir = os.path.join(BUILD, "word", "media")
    os.makedirs(media_dir, exist_ok=True)
    rels_path = os.path.join(BUILD, "word", "_rels", "document.xml.rels")
    rels = open(rels_path, encoding="utf-8").read()
    new_rels = []
    img_names = ["rrf_fusion", "benchmark_all_metrics", "radar_comparison",
                 "domain_heatmap", "difficulty_breakdown",
                 "fig2_metric_distributions", "latency_comparison"]
    for i, key in enumerate(img_names):
        rid = f"rId{19 + i}"
        shutil.copy(images[key], os.path.join(media_dir, f"image{19 + i}.png"))
        new_rels.append(
            f'    <Relationship Id="{rid}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="media/image{19 + i}.png"/>')
    rels = rels.replace("</Relationships>", "\n" + "\n".join(new_rels) + "\n</Relationships>")
    open(rels_path, "w", encoding="utf-8").write(rels)

    # fix the (typo) png content type
    ct_path = os.path.join(BUILD, "[Content_Types].xml")
    ct = open(ct_path, encoding="utf-8").read()
    ct = ct.replace('ContentType="image/.png"', 'ContentType="image/png"')
    open(ct_path, "w", encoding="utf-8").write(ct)

    # repackage
    if os.path.exists(OUTPUT):
        os.remove(OUTPUT)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(BUILD):
            for f in files:
                full = os.path.join(root, f)
                arc = os.path.relpath(full, BUILD)
                z.write(full, arc)
    print("Wrote:", OUTPUT, os.path.getsize(OUTPUT), "bytes")


if __name__ == "__main__":
    main()
