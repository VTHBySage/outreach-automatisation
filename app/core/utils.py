"""Core utility functions."""

import asyncio
from typing import Coroutine, TypeVar

T = TypeVar("T")


def run_async(coro: Coroutine[None, None, T]) -> T:
    """
    Run an async coroutine from a sync context safely.

    This function is designed for use in Celery tasks where we need to run
    async code from sync task functions. It handles event loop management
    properly to avoid conflicts with any existing event loops.

    Unlike asyncio.run(), this function:
    - Reuses an existing event loop if one is running (in nested contexts)
    - Creates a new event loop only when necessary
    - Is safer for use in threaded environments like Celery workers

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine
    """
    try:
        # Check if there's already a running event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create a new one
        loop = None

    if loop is not None:
        # If we're already in an async context (shouldn't happen in Celery sync tasks,
        # but handle it gracefully), we need to handle it differently
        # For Celery sync tasks, this branch shouldn't be hit normally
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        # Standard case for Celery sync tasks - create a new event loop
        # Using get_event_loop() for broader compatibility
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(coro)
        finally:
            # Clean up pending tasks to avoid warnings
            try:
                _cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass


def _cancel_all_tasks(loop: asyncio.AbstractEventLoop) -> None:
    """Cancel all pending tasks on the event loop."""
    try:
        tasks = asyncio.all_tasks(loop)
    except RuntimeError:
        return

    for task in tasks:
        task.cancel()

    loop.run_until_complete(
        asyncio.gather(*tasks, return_exceptions=True)
    )
