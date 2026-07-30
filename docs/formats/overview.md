# Supported formats

The table reflects adapter declarations and regression tests. External codec
availability and conversion fidelity vary by tool build and input.

| Adapter | Input | Output | Requirement |
| --- | --- | --- | --- |
| Pillow | PNG, JPEG, WebP, BMP, TIFF | PNG, JPEG, WebP, BMP, TIFF | default |
| Pillow optional | AVIF, HEIC/HEIF, JXL | AVIF, HEIC, JXL | `.[all-formats]` |
| Text | TXT, MD, HTML | TXT, MD, HTML | default |
| Structured | JSON, YAML, CSV, TSV | JSON, YAML, CSV, TSV | default |
| CairoSVG | SVG, SVGZ | PNG, PDF, EPS, PS, SVG | CairoSVG |
| FFmpeg | MP3, WAV, FLAC, AAC, M4A, MP4, WebM, MOV, MKV | same set | FFmpeg |
| Pandoc | DOCX, ODT, EPUB, RST, LaTeX/TEX, MD, HTML, TXT, Org, CSV | DOCX, ODT, EPUB, PDF, RST, LaTeX/TEX, MD, HTML, TXT, Org | Pandoc |
| LibreOffice | DOCX, ODT, PPTX, ODP, XLSX, ODS | PDF and paired open/proprietary office formats | LibreOffice |

Pandoc does not accept PDF as an input in Omnixform. Pandoc PDF output normally
requires a separately installed PDF engine. LibreOffice supports DOCX↔ODT,
PPTX↔ODP, XLSX↔ODS, plus each supported input to PDF.

Structured-data caveats:

- JSON/YAML to CSV/TSV requires a top-level list of objects.
- CSV/TSV values are strings when read.
- Nested JSON/YAML cells are serialized; full round-trip fidelity is not
  promised.

Text caveats:

- HTML-to-Markdown and HTML-to-text use basic tag stripping.
- Markdown-to-HTML supports the extensions configured in the adapter.
- Sanitizing active HTML is outside the converter's scope.

Use `omnix formats` for adapter-level availability on the current machine
and `omnix inspect PATH` for target suggestions.
