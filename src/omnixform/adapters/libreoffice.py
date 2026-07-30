from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from omnixform.adapters.base import BaseAdapter
from omnixform.errors import ConversionError, MissingDependencyError, UnsupportedFormatError
from omnixform.models import Category
from omnixform.paths import atomic_write
from omnixform.subprocesses import check_dependency, run_subprocess_sync


class LibreOfficeAdapter(BaseAdapter):
    name = "libreoffice"
    category = Category.EXTERNAL_LIBREOFFICE
    description = "Office document conversion via LibreOffice headless (DOCX, ODT, PPTX, XLSX, PDF)"
    input_extensions = ["docx", "odt", "pptx", "odp", "xlsx", "ods"]
    output_extensions = ["pdf", "docx", "odt", "pptx", "odp", "xlsx", "ods"]
    priority = 60
    options = {}

    _supported_pairs: dict[str, set[str]] = {
        "docx": {"pdf", "odt"},
        "odt": {"pdf", "docx"},
        "pptx": {"pdf", "odp"},
        "odp": {"pdf", "pptx"},
        "xlsx": {"pdf", "ods"},
        "ods": {"pdf", "xlsx"},
    }

    def __init__(self) -> None:
        self._soffice_path: str | None = None

    def is_available(self) -> bool:
        path = check_dependency("soffice")
        if path is None:
            for candidate in ["/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice"]:
                if os.path.isfile(candidate):
                    path = candidate
                    break
        if path is None:
            path = check_dependency("libreoffice")
        self._soffice_path = path
        return path is not None

    def can_convert(self, source_ext: str, target_ext: str) -> bool:
        source = source_ext.lstrip(".").lower()
        target = target_ext.lstrip(".").lower()
        return source in self._supported_pairs and target in self._supported_pairs[source]

    def convert(
        self,
        input_path: str,
        target_format: str,
        *,
        output_path: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        if self._soffice_path is None:
            self._soffice_path = check_dependency("soffice") or check_dependency("libreoffice")
        if self._soffice_path is None:
            raise MissingDependencyError(
                "libreoffice",
                install_hint=(
                    "Install LibreOffice:\n"
                    "  Linux: sudo apt install libreoffice\n"
                    "  macOS: brew install --cask libreoffice\n"
                    "  Windows: choco install libreoffice"
                ),
            )

        target_format = target_format.lstrip(".").lower()
        source_ext = os.path.splitext(input_path)[1].lstrip(".").lower()

        if not self.can_convert(source_ext, target_format):
            raise UnsupportedFormatError(source_ext, target_format)

        if not output_path:
            output_path = os.path.join(
                os.path.dirname(os.path.abspath(input_path)),
                os.path.splitext(os.path.basename(input_path))[0] + "." + target_format,
            )

        temp_dir = tempfile.mkdtemp(prefix="omnixform_lo_")
        profile_dir = os.path.join(temp_dir, "profile")
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(profile_dir)
        os.makedirs(output_dir)
        try:
            result = run_subprocess_sync(
                [
                    self._soffice_path,
                    f"-env:UserInstallation={Path(profile_dir).as_uri()}",
                    "--headless",
                    "--nologo",
                    "--nodefault",
                    "--nolockcheck",
                    "--nofirststartwizard",
                    "--convert-to",
                    target_format,
                    "--outdir",
                    output_dir,
                    os.path.abspath(input_path),
                ],
                timeout=float(options.get("timeout", 120) if options else 120),
            )

            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")[:2000]
                raise ConversionError(
                    f"LibreOffice exited with code {result.returncode}: {stderr}",
                    input_path=input_path,
                    adapter=self.name,
                )

            expected = os.path.join(
                output_dir,
                os.path.splitext(os.path.basename(input_path))[0] + "." + target_format,
            )
            candidates = [
                os.path.join(output_dir, name)
                for name in os.listdir(output_dir)
                if name.lower().endswith(f".{target_format}")
                and os.path.isfile(os.path.join(output_dir, name))
            ]
            temp_output = (
                expected if os.path.isfile(expected) else (candidates[0] if len(candidates) == 1 else None)
            )
            if not temp_output:
                raise ConversionError(
                    "LibreOffice did not produce an output file",
                    input_path=input_path,
                    adapter=self.name,
                )

            # LibreOffice writes to an isolated temporary directory, which may
            # be on another filesystem than the requested destination.
            atomic_write(output_path, source_path=temp_output)
            return output_path
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
