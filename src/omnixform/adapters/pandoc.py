from __future__ import annotations

import os
from typing import Any

from omnixform.adapters.base import BaseAdapter
from omnixform.errors import ConversionError, MissingDependencyError, OmnixformError, UnsupportedFormatError
from omnixform.formats import normalize_format
from omnixform.models import Category
from omnixform.paths import make_staging_path, publish_staged_output, remove_staging_file, replace_extension
from omnixform.subprocesses import check_dependency, run_subprocess_sync


class PandocAdapter(BaseAdapter):
    name = "pandoc"
    category = Category.EXTERNAL_PANDOC
    description = "Document conversion via Pandoc (DOCX, ODT, EPUB, markup, and more)"
    input_extensions = [
        "docx",
        "odt",
        "epub",
        "rst",
        "latex",
        "tex",
        "md",
        "html",
        "htm",
        "txt",
        "org",
        "csv",
    ]
    output_extensions = [
        "docx",
        "odt",
        "epub",
        "pdf",
        "rst",
        "latex",
        "tex",
        "md",
        "html",
        "htm",
        "txt",
        "org",
    ]
    priority = 50
    options = {
        "encoding": {"type": "str", "default": "utf-8"},
    }

    _pandoc_format_map = {
        "md": "markdown",
        "html": "html",
        "htm": "html",
        "txt": "plain",
        "latex": "latex",
        "tex": "latex",
        "docx": "docx",
        "odt": "odt",
        "epub": "epub",
        "pdf": "pdf",
        "rst": "rst",
        "org": "org",
        "csv": "csv",
        "yaml": "yaml",
        "json": "json",
    }
    _pdf_engines = (
        "pdflatex",
        "lualatex",
        "xelatex",
        "tectonic",
        "wkhtmltopdf",
        "weasyprint",
        "prince",
        "context",
        "pdfroff",
    )

    def __init__(self) -> None:
        self._pandoc_path: str | None = None

    def is_available(self) -> bool:
        self._pandoc_path = check_dependency("pandoc")
        return self._pandoc_path is not None

    def is_conversion_available(self, source_ext: str, target_ext: str) -> bool:
        if not self.can_convert(source_ext, target_ext) or not self.is_available():
            return False
        if normalize_format(target_ext) == "pdf":
            return any(check_dependency(engine) is not None for engine in self._pdf_engines)
        return True

    def convert(
        self,
        input_path: str,
        target_format: str,
        *,
        output_path: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        if self._pandoc_path is None:
            self._pandoc_path = check_dependency("pandoc")
        if self._pandoc_path is None:
            raise MissingDependencyError(
                "pandoc",
                install_hint=(
                    "Install Pandoc:\n"
                    "  Linux: sudo apt install pandoc\n"
                    "  macOS: brew install pandoc\n"
                    "  Windows: choco install pandoc"
                ),
            )

        target_format = normalize_format(target_format)
        if target_format not in self.output_extensions:
            raise UnsupportedFormatError(
                os.path.splitext(input_path)[1],
                target_format,
                reason="Pandoc does not support this output format",
            )

        if not output_path:
            output_path = replace_extension(input_path, target_format)

        source_ext = normalize_format(os.path.splitext(input_path)[1])
        if source_ext == "tex":
            source_ext = "latex"

        staging_path = make_staging_path(output_path, target_format)
        args = [
            self._pandoc_path,
            os.path.abspath(input_path),
            "-f",
            self._pandoc_format_map.get(source_ext, source_ext),
            "-t",
            self._pandoc_format_map.get(target_format, target_format),
            "-o",
            staging_path,
        ]

        try:
            result = run_subprocess_sync(args, timeout=float(options.get("timeout", 120) if options else 120))
        except OmnixformError:
            remove_staging_file(staging_path)
            raise
        except Exception as e:
            remove_staging_file(staging_path)
            raise ConversionError(
                "Pandoc conversion failed",
                input_path=input_path,
                adapter=self.name,
                details=str(e),
            ) from e

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[:2000]
            remove_staging_file(staging_path)
            raise ConversionError(
                f"Pandoc exited with code {result.returncode}: {stderr}",
                input_path=input_path,
                adapter=self.name,
            )

        try:
            publish_staged_output(staging_path, output_path, overwrite=True)
            return output_path
        finally:
            remove_staging_file(staging_path)
