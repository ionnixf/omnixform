"""Regression tests for external process execution."""

from __future__ import annotations

import asyncio
import sys
import time

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
