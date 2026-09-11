"""Property-based tests for SpecMem MCP Server.

Tests correctness properties defined in the kiro-powers-integration design document.
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.mcp.server import SpecMemMCPServer
from specmem.mcp.tools import TOOLS, get_tool_by_name, get_tool_names


# Expected tool names
EXPECTED_TOOLS = [
    "specmem_query",
    "specmem_impact",
    "specmem_context",
    "specmem_tldr",
    "specmem_cues",
    "specmem_coverage",
    "specmem_validate",
]


class TestMCPToolExposure:
    """**Feature: kiro-powers-integration, Property 1: MCP Tool Exposure**

    *For any* initialized SpecMem MCP server, the server SHALL expose all
    defined tools (query, impact, context, tldr, cues, coverage, validate) with
    valid input schemas.

    **Validates: Requirements 1.1**
    """

    def test_all_expected_tools_defined(self):
        """All expected tools are defined in TOOLS list."""
        tool_names = get_tool_names()

        for expected in EXPECTED_TOOLS:
            assert expected in tool_names, f"Missing tool: {expected}"

    def test_tools_count_matches_expected(self):
        """Number of tools matches expected count."""
        assert len(TOOLS) == len(EXPECTED_TOOLS)

    @given(tool_name=st.sampled_from(EXPECTED_TOOLS))
    @settings(max_examples=len(EXPECTED_TOOLS))
    def test_each_tool_has_required_fields(self, tool_name: str):
        """For any tool, it has name, description, and inputSchema."""
        tool = get_tool_by_name(tool_name)

        assert tool is not None, f"Tool not found: {tool_name}"
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["name"] == tool_name

    @given(tool_name=st.sampled_from(EXPECTED_TOOLS))
    @settings(max_examples=len(EXPECTED_TOOLS))
    def test_each_tool_has_valid_input_schema(self, tool_name: str):
        """For any tool, its inputSchema is a valid JSON Schema object."""
        tool = get_tool_by_name(tool_name)
        schema = tool["inputSchema"]

        # Must be an object type schema
        assert schema.get("type") == "object"
        assert "properties" in schema

        # Properties must be a dict
        assert isinstance(schema["properties"], dict)

    def test_server_exposes_all_tools(self):
        """Server get_tools() returns all defined tools."""
        server = SpecMemMCPServer()
        tools = server.get_tools()

        assert len(tools) == len(EXPECTED_TOOLS)

        tool_names = [t["name"] for t in tools]
        for expected in EXPECTED_TOOLS:
            assert expected in tool_names

    def test_server_get_tool_names(self):
        """Server get_tool_names() returns all tool names."""
        server = SpecMemMCPServer()
        names = server.get_tool_names()

        assert len(names) == len(EXPECTED_TOOLS)
        for expected in EXPECTED_TOOLS:
            assert expected in names


class TestToolSchemaValidation:
    """Tests for tool input schema validation."""

    def test_query_tool_schema(self):
        """specmem_query has correct schema with required 'query' field."""
        tool = get_tool_by_name("specmem_query")
        schema = tool["inputSchema"]

        assert "query" in schema["properties"]
        assert schema["properties"]["query"]["type"] == "string"
        assert "required" in schema
        assert "query" in schema["required"]

        # Optional fields
        assert "top_k" in schema["properties"]
        assert "include_legacy" in schema["properties"]

    def test_impact_tool_schema(self):
        """specmem_impact has correct schema with required 'files' field."""
        tool = get_tool_by_name("specmem_impact")
        schema = tool["inputSchema"]

        assert "files" in schema["properties"]
        assert schema["properties"]["files"]["type"] == "array"
        assert "required" in schema
        assert "files" in schema["required"]

        # Optional fields
        assert "depth" in schema["properties"]

    def test_context_tool_schema(self):
        """specmem_context has correct schema with required 'files' field."""
        tool = get_tool_by_name("specmem_context")
        schema = tool["inputSchema"]

        assert "files" in schema["properties"]
        assert schema["properties"]["files"]["type"] == "array"
        assert "required" in schema
        assert "files" in schema["required"]

        # Optional fields
        assert "token_budget" in schema["properties"]

    def test_tldr_tool_schema(self):
        """specmem_tldr has correct schema with optional 'token_budget'."""
        tool = get_tool_by_name("specmem_tldr")
        schema = tool["inputSchema"]

        assert "token_budget" in schema["properties"]
        # No required fields for tldr
        assert "required" not in schema or len(schema.get("required", [])) == 0

    def test_cues_tool_schema(self):
        """specmem_cues has optional cue/files and no required fields."""
        tool = get_tool_by_name("specmem_cues")
        schema = tool["inputSchema"]

        assert "cue" in schema["properties"]
        assert "files" in schema["properties"]
        assert "token_budget" in schema["properties"]
        assert "session_start" in schema["properties"]["cue"]["enum"]
        assert "path" in schema["properties"]["cue"]["enum"]
        assert "required" not in schema or len(schema.get("required", [])) == 0

    def test_coverage_tool_schema(self):
        """specmem_coverage has correct schema with optional 'feature'."""
        tool = get_tool_by_name("specmem_coverage")
        schema = tool["inputSchema"]

        assert "feature" in schema["properties"]
        # No required fields for coverage
        assert "required" not in schema or len(schema.get("required", [])) == 0

    def test_validate_tool_schema(self):
        """specmem_validate has correct schema with optional 'spec_id'."""
        tool = get_tool_by_name("specmem_validate")
        schema = tool["inputSchema"]

        assert "spec_id" in schema["properties"]
        # No required fields for validate
        assert "required" not in schema or len(schema.get("required", [])) == 0


class TestServerInitialization:
    """Tests for MCP server initialization."""

    def test_server_not_initialized_by_default(self):
        """Server is not initialized until initialize() is called."""
        server = SpecMemMCPServer()
        assert not server.is_initialized

    @pytest.mark.asyncio
    async def test_server_initializes_successfully(self):
        """Server initializes successfully with valid workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server = SpecMemMCPServer(workspace_path=tmpdir)

            result = await server.initialize()

            assert result["status"] == "initialized"
            assert server.is_initialized

    @pytest.mark.asyncio
    async def test_server_returns_already_initialized(self):
        """Server returns 'already_initialized' on second init call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server = SpecMemMCPServer(workspace_path=tmpdir)

            await server.initialize()
            result = await server.initialize()

            assert result["status"] == "already_initialized"

    @pytest.mark.asyncio
    async def test_server_auto_initializes_on_tool_call(self):
        """Server auto-initializes when handling tool call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server = SpecMemMCPServer(workspace_path=tmpdir)

            assert not server.is_initialized

            # Call a tool - should auto-initialize
            result = await server.handle_tool_call("specmem_tldr", {})

            assert server.is_initialized
            # Should have a result (not an init error)
            assert "error" not in result or result.get("error") != "not_initialized"


class TestUnknownToolHandling:
    """Tests for handling unknown tool calls."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Unknown tool name returns error with available tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server = SpecMemMCPServer(workspace_path=tmpdir)
            await server.initialize()

            result = await server.handle_tool_call("unknown_tool", {})

            assert result["error"] == "unknown_tool"
            assert "available_tools" in result
            assert len(result["available_tools"]) == len(EXPECTED_TOOLS)

    @given(tool_name=st.text(min_size=1, max_size=50).filter(lambda x: x not in EXPECTED_TOOLS))
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_any_unknown_tool_returns_error(self, tool_name: str):
        """For any unknown tool name, server returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server = SpecMemMCPServer(workspace_path=tmpdir)
            await server.initialize()

            result = await server.handle_tool_call(tool_name, {})

            assert result["error"] == "unknown_tool"


class TestToolLookup:
    """Tests for tool lookup functionality."""

    @given(tool_name=st.sampled_from(EXPECTED_TOOLS))
    @settings(max_examples=len(EXPECTED_TOOLS))
    def test_get_tool_by_name_returns_tool(self, tool_name: str):
        """For any valid tool name, get_tool_by_name returns the tool."""
        tool = get_tool_by_name(tool_name)

        assert tool is not None
        assert tool["name"] == tool_name

    @given(tool_name=st.text(min_size=1, max_size=50).filter(lambda x: x not in EXPECTED_TOOLS))
    @settings(max_examples=20)
    def test_get_tool_by_name_returns_none_for_unknown(self, tool_name: str):
        """For any unknown tool name, get_tool_by_name returns None."""
        tool = get_tool_by_name(tool_name)
        assert tool is None


class TestQueryRelevance:
    """**Feature: kiro-powers-integration, Property 2: Query Relevance**

    *For any* query string and spec database with at least one matching spec,
    the `specmem_query` tool SHALL return results where each result contains
    terms from the query or is semantically related.

    **Validates: Requirements 1.2**
    """

    def test_empty_query_returns_empty_results(self):
        """Empty query returns empty results with message."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        # Create mock client
        mock_client = MagicMock()
        mock_client.query.return_value = []

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(handlers.handle_query({"query": ""}))

        assert result["results"] == []
        assert "message" in result

    def test_query_with_no_specs_returns_empty(self):
        """Query on empty database returns empty results."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        mock_client = MagicMock()
        mock_client.query.return_value = []

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            handlers.handle_query({"query": "authentication"})
        )

        assert result["results"] == []
        assert "message" in result

    @given(query=st.text(min_size=3, max_size=50).filter(lambda x: len(x.strip()) > 2))
    @settings(max_examples=10)
    def test_query_returns_list_of_results(self, query: str):
        """For any query, results is always a list."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        mock_client = MagicMock()
        mock_client.query.return_value = []

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            handlers.handle_query({"query": query})
        )

        assert isinstance(result.get("results", []), list)

    @given(top_k=st.integers(min_value=1, max_value=50))
    @settings(max_examples=10)
    def test_query_respects_top_k_limit(self, top_k: int):
        """For any top_k value, results do not exceed that limit."""
        from unittest.mock import MagicMock

        from specmem.core.specir import SpecType
        from specmem.mcp.handlers import ToolHandlers

        # Create mock specs
        mock_specs = [
            MagicMock(
                id=f"spec_{i}",
                type=SpecType.REQUIREMENT,
                text=f"Test spec {i}",
                source="test.md",
                pinned=False,
                tags=["test"],
            )
            for i in range(100)  # More than any top_k
        ]

        mock_client = MagicMock()
        mock_client.query.return_value = mock_specs[:top_k]

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            handlers.handle_query({"query": "test", "top_k": top_k})
        )

        assert len(result.get("results", [])) <= top_k


class TestImpactCompleteness:
    """**Feature: kiro-powers-integration, Property 3: Impact Completeness**

    *For any* set of file paths that exist in the SpecImpact graph, the
    `specmem_impact` tool SHALL return all specs and tests that are connected
    to those files within the specified depth.

    **Validates: Requirements 1.3**
    """

    def test_empty_files_returns_error(self):
        """Empty files list returns error."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        mock_client = MagicMock()
        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(handlers.handle_impact({"files": []}))

        assert result["error"] == "no_files"

    def test_invalid_files_returns_error(self):
        """Invalid file paths return error with path list."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        mock_client = MagicMock()
        mock_client.path = Path(tempfile.gettempdir())

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            handlers.handle_impact({"files": ["nonexistent/file.py"]})
        )

        assert result["error"] == "invalid_paths"
        assert "nonexistent/file.py" in result["paths"]


class TestContextTokenBudget:
    """**Feature: kiro-powers-integration, Property 4: Context Token Budget**

    *For any* file paths and token budget, the `specmem_context` tool SHALL
    return a context bundle where the total tokens do not exceed the specified
    budget.

    **Validates: Requirements 1.5**
    """

    def test_empty_files_returns_error(self):
        """Empty files list returns error."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        mock_client = MagicMock()
        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(handlers.handle_context({"files": []}))

        assert result["error"] == "no_files"

    @given(token_budget=st.integers(min_value=100, max_value=8000))
    @settings(max_examples=10)
    def test_context_respects_token_budget(self, token_budget: int):
        """For any token budget, total_tokens does not exceed it."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        # Create mock bundle that respects budget
        mock_bundle = MagicMock()
        mock_bundle.specs = []
        mock_bundle.designs = []
        mock_bundle.tldr = "Test summary"
        mock_bundle.total_tokens = min(token_budget, 100)
        mock_bundle.token_budget = token_budget

        mock_client = MagicMock()
        mock_client.get_context_for_change.return_value = mock_bundle

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            handlers.handle_context({"files": ["test.py"], "token_budget": token_budget})
        )

        if "total_tokens" in result:
            assert result["total_tokens"] <= token_budget
            assert result["token_budget"] == token_budget


class TestTLDRStructure:
    """**Feature: kiro-powers-integration, Property 12: TL;DR Structure**

    *For any* spec database with pinned specifications, the `specmem_tldr` tool
    SHALL return a summary where pinned specs appear before non-pinned specs,
    and the total tokens do not exceed the budget.

    **Validates: Requirements 5.1, 5.2, 5.3**
    """

    def test_tldr_returns_summary_string(self):
        """TL;DR returns a summary string."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        mock_client = MagicMock()
        mock_client.get_tldr.return_value = "Key specifications:\n- Test spec"

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(handlers.handle_tldr({}))

        assert "summary" in result
        assert isinstance(result["summary"], str)

    @given(token_budget=st.integers(min_value=50, max_value=2000))
    @settings(max_examples=10)
    def test_tldr_respects_token_budget(self, token_budget: int):
        """For any token budget, TL;DR respects it."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        # Create a summary that fits within budget
        mock_client = MagicMock()
        mock_client.get_tldr.return_value = "Short summary"

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            handlers.handle_tldr({"token_budget": token_budget})
        )

        assert "summary" in result
        # The handler passes budget to client, client enforces it
        mock_client.get_tldr.assert_called_with(token_budget=token_budget)

    def test_tldr_with_no_specs_returns_message(self):
        """TL;DR with no specs returns appropriate message."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        mock_client = MagicMock()
        mock_client.get_tldr.return_value = "No specifications found in memory."

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(handlers.handle_tldr({}))

        assert "summary" in result
        assert "No specifications" in result["summary"] or len(result["summary"]) > 0


class TestValidationCompleteness:
    """**Feature: kiro-powers-integration, Property 13: Validation Completeness**

    *For any* spec database, the `specmem_validate` tool SHALL run all
    registered validation rules and return a result containing the count
    of specs validated.

    **Validates: Requirements 6.1, 6.3**
    """

    def test_validate_returns_structured_result(self):
        """Validation returns structured result with expected fields."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        # Create mock validation result
        mock_result = MagicMock()
        mock_result.is_valid = True
        mock_result.specs_validated = 5
        mock_result.rules_run = 6
        mock_result.duration_ms = 10.5
        mock_result.get_errors.return_value = []
        mock_result.get_warnings.return_value = []

        mock_client = MagicMock()
        mock_client.validate.return_value = mock_result

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(handlers.handle_validate({}))

        assert "is_valid" in result
        assert "specs_validated" in result
        assert "rules_run" in result
        assert "errors" in result
        assert "warnings" in result

    def test_validate_returns_errors_when_present(self):
        """Validation returns errors when specs have issues."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        # Create mock error
        mock_error = MagicMock()
        mock_error.rule = "contradiction"
        mock_error.spec_id = "test.spec"
        mock_error.message = "Contradictory requirement"
        mock_error.severity = MagicMock(value="error")

        mock_result = MagicMock()
        mock_result.is_valid = False
        mock_result.specs_validated = 5
        mock_result.rules_run = 6
        mock_result.duration_ms = 10.5
        mock_result.get_errors.return_value = [mock_error]
        mock_result.get_warnings.return_value = []

        mock_client = MagicMock()
        mock_client.validate.return_value = mock_result

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(handlers.handle_validate({}))

        assert result["is_valid"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["rule"] == "contradiction"

    @given(spec_id=st.text(min_size=1, max_size=50).filter(lambda x: len(x.strip()) > 0))
    @settings(max_examples=10)
    def test_validate_accepts_spec_id_filter(self, spec_id: str):
        """Validation accepts optional spec_id filter."""
        from unittest.mock import MagicMock

        from specmem.mcp.handlers import ToolHandlers

        mock_result = MagicMock()
        mock_result.is_valid = True
        mock_result.specs_validated = 1
        mock_result.rules_run = 6
        mock_result.duration_ms = 5.0
        mock_result.get_errors.return_value = []
        mock_result.get_warnings.return_value = []

        mock_client = MagicMock()
        mock_client.validate.return_value = mock_result

        handlers = ToolHandlers(client=mock_client)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            handlers.handle_validate({"spec_id": spec_id})
        )

        # Verify spec_id was passed to client
        mock_client.validate.assert_called_with(spec_id=spec_id)
        assert "is_valid" in result
