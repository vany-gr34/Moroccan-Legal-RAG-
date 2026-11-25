# ICCT2026 Article — Springer LNCS Proceedings Format (Microsoft Word)

The English article **in Microsoft Word format**, generated directly from the
Springer **`splnproc2510.docm`** proceedings template.

## Primary deliverable

| File | Description |
|------|-------------|
| **`article.docm`** | The full article in Word. Open it with Microsoft Word (or LibreOffice / Google Docs). Built from the `splnproc2510.docm` template: it keeps the template's styles, running heads, footers, page numbering, heading auto-numbering and the LNCS macro ribbon. |

Contents of `article.docm`:
- Title, placeholder authors + affiliation + e-mail
- Abstract & keywords (LNCS `abstract` / `keywords` styles)
- 7 numbered sections (auto-numbered headings: 1 Introduction … 7 Conclusion and Future Work)
- 8 tables and 7 result figures (embedded, booktabs-style rules)
- RRF equation and 34 auto-numbered references with `[n]` in-text citations

## How to regenerate

```bash
python3 -m venv /tmp/docxenv
/tmp/docxenv/bin/pip install python-docx
/tmp/docxenv/bin/python generate_docx.py
```

The generator rebuilds only the document body inside the Springer template
package (styles/headers/footers/numbering preserved) and embeds the figures.

## Important before submission

- **Replace the placeholder authors** (`Author One/Two/Three`, affiliation,
  e-mail) in the title block with the real ICCT2026 submission metadata.
- The LaTeX source (`main.tex`, `sections/`, `llncs.cls`, `splncs04.bst`,
  `references.bib`) is kept alongside for reference/alternate format — the
  Word file `article.docm` is the primary deliverable.
