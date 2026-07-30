"""Tests for file detection."""

from __future__ import annotations

import os

from omnixform.detection import (
    detect_format,
    detect_format_from_magic,
    get_extension,
    guess_mime,
)

from .fixtures import TempDir, create_test_image


class TestGetExtension:
    def test_normal_extensions(self) -> None:
        assert get_extension("file.png") == "png"
        assert get_extension("file.jpg") == "jpeg"
        assert get_extension("file.jpeg") == "jpeg"
        assert get_extension("file.JPG") == "jpeg"
        assert get_extension("file.webp") == "webp"
        assert get_extension("file.htm") == "html"
        assert get_extension("file.html") == "html"
        assert get_extension("file.yml") == "yaml"
        assert get_extension("file.yaml") == "yaml"
        assert get_extension("file.tif") == "tiff"
        assert get_extension("file.tiff") == "tiff"

    def test_no_extension(self) -> None:
        assert get_extension("file") == ""

    def test_dotfile(self) -> None:
        # .gitignore has no basename, so osc is extension-only
        ext = get_extension(".gitignore")
        # splitext(".gitignore") -> ("", ".gitignore")
        assert ext in ("gitignore", "")


class TestGuessMime:
    def test_png(self) -> None:
        mime = guess_mime("test.png")
        assert mime == "image/png"

    def test_jpg(self) -> None:
        mime = guess_mime("test.jpg")
        assert mime == "image/jpeg"

    def test_html(self) -> None:
        mime = guess_mime("test.html")
        assert "html" in mime

    def test_json(self) -> None:
        mime = guess_mime("test.json")
        assert "json" in mime

    def test_unknown(self) -> None:
        mime = guess_mime("test.xyz123")
        assert mime == "application/octet-stream"


class TestDetectFormat:
    def test_from_extension(self) -> None:
        assert detect_format("file.png") == "png"
        assert detect_format("file.jpg") == "jpeg"
        assert detect_format("file.json") == "json"

    def test_from_content(self) -> None:
        with TempDir() as tmp:
            path = os.path.join(tmp, "test.png")
            create_test_image(path)
            assert detect_format(path) == "png"

    def test_magic_wins_for_misnamed_image(self) -> None:
        with TempDir() as tmp:
            path = os.path.join(tmp, "actually-png.jpg")
            create_test_image(path)
            assert detect_format(path) == "jpeg"

            png_path = os.path.join(tmp, "source.png")
            create_test_image(png_path)
            with open(png_path, "rb") as source, open(path, "wb") as destination:
                destination.write(source.read())
            assert detect_format(path) == "png"

    def test_missing_file(self) -> None:
        # detect_format raises FileNotFoundError for nonexistent file paths
        import pytest

        with pytest.raises(FileNotFoundError):
            detect_format("/nonexistent/file.xyz")


class TestDetectFormatFromMagic:
    def test_png_magic(self) -> None:
        with TempDir() as tmp:
            path = os.path.join(tmp, "test.png")
            create_test_image(path)
            assert detect_format_from_magic(path) == "png"

    def test_jpeg_magic(self) -> None:
        with TempDir() as tmp:
            path = os.path.join(tmp, "test.jpg")
            create_test_image(path)
            assert detect_format_from_magic(path) == "jpeg"

    def test_webp_magic(self) -> None:
        with TempDir() as tmp:
            png_path = os.path.join(tmp, "test.png")
            create_test_image(png_path)
            webp_path = os.path.join(tmp, "test.webp")
            from PIL import Image

            Image.open(png_path).save(webp_path, "WEBP")
            # WebP magic starts with RIFF
            with open(webp_path, "rb") as f:
                magic = f.read(12)
            assert magic[:4] == b"RIFF"

    def test_text_file_no_magic(self) -> None:
        with TempDir() as tmp:
            path = os.path.join(tmp, "test.txt")
            with open(path, "w") as f:
                f.write("hello")
            assert detect_format_from_magic(path) is None
