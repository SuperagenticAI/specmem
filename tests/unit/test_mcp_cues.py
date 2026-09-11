"""Unit tests for MCP specmem_cues registration and handler."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

from specmem.client.models import ContextBundle, SpecSummary
from specmem.guidelines.models import Guideline, SourceType
from specmem.mcp.handlers import ToolHandlers
from specmem.mcp.server import SpecMemMCPServer
from specmem.mcp.tools import TOOLS, get_tool_by_name, get_tool_names


def test_specmem_cues_registered_in_tools() -> None:
    names = get_tool_names()
    assert "specmem_cues" in names
    tool = get_tool_by_name("specmem_cues")
    assert tool is not None
    assert tool["name"] == "specmem_cues"
    props = tool["inputSchema"]["properties"]
    assert "cue" in props
    assert "files" in props
    assert "session_start" in props["cue"]["enum"]
    assert "path" in props["cue"]["enum"]
    # No required fields: session_start works with empty args
    assert "required" not in tool["inputSchema"] or not tool["inputSchema"].get("required")


def test_server_exposes_specmem_cues() -> None:
    server = SpecMemMCPServer()
    assert "specmem_cues" in server.get_tool_names()
    assert any(t["name"] == "specmem_cues" for t in server.get_tools())
    assert len(TOOLS) == len(server.get_tools())


def test_handle_cues_session_start_returns_tldr_and_always_on(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Rules\n\nAlways pin architecture intent.")

    client = MagicMock()
    client.path = tmp_path
    client.get_tldr.return_value = "Pinned: Always pin architecture intent."

    handlers = ToolHandlers(client=client)
    result = asyncio.run(
        handlers.handle_cues({"cue": "session_start"})
    )

    assert result.get("error") is None
    assert result["mode"] == "session_start"
    assert result["delivery"] == "cue_anchored"
    assert "Pinned" in result["tldr"]
    assert "always_on" in result["layers"]
    assert len(result["layers"]["always_on"]) >= 1
    client.get_tldr.assert_called_once()
    client.get_context_for_change.assert_not_called()


def test_handle_cues_path_requires_files() -> None:
    handlers = ToolHandlers(client=MagicMock())
    result = asyncio.run(
        handlers.handle_cues({"cue": "path"})
    )
    assert result["error"] == "no_files"


def test_handle_cues_path_returns_layers_and_context(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Rules\n\nKeep changes scoped.")
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "python.mdc").write_text(
        "---\ndescription: Python\nglobs: **/*.py\n---\n# Python\n\nUse ruff.\n"
    )

    client = MagicMock()
    client.path = tmp_path
    client.get_context_for_change.return_value = ContextBundle(
        specs=[
            SpecSummary(
                id="s1",
                type="requirement",
                title="Auth",
                summary="JWT required",
                source="specs/auth.md",
                relevance=0.9,
                pinned=True,
            )
        ],
        designs=[],
        tldr="JWT required",
        total_tokens=42,
        token_budget=4000,
        changed_files=["src/auth.py"],
    )

    handlers = ToolHandlers(client=client)
    result = asyncio.run(
        handlers.handle_cues({"cue": "path", "files": ["src/auth.py"]})
    )

    assert result.get("error") is None
    assert result["mode"] == "path"
    assert result["files"] == ["src/auth.py"]
    assert result["tldr"] == "JWT required"
    assert result["specs"][0]["id"] == "s1"
    assert "layers" in result
    client.get_context_for_change.assert_called_once()


def test_handle_cues_defaults_to_session_start_without_files() -> None:
    client = MagicMock()
    client.path = Path(".")
    client.get_tldr.return_value = "summary"

    # Avoid scanning the real repo: stub aggregator via empty path with no files
    # by patching build_context through a tiny fake workspace.
    handlers = ToolHandlers(client=client)

    # Use a temp empty dir so GuidelinesAggregator finds nothing
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        client.path = Path(td)
        result = asyncio.run(handlers.handle_cues({}))

    assert result["mode"] == "session_start"
    assert result["tldr"] == "summary"


def test_resolve_cue_helpers() -> None:
    handlers = ToolHandlers()
    assert handlers._resolve_cue(None, []) == "session_start"
    assert handlers._resolve_cue(None, ["a.py"]) == "path"
    assert handlers._resolve_cue("event", []) == "session_start"
    assert handlers._resolve_cue("path", ["a.py"]) == "path"
    assert handlers._resolve_cue("semantic", ["a.py"]) == "path"
    assert handlers._resolve_cue("temporal", []) == "session_start"


def test_summarize_guideline() -> None:
    g = Guideline(
        id="abc",
        title="Style",
        content="x" * 400,
        source_file="AGENTS.md",
        source_type=SourceType.AGENTS,
        file_pattern=None,
    )
    summary = ToolHandlers._summarize_guideline(g)
    assert summary["id"] == "abc"
    assert summary["title"] == "Style"
    assert summary["summary"].endswith("...")
    assert len(summary["summary"]) == 303
