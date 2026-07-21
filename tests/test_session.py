"""Tests for SessionState."""

import asyncio

import pytest

from tac.session import SessionState

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


class TestSessionState:
    """Test SessionState functionality."""

    def test_initialization(self) -> None:
        """Test SessionState initializes with None stream_task."""
        session = SessionState()

        assert session.stream_task is None

    async def test_stream_task_assignment(self) -> None:
        """Test assigning an asyncio.Task to stream_task."""
        session = SessionState()

        async def dummy_task() -> str:
            await asyncio.sleep(0.01)
            return "completed"

        task = asyncio.create_task(dummy_task())
        session.stream_task = task

        assert session.stream_task == task
        assert isinstance(session.stream_task, asyncio.Task)

        # Clean up
        await task

    async def test_stream_task_lifecycle(self) -> None:
        """Test stream_task lifecycle from creation to completion."""
        session = SessionState()

        async def dummy_stream() -> str:
            await asyncio.sleep(0.01)
            return "done"

        # Create and assign task
        task = asyncio.create_task(dummy_stream())
        session.stream_task = task

        # Task should not be done immediately
        assert not session.stream_task.done()

        # Wait for completion
        result = await session.stream_task

        # Task should be done now
        assert session.stream_task.done()
        assert result == "done"

    async def test_stream_task_cancellation(self) -> None:
        """Test cancelling a stream_task."""
        session = SessionState()

        async def long_running_task() -> None:
            await asyncio.sleep(10)  # Long enough to cancel

        # Create and assign task
        task = asyncio.create_task(long_running_task())
        session.stream_task = task

        # Task should be running
        assert not session.stream_task.done()

        # Cancel the task
        session.stream_task.cancel()

        # Wait for cancellation to propagate
        with pytest.raises(asyncio.CancelledError):
            await session.stream_task

        # Task should be done (cancelled)
        assert session.stream_task.done()
        assert session.stream_task.cancelled()

    async def test_stream_task_replacement(self) -> None:
        """Test replacing an active stream_task with a new one."""
        session = SessionState()

        async def first_task() -> str:
            await asyncio.sleep(10)
            return "first"

        async def second_task() -> str:
            await asyncio.sleep(0.01)
            return "second"

        # Create first task
        task1 = asyncio.create_task(first_task())
        session.stream_task = task1

        # Cancel first task
        if session.stream_task and not session.stream_task.done():
            session.stream_task.cancel()
            try:
                await session.stream_task
            except asyncio.CancelledError:
                pass

        # Replace with second task
        task2 = asyncio.create_task(second_task())
        session.stream_task = task2

        # Second task should complete
        result = await session.stream_task
        assert result == "second"

        # First task should be cancelled
        assert task1.cancelled()

    async def test_stream_task_can_be_none(self) -> None:
        """Test that stream_task can be set back to None."""
        session = SessionState()

        async def dummy_task() -> None:
            await asyncio.sleep(0.01)

        # Assign a task
        task = asyncio.create_task(dummy_task())
        session.stream_task = task
        assert session.stream_task is not None

        # Wait for it to complete
        await task

        # Clear the task
        session.stream_task = None
        assert session.stream_task is None

    async def test_multiple_cancellations_safe(self) -> None:
        """Test that multiple cancellations don't cause issues."""
        session = SessionState()

        async def dummy_task() -> None:
            await asyncio.sleep(10)

        task = asyncio.create_task(dummy_task())
        session.stream_task = task

        # Cancel multiple times
        session.stream_task.cancel()
        session.stream_task.cancel()
        session.stream_task.cancel()

        # Should still handle gracefully
        with pytest.raises(asyncio.CancelledError):
            await session.stream_task

        assert session.stream_task.cancelled()
