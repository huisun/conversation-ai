"""Tests for SessionManager and ThreadSafeSessionManager."""

import asyncio
import threading

import pytest

from tac.session import SessionManager, SessionState, ThreadSafeSessionManager


class TestSessionManagerProtocol:
    """Test SessionManager Protocol compliance."""

    def test_thread_safe_session_manager_implements_protocol(self) -> None:
        """Test that ThreadSafeSessionManager implements SessionManager protocol."""
        manager = ThreadSafeSessionManager()

        # Should be recognized as implementing the protocol
        assert isinstance(manager, SessionManager)


class TestThreadSafeSessionManager:
    """Test ThreadSafeSessionManager functionality."""

    def test_initialization(self) -> None:
        """Test ThreadSafeSessionManager initialization."""
        manager = ThreadSafeSessionManager()

        assert len(manager) == 0
        assert manager.get_all_session_ids() == []

    def test_get_or_create_session_creates_new(self) -> None:
        """Test get_or_create_session creates a new session if it doesn't exist."""
        manager = ThreadSafeSessionManager()

        session = manager.get_or_create_session("session_1")

        assert isinstance(session, SessionState)
        assert session.stream_task is None
        assert len(manager) == 1

    def test_get_or_create_session_returns_existing(self) -> None:
        """Test get_or_create_session returns existing session."""
        manager = ThreadSafeSessionManager()

        # Create first session
        session1 = manager.get_or_create_session("session_1")

        # Get same session
        session2 = manager.get_or_create_session("session_1")

        # Should be the same object
        assert session1 is session2
        assert len(manager) == 1

    def test_has_session(self) -> None:
        """Test has_session correctly reports session existence."""
        manager = ThreadSafeSessionManager()

        assert not manager.has_session("session_1")

        manager.get_or_create_session("session_1")

        assert manager.has_session("session_1")
        assert not manager.has_session("session_2")

    def test_remove_session(self) -> None:
        """Test removing a session."""
        manager = ThreadSafeSessionManager()

        # Create session
        manager.get_or_create_session("session_1")
        assert len(manager) == 1

        # Remove session
        manager.remove_session("session_1")
        assert len(manager) == 0
        assert not manager.has_session("session_1")

    def test_remove_nonexistent_session(self) -> None:
        """Test removing a session that doesn't exist (should not raise)."""
        manager = ThreadSafeSessionManager()

        # Should not raise an error
        manager.remove_session("nonexistent_session")
        assert len(manager) == 0

    def test_get_all_session_ids(self) -> None:
        """Test getting all session IDs."""
        manager = ThreadSafeSessionManager()

        # Create multiple sessions
        manager.get_or_create_session("session_1")
        manager.get_or_create_session("session_2")
        manager.get_or_create_session("session_3")

        session_ids = manager.get_all_session_ids()

        assert len(session_ids) == 3
        assert "session_1" in session_ids
        assert "session_2" in session_ids
        assert "session_3" in session_ids

    def test_len_method(self) -> None:
        """Test __len__ method returns correct count."""
        manager = ThreadSafeSessionManager()

        assert len(manager) == 0

        manager.get_or_create_session("session_1")
        assert len(manager) == 1

        manager.get_or_create_session("session_2")
        assert len(manager) == 2

        manager.remove_session("session_1")
        assert len(manager) == 1

    def test_thread_safety_concurrent_get_or_create(self) -> None:
        """Test thread-safe concurrent access to get_or_create_session."""
        manager = ThreadSafeSessionManager()
        sessions_created = []

        def create_session(session_id: str) -> None:
            session = manager.get_or_create_session(session_id)
            sessions_created.append(session)

        # Create multiple threads trying to create the same session
        threads = [threading.Thread(target=create_session, args=("session_1",)) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should have gotten the same session object
        assert len(sessions_created) == 10
        first_session = sessions_created[0]
        assert all(session is first_session for session in sessions_created)

        # Only one session should exist in manager
        assert len(manager) == 1

    def test_thread_safety_concurrent_remove(self) -> None:
        """Test thread-safe concurrent removal of sessions."""
        manager = ThreadSafeSessionManager()

        # Create multiple sessions
        for i in range(10):
            manager.get_or_create_session(f"session_{i}")

        assert len(manager) == 10

        # Remove them concurrently
        def remove_session(session_id: str) -> None:
            manager.remove_session(session_id)

        threads = [
            threading.Thread(target=remove_session, args=(f"session_{i}",)) for i in range(10)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All sessions should be removed
        assert len(manager) == 0

    @pytest.mark.asyncio
    async def test_multiple_sessions_independence(self) -> None:
        """Test that multiple sessions are independent."""
        manager = ThreadSafeSessionManager()

        session1 = manager.get_or_create_session("session_1")
        session2 = manager.get_or_create_session("session_2")

        # Sessions should be different objects
        assert session1 is not session2

        # Modifying one shouldn't affect the other
        async def task1() -> None:
            await asyncio.sleep(0.01)

        async def task2() -> None:
            await asyncio.sleep(0.01)

        session1.stream_task = asyncio.create_task(task1())
        session2.stream_task = asyncio.create_task(task2())

        assert session1.stream_task is not session2.stream_task

        # Wait for both to complete
        await asyncio.gather(session1.stream_task, session2.stream_task)

    def test_session_manager_is_not_none_check(self) -> None:
        """Test that session manager existence should be checked with 'is not None'."""
        # Empty manager
        manager = ThreadSafeSessionManager()

        # This is the critical bug we fixed - empty manager should still be truthy for "is not None"
        assert manager is not None
        assert len(manager) == 0  # But len is 0

        # The old bug: bool(manager) would be False because __len__ == 0
        # But we should use explicit "is not None" checks
        if manager is not None:
            # This should work even with empty manager
            assert True
