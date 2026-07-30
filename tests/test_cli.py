"""Comprehensive tests for the CLI and conversion pipeline.

Covers all 23+ required scenarios.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from .fixtures import (
    TempDir,
    create_test_csv,
    create_test_html,
    create_test_image,
    create_test_json,
    create_test_markdown,
    create_test_yaml,
)


def run_omnixform(*args: str, expected_code: int = 0) -> subprocess.CompletedProcess[str]:
    """Run omnixform and return result."""
    result = subprocess.run(
        [sys.executable, "-m", "omnixform", *args],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    if result.returncode != expected_code:
        print(f"  STDOUT: {result.stdout[:500]}")
        print(f"  STDERR: {result.stderr[:500]}")
    return result


def check_stdout(result: subprocess.CompletedProcess[str]) -> str:
    """Get output, checking both stdout and stderr (Rich uses stderr)."""
    return result.stdout + result.stderr


# ── Scenario 1: PNG → WebP ───────────────────────────────────────────────


class TestPngToWebp:
    def test_conversion(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "input.png")
            create_test_image(src)
            result = run_omnixform("convert", src, "--to", "webp", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "input.webp")
            assert os.path.isfile(dst)
            assert os.path.getsize(dst) > 0


# ── Scenario 2: PNG with transparency → JPEG ─────────────────────────────


class TestPngWithAlphaToJpeg:
    def test_conversion(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "alpha.png")
            create_test_image(src, with_alpha=True)
            result = run_omnixform("convert", src, "--to", "jpg", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "alpha.jpeg")
            assert os.path.isfile(dst)

    def test_with_background_option(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "alpha.png")
            create_test_image(src, with_alpha=True)
            result = run_omnixform("convert", src, "--to", "jpg", "--overwrite", "--background", "black")
            assert result.returncode == 0
            dst = os.path.join(tmp, "alpha.jpeg")
            assert os.path.isfile(dst)


# ── Scenario 3: JPEG → PNG ────────────────────────────────────────────────


class TestJpegToPng:
    def test_conversion(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "input.jpg")
            create_test_image(src)
            result = run_omnixform("convert", src, "--to", "png", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "input.png")
            assert os.path.isfile(dst)


# ── Scenario 4: Markdown → HTML ─────────────────────────────────────────


class TestMarkdownToHtml:
    def test_conversion(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "doc.md")
            create_test_markdown(src)
            result = run_omnixform("convert", src, "--to", "html", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "doc.html")
            assert os.path.isfile(dst)
            with open(dst) as f:
                content = f.read()
            assert "<h1>" in content or "<p>" in content


# ── Scenario 5: HTML → TXT ────────────────────────────────────────────────


class TestHtmlToTxt:
    def test_conversion(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "page.html")
            create_test_html(src)
            result = run_omnixform("convert", src, "--to", "txt", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "page.txt")
            assert os.path.isfile(dst)
            with open(dst) as f:
                content = f.read()
            assert "Test Document" in content


# ── Scenario 6: JSON → YAML → JSON ────────────────────────────────────────


class TestJsonToYamlToJson:
    def test_json_to_yaml(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "data.json")
            create_test_json(src)
            result = run_omnixform("convert", src, "--to", "yaml", "--overwrite")
            assert result.returncode == 0
            yaml_path = os.path.join(tmp, "data.yaml")
            assert os.path.isfile(yaml_path)

            # YAML → JSON
            result2 = run_omnixform("convert", yaml_path, "--to", "json", "--overwrite")
            assert result2.returncode == 0
            json2_path = os.path.join(tmp, "data.json")
            with open(json2_path) as f:
                data = json.load(f)
            assert data["name"] == "test"
            assert data["version"] == 1


# ── Scenario 7: CSV → JSON ───────────────────────────────────────────────


class TestCsvToJson:
    def test_conversion(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "data.csv")
            create_test_csv(src)
            result = run_omnixform("convert", src, "--to", "json", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "data.json")
            assert os.path.isfile(dst)
            with open(dst) as f:
                data = json.load(f)
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["name"] == "Alice"

    def test_with_delimiter(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "data.csv")
            create_test_csv(src)
            result = run_omnixform("convert", src, "--to", "json", "--overwrite", "--delimiter", ",")
            assert result.returncode == 0


# ── Scenario 8: JSON array of objects → CSV ──────────────────────────────


class TestJsonArrayToCsv:
    def test_conversion(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "data.json")
            create_test_json(src, array_of_objects=True)
            result = run_omnixform("convert", src, "--to", "csv", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "data.csv")
            assert os.path.isfile(dst)
            with open(dst) as f:
                content = f.read()
            assert "Alice" in content
            assert "Bob" in content


# ── Scenario 9: Overwrite protection without --overwrite ─────────────────


class TestNoOverwrite:
    def test_overwrite_refused(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)
            # First conversion creates output
            run_omnixform("convert", src, "--to", "webp", "--overwrite")
            # Second without --overwrite should fail
            result = run_omnixform("convert", src, "--to", "webp")
            assert result.returncode != 0
            assert "already exists" in (result.stdout + result.stderr).lower()


# ── Scenario 10: Successful overwrite with --overwrite ──────────────────


class TestOverwrite:
    def test_overwrite_allowed(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)
            run_omnixform("convert", src, "--to", "webp", "--overwrite")
            result = run_omnixform("convert", src, "--to", "webp", "--overwrite")
            assert result.returncode == 0


# ── Scenario 11: Non-existent input file ─────────────────────────────────


class TestMissingInput:
    def test_file_not_found(self) -> None:
        result = run_omnixform("convert", "/nonexistent/file.png", "--to", "webp")
        assert result.returncode != 0


# ── Scenario 12: Unsupported format pair ──────────────────────────────────


class TestUnsupportedFormat:
    def test_unsupported(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)
            result = run_omnixform("convert", src, "--to", "docx")
            assert result.returncode != 0

    def test_path_like_target_format_is_rejected_as_bad_arguments(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)

            result = run_omnixform("convert", src, "--to", "../../webp")

            assert result.returncode == 2
            assert "invalid target format" in check_stdout(result).lower()


# ── Scenario 13: Corrupted image ──────────────────────────────────────────


class TestCorruptedImage:
    def test_corrupted(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "bad.png")
            with open(src, "wb") as f:
                f.write(b"not a real image file at all")
            result = run_omnixform("convert", src, "--to", "webp")
            assert result.returncode != 0


# ── Scenario 14: Same input and output path ──────────────────────────────


class TestSamePath:
    def test_same_path(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)
            result = run_omnixform("convert", src, "--to", "png", "--overwrite")
            assert result.returncode != 0


# ── Scenario 15: JSON mode output correctness ─────────────────────────────


class TestJsonMode:
    def test_success_json(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)
            result = run_omnixform("--json", "convert", src, "--to", "webp", "--overwrite")
            data = json.loads(result.stdout)
            assert data["success"] is True
            assert data["source_format"] == "png"
            assert data["target_format"] == "webp"
            assert data["adapter"] == "pillow"
            assert "duration_ms" in data

    def test_error_json(self) -> None:
        result = run_omnixform("--json", "convert", "/nonexistent.png", "--to", "webp")
        assert result.returncode == 3
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["code"] == 3


# ── Scenario 16: omnix formats ────────────────────────────────────────


class TestFormats:
    def test_formats_table(self) -> None:
        result = run_omnixform("formats")
        assert result.returncode == 0
        output = check_stdout(result)
        assert "pillow" in output
        assert "ffmpeg" in output

    def test_formats_json(self) -> None:
        result = run_omnixform("--json", "formats")
        data = json.loads(result.stdout)
        assert "adapters" in data
        assert len(data["adapters"]) > 0


# ── Scenario 17: omnix inspect ────────────────────────────────────────


class TestInspect:
    def test_inspect_file(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)
            result = run_omnixform("inspect", src)
            assert result.returncode == 0
            output = check_stdout(result)
            assert "png" in output

    def test_inspect_json(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)
            result = run_omnixform("--json", "inspect", src)
            data = json.loads(result.stdout)
            assert data["extension"] == "png"

    def test_inspect_missing(self) -> None:
        result = run_omnixform("inspect", "/nonexistent")
        assert result.returncode != 0

    def test_inspect_warns_on_extension_content_mismatch(self) -> None:
        with TempDir() as tmp:
            png_path = os.path.join(tmp, "source.png")
            disguised_path = os.path.join(tmp, "disguised.jpg")
            create_test_image(png_path)
            with open(png_path, "rb") as source, open(disguised_path, "wb") as destination:
                destination.write(source.read())

            result = run_omnixform("--json", "inspect", disguised_path)
            data = json.loads(result.stdout)

            assert data["detected_format"] == "png"
            assert data["content_format"] == "png"
            assert data["warnings"]


# ── Scenario 18: omnix doctor ─────────────────────────────────────────


class TestDoctor:
    def test_doctor(self) -> None:
        result = run_omnixform("doctor")
        assert result.returncode == 0
        output = check_stdout(result)
        assert "Python" in output

    def test_doctor_json(self) -> None:
        result = run_omnixform("--json", "doctor")
        data = json.loads(result.stdout)
        assert "healthy" in data
        assert "checks" in data


# ── Scenario 19: Paths with spaces and Unicode ──────────────────────────


@pytest.mark.slow
class TestUnicodePaths:
    def test_spaces_in_path(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "my file.png")
            create_test_image(src)
            run_omnixform("convert", src, "--to", "webp", "--overwrite")
            dst = os.path.join(tmp, "my file.webp")
            assert os.path.isfile(dst)

    def test_unicode_in_path(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "файл.png")
            create_test_image(src)
            run_omnixform("convert", src, "--to", "webp", "--overwrite")
            dst = os.path.join(tmp, "файл.webp")
            assert os.path.isfile(dst)


# ── Scenario 20: Temp file cleanup on error ────────────────────────────────


class TestTempFileCleanup:
    def test_cleanup_on_error(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "bad.png")
            with open(src, "wb") as f:
                f.write(b"garbage data")
            # Check for leftover .omnixform_ files
            before = {f for f in os.listdir(tmp) if f.startswith(".omnixform_")}
            run_omnixform("convert", src, "--to", "webp")
            after = {f for f in os.listdir(tmp) if f.startswith(".omnixform_")}
            # Expect no new temp files
            assert after == before or not after


# ── Scenario 21: Behavior when external deps missing ─────────────────────


class TestMissingExternalDependencies:
    def test_pandoc_not_available(self) -> None:
        """Pandoc absence shouldn't crash the app"""
        result = run_omnixform("formats")
        assert "pandoc" in check_stdout(result).lower()
        assert result.returncode == 0


# ── Scenario 22: Dry run ──────────────────────────────────────────────────


class TestDryRun:
    def test_dry_run(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)
            result = run_omnixform("convert", src, "--to", "webp", "--dry-run")
            assert result.returncode == 0
            # File should NOT be created
            dst = os.path.join(tmp, "test.webp")
            assert not os.path.isfile(dst)

    def test_json_dry_run_is_one_parseable_document(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)

            result = run_omnixform("--json", "convert", src, "--to", "webp", "--dry-run")

            assert result.returncode == 0
            payload = json.loads(result.stdout)
            assert payload["success"] is True
            assert payload["dry_run"] is True
            assert not os.path.isfile(os.path.join(tmp, "test.webp"))


# ── Scenario 23: Version command ─────────────────────────────────────────


class TestVersion:
    def test_root_version_option(self) -> None:
        result = run_omnixform("--version")
        assert result.returncode == 0
        assert "Omnixform 0.1.0" in check_stdout(result)

    def test_version(self) -> None:
        result = run_omnixform("version")
        assert result.returncode == 0
        output = check_stdout(result)
        assert "0.1.0" in output

    def test_version_json(self) -> None:
        result = run_omnixform("--json", "version")
        data = json.loads(result.stdout)
        assert data["version"] == "0.1.0"
        assert data["command"] == "omnix"


class TestBatchCommand:
    def test_dedicated_batch_command(self) -> None:
        with TempDir() as tmp:
            create_test_image(os.path.join(tmp, "one.png"))
            create_test_image(os.path.join(tmp, "two.png"))

            result = run_omnixform(
                "batch",
                os.path.join(tmp, "*.png"),
                "--to",
                "webp",
                "--output-dir",
                os.path.join(tmp, "converted"),
            )

            assert result.returncode == 0
            assert os.path.isfile(os.path.join(tmp, "converted", "one.webp"))
            assert os.path.isfile(os.path.join(tmp, "converted", "two.webp"))

    def test_expanded_paths_are_accepted(self) -> None:
        with TempDir() as tmp:
            one = create_test_image(os.path.join(tmp, "one.png"))
            two = create_test_image(os.path.join(tmp, "two.png"))

            result = run_omnixform(
                "batch",
                one,
                two,
                "--to",
                "webp",
                "--output-dir",
                os.path.join(tmp, "converted"),
            )

            assert result.returncode == 0
            assert os.path.isfile(os.path.join(tmp, "converted", "one.webp"))
            assert os.path.isfile(os.path.join(tmp, "converted", "two.webp"))


# ── Scenario 24: Exit codes ────────────────────────────────────────────────


class TestExitCodes:
    def test_success(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src)
            result = run_omnixform("convert", src, "--to", "webp", "--overwrite")
            assert result.returncode == 0

    def test_file_not_found(self) -> None:
        result = run_omnixform("convert", "/nonexistent", "--to", "webp")
        assert result.returncode == 3

    def test_quiet_failure_is_nonzero(self) -> None:
        result = run_omnixform("--quiet", "convert", "/nonexistent", "--to", "webp")
        assert result.returncode == 3
        assert result.stdout == ""
        assert result.stderr == ""

    def test_local_quiet_suppresses_argument_error(self) -> None:
        result = run_omnixform("convert", "unused.png", "--to", "../webp", "--quiet")
        assert result.returncode == 2
        assert result.stdout == ""
        assert result.stderr == ""

    def test_mixed_batch_failure_is_nonzero_and_json_is_parseable(self) -> None:
        with TempDir() as tmp:
            create_test_image(os.path.join(tmp, "good.png"))
            with open(os.path.join(tmp, "bad.png"), "wb") as f:
                f.write(b"not an image")

            result = run_omnixform(
                "--json",
                "convert",
                os.path.join(tmp, "*.png"),
                "--to",
                "webp",
            )

            assert result.returncode == 8
            data = json.loads(result.stdout)
            assert data["successful"] == 1
            assert data["failed"] == 1


# ── Additional: TXT → Markdown, Markdown → TXT ─────────────────────────


class TestTextConversions:
    def test_txt_to_md(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "doc.txt")
            with open(src, "w") as f:
                f.write("Hello world")
            result = run_omnixform("convert", src, "--to", "md", "--overwrite")
            assert result.returncode == 0
            assert os.path.isfile(os.path.join(tmp, "doc.md"))

    def test_md_to_txt(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "doc.md")
            create_test_markdown(src)
            result = run_omnixform("convert", src, "--to", "txt", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "doc.txt")
            assert os.path.isfile(dst)

    def test_txt_to_html(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "doc.txt")
            with open(src, "w") as f:
                f.write("Hello world")
            result = run_omnixform("convert", src, "--to", "html", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "doc.html")
            assert os.path.isfile(dst)
            with open(dst) as f:
                content = f.read()
            assert "<p>" in content


# ── Additional: CSV ↔ TSV, JSON → YAML, etc. ──────────────────────────


class TestDataConversions:
    def test_csv_to_tsv(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "data.csv")
            create_test_csv(src)
            result = run_omnixform("convert", src, "--to", "tsv", "--overwrite")
            assert result.returncode == 0
            dst = os.path.join(tmp, "data.tsv")
            assert os.path.isfile(dst)

    def test_json_to_yaml(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "data.json")
            create_test_json(src)
            result = run_omnixform("convert", src, "--to", "yaml", "--overwrite")
            assert result.returncode == 0
            assert os.path.isfile(os.path.join(tmp, "data.yaml"))

    def test_yaml_to_json(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "data.yaml")
            create_test_yaml(src)
            result = run_omnixform("convert", src, "--to", "json", "--overwrite")
            assert result.returncode == 0
            assert os.path.isfile(os.path.join(tmp, "data.json"))


# ── Additional: Resize options ──────────────────────────────────────────


class TestImageOptions:
    def test_resize(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "test.png")
            create_test_image(src, width=200, height=100)
            result = run_omnixform(
                "convert",
                src,
                "--to",
                "webp",
                "--overwrite",
                "--width",
                "50",
                "--height",
                "50",
            )
            assert result.returncode == 0
            dst = os.path.join(tmp, "test.webp")
            from PIL import Image

            with Image.open(dst) as img:
                assert img.width <= 50
                assert img.height <= 50
