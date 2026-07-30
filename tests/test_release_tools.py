from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

from scripts.inspect_distributions import (
    _unsafe_archive_name,
    inspect_sdist,
    inspect_wheel,
)
from scripts.release_preflight import validate_release_source


def _write_release_tree(root: Path, *, released: bool = True) -> None:
    package = root / "src" / "omnixform"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    changelog_state = "2026-07-30" if released else "Unreleased"
    (root / "CHANGELOG.md").write_text(
        f"## [0.1.0] - {changelog_state}\n",
        encoding="utf-8",
    )
    notes_status = "Released" if released else "Unreleased"
    (root / "RELEASE_NOTES.md").write_text(
        f"Status: **{notes_status}**\n",
        encoding="utf-8",
    )


def test_release_preflight_accepts_exact_tag_and_finalized_documents(tmp_path: Path) -> None:
    _write_release_tree(tmp_path)

    assert (
        validate_release_source(
            tmp_path,
            expected_version="0.1.0",
            ref_type="tag",
            tag="v0.1.0",
        )
        == []
    )


def test_release_preflight_rejects_branch_version_and_unreleased_docs(tmp_path: Path) -> None:
    _write_release_tree(tmp_path, released=False)

    errors = validate_release_source(
        tmp_path,
        expected_version="9.9.9",
        ref_type="branch",
        tag="main",
    )

    assert len(errors) == 5
    assert any("project version" in error for error in errors)
    assert any("tag ref" in error for error in errors)
    assert any("CHANGELOG" in error for error in errors)
    assert any("Unreleased" in error for error in errors)


def test_archive_path_guard_rejects_traversal_and_stale_names() -> None:
    assert _unsafe_archive_name("../escape") is not None
    assert _unsafe_archive_name("pkg/pictures/input.png") is not None
    assert _unsafe_archive_name(f"pkg/{'file' + 'forge'}_compat.py") is not None
    assert _unsafe_archive_name("omnixform/module.py") is None


def test_wheel_inspection_checks_metadata_and_package(tmp_path: Path) -> None:
    wheel = tmp_path / "omnixform-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, mode="w") as archive:
        archive.writestr("omnixform/__init__.py", '__version__ = "0.1.0"\n')
        archive.writestr(
            "omnixform-0.1.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: omnixform\nVersion: 0.1.0\n",
        )

    assert inspect_wheel(wheel, "0.1.0") == []


def test_wheel_inspection_rejects_legacy_content(tmp_path: Path) -> None:
    wheel = tmp_path / "omnixform-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, mode="w") as archive:
        archive.writestr("omnixform/__init__.py", f'legacy = "{"file" + "forge"}"\n')
        archive.writestr(
            "omnixform-0.1.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: omnixform\nVersion: 0.1.0\n",
        )

    assert any("stale internal project name in content" in error for error in inspect_wheel(wheel, "0.1.0"))


def test_sdist_inspection_checks_metadata_and_package(tmp_path: Path) -> None:
    sdist = tmp_path / "omnixform-0.1.0.tar.gz"
    with tarfile.open(sdist, mode="w:gz") as archive:
        for name, data in (
            (
                "omnixform-0.1.0/PKG-INFO",
                b"Metadata-Version: 2.4\nName: omnixform\nVersion: 0.1.0\n",
            ),
            ("omnixform-0.1.0/src/omnixform/__init__.py", b'__version__ = "0.1.0"\n'),
        ):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))

    assert inspect_sdist(sdist, "0.1.0") == []


def test_publish_workflow_keeps_dispatch_input_out_of_shell_source() -> None:
    workflow = Path(".github/workflows/publish-pypi.yml").read_text(encoding="utf-8")

    assert "RELEASE_VERSION: ${{ inputs.version }}" in workflow
    assert '--expected-version "${{ inputs.version }}"' not in workflow
    assert "environment:\n      name: pypi" in workflow


def test_container_base_is_pinned_consistently() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    base_lines = [line for line in dockerfile.splitlines() if line.startswith("FROM python:")]

    assert len(base_lines) == 2
    assert all("@sha256:" in line for line in base_lines)
    assert base_lines[0].split(" AS ", 1)[0] == base_lines[1].split(" AS ", 1)[0]
