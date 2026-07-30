"""Tests for the image conversion adapter."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

from omnixform.adapters.images import ImageAdapter

from .fixtures import TempDir, create_test_image


class TestImageAdapter:
    def setup_method(self) -> None:
        self.adapter = ImageAdapter()

    def test_available(self) -> None:
        assert self.adapter.is_available()

    def test_png_to_webp(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "input.png")
            create_test_image(src)
            dst = self.adapter.convert(src, "webp", output_path=os.path.join(tmp, "output.webp"))
            assert os.path.isfile(dst)
            assert os.path.getsize(dst) > 0

    def test_jpeg_to_png(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "input.jpg")
            create_test_image(src)
            dst = self.adapter.convert(src, "png", output_path=os.path.join(tmp, "output.png"))
            assert os.path.isfile(dst)

    def test_png_alpha_to_jpeg(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "alpha.png")
            create_test_image(src, with_alpha=True)
            dst = self.adapter.convert(
                src,
                "jpeg",
                output_path=os.path.join(tmp, "output.jpg"),
                options={"background": "white"},
            )
            assert os.path.isfile(dst)

    def test_auto_output_path(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "input.png")
            create_test_image(src)
            dst = self.adapter.convert(src, "webp")
            assert dst == os.path.join(tmp, "input.webp")
            assert os.path.isfile(dst)

    def test_unsupported_format(self) -> None:
        from omnixform.errors import UnsupportedFormatError

        with TempDir() as tmp:
            src = os.path.join(tmp, "input.png")
            create_test_image(src)
            with pytest.raises(UnsupportedFormatError):
                self.adapter.convert(src, "docx")

    def test_corrupt_input(self) -> None:
        from omnixform.errors import CorruptInputError

        with TempDir() as tmp:
            src = os.path.join(tmp, "bad.png")
            with open(src, "wb") as f:
                f.write(b"not an image")
            with pytest.raises(CorruptInputError):
                self.adapter.convert(src, "webp")

    def test_resize(self) -> None:
        from PIL import Image

        with TempDir() as tmp:
            src = os.path.join(tmp, "input.png")
            create_test_image(src, width=200, height=100)
            dst = self.adapter.convert(
                src,
                "png",
                output_path=os.path.join(tmp, "output.png"),
                options={"width": 50, "height": 50, "keep_aspect": True},
            )
            with Image.open(dst) as img:
                assert img.width <= 50
                assert img.height <= 50

    def test_quality_option(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "input.png")
            create_test_image(src)
            dst = self.adapter.convert(
                src,
                "jpeg",
                output_path=os.path.join(tmp, "output.jpg"),
                options={"quality": 50},
            )
            assert os.path.isfile(dst)

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("target_format", "dependency", "pillow_format"),
        [
            ("avif", "pillow_avif", "AVIF"),
            ("heic", "pillow_heif", "HEIF"),
            ("jxl", "pillow_jxl", "JXL"),
        ],
    )
    def test_optional_image_formats_round_trip(
        self,
        tmp_path: Path,
        target_format: str,
        dependency: str,
        pillow_format: str,
    ) -> None:
        pytest.importorskip(dependency)
        source = tmp_path / "исходник with spaces.png"
        destination = tmp_path / f"результат #.{target_format}"
        create_test_image(str(source))

        result = self.adapter.convert(
            str(source),
            target_format,
            output_path=str(destination),
        )

        assert result == str(destination)
        with Image.open(destination) as image:
            image.load()
            assert image.format == pillow_format
            assert image.size == (100, 100)


class TestTextAdapter:
    def setup_method(self) -> None:
        from omnixform.adapters.text import TextAdapter

        self.adapter = TextAdapter()

    def test_md_to_html(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "doc.md")
            with open(src, "w") as f:
                f.write("# Hello\n\n**world**")
            dst = self.adapter.convert(src, "html", output_path=os.path.join(tmp, "doc.html"))
            assert os.path.isfile(dst)
            with open(dst) as f:
                content = f.read()
            assert "<h1>" in content or "<strong>" in content

    def test_html_to_txt(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "doc.html")
            with open(src, "w") as f:
                f.write("<html><body><h1>Title</h1><p>Content</p></body></html>")
            dst = self.adapter.convert(src, "txt", output_path=os.path.join(tmp, "doc.txt"))
            assert os.path.isfile(dst)
            with open(dst) as f:
                content = f.read()
            assert "Title" in content
            assert "Content" in content

    def test_txt_to_md(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "doc.txt")
            with open(src, "w") as f:
                f.write("Plain text")
            dst = self.adapter.convert(src, "md", output_path=os.path.join(tmp, "doc.md"))
            assert os.path.isfile(dst)

    def test_available(self) -> None:
        assert self.adapter.is_available()


class TestStructuredDataAdapter:
    def setup_method(self) -> None:
        from omnixform.adapters.structured_data import StructuredDataAdapter

        self.adapter = StructuredDataAdapter()

    def test_json_to_yaml(self) -> None:
        import json

        with TempDir() as tmp:
            src = os.path.join(tmp, "data.json")
            with open(src, "w") as f:
                json.dump({"key": "value", "num": 42}, f)
            dst = self.adapter.convert(src, "yaml", output_path=os.path.join(tmp, "data.yaml"))
            assert os.path.isfile(dst)
            with open(dst) as f:
                content = f.read()
            assert "key" in content

    def test_yaml_to_json(self) -> None:
        import yaml

        with TempDir() as tmp:
            src = os.path.join(tmp, "data.yaml")
            with open(src, "w") as f:
                yaml.dump({"key": "value"}, f)
            dst = self.adapter.convert(src, "json", output_path=os.path.join(tmp, "data.json"))
            assert os.path.isfile(dst)

    def test_csv_to_json(self) -> None:
        with TempDir() as tmp:
            src = os.path.join(tmp, "data.csv")
            with open(src, "w", newline="") as f:
                import csv

                w = csv.writer(f)
                w.writerow(["name", "age"])
                w.writerow(["Alice", 30])
            dst = self.adapter.convert(src, "json", output_path=os.path.join(tmp, "data.json"))
            assert os.path.isfile(dst)

    def test_json_array_to_csv(self) -> None:
        import json

        with TempDir() as tmp:
            src = os.path.join(tmp, "data.json")
            data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
            with open(src, "w") as f:
                json.dump(data, f)
            dst = self.adapter.convert(src, "csv", output_path=os.path.join(tmp, "data.csv"))
            assert os.path.isfile(dst)
            with open(dst) as f:
                content = f.read()
            assert "a" in content
            assert "1" in content

    def test_available(self) -> None:
        assert self.adapter.is_available()
