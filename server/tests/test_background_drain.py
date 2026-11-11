"""A child deadline can detect a blocked loop; an asyncio timeout cannot."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("finish_mode", ["result", "cancel"])
def test_drain_yields_to_queued_completion_callbacks(finish_mode):
    code = f"""
import asyncio
from app.common import async_utils

async def main():
    entered, released = asyncio.Event(), asyncio.Event()

    async def work():
        entered.set()
        await released.wait()
        if {finish_mode!r} == 'cancel':
            raise asyncio.CancelledError

    async_utils.fire_and_forget(work())
    await entered.wait()
    # Ready order: work completes, then drain starts, then discard callback.
    # A synchronous gather(done task) must not starve that callback.
    released.set()
    await async_utils.drain_background_tasks()
    assert not async_utils._background_tasks

asyncio.run(main())
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "STREMHU_LOAD_DOTENV": "false"},
        capture_output=True, text=True, timeout=3,
    )
    assert result.returncode == 0, "Synthetic background drain did not complete"
