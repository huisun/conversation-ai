"""
Thread-safe session manager implementation.

Provides concurrent session handling with RLock-based synchronization.
"""

import threading

from .base import SessionManager
from .state import SessionState


class ThreadSafeSessionManager(SessionManager):
    """
    Thread-safe implementation of SessionManager for concurrent session handling.

    This implementation provides:
    - Thread-safe session storage using RLock for concurrent access
    - Task lifecycle management with graceful cancellation
    - SessionState tracking for each conversation

    Tracks active async tasks per session, enabling cancellation when:
    - A new request arrives (cancels previous in-flight task)
    - An interrupt occurs (e.g., voice channel user interrupts mid-response)
    - The session ends (cleanup with graceful task cancellation)
    """

    def __init__(self) -> None:
        """Initialize thread-safe session manager."""
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety

    def get_or_create_session(self, session_id: str) -> SessionState:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionState()
            return self._sessions[session_id]

    def has_session(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def remove_session(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    def get_all_session_ids(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)
