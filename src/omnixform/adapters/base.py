from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from omnixform.models import AdapterInfo, Category


class BaseAdapter(ABC):
    name: str = ""
    category: Category = Category.TEXT
    description: str = ""
    input_extensions: list[str] = []
    output_extensions: list[str] = []
    priority: int = 100
    options: dict[str, Any] = {}

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def convert(
        self,
        input_path: str,
        target_format: str,
        *,
        output_path: str = "",
        options: dict[str, Any] | None = None,
    ) -> str: ...

    def get_info(self) -> AdapterInfo:
        available = self.is_available()
        return AdapterInfo(
            name=self.name,
            category=self.category,
            description=self.description,
            input_extensions=self.input_extensions,
            output_extensions=self.output_extensions,
            available=available,
            priority=self.priority,
            options=self.options,
            unavailability_reason="" if available else "Missing dependency",
        )

    def can_convert(self, source_ext: str, target_ext: str) -> bool:
        return (
            source_ext.lstrip(".").lower() in self.input_extensions
            and target_ext.lstrip(".").lower() in self.output_extensions
        )

    def is_conversion_available(self, source_ext: str, target_ext: str) -> bool:
        """Return whether this specific conversion can run in this environment."""
        return self.can_convert(source_ext, target_ext) and self.is_available()


__all__ = ["BaseAdapter"]
