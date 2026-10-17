import asyncio
from collections.abc import Coroutine
from typing import Any

_background_tasks: set[asyncio.Task[Any]] = set()


def fire_and_forget(coroutine: Coroutine[Any, Any, Any]) -> None:
    """
    Elindít egy coroutine-t a háttérben (fire-and-forget).
    Megóvja a Task objektumot attól, hogy a Python Garbage Collector
    megsemmisítse futás közben, ha senki sem várja meg (await) az eredményét.
    """
    task = asyncio.create_task(coroutine)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
