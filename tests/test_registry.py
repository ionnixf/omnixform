"""Tests for the registry."""

from __future__ import annotations

import pytest

from omnixform.adapters.images import ImageAdapter
from omnixform.adapters.libreoffice import LibreOfficeAdapter
from omnixform.adapters.pandoc import PandocAdapter
from omnixform.registry import get_registry, reset_registry


class TestRegistry:
    def setup_method(self) -> None:
        reset_registry()

    def test_singleton(self) -> None:
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_all_adapters(self) -> None:
        registry = get_registry()
        adapters = registry.get_all_adapters()
        names = [a.name for a in adapters]
        assert "pillow" in names
        assert "ffmpeg" in names
        assert "text" in names
        assert "structured_data" in names
        assert "pandoc" in names
        assert "libreoffice" in names

    def test_select_pillow(self) -> None:
        registry = get_registry()
        adapter = registry.select_adapter("png", "webp")
        assert adapter is not None
        assert adapter.name == "pillow"

    def test_select_ffmpeg(self) -> None:
        registry = get_registry()
        adapter = registry.select_adapter("mp4", "mp3")
        assert adapter is not None
        assert adapter.name == "ffmpeg"

    def test_select_text(self) -> None:
        registry = get_registry()
        adapter = registry.select_adapter("md", "html")
        assert adapter is not None
        assert adapter.name == "text"

    def test_select_structured(self) -> None:
        registry = get_registry()
        adapter = registry.select_adapter("json", "yaml")
        assert adapter is not None
        assert adapter.name == "structured_data"

    def test_unsupported_conversion(self) -> None:
        registry = get_registry()
        adapter = registry.select_adapter("png", "docx")
        assert adapter is None

    def test_possible_targets_png(self) -> None:
        registry = get_registry()
        targets = registry.get_possible_targets("png")
        formats = [t["format"] for t in targets]
        assert "jpeg" in formats
        assert "webp" in formats
        assert "bmp" in formats

    def test_optional_target_availability_is_format_specific(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(ImageAdapter, "_check_avif_support", lambda _self: False)
        registry = get_registry()
        targets = {target["format"]: target for target in registry.get_possible_targets("png")}

        assert targets["webp"]["available"] is True
        assert targets["avif"]["available"] is False

    def test_possible_targets_md(self) -> None:
        registry = get_registry()
        targets = registry.get_possible_targets("md")
        formats = [t["format"] for t in targets]
        assert "html" in formats
        assert "txt" in formats

    def test_possible_target_uses_available_fallback_adapter(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(PandocAdapter, "is_available", lambda _self: False)
        monkeypatch.setattr(LibreOfficeAdapter, "is_available", lambda _self: True)
        registry = get_registry()

        targets = {target["format"]: target for target in registry.get_possible_targets("docx")}

        assert targets["pdf"] == {
            "format": "pdf",
            "adapter": "libreoffice",
            "available": True,
        }

    def test_office_pdf_falls_back_when_pandoc_has_no_pdf_engine(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(PandocAdapter, "is_available", lambda _self: True)
        monkeypatch.setattr(
            PandocAdapter,
            "is_conversion_available",
            lambda _self, _source, target: target != "pdf",
        )
        monkeypatch.setattr(LibreOfficeAdapter, "is_available", lambda _self: True)

        adapter = get_registry().select_adapter("docx", "pdf")

        assert adapter is not None
        assert adapter.name == "libreoffice"
