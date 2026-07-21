"""
Abstract base class for session management.

Defines the interface that all session manager implementations must follow.
"""

from abc import ABC, abstractmethod

from .state import SessionState


class SessionManager(ABC):
    """
    Abstract base class for managing session state with task cancellation support.

    Implementations manage session state and track async tasks for graceful
    cancellation. This enables responsive interactions across different channels where:
    - New requests can cancel previous incomplete responses
    - Sessions are properly cleaned up with task cancellation
    - Concurrent sessions are tracked independently

    Example use cases:
    - Voice channels: Track streaming tasks and cancel when user interrupts
    - Chat channels: Track typing indicators or long-running operations
    - Any channel with async operations that need graceful cancellation

    To implement a custom session manager, inherit from this class and implement
    all abstract methods. See ThreadSafeSessionManager for a reference implementation.
    """

    @abstractmethod
    def get_or_create_session(self, session_id: str) -> SessionState:
        """
        Get existing session or create a new one.

        Args:
            session_id: Unique session identifier

        Returns:
            SessionState object for the session
        """
        ...

    @abstractmethod
    def has_session(self, session_id: str) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session exists, False otherwise
        """
        ...

    @abstractmethod
    def remove_session(self, session_id: str) -> None:
        """
        Remove session and clean up resources.

        Args:
            session_id: Unique session identifier
        """
        ...

    @abstractmethod
    def get_all_session_ids(self) -> list[str]:
        """
        Get all active session IDs.

        Returns:
            List of session identifiers
        """
        ...

    @abstractmethod
    def __len__(self) -> int:
        """
        Return number of active sessions.

        Returns:
            Count of active sessions
        """
        ...
