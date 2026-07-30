# Omnixform

Omnixform is a Python 3.11+ command-line converter for images, audio/video,
text, structured data, vector graphics, and office/document formats.

The `0.1.0` tree is a release candidate, not a confirmed public PyPI release.
Install it from source and review the audit and release checklist before
publication.

```bash
python -m pip install .
omnix convert photo.png --to webp
```

Core Pillow, Markdown, JSON, YAML, CSV, and TSV support is installed by
default. AVIF, HEIC, JPEG XL, and CairoSVG need optional Python dependencies.
Audio/video and office/document conversions call external tools.

Omnixform stages and validates CLI output before atomic publication, refuses
existing output by default, supports machine-readable JSON, and returns
documented non-zero exit codes on errors.

Start with [installation](installation.md), the [quick start](quickstart.md),
or the [format matrix](formats/overview.md).
