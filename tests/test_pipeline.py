"""Regression tests for staging and plugin failure containment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from omnixform.adapters.base import BaseAdapter
from omnixform.cli import _convert_single
from omnixform.errors import EXIT_CONVERSION_ERROR, EXIT_VALIDATION_ERROR
from omnixform.models import Category


class _Registry:
    def __init__(self, adapter: BaseAdapter) -> None:
        self.adapter = adapter

    def select_adapter(self, source_format: str, target_format: str) -> BaseAdapter:
        return self.adapter


class _InvalidJsonAdapter(BaseAdapter):
    name = "invalid-json"
    category = Category.STRUCTURED_DATA
    input_extensions = ["png"]
    output_extensions = ["json"]

    def is_available(self) -> bool:
        return True

    def convert(
        self,
        input_path: str,
        target_format: str,
        *,
        output_path: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        Path(output_path).write_text("not valid json")
        return output_path


class _CrashingPluginAdapter(_InvalidJsonAdapter):
    name = "crashing-plugin"

    def convert(
        self,
        input_path: str,
        target_format: str,
        *,
        output_path: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        Path(output_path).write_text("partial")
        raise RuntimeError("plugin exploded")


class _InterruptedPluginAdapter(_InvalidJsonAdapter):
    name = "interrupted-plugin"

    def convert(
        self,
        input_path: str,
        target_format: str,
        *,
        output_path: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        Path(output_path).write_text("partial")
        raise KeyboardInterrupt


def _source_image(path: Path) -> None:
    Image.new("RGB", (2, 2), "red").save(path)


def test_validation_failure_preserves_existing_output(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.png"
    output = tmp_path / "output.json"
    _source_image(source)
    output.write_text('{"original": true}\n')
    monkeypatch.setattr("omnixform.cli.get_registry", lambda: _Registry(_InvalidJsonAdapter()))

    result, _ = _convert_single(
        str(source),
        "json",
        str(output),
        None,
        True,
        False,
        {},
        False,
        True,
    )

    assert result["success"] is False
    assert result["error"]["code"] == EXIT_VALIDATION_ERROR
    assert output.read_text() == '{"original": true}\n'
    assert not list(tmp_path.glob(".omnixform_*"))


def test_plugin_exception_is_contained_and_partial_output_is_removed(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.png"
    output = tmp_path / "output.json"
    _source_image(source)
    monkeypatch.setattr("omnixform.cli.get_registry", lambda: _Registry(_CrashingPluginAdapter()))

    result, _ = _convert_single(
        str(source),
        "json",
        str(output),
        None,
        False,
        False,
        {},
        False,
        True,
    )

    assert result["success"] is False
    assert result["error"]["code"] == EXIT_CONVERSION_ERROR
    assert "plugin exploded" in result["error"]["message"]
    assert not output.exists()
    assert not list(tmp_path.glob(".omnixform_*"))


def test_interruption_removes_partial_output(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.png"
    output = tmp_path / "output.json"
    _source_image(source)
    monkeypatch.setattr("omnixform.cli.get_registry", lambda: _Registry(_InterruptedPluginAdapter()))

    with pytest.raises(KeyboardInterrupt):
        _convert_single(
            str(source),
            "json",
            str(output),
            None,
            False,
            False,
            {},
            False,
            True,
        )

    assert not output.exists()
    assert not list(tmp_path.glob(".omnixform_*"))
