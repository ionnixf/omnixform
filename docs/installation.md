# Installation

## Current release-candidate installation

The proposed `omnixform` PyPI distribution is not published or reserved.
Install the checked-out source:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
omnix version
```

Windows activation:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install .
```

Optional image/vector formats:

```bash
python -m pip install ".[all-formats]"
```

This installs `pillow-avif-plugin`, `pillow-heif`, `pillow-jxl-plugin`, and
`cairosvg`. Binary wheels depend on the Python version, operating system, and
architecture.

## External converters

Install tools only for the relevant adapter:

| Tool | Used for |
| --- | --- |
| FFmpeg and FFprobe | audio/video conversion and validation |
| Pandoc | document and markup conversion |
| LibreOffice (`soffice`) | office document conversion |

Examples:

```bash
# Debian/Ubuntu
sudo apt-get install ffmpeg pandoc libreoffice

# macOS with Homebrew
brew install ffmpeg pandoc
brew install --cask libreoffice

# Windows with Chocolatey
choco install ffmpeg pandoc libreoffice
```

Package names and supported codecs vary by platform. Verify the actual
environment:

```bash
omnix doctor
omnix formats
```

Missing optional tools are warnings. The core converters remain usable.
