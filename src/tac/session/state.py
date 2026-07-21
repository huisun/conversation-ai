"""
Session management utilities for agents
"""

import asyncio

from tac.core.logging import get_logger

# Timeout for task cancellation (seconds)
TASK_CANCELLATION_TIMEOUT = 5.0

logger = get_logger(__name__)


class SessionState:
    """
    Manages session state for voice conversations with streaming task tracking.

    Tracks the active streaming task to enable cancellation when:
    - A new prompt arrives (cancel previous incomplete response)
    - An interrupt occurs (user speaks over the agent)
    - The session ends (cleanup)
    """

    def __init__(self) -> None:
        self.stream_task: asyncio.Task | None = None  # Track active streaming task for cancellation

    async def cancel_stream_task(self) -> None:
        """
        Cancel an in-flight streaming task with timeout protection.
        """
        if self.stream_task and not self.stream_task.done():
            logger.debug("Cancelling streaming task")
            self.stream_task.cancel()
            try:
                await asyncio.wait_for(self.stream_task, timeout=TASK_CANCELLATION_TIMEOUT)
            except asyncio.TimeoutError:
                logger.error(
                    "Task cancellation timed out. "
                    "The stream generator is not handling cancellation properly."
                )
            except asyncio.CancelledError:
                logger.debug("Streaming task cancelled successfully")
            except Exception as e:
                # Catch any other unexpected exceptions from the task
                logger.warning(
                    f"Task raised unexpected exception during cancellation: {type(e).__name__}"
                )
