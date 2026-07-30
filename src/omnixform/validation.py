from __future__ import annotations

import json
import os

import yaml

from omnixform.detection import detect_format_from_magic
from omnixform.errors import ValidationError
from omnixform.formats import normalize_format


def validate_output(path: str, target_format: str) -> None:
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise ValidationError(path, "Output file is missing or empty")

    target_format = normalize_format(target_format)

    if target_format in ("png", "jpeg", "webp", "bmp", "tiff", "avif", "heic", "jxl"):
        _validate_image(path)
    elif target_format in ("json",):
        _validate_json(path)
    elif target_format in ("yaml",):
        _validate_yaml(path)
    elif target_format in ("csv", "tsv"):
        _validate_csv_tsv(path)
    elif target_format in ("html",):
        _validate_html(path)
    elif target_format in ("pdf",) and detect_format_from_magic(path) != "pdf":
        raise ValidationError(path, "Output is not a valid PDF file")
    elif target_format in ("docx", "odt", "pptx", "odp", "xlsx", "ods", "epub") and (
        detect_format_from_magic(path) != "zip"
    ):
        raise ValidationError(path, f"Output is not a valid {target_format.upper()} file")


def _validate_image(path: str) -> None:
    try:
        from PIL import Image

        with Image.open(path) as img:
            img.verify()
    except ImportError:
        pass
    except Exception as e:
        raise ValidationError(path, f"Image validation failed: {e}") from e


def _validate_json(path: str) -> None:
    try:
        with open(path, encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(path, f"Invalid JSON: {e}") from e


def _validate_yaml(path: str) -> None:
    try:
        with open(path, encoding="utf-8") as f:
            yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValidationError(path, f"Invalid YAML: {e}") from e


def _validate_csv_tsv(path: str) -> None:
    import csv

    try:
        with open(path, encoding="utf-8", newline="") as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            rows = list(csv.reader(f, dialect))
            if not rows:
                raise ValidationError(path, "CSV/TSV file is empty")
    except csv.Error as e:
        raise ValidationError(path, f"CSV/TSV parsing failed: {e}") from e


def _validate_html(path: str) -> None:
    try:
        with open(path, encoding="utf-8") as f:
            f.read()
    except Exception as e:
        raise ValidationError(path, f"HTML validation failed: {e}") from e
