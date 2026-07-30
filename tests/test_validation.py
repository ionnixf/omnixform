"""Output validation regression tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnixform.errors import ValidationError
from omnixform.validation import validate_output


@pytest.mark.parametrize("target_format", ["avif", "heic", "jxl"])
def test_optional_image_output_must_be_decodable(
    tmp_path: Path,
    target_format: str,
) -> None:
    output = tmp_path / f"broken.{target_format}"
    output.write_bytes(b"not an image")

    with pytest.raises(ValidationError):
        validate_output(str(output), target_format)


@pytest.mark.parametrize("target_format", ["odt", "odp", "ods", "epub"])
def test_zip_container_output_requires_zip_signature(
    tmp_path: Path,
    target_format: str,
) -> None:
    output = tmp_path / f"broken.{target_format}"
    output.write_bytes(b"not a zip container")

    with pytest.raises(ValidationError):
        validate_output(str(output), target_format)
