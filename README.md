# Omnixform

A local-first CLI for converting images, media, documents, text, and structured data through one extensible interface.

> **Project status:** Omnixform 0.1.0 is being prepared as the first public
> release. The source repository is public, but the Python distribution and
> container image have not been published.

## What Omnixform does

Omnixform provides one command-line interface for single-file and batch
conversion. It includes small converters for text and structured data and
orchestrates established tools for more complex formats:

- Pillow for raster images;
- FFmpeg for audio and video;
- CairoSVG for SVG rendering;
- Pandoc for markup and document formats;
- LibreOffice for office documents.

This architecture keeps the interface consistent, but output quality and
available formats depend on the selected converter, its version, and the host
platform.

## Requirements

- Python 3.11 or newer;
- Pillow, PyYAML, Markdown, Typer, and Rich (installed automatically);
- optional Python packages and external programs for additional formats.

## Installation

Until the first PyPI release, install from a local clone:

```bash
git clone git@github.com:ionnixf/omnixform.git
cd omnixform
python -m venv .venv
source .venv/bin/activate
python -m pip install .
omnix --version
```

On Windows, activate the environment with `.venv\Scripts\activate`.

Install optional image and SVG support with:

```bash
python -m pip install ".[all-formats]"
```

`pip install omnixform` will become the normal installation command only after
the distribution is published.

## Quick start

```bash
omnix convert photo.png --to webp
omnix convert notes.md --to html
omnix --json convert data.yaml --to json
```

Run `omnix doctor` to see which optional converters are available.

## Main commands

| Command | Purpose |
| --- | --- |
| `omnix convert` | Convert one file or a quoted glob |
| `omnix batch` | Batch-oriented alias with the same conversion options |
| `omnix formats` | List declared formats and adapter availability |
| `omnix inspect` | Inspect a file and possible targets |
| `omnix doctor` | Check optional dependencies |
| `omnix completion` | Print a shell completion script |
| `omnix version` | Print version information |

Use `omnix COMMAND --help` for the complete option list.

## Format support

“Supported” means that an adapter declares the conversion pair. Actual codec
availability may vary.

| Category | Common inputs | Common outputs | Converter |
| --- | --- | --- | --- |
| Raster images | PNG, JPEG, WebP, BMP, TIFF | PNG, JPEG, WebP, BMP, TIFF | Pillow |
| Optional images | AVIF, HEIC/HEIF, JPEG XL | AVIF, HEIC, JPEG XL | Pillow plugins |
| Vector images | SVG, SVGZ | PNG, PDF, EPS, PS, SVG | CairoSVG |
| Audio/video | MP3, WAV, FLAC, AAC, M4A, MP4, WebM, MOV, MKV | formats supported by the installed build | FFmpeg |
| Text/markup | TXT, Markdown, HTML | TXT, Markdown, HTML | built-in converter |
| Structured data | JSON, YAML, CSV, TSV | JSON, YAML, CSV, TSV | built-in converter |
| Documents | Markdown, HTML, RST, LaTeX, EPUB, DOCX, ODT and others | formats supported by the installed build | Pandoc |
| Office documents | DOCX, ODT, PPTX, ODP, XLSX, ODS | paired open/proprietary formats and PDF | LibreOffice |

The built-in HTML and Markdown transformations are intentionally simple and
can be lossy. CSV and TSV conversion expects tabular data; nested values may
be serialized rather than round-tripped exactly.

## Optional dependencies

Install only the tools you need. For example, on Debian or Ubuntu:

```bash
sudo apt-get install ffmpeg
sudo apt-get install pandoc
sudo apt-get install libreoffice
```

SVG rendering and additional Pillow codecs are Python extras:

```bash
python -m pip install "omnixform[all-formats]"
```

Pandoc PDF output may also require a TeX or another PDF engine. LibreOffice,
Pandoc, and FFmpeg availability and codec support differ across platforms.

## Conversion examples

Single conversion:

```bash
omnix convert report.md --to html
```

Batch conversion (quote the glob so Omnixform receives it):

```bash
omnix batch "images/*.png" --to webp --output-dir converted
```

Preview without changing files:

```bash
omnix convert report.md --to html --dry-run
```

Machine-readable output:

```bash
omnix --json convert data.yaml --to json
```

JSON mode writes a JSON document to stdout. Failures still return a non-zero
exit code. `--quiet` suppresses normal human output but never changes the exit
status.

Existing destinations are protected:

```bash
omnix convert report.md --to html          # refuses an existing report.html
omnix convert report.md --to html --overwrite
```

Presets apply related options but do not infer the required target format:

```bash
omnix convert video.mov --to mp4 --preset web
omnix convert photo.png --to jpeg --preset high-quality
```

## Shell completions

Print a completion script for the active shell:

```bash
omnix completion bash > omnix.bash
omnix completion zsh > _omnix
omnix completion fish > omnix.fish
```

Review generated scripts before sourcing or installing them. See
`omnix completion --help` for shell-specific guidance.

## Plugins

Third-party adapters are discovered through the `omnixform.adapters`
entry-point group. A minimal package can expose an adapter like this:

```toml
[project.entry-points."omnixform.adapters"]
example = "example_plugin:ExampleAdapter"
```

```python
from omnixform.adapters.base import BaseAdapter
from omnixform.models import Category


class ExampleAdapter(BaseAdapter):
    name = "example"
    category = Category.TEXT
    input_extensions = ["foo"]
    output_extensions = ["bar"]

    def is_available(self) -> bool:
        return True

    def convert(self, input_path, target_format, *, output_path="", options=None):
        with open(input_path, encoding="utf-8") as source:
            value = source.read()
        with open(output_path, "w", encoding="utf-8") as target:
            target.write(value.upper())
        return output_path
```

See [the plugin guide](docs/advanced/plugins.md) for a complete example and
metadata rules. Plugins execute arbitrary Python in the Omnixform process;
they are not sandboxed and should be installed only from trusted sources.

## Containers

The proposed image name is `ghcr.io/ionnixf/omnixform`, but no image has been
published. Build and run it locally:

```bash
docker build --no-cache -t omnixform:local .
docker run --rm -v "$PWD:/work" omnixform:local convert input.png --to webp
```

The container runs as an unprivileged user. Rootless Podman users may need
`--userns=keep-id` for writable bind mounts.

## Platform and security considerations

- Omnixform itself does not upload user files to a cloud service.
- External converters still parse untrusted data as native programs. Use a
  container, VM, or OS sandbox for hostile files.
- Plugins are trusted in-process code, not a security boundary.
- Conversion availability depends on installed programs, codecs, fonts, and
  platform behavior.
- Unsupported or damaged inputs return a diagnostic and non-zero exit code;
  no converter can guarantee recovery from every malformed file.
- Omnixform invokes external programs with argument vectors rather than a
  shell, applies timeouts, validates staged output, and publishes validated
  results atomically where supported.
- Benchmark results measure a particular environment and do not establish
  universal superiority over the underlying tools.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,all-formats,docs]"
ruff check .
ruff format --check .
mypy src tests
pytest
mkdocs build --strict
```

Build distributions with:

```bash
python -m build
python -m twine check --strict dist/*
```

The documentation source is under `docs/`. Read
[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md),
[AUDIT.md](AUDIT.md), and [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) before
submitting changes or preparing a release.

## Contributing and license

Contributions are welcome under the process in
[CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). Omnixform is licensed under the
[MIT License](LICENSE).

## Acknowledgements

Omnixform relies on the work of the Pillow, FFmpeg, CairoSVG, Pandoc,
LibreOffice, Typer, Rich, PyYAML, and Python Markdown communities. Omnixform is
an independent interface and is not affiliated with those projects.
