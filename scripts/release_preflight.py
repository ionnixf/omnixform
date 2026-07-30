"""Fail closed unless the source tree is ready for a tagged release build."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

VERSION_PATTERN = re.compile(r'__version__\s*=\s*"([^"]+)"')
RELEASED_CHANGELOG_PATTERN = r"^## \[{version}\] - \d{{4}}-\d{{2}}-\d{{2}}$"


def read_project_version(root: Path) -> str:
    version_file = root / "src" / "omnixform" / "__init__.py"
    match = VERSION_PATTERN.search(version_file.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Could not read __version__ from {version_file}")
    return match.group(1)


def validate_release_source(
    root: Path,
    *,
    expected_version: str,
    ref_type: str,
    tag: str,
) -> list[str]:
    errors: list[str] = []
    actual_version = read_project_version(root)
    expected_tag = f"v{expected_version}"

    if actual_version != expected_version:
        errors.append(
            f"workflow version {expected_version!r} does not match project version {actual_version!r}"
        )
    if ref_type != "tag":
        errors.append(f"release workflow must run from a tag ref, got {ref_type!r}")
    if tag != expected_tag:
        errors.append(f"release tag must be {expected_tag!r}, got {tag!r}")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    released_heading = re.compile(
        RELEASED_CHANGELOG_PATTERN.format(version=re.escape(expected_version)),
        flags=re.MULTILINE,
    )
    if released_heading.search(changelog) is None:
        errors.append(f"CHANGELOG.md must contain a dated '## [{expected_version}] - YYYY-MM-DD' heading")

    release_notes = (root / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    if "Status: **Unreleased**" in release_notes:
        errors.append("RELEASE_NOTES.md must not still be marked Unreleased")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--ref-type", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    errors = validate_release_source(
        args.root.resolve(),
        expected_version=args.expected_version,
        ref_type=args.ref_type,
        tag=args.tag,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Release source gate passed for v{args.expected_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
