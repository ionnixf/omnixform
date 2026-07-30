"""Integration tests for the optional CairoSVG adapter."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from omnixform.adapters.vector import VectorAdapter
from omnixform.errors import ConversionError


@pytest.mark.integration
def test_svg_to_png_real_conversion_with_unicode_path(tmp_path: Path) -> None:
    adapter = VectorAdapter()
    if not adapter.is_available():
        pytest.skip("CairoSVG not installed")
    source = tmp_path / "вектор с пробелом.svg"
    output = tmp_path / "результат с пробелом.png"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="6">'
        '<rect width="8" height="6" fill="red"/></svg>',
        encoding="utf-8",
    )

    result = adapter.convert(str(source), "png", output_path=str(output))

    assert result == str(output)
    with Image.open(output) as image:
        image.verify()
        assert image.size == (8, 6)


@pytest.mark.integration
def test_svg_external_entity_is_rejected_without_output(tmp_path: Path) -> None:
    adapter = VectorAdapter()
    if not adapter.is_available():
        pytest.skip("CairoSVG not installed")
    secret = tmp_path / "secret.txt"
    secret.write_text("must-not-be-expanded", encoding="utf-8")
    source = tmp_path / "entity.svg"
    output = tmp_path / "entity.png"
    source.write_text(
        '<!DOCTYPE svg [<!ENTITY xxe SYSTEM "secret.txt">]>'
        '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="6">'
        "<text>&xxe;</text></svg>",
        encoding="utf-8",
    )

    with pytest.raises(ConversionError):
        adapter.convert(str(source), "png", output_path=str(output))

    assert not output.exists()
