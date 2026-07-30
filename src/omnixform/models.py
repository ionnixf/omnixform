"""Data models for Omnixform."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

EXIT_SUCCESS = 0


class Category(str, Enum):
    """Category of conversion adapters."""

    IMAGE = "image"
    AUDIO_VIDEO = "audio_video"
    TEXT = "text"
    OFFICE = "office"
    STRUCTURED_DATA = "structured_data"
    EXTERNAL_PANDOC = "pandoc"
    EXTERNAL_LIBREOFFICE = "libreoffice"


class DependencyStatus(str, Enum):
    """Availability status of a dependency."""

    AVAILABLE = "available"
    MISSING = "missing"


@dataclass
class DependencyInfo:
    """Information about an external dependency."""

    name: str
    status: DependencyStatus
    version: str | None = None
    install_hint: str = ""
    reason: str = ""


@dataclass
class AdapterInfo:
    """Information about a conversion adapter."""

    name: str
    category: Category
    description: str
    input_extensions: list[str]
    output_extensions: list[str]
    available: bool
    priority: int = 100
    options: dict[str, Any] = field(default_factory=dict)
    unavailability_reason: str = ""


@dataclass
class ConversionResult:
    """Result of a conversion operation."""

    success: bool
    input_path: str
    output_path: str
    source_format: str
    target_format: str
    adapter: str
    duration_ms: float
    warnings: list[str] = field(default_factory=list)
    error_code: int = EXIT_SUCCESS
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "success": self.success,
            "input": self.input_path,
            "output": self.output_path,
            "source_format": self.source_format,
            "target_format": self.target_format,
            "adapter": self.adapter,
            "duration_ms": round(self.duration_ms, 1),
        }
        if self.warnings:
            d["warnings"] = self.warnings
        if not self.success:
            d["error"] = {
                "code": self.error_code,
                "type": self.error_message,
                "message": self.error_message,
            }
        return d
