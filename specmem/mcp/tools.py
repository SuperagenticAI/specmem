"""MCP Tool definitions for SpecMem.

Defines the tools exposed by the SpecMem MCP server following
the Model Context Protocol specification.
"""

from typing import Any


# Tool definitions following MCP specification
TOOLS: list[dict[str, Any]] = [
    {
        "name": "specmem_query",
        "description": "Query specifications by natural language. Returns relevant specs matching the query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query to search specifications",
                },
                "top_k": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of results to return",
                },
                "include_legacy": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to include legacy/deprecated specs",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "specmem_impact",
        "description": "Get specs and tests affected by file changes. Analyzes the SpecImpact graph to find related specifications.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to analyze",
                },
                "depth": {
                    "type": "integer",
                    "default": 2,
                    "description": "Maximum traversal depth for transitive relationships",
                },
            },
            "required": ["files"],
        },
    },
    {
        "name": "specmem_context",
        "description": (
            "Get optimized context bundle for files (path cue). Returns specs, "
            "designs, and TL;DR within a token budget. Prefer harness hooks or "
            "specmem_cues for deterministic delivery; this tool remains available "
            "for voluntary agent lookup."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to get context for",
                },
                "token_budget": {
                    "type": "integer",
                    "default": 4000,
                    "description": "Maximum tokens for the context bundle",
                },
            },
            "required": ["files"],
        },
    },
    {
        "name": "specmem_tldr",
        "description": (
            "Get TL;DR summary of key specifications, prioritizing pinned specs. "
            "Useful as part of session_start / event-cue re-injection after "
            "compaction. Prefer harness hooks or specmem_cues for automatic "
            "delivery; this tool remains available for voluntary lookup."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "token_budget": {
                    "type": "integer",
                    "default": 500,
                    "description": "Maximum tokens for the summary",
                },
            },
        },
    },
    {
        "name": "specmem_cues",
        "description": (
            "Cue-anchored delivery: return pinned and path-matched SpecMem "
            "blocks without inventing a natural-language query. Accepts optional "
            "cue (session_start|path|event|...) and files. Primary story is "
            "harness hooks; this MCP tool is the voluntary-compatible twin."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cue": {
                    "type": "string",
                    "enum": [
                        "session_start",
                        "path",
                        "event",
                        "semantic",
                        "symbol",
                        "temporal",
                    ],
                    "description": (
                        "Delivery cue. session_start/event re-deliver always-on "
                        "guidance and TL;DR. path delivers file-scoped layers "
                        "plus context for files. semantic/symbol/temporal are "
                        "accepted for vocabulary alignment and currently fall "
                        "back to session_start or path when files are provided."
                    ),
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional file paths for path-cue delivery",
                },
                "token_budget": {
                    "type": "integer",
                    "default": 4000,
                    "description": "Maximum tokens for path-cue context bundles",
                },
                "tldr_budget": {
                    "type": "integer",
                    "default": 500,
                    "description": "Maximum tokens for session_start TL;DR",
                },
            },
        },
    },
    {
        "name": "specmem_coverage",
        "description": "Get spec coverage analysis. Analyzes gaps between acceptance criteria and existing tests.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {
                    "type": "string",
                    "description": "Optional feature name to analyze (analyzes all if not provided)",
                },
            },
        },
    },
    {
        "name": "specmem_validate",
        "description": "Validate specifications for quality issues. Checks for contradictions, missing criteria, and other problems.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_id": {
                    "type": "string",
                    "description": "Optional spec ID to validate (validates all if not provided)",
                },
            },
        },
    },
]


def get_tool_by_name(name: str) -> dict[str, Any] | None:
    """Get a tool definition by name.

    Args:
        name: The tool name to look up

    Returns:
        Tool definition dict or None if not found
    """
    for tool in TOOLS:
        if tool["name"] == name:
            return tool
    return None


def get_tool_names() -> list[str]:
    """Get list of all tool names.

    Returns:
        List of tool name strings
    """
    return [tool["name"] for tool in TOOLS]
