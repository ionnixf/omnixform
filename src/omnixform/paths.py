from __future__ import annotations

import errno
import os
import shutil
import tempfile

from omnixform.errors import BadArgumentsError, OutputExistsError
from omnixform.formats import is_valid_format_name


def replace_extension(path: str, new_ext: str) -> str:
    new_ext = new_ext.lstrip(".").lower()
    base = os.path.splitext(path)[0]
    return f"{base}.{new_ext}"


def resolve_output_path(
    input_path: str,
    target_format: str,
    *,
    output: str | None = None,
    output_dir: str | None = None,
    overwrite: bool = False,
) -> tuple[str, bool]:
    target_format = target_format.lstrip(".").lower()
    if not is_valid_format_name(target_format):
        raise BadArgumentsError(f"Invalid target format: {target_format!r}")

    if output:
        out = output
    elif output_dir:
        basename = os.path.basename(replace_extension(input_path, target_format))
        out = os.path.join(output_dir, basename)
    else:
        out = replace_extension(input_path, target_format)

    in_abs = os.path.abspath(input_path)
    out_abs = os.path.abspath(out)

    if _paths_refer_to_same_file(in_abs, out_abs):
        raise BadArgumentsError(
            "Input and output paths are the same. Specify a different output path.",
        )

    return out_abs, os.path.exists(out_abs)


def _paths_refer_to_same_file(first: str, second: str) -> bool:
    first_real = os.path.normcase(os.path.realpath(first))
    second_real = os.path.normcase(os.path.realpath(second))
    if first_real == second_real:
        return True
    try:
        return os.path.samefile(first, second)
    except (FileNotFoundError, OSError):
        return False


def make_staging_path(output_path: str, target_format: str) -> str:
    """Create a private same-directory staging file with the target suffix."""
    directory = os.path.dirname(os.path.abspath(output_path)) or "."
    os.makedirs(directory, exist_ok=True)
    suffix = f".{target_format.lstrip('.').lower()}"
    fd, staging_path = tempfile.mkstemp(dir=directory, prefix=".omnixform_", suffix=suffix)
    os.close(fd)
    return staging_path


def publish_staged_output(staging_path: str, output_path: str, *, overwrite: bool) -> None:
    """Atomically publish a staged file, optionally refusing replacement."""
    if overwrite:
        os.replace(staging_path, output_path)
        return

    try:
        os.link(staging_path, output_path)
    except FileExistsError:
        raise OutputExistsError(output_path) from None
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise OutputExistsError(output_path) from None
        raise
    os.unlink(staging_path)


def remove_staging_file(path: str | None) -> None:
    if not path:
        return
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def atomic_write(
    output_path: str,
    *,
    content: bytes | None = None,
    source_path: str | None = None,
) -> None:
    dir_path = os.path.dirname(os.path.abspath(output_path)) or "."
    os.makedirs(dir_path, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=".omnixform_")
    try:
        if content is not None:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
        elif source_path is not None:
            os.close(fd)
            shutil.copy2(source_path, tmp_path)
        else:
            os.close(fd)
            raise ValueError("Either content or source_path must be provided")

        os.replace(tmp_path, output_path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


__all__ = [
    "replace_extension",
    "resolve_output_path",
    "make_staging_path",
    "publish_staged_output",
    "remove_staging_file",
    "atomic_write",
]
