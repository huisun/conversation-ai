"""Memory API tools for the Twilio Agent Connect."""

from typing import Annotated, Any

from tac.context.memory import MemoryClient
from tac.models.session import ConversationSession
from tac.tools.base import InjectedToolArg, TACTool, function_tool


async def retrieve_profile_memory(
    query: str,
    conversation_memory_client: Annotated[MemoryClient, InjectedToolArg],
    profile_id: Annotated[str, InjectedToolArg],
) -> dict[str, Any]:
    """
    Search and retrieve relevant memories for the current profile.

    Performs semantic search across the user's conversation history, observations,
    and stored traits to find contextually relevant information.

    Args:
        query: What to search for in the user's memory (e.g., "preferences about food",
               "previous complaints", "contact information")

    Returns:
        Dictionary containing relevant memories, traits, and metadata
    """
    memory_response = await conversation_memory_client.retrieve_memory(
        profile_id=profile_id,
        query=query,
    )
    return memory_response.model_dump(by_alias=True, exclude_none=True)


def create_memory_tool(
    conversation_memory_client: MemoryClient,
    session: ConversationSession,
    *,
    name: str | None = None,
    description: str | None = None,
) -> TACTool:
    """
    Create memory tool with injected MemoryClient and session context.

    Args:
        conversation_memory_client: MemoryClient instance for retrieving memories
        session: Current session identity with profile and conversation IDs
        name: Tool name exposed to the LLM. Defaults to the function name
            (``"retrieve_profile_memory"``).
        description: Tool description exposed to the LLM. Defaults to the
            function's docstring.

    Returns:
        Configured memory tool

    Example:
        >>> tool = create_memory_tool(
        ...     conversation_memory_client,
        ...     session,
        ...     name="recall_customer_history",
        ...     description="Recall prior preferences and complaints for this customer.",
        ... )
        >>> result = await tool(query="user preferences")
    """
    memory_tool = function_tool(name=name, description=description)(retrieve_profile_memory)

    return memory_tool.configure_injection(
        conversation_memory_client=conversation_memory_client,
        profile_id=session.profile_id,
    )
