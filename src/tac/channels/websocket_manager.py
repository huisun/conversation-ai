"""
WebSocket connection management for voice channels.

Provides WebSocket connection tracking for concurrent conversations,
enabling proper response routing in multi-connection scenarios.
"""

from tac.channels.websocket_protocol import WebSocketProtocol


class WebSocketManager:
    """
    Manager for WebSocket connections per conversation.

    Manages the mapping between conversation IDs and their associated WebSocket
    connections, enabling proper response routing when multiple calls are active
    simultaneously.

    This manager is separate from SessionManager (which handles LLM streaming tasks)
    to maintain clean separation of concerns:
    - WebSocketManager: Connection routing and lifecycle
    - SessionManager: LLM streaming and task cancellation

    Thread safety: No locking needed because each conversation operates on different
    dict keys, and Python's dict operations are atomic for simple get/set/delete.

    Example:
        >>> ws_manager = WebSocketManager()
        >>> ws_manager.add_websocket("conv_123", websocket)
        >>> ws = ws_manager.get_websocket("conv_123")
        >>> await ws.send_text("Hello")
        >>> ws_manager.remove_websocket("conv_123")
    """

    def __init__(self) -> None:
        """Initialize WebSocket manager."""
        self._websockets: dict[str, WebSocketProtocol] = {}

    def add_websocket(self, conversation_id: str, websocket: WebSocketProtocol) -> None:
        """
        Store WebSocket connection for a conversation.

        Args:
            conversation_id: Unique conversation identifier
            websocket: WebSocket connection satisfying WebSocketProtocol
        """
        self._websockets[conversation_id] = websocket

    def get_websocket(self, conversation_id: str) -> WebSocketProtocol | None:
        """
        Retrieve WebSocket connection for a conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            WebSocket connection if exists, None otherwise
        """
        return self._websockets.get(conversation_id)

    def has_websocket(self, conversation_id: str) -> bool:
        """
        Check if WebSocket exists for a conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if WebSocket connection exists, False otherwise
        """
        return conversation_id in self._websockets

    def remove_websocket(self, conversation_id: str) -> None:
        """
        Remove WebSocket connection for a conversation.

        Args:
            conversation_id: Unique conversation identifier
        """
        self._websockets.pop(conversation_id, None)

    def get_all_conversation_ids(self) -> list[str]:
        """
        Get list of all active conversation IDs.

        Returns:
            List of conversation IDs with active WebSocket connections
        """
        return list(self._websockets.keys())

    def __len__(self) -> int:
        """
        Get count of active WebSocket connections.

        Returns:
            Number of active connections
        """
        return len(self._websockets)
