import asyncio
import contextvars
import logging
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

_background_tasks: set[asyncio.Task[Any]] = set()
P = ParamSpec("P")
T = TypeVar("T")
logger = logging.getLogger(__name__)


async def await_owned_task(task: asyncio.Future[T]) -> T:
    """A cancelled waiter still joins its real owned work before propagating."""
    cancelled = False
    while True:
        try:
            result = await asyncio.shield(task)
            break
        except asyncio.CancelledError:
            if task.cancelled():
                raise
            cancelled = True
        except Exception as error:
            if cancelled:
                logger.warning("Owned work failed after waiter cancellation: kind=%s", type(error).__name__)
                raise asyncio.CancelledError from None
            raise
    if cancelled:
        raise asyncio.CancelledError
    return result


async def owned_to_thread(function: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    # Keep the actual executor future alive and join its real completion.
    # Context propagation matches asyncio.to_thread without an extra Task.
    loop = asyncio.get_running_loop()
    context = contextvars.copy_context()
    def call() -> T:
        return context.run(function, *args, **kwargs)

    future = loop.run_in_executor(None, call)
    return await await_owned_task(future)


def fire_and_forget(coroutine: Coroutine[Any, Any, Any]) -> None:
    """
    Elindít egy coroutine-t a háttérben (fire-and-forget).
    Megóvja a Task objektumot attól, hogy a Python Garbage Collector
    megsemmisítse futás közben, ha senki sem várja meg (await) az eredményét.
    """
    task = asyncio.create_task(coroutine)
    _background_tasks.add(task)

    def finished(completed: asyncio.Task[Any]) -> None:
        _background_tasks.discard(completed)
        if not completed.cancelled() and (error := completed.exception()) is not None:
            logger.warning("Background work failed: kind=%s", type(error).__name__)

    task.add_done_callback(finished)


async def drain_background_tasks() -> None:
    async def drain() -> None:
        while _background_tasks:
            await asyncio.gather(*tuple(_background_tasks), return_exceptions=True)
            # gather(done tasks) can finish synchronously. Their registered
            # discard/exception callbacks must run before checking the set again.
            if _background_tasks:
                await asyncio.sleep(0)

    await await_owned_task(asyncio.create_task(drain(), name="background-drain"))
