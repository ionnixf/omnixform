"""Subprocess utilities for calling external commands."""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import subprocess
from collections.abc import Sequence

from omnixform.errors import TimeoutError_


def check_dependency(name: str, *, install_hint: str = "") -> str | None:
    """Check if an external dependency is available.

    Returns the path to the executable, or None if not found.
    """
    path = shutil.which(name)
    if path is None:
        return None
    return path


async def run_subprocess(
    args: Sequence[str],
    *,
    timeout: float = 300,
    input_data: bytes | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    """Run an external command subprocess with timeout.

    Args:
        args: Command arguments as a sequence; no shell is invoked.
        timeout: Maximum execution time in seconds.
        input_data: Optional stdin data.
        capture_output: Whether to capture stdout/stderr.

    Returns:
        subprocess.CompletedProcess instance.

    Raises:
        TimeoutError_: If process exceeds timeout.
    """
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=subprocess.PIPE if input_data is not None else None,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
        start_new_session=os.name == "posix",
    )
    try:
        stdout_data, stderr_data = await asyncio.wait_for(
            proc.communicate(input=input_data),
            timeout=timeout,
        )
    except TimeoutError:
        _kill_process_tree(proc)
        await proc.communicate()
        raise TimeoutError_(" ".join(str(a) for a in args), timeout) from None
    except asyncio.CancelledError:
        _kill_process_tree(proc)
        await proc.communicate()
        raise

    return subprocess.CompletedProcess(
        args=args,
        returncode=proc.returncode or 0,
        stdout=stdout_data or b"",
        stderr=stderr_data or b"",
    )


def run_subprocess_sync(
    args: Sequence[str],
    *,
    timeout: float = 300,
    input_data: bytes | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    """Run a command synchronously without invoking a shell."""
    proc = subprocess.Popen(
        list(args),
        stdin=subprocess.PIPE if input_data is not None else None,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
        start_new_session=os.name == "posix",
    )
    try:
        stdout_data, stderr_data = proc.communicate(input=input_data, timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        proc.communicate()
        raise TimeoutError_(" ".join(str(a) for a in args), timeout) from None
    except BaseException:
        if proc.poll() is None:
            _kill_process_tree(proc)
            proc.communicate()
        raise

    return subprocess.CompletedProcess(
        args=args,
        returncode=proc.returncode or 0,
        stdout=stdout_data or b"",
        stderr=stderr_data or b"",
    )


def _kill_process_tree(proc: asyncio.subprocess.Process | subprocess.Popen[bytes]) -> None:
    if proc.returncode is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
    proc.kill()
