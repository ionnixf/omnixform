"""Regression tests for external process execution."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest

from omnixform.errors import TimeoutError_
from omnixform.subprocesses import run_subprocess, run_subprocess_sync


def test_sync_subprocess_captures_output() -> None:
    result = run_subprocess_sync(
        [sys.executable, "-c", "print('ok')"],
        timeout=2,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == [b"ok"]
    assert result.stderr == b""


def test_sync_subprocess_timeout_is_enforced() -> None:
    started = time.monotonic()

    with pytest.raises(TimeoutError_):
        run_subprocess_sync(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            timeout=0.1,
        )

    assert time.monotonic() - started < 2


def test_async_subprocess_timeout_is_enforced() -> None:
    async def run() -> None:
        with pytest.raises(TimeoutError_):
            await run_subprocess(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                timeout=0.1,
            )

    asyncio.run(run())


def test_async_subprocess_cancellation_reaps_process() -> None:
    async def run() -> None:
        task = asyncio.create_task(
            run_subprocess(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                timeout=10,
            )
        )
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    started = time.monotonic()
    asyncio.run(run())
    assert time.monotonic() - started < 2


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group behavior")
def test_sync_timeout_kills_spawned_child(tmp_path: Path) -> None:
    marker = tmp_path / "child-survived"
    child_code = f"import pathlib,time;time.sleep(0.5);pathlib.Path({str(marker)!r}).write_text('survived')"
    parent_code = (
        f"import subprocess,sys,time;subprocess.Popen([sys.executable, '-c', {child_code!r}]);time.sleep(5)"
    )

    with pytest.raises(TimeoutError_):
        run_subprocess_sync([sys.executable, "-c", parent_code], timeout=0.1)

    time.sleep(0.7)
    assert not marker.exists()
