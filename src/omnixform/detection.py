from __future__ import annotations

import mimetypes
import os

from omnixform.config import MAGIC_SIGNATURES

_EXTENSION_ALIASES = {
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "tif": "tiff",
    "tiff": "tiff",
    "htm": "html",
    "html": "html",
    "yml": "yaml",
    "yaml": "yaml",
}

_IMAGE_MAGIC_FORMATS = {
    "tiff_le": "tiff",
    "tiff_be": "tiff",
    "jpg": "jpeg",
    "jpeg": "jpeg",
}


def guess_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def get_extension(path: str) -> str:
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    return _EXTENSION_ALIASES.get(ext, ext)


def read_magic_bytes(path: str, n: int = 16) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except (OSError, FileNotFoundError):
        return None


def detect_format_from_magic(path: str) -> str | None:
    magic = read_magic_bytes(path)
    if magic is None:
        return None

    if len(magic) >= 12 and magic[:4] == b"RIFF" and magic[8:12] == b"WEBP":
        return "webp"

    for fmt, sig in MAGIC_SIGNATURES.items():
        if fmt == "webp":
            continue
        if magic.startswith(sig):
            return _IMAGE_MAGIC_FORMATS.get(fmt, fmt)

    return None


def detect_type(path: str) -> str:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")

    ext = get_extension(path)
    magic_format = detect_format_from_magic(path)
    if magic_format and magic_format != "zip":
        return magic_format
    return ext or magic_format or ""


def detect_format(path_or_ext: str) -> str:
    if os.path.isfile(path_or_ext):
        return detect_type(path_or_ext)
    # If it's not a file but looks like a path (contains path separators), it's a missing file
    if os.path.sep in path_or_ext or (os.path.altsep and os.path.altsep in path_or_ext):
        raise FileNotFoundError(f"File not found: {path_or_ext}")
    return get_extension(path_or_ext)


__all__ = [
    "guess_mime",
    "get_extension",
    "read_magic_bytes",
    "detect_format_from_magic",
    "detect_type",
    "detect_format",
]
