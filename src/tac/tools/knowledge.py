"""Knowledge API tools for the Twilio Agent Connect."""

from typing import Annotated

from tac.context.knowledge import KnowledgeClient
from tac.models.knowledge import KnowledgeChunkResult
from tac.tools.base import InjectedToolArg, TACTool, function_tool


async def search_knowledge(
    query: str,
    knowledge_client: Annotated[KnowledgeClient, InjectedToolArg],
    knowledge_base_id: Annotated[str, InjectedToolArg],
    top_k: Annotated[int, InjectedToolArg],
) -> list[KnowledgeChunkResult]:
    """
    Search the knowledge base with the given query.

    Args:
        query: The search query string (max 2048 characters)
        knowledge_client: KnowledgeClient instance for API calls (injected, not visible to LLM)
        knowledge_base_id: Knowledge base ID to search (injected, not visible to LLM)
        top_k: Number of chunks to return (injected, not visible to LLM)

    Returns:
        List of KnowledgeChunkResult objects with content, knowledge_id, created_at, and score
    """
    return await knowledge_client.search_knowledge_base(
        knowledge_base_id=knowledge_base_id,
        query=query,
        top_k=top_k,
    )


async def create_knowledge_tool(
    knowledge_client: KnowledgeClient,
    knowledge_base_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    top_k: int = 5,
) -> TACTool:
    """
    Create a knowledge search tool for the given knowledge base.

    Creates a function tool that searches the specified knowledge using Twilio's
    Knowledge Base Search API via KnowledgeClient. The tool uses dependency injection
    to hide the knowledge client and knowledge ID from the LLM schema.

    If both ``name`` and ``description`` are provided, uses them directly (no API call).
    If either is missing, fetches the knowledge base metadata to derive defaults.

    Args:
        knowledge_client: KnowledgeClient instance for searching knowledge bases
        knowledge_base_id: Knowledge base ID string (e.g., "know_knowledgebase_...")
        name: Tool name exposed to the LLM. Defaults to ``search_<kb_display_name>``
            (fetched from the knowledge base if unset).
        description: Tool description exposed to the LLM. Defaults to the knowledge
            base's ``description`` field (fetched if unset).
        top_k: Number of knowledge chunks to return per query. Defaults to 5.

    Returns:
        A configured TACTool that searches the specified knowledge with injected dependencies

    Example with custom name and description (no API call):
        >>> tool = await create_knowledge_tool(
        ...     knowledge_client=tac.knowledge_client,
        ...     knowledge_base_id="know_knowledgebase_...",
        ...     name="search_promotions",
        ...     description="Search for promotions and discounts",
        ...     top_k=3,
        ... )

    Example using KB metadata as defaults (fetches KB):
        >>> tool = await create_knowledge_tool(
        ...     knowledge_client=tac.knowledge_client,
        ...     knowledge_base_id="know_knowledgebase_...",
        ...     top_k=3,
        ... )
    """
    if name and description:
        tool_name = name
        tool_description = description
    else:
        knowledge_base = await knowledge_client.get_knowledge_base(knowledge_base_id)
        tool_name = name or (
            f"search_{knowledge_base.display_name.lower().replace(' ', '_').replace('-', '_')}"
        )
        tool_description = description or (
            f"{knowledge_base.description}\n\nThe input MUST be a question in the form of a string."
        )

    knowledge_tool = function_tool(name=tool_name, description=tool_description)(search_knowledge)

    return knowledge_tool.configure_injection(
        knowledge_client=knowledge_client,
        knowledge_base_id=knowledge_base_id,
        top_k=top_k,
    )
