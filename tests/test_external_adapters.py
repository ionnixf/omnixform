"""Tests for adapters that require external dependencies (FFmpeg, Pandoc, LibreOffice).

These tests use mocking to test the command-building logic without requiring
the actual external programs to be installed. Integration tests are marked
with @pytest.mark.integration and only run when the dependency is available.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from omnixform.errors import TimeoutError_, UnsupportedFormatError

from .fixtures import TempDir

# ── FFmpeg / MultimediaAdapter Tests ──────────────────────────────────────


class TestMultimediaAdapterMocked:
    """Test FFmpeg adapter logic with mocked subprocess."""

    def setup_method(self) -> None:
        from omnixform.adapters.multimedia import MultimediaAdapter

        self.adapter = MultimediaAdapter()

    def test_available_when_ffmpeg_found(self) -> None:
        with patch("omnixform.adapters.multimedia.check_dependency", return_value="/usr/bin/ffmpeg"):
            assert self.adapter.is_available()

    def test_not_available_when_ffmpeg_missing(self) -> None:
        with patch("omnixform.adapters.multimedia.check_dependency", return_value=None):
            assert not self.adapter.is_available()

    @patch("omnixform.adapters.multimedia.check_dependency", return_value="/usr/bin/ffmpeg")
    def test_unsupported_format_raises_error(self, mock_check: MagicMock) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.mp4")
            with open(src, "wb") as f:
                f.write(b"\x00\x00\x00\x20ftypmp42")
            with pytest.raises(UnsupportedFormatError):
                self.adapter.convert(src, "docx")

    def test_can_convert(self) -> None:
        assert self.adapter.can_convert("mp4", "mp3")
        assert self.adapter.can_convert("mp3", "wav")
        assert self.adapter.can_convert("mov", "mp4")
        assert not self.adapter.can_convert("mp4", "png")

    def test_command_uses_argument_vector_and_absolute_paths(self) -> None:
        self.adapter._ffmpeg_path = "/opt/ffmpeg"
        self.adapter._ffprobe_path = None
        with TempDir() as tmp:
            src = os.path.join(tmp, "input ; $(touch injected).wav")
            dst = os.path.join(tmp, "output file.mp3")
            with open(src, "wb") as f:
                f.write(b"input")

            completed = subprocess.CompletedProcess([], 0, b"", b"")
            with patch(
                "omnixform.adapters.multimedia.run_subprocess_sync",
                return_value=completed,
            ) as run:
                self.adapter.convert(src, "mp3", output_path=dst)

            args = run.call_args.args[0]
            assert args[0] == "/opt/ffmpeg"
            assert args[args.index("-i") + 1] == os.path.abspath(src)
            assert src in args
            assert all(arg != "touch" for arg in args)
            assert os.path.isfile(dst)

    def test_timeout_is_not_wrapped_and_staging_is_cleaned(self) -> None:
        self.adapter._ffmpeg_path = "/opt/ffmpeg"
        self.adapter._ffprobe_path = None
        with TempDir() as tmp:
            src = os.path.join(tmp, "input.wav")
            dst = os.path.join(tmp, "output.mp3")
            with open(src, "wb") as f:
                f.write(b"input")

            with patch(
                "omnixform.adapters.multimedia.run_subprocess_sync",
                side_effect=TimeoutError_("ffmpeg", 0.1),
            ):
                with pytest.raises(TimeoutError_):
                    self.adapter.convert(src, "mp3", output_path=dst)

            assert not os.path.exists(dst)
            assert not [name for name in os.listdir(tmp) if name.startswith(".omnixform_")]


@pytest.mark.integration
class TestMultimediaAdapterIntegration:
    """Integration tests requiring FFmpeg."""

    def test_ffmpeg_available(self) -> None:
        from omnixform.subprocesses import check_dependency

        assert check_dependency("ffmpeg") is not None, "FFmpeg not installed"

    def test_mp4_to_mp3_conversion(self) -> None:
        from omnixform.adapters.multimedia import MultimediaAdapter

        adapter = MultimediaAdapter()
        if not adapter.is_available():
            pytest.skip("FFmpeg not available")
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.mp4")
            # Create a valid test by using ffmpeg to generate a small test video
            import subprocess as sp

            gen_result = sp.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=red:size=16x16:d=0.5",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=44100:cl=mono",
                    "-shortest",
                    src,
                ],
                capture_output=True,
                timeout=30,
            )
            assert gen_result.returncode == 0, gen_result.stderr.decode(errors="replace")
            assert os.path.isfile(src)
            assert os.path.getsize(src) > 0

            dst = adapter.convert(src, "mp3", output_path=os.path.join(tmp, "test.mp3"))
            assert os.path.isfile(dst)
            assert os.path.getsize(dst) > 0


# ── PandocAdapter Tests ──────────────────────────────────────────────────


class TestPandocAdapterMocked:
    """Test Pandoc adapter logic with mocked subprocess."""

    def setup_method(self) -> None:
        from omnixform.adapters.pandoc import PandocAdapter

        self.adapter = PandocAdapter()

    def test_not_available_when_pandoc_missing(self) -> None:
        with patch("omnixform.adapters.pandoc.check_dependency", return_value=None):
            assert not self.adapter.is_available()

    def test_available_when_pandoc_found(self) -> None:
        with patch("omnixform.adapters.pandoc.check_dependency", return_value="/usr/bin/pandoc"):
            assert self.adapter.is_available()

    def test_can_convert(self) -> None:
        assert self.adapter.can_convert("docx", "pdf")
        assert self.adapter.can_convert("md", "pdf")

    def test_pdf_requires_a_pdf_engine(self) -> None:
        def dependency(name: str) -> str | None:
            return "/opt/pandoc" if name == "pandoc" else None

        with patch("omnixform.adapters.pandoc.check_dependency", side_effect=dependency):
            assert not self.adapter.is_conversion_available("md", "pdf")
            assert self.adapter.is_conversion_available("md", "html")

    def test_command_uses_argument_vector_and_absolute_paths(self) -> None:
        self.adapter._pandoc_path = "/opt/pandoc"
        with TempDir() as tmp:
            src = os.path.join(tmp, "input ; $(touch injected).md")
            dst = os.path.join(tmp, "output file.html")
            with open(src, "w") as f:
                f.write("# heading")

            completed = subprocess.CompletedProcess([], 0, b"", b"")
            with patch(
                "omnixform.adapters.pandoc.run_subprocess_sync",
                return_value=completed,
            ) as run:
                self.adapter.convert(src, "html", output_path=dst)

            args = run.call_args.args[0]
            assert args[0] == "/opt/pandoc"
            assert args[1] == os.path.abspath(src)
            assert src in args
            assert all(arg != "touch" for arg in args)
            assert os.path.isfile(dst)


@pytest.mark.integration
class TestPandocAdapterIntegration:
    """Integration tests requiring Pandoc."""

    def test_pandoc_available(self) -> None:
        from omnixform.subprocesses import check_dependency

        if check_dependency("pandoc") is None:
            pytest.skip("Pandoc not installed")

    def test_markdown_to_html_conversion(self, tmp_path: Path) -> None:
        from omnixform.adapters.pandoc import PandocAdapter

        adapter = PandocAdapter()
        if not adapter.is_available():
            pytest.skip("Pandoc not installed")
        source = tmp_path / "input with spaces.md"
        destination = tmp_path / "результат.html"
        source.write_text("# Verified heading\n", encoding="utf-8")

        result = adapter.convert(str(source), "html", output_path=str(destination))

        assert result == str(destination)
        assert "<h1" in destination.read_text(encoding="utf-8")


# ── LibreOfficeAdapter Tests ────────────────────────────────────────────────


class TestLibreOfficeAdapterMocked:
    """Test LibreOffice adapter logic with mocked subprocess."""

    def setup_method(self) -> None:
        from omnixform.adapters.libreoffice import LibreOfficeAdapter

        self.adapter = LibreOfficeAdapter()

    def test_not_available_when_soffice_missing(self) -> None:
        with patch("omnixform.adapters.libreoffice.check_dependency", return_value=None):
            assert not self.adapter.is_available()

    def test_can_convert(self) -> None:
        assert self.adapter.can_convert("docx", "pdf")
        assert self.adapter.can_convert("odt", "pdf")
        assert self.adapter.can_convert("pptx", "odp")
        assert self.adapter.can_convert("xlsx", "ods")
        assert not self.adapter.can_convert("png", "pdf")

    def test_command_uses_argument_vector_and_isolated_profile(self, tmp_path: Path) -> None:
        source = tmp_path / "input ; $(touch injected).docx"
        destination = tmp_path / "output file.pdf"
        source.write_bytes(b"input")
        self.adapter._soffice_path = "/opt/soffice"

        def run_command(args: list[str], *, timeout: float) -> subprocess.CompletedProcess[bytes]:
            output_dir = Path(args[args.index("--outdir") + 1])
            (output_dir / "input ; $(touch injected).pdf").write_bytes(b"%PDF-1.4\n")
            return subprocess.CompletedProcess(args, 0, b"", b"")

        with patch(
            "omnixform.adapters.libreoffice.run_subprocess_sync",
            side_effect=run_command,
        ) as run:
            result = self.adapter.convert(str(source), "pdf", output_path=str(destination))

        args = run.call_args.args[0]
        assert result == str(destination)
        assert args[0] == "/opt/soffice"
        assert args[-1] == os.path.abspath(source)
        assert any(arg.startswith("-env:UserInstallation=file:") for arg in args)
        assert all(arg != "touch" for arg in args)
        assert destination.read_bytes().startswith(b"%PDF")


@pytest.mark.integration
class TestLibreOfficeAdapterIntegration:
    """Integration tests requiring both LibreOffice and Pandoc for the fixture."""

    def test_docx_to_pdf_conversion(self, tmp_path: Path) -> None:
        from omnixform.adapters.libreoffice import LibreOfficeAdapter
        from omnixform.subprocesses import check_dependency

        pandoc = check_dependency("pandoc")
        adapter = LibreOfficeAdapter()
        if pandoc is None or not adapter.is_available():
            pytest.skip("LibreOffice and Pandoc are required")

        markdown = tmp_path / "source.md"
        source = tmp_path / "input with spaces.docx"
        destination = tmp_path / "результат.pdf"
        markdown.write_text("# LibreOffice integration\n", encoding="utf-8")
        generated = subprocess.run(
            [pandoc, str(markdown), "-o", str(source)],
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert generated.returncode == 0, generated.stderr.decode(errors="replace")

        result = adapter.convert(str(source), "pdf", output_path=str(destination))

        assert result == str(destination)
        assert destination.read_bytes().startswith(b"%PDF")


# ── Adapter info tests ────────────────────────────────────────────────────


class TestAdapterInfo:
    def test_adapter_infos_have_correct_names(self) -> None:
        from omnixform.registry import get_registry

        registry = get_registry()
        infos = registry.get_adapter_infos()
        names = [i.name for i in infos]
        assert "pandoc" in names
        assert "libreoffice" in names
        assert "ffmpeg" in names

    def test_missing_dependencies_marked(self) -> None:
        from omnixform.registry import get_registry

        registry = get_registry()
        infos = registry.get_adapter_infos()
        for info in infos:
            if info.name in ("pandoc", "libreoffice") and not info.available:
                assert info.unavailability_reason
