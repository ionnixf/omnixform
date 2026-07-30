from __future__ import annotations

import importlib.metadata
from typing import Any

from omnixform.adapters.base import BaseAdapter
from omnixform.adapters.images import ImageAdapter
from omnixform.adapters.libreoffice import LibreOfficeAdapter
from omnixform.adapters.multimedia import MultimediaAdapter
from omnixform.adapters.pandoc import PandocAdapter
from omnixform.adapters.structured_data import StructuredDataAdapter
from omnixform.adapters.text import TextAdapter
from omnixform.adapters.vector import VectorAdapter
from omnixform.models import AdapterInfo


class Registry:
    def __init__(self) -> None:
        self._adapters: list[BaseAdapter] = []
        self._register_builtins()
        self._register_entry_points()

    def _register_builtins(self) -> None:
        self.register(ImageAdapter())
        self.register(VectorAdapter())
        self.register(MultimediaAdapter())
        self.register(TextAdapter())
        self.register(StructuredDataAdapter())
        self.register(PandocAdapter())
        self.register(LibreOfficeAdapter())

    def _register_entry_points(self) -> None:
        """Load adapters from entry points (plugins)."""
        try:
            eps = importlib.metadata.entry_points(group="omnixform.adapters")
        except Exception:
            return

        for ep in eps:
            try:
                adapter_class = ep.load()
                if issubclass(adapter_class, BaseAdapter):
                    self.register(adapter_class())
                else:
                    import warnings

                    warnings.warn(f"Entry point {ep.name} does not implement BaseAdapter", stacklevel=2)
            except Exception as e:
                import warnings

                warnings.warn(f"Failed to load adapter from entry point {ep.name}: {e}", stacklevel=2)

    def register(self, adapter: BaseAdapter) -> None:
        # Replace existing adapter with same name if new one has higher priority (lower number)
        for i, existing in enumerate(self._adapters):
            if existing.name == adapter.name:
                if adapter.priority <= existing.priority:
                    self._adapters[i] = adapter
                    self._adapters.sort(key=lambda a: a.priority)
                return
        self._adapters.append(adapter)
        self._adapters.sort(key=lambda a: a.priority)

    def get_all_adapters(self) -> list[BaseAdapter]:
        return list(self._adapters)

    def get_adapter_infos(self) -> list[AdapterInfo]:
        return [a.get_info() for a in self._adapters]

    def select_adapter(
        self,
        source_format: str,
        target_format: str,
        *,
        prefer_external: bool = False,
    ) -> BaseAdapter | None:
        source_format = source_format.lstrip(".").lower()
        target_format = target_format.lstrip(".").lower()

        candidates = [a for a in self._adapters if a.can_convert(source_format, target_format)]
        if not candidates:
            return None

        candidates.sort(
            key=lambda a: (
                0 if a.is_conversion_available(source_format, target_format) else 1,
                a.priority if not prefer_external else -a.priority,
            )
        )
        return candidates[0]

    def get_possible_targets(self, source_format: str) -> list[dict[str, Any]]:
        source_format = source_format.lstrip(".").lower()
        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        for adapter in self._adapters:
            if source_format not in adapter.input_extensions:
                continue
            for out_ext in adapter.output_extensions:
                if out_ext != source_format and out_ext not in seen:
                    seen.add(out_ext)
                    selected = self.select_adapter(source_format, out_ext)
                    if selected is None:
                        continue
                    results.append(
                        {
                            "format": out_ext,
                            "adapter": selected.name,
                            "available": selected.is_conversion_available(source_format, out_ext),
                        }
                    )

        return results


_registry: Registry | None = None


def get_registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = Registry()
    return _registry


def reset_registry() -> None:
    global _registry
    _registry = None
