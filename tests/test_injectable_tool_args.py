"""Tests for injectable tool arguments pattern."""

from typing import Annotated

import pytest

from tac.tools import InjectedToolArg, function_tool


class MockClient:
    """Mock client for testing injection."""

    def process(self, query: str) -> str:
        return f"Processed: {query}"


def test_injected_tool_arg_basic() -> None:
    """Test that InjectedToolArg parameters are excluded from schema."""

    @function_tool()
    def my_tool(
        user_input: str,
        client: Annotated[MockClient, InjectedToolArg],
    ) -> str:
        """A tool that uses an injected client.

        Args:
            user_input: The user's input query
        """
        return client.process(user_input)

    # Check that only user_input is in the schema
    assert "user_input" in my_tool.params_json_schema["properties"]
    assert "client" not in my_tool.params_json_schema["properties"]

    # Check that user_input is required
    assert "user_input" in my_tool.params_json_schema["required"]


@pytest.mark.asyncio
async def test_injected_tool_arg_execution() -> None:
    """Test that injected arguments work correctly at runtime."""

    @function_tool()
    async def my_tool(
        user_input: str,
        client: Annotated[MockClient, InjectedToolArg],
    ) -> str:
        """A tool that uses an injected client."""
        return client.process(user_input)

    # Configure injection
    mock_client = MockClient()
    my_tool.configure_injection(client=mock_client)

    # Call the tool with only the non-injected param
    result = await my_tool(user_input="test query")

    assert result == "Processed: test query"


@pytest.mark.asyncio
async def test_multiple_injected_args() -> None:
    """Test tool with multiple injected arguments."""

    @function_tool()
    async def multi_inject_tool(
        query: str,
        client: Annotated[MockClient, InjectedToolArg],
        config: Annotated[dict, InjectedToolArg],
    ) -> str:
        """Tool with multiple injected dependencies."""
        result = client.process(query)
        return f"{result} with config={config.get('setting')}"

    # Only query should be in schema
    assert list(multi_inject_tool.params_json_schema["properties"].keys()) == ["query"]
    assert multi_inject_tool.params_json_schema["required"] == ["query"]

    # Configure both injections
    mock_client = MockClient()
    mock_config = {"setting": "value"}
    multi_inject_tool.configure_injection(client=mock_client, config=mock_config)

    # Execute
    result = await multi_inject_tool(query="test")
    assert result == "Processed: test with config=value"


def test_implementation_property_clean_signature() -> None:
    """Test that implementation property returns a function with clean signature."""

    @function_tool()
    async def my_tool(
        query: str,
        client: Annotated[MockClient, InjectedToolArg],
    ) -> str:
        """Tool with injected client."""
        return client.process(query)

    # Get clean callable via implementation property
    callable_func = my_tool.implementation

    # Check signature has only non-injected params
    import inspect

    sig = inspect.signature(callable_func)
    assert "query" in sig.parameters
    assert "client" not in sig.parameters


@pytest.mark.asyncio
async def test_sync_tool_with_injection() -> None:
    """Test that sync tools also work with injection."""

    @function_tool()
    def sync_tool(
        query: str,
        client: Annotated[MockClient, InjectedToolArg],
    ) -> str:
        """Sync tool with injection."""
        return client.process(query)

    # Configure and execute
    mock_client = MockClient()
    sync_tool.configure_injection(client=mock_client)

    result = await sync_tool(query="sync test")
    assert result == "Processed: sync test"
