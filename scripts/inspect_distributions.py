"""Inspect release archives without extracting untrusted paths."""

from __future__ import annotations

import argparse
import re
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

LEGACY_NAME = "file" + "forge"
FORBIDDEN_PATH_PARTS = {
    ".env",
    ".git",
    "__pycache__",
    "build",
    LEGACY_NAME,
    f"{LEGACY_NAME}_cli",
    "pictures",
}


def _unsafe_archive_name(name: str) -> str | None:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    lowered_parts = {part.casefold() for part in path.parts}

    if path.is_absolute() or ".." in path.parts:
        return "absolute or traversing archive path"
    forbidden = sorted(lowered_parts & FORBIDDEN_PATH_PARTS)
    if forbidden:
        return f"forbidden path component: {', '.join(forbidden)}"
    if LEGACY_NAME in normalized.casefold():
        return "stale internal project name"
    return None


def _metadata_value(data: str, field: str) -> str | None:
    match = re.search(rf"^{re.escape(field)}:\s*(.+)$", data, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _contains_legacy_branding(data: bytes) -> bool:
    return LEGACY_NAME.encode("ascii") in data.lower()


def inspect_wheel(path: Path, expected_version: str) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name in names:
            if problem := _unsafe_archive_name(name):
                errors.append(f"{path.name}: {name!r}: {problem}")
            if _contains_legacy_branding(archive.read(name)):
                errors.append(f"{path.name}: {name!r}: stale internal project name in content")

        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            errors.append(f"{path.name}: expected one METADATA file, found {len(metadata_names)}")
        else:
            metadata = archive.read(metadata_names[0]).decode("utf-8")
            if _metadata_value(metadata, "Name") != "omnixform":
                errors.append(f"{path.name}: distribution name is not omnixform")
            if _metadata_value(metadata, "Version") != expected_version:
                errors.append(f"{path.name}: version is not {expected_version}")

        if not any(name.startswith("omnixform/") for name in names):
            errors.append(f"{path.name}: omnixform package is missing")
    return errors


def inspect_sdist(path: Path, expected_version: str) -> list[str]:
    errors: list[str] = []
    with tarfile.open(path, mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if problem := _unsafe_archive_name(member.name):
                errors.append(f"{path.name}: {member.name!r}: {problem}")
            if member.isfile():
                extracted_member = archive.extractfile(member)
                if extracted_member is not None and _contains_legacy_branding(extracted_member.read()):
                    errors.append(f"{path.name}: {member.name!r}: stale internal project name in content")

        pkg_info_members = [
            member
            for member in members
            if PurePosixPath(member.name).name == "PKG-INFO" and len(PurePosixPath(member.name).parts) == 2
        ]
        if len(pkg_info_members) != 1:
            errors.append(f"{path.name}: expected one top-level PKG-INFO, found {len(pkg_info_members)}")
        else:
            extracted = archive.extractfile(pkg_info_members[0])
            if extracted is None:
                errors.append(f"{path.name}: PKG-INFO is unreadable")
            else:
                metadata = extracted.read().decode("utf-8")
                if _metadata_value(metadata, "Name") != "omnixform":
                    errors.append(f"{path.name}: distribution name is not omnixform")
                if _metadata_value(metadata, "Version") != expected_version:
                    errors.append(f"{path.name}: version is not {expected_version}")

        package_suffix = "/src/omnixform/__init__.py"
        if not any(member.name.endswith(package_suffix) for member in members):
            errors.append(f"{path.name}: omnixform package is missing")
    return errors


def inspect_dist_directory(dist: Path, expected_version: str) -> list[str]:
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    errors: list[str] = []
    if len(wheels) != 1:
        errors.append(f"expected one wheel in {dist}, found {len(wheels)}")
    if len(sdists) != 1:
        errors.append(f"expected one sdist in {dist}, found {len(sdists)}")
    if len(wheels) == 1:
        errors.extend(inspect_wheel(wheels[0], expected_version))
    if len(sdists) == 1:
        errors.extend(inspect_sdist(sdists[0], expected_version))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()

    errors = inspect_dist_directory(args.dist.resolve(), args.expected_version)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Distribution inspection passed for omnixform {args.expected_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
