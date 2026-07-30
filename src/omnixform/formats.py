"""Format normalization utilities."""

from __future__ import annotations

import re

# Format normalization map: maps aliases to canonical names
_FORMAT_NORMALIZE: dict[str, str] = {
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "tif": "tiff",
    "tiff": "tiff",
    "htm": "html",
    "html": "html",
    "yml": "yaml",
    "yaml": "yaml",
}
_FORMAT_NAME = re.compile(r"[a-z0-9][a-z0-9+_-]*\Z")


def normalize_format(fmt: str) -> str:
    """Normalize a format name to its canonical form.

    Handles equivalent extensions like jpg/jpeg, tif/tiff, htm/html, yml/yaml.
    """
    fmt = fmt.lstrip(".").lower().strip()
    return _FORMAT_NORMALIZE.get(fmt, fmt)


def is_valid_format_name(fmt: str) -> bool:
    """Return whether a normalized format is safe to use as a file suffix."""
    return _FORMAT_NAME.fullmatch(fmt) is not None


__all__ = ["is_valid_format_name", "normalize_format"]
