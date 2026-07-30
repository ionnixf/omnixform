"""Tests for path handling."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from omnixform.errors import BadArgumentsError, OutputExistsError
from omnixform.paths import (
    make_staging_path,
    publish_staged_output,
    replace_extension,
    resolve_output_path,
)

from .fixtures import TempDir


class TestReplaceExtension:
    def test_basic(self) -> None:
        assert replace_extension("photo.png", "webp") == "photo.webp"
        assert replace_extension("photo.png", ".webp") == "photo.webp"

    def test_dotfile(self) -> None:
        assert replace_extension(".hidden.png", "webp") == ".hidden.webp"

    def test_no_extension(self) -> None:
        assert replace_extension("photo", "png") == "photo.png"


class TestResolveOutputPath:
    def test_default_derived(self) -> None:
        path, exists = resolve_output_path("/tmp/test.png", "webp")
        assert path == "/tmp/test.webp"
        assert not exists

    def test_output_override(self) -> None:
        path, exists = resolve_output_path("/tmp/test.png", "webp", output="/tmp/out.webp")
        assert path == "/tmp/out.webp"

    def test_output_dir(self) -> None:
        path, exists = resolve_output_path("/tmp/test.png", "webp", output_dir="/other")
        assert path == "/other/test.webp"

    def test_existing_file(self) -> None:
        with TempDir() as tmp:
            path = os.path.join(tmp, "test.png")
            out_path = os.path.join(tmp, "test.jpg")
            # Create input
            with open(path, "w") as f:
                f.write("test")
            # Resolution should see no existing output
            _, exists = resolve_output_path(path, "jpg")
            assert not exists
            # Create the output
            with open(out_path, "w") as f:
                f.write("test")
            # Now it should be detected
            _, exists = resolve_output_path(path, "jpg")
            assert exists

    def test_symlink_alias_of_input_is_rejected(self, tmp_path: Path) -> None:
        source = tmp_path / "source.png"
        alias = tmp_path / "alias.png"
        source.write_bytes(b"input")
        try:
            alias.symlink_to(source)
        except OSError:
            pytest.skip("symlinks are not available")

        with pytest.raises(BadArgumentsError):
            resolve_output_path(str(source), "webp", output=str(alias))


class TestPublishStagedOutput:
    def test_no_overwrite_is_atomic(self, tmp_path: Path) -> None:
        output = tmp_path / "output.txt"
        output.write_text("original")
        staging = Path(make_staging_path(str(output), "txt"))
        staging.write_text("replacement")

        with pytest.raises(OutputExistsError):
            publish_staged_output(str(staging), str(output), overwrite=False)

        assert output.read_text() == "original"
        assert staging.read_text() == "replacement"

    def test_overwrite_replaces_destination(self, tmp_path: Path) -> None:
        output = tmp_path / "output.txt"
        output.write_text("original")
        staging = Path(make_staging_path(str(output), "txt"))
        staging.write_text("replacement")

        publish_staged_output(str(staging), str(output), overwrite=True)

        assert output.read_text() == "replacement"
        assert not staging.exists()
