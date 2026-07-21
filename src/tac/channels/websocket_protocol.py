"""
WebSocket protocol abstraction for framework-agnostic channel implementation.

Defines a Protocol class that any WebSocket implementation (FastAPI, Starlette,
custom, etc.) can satisfy, along with a common disconnect error type.
"""

from typing import Any, Protocol, runtime_checkable


class WebSocketDisconnectError(Exception):
    """Raised when a WebSocket connection is unexpectedly closed."""


@runtime_checkable
class WebSocketProtocol(Protocol):
    """Protocol defining the WebSocket interface used by VoiceChannel.

    Any WebSocket implementation that provides these async methods can be used
    with VoiceChannel, including FastAPI WebSocket, raw Starlette WebSocket,
    or custom adapters.
    """

    async def accept(self) -> None: ...

    async def receive_json(self) -> Any: ...

    async def send_text(self, data: str) -> None: ...

    async def close(self) -> None: ...
