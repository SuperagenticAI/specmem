# 🔌 MCP Server API

SpecMem provides an MCP (Model Context Protocol) server for integration with Kiro and other MCP-compatible tools.

## Overview

The MCP server exposes SpecMem functionality as tools that can be invoked by AI agents. It follows the [Model Context Protocol](https://modelcontextprotocol.io/) specification.

## Server Class

::: specmem.mcp.server.SpecMemMCPServer
    options:
      show_source: true
      members:
        - __init__
        - initialize
        - is_initialized
        - get_tools
        - get_tool_names
        - handle_tool_call

## Usage

### Programmatic Usage

```python
from pathlib import Path
from specmem.mcp.server import SpecMemMCPServer

# Create server instance
server = SpecMemMCPServer(workspace_path=Path("."))

# Initialize
await server.initialize()

# Handle tool calls
result = await server.handle_tool_call(
    "specmem_query",
    {"query": "authentication requirements", "top_k": 5}
)
print(result)
```

### Command Line

Run the MCP server via stdio transport:

```bash
specmem-mcp --workspace /path/to/project
```

Options:

| Flag | Description | Default |
|------|-------------|---------|
| `--workspace`, `-w` | Workspace path | Current directory |
| `--log-level` | Log level (DEBUG, INFO, WARNING, ERROR) | INFO |

## Tool Definitions

### specmem_query

Query specifications by natural language.

```python
{
    "name": "specmem_query",
    "description": "Query specifications by natural language",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query"
            },
            "top_k": {
                "type": "integer",
                "default": 10,
                "description": "Maximum results to return"
            },
            "include_legacy": {
                "type": "boolean",
                "default": False,
                "description": "Include deprecated specs"
            }
        },
        "required": ["query"]
    }
}
```

### specmem_impact

Get specs and tests affected by file changes.

```python
{
    "name": "specmem_impact",
    "description": "Get specs and tests affected by file changes",
    "inputSchema": {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File paths to analyze"
            },
            "depth": {
                "type": "integer",
                "default": 2,
                "description": "Traversal depth for relationships"
            }
        },
        "required": ["files"]
    }
}
```

### specmem_context

Get optimized context bundle for files.

```python
{
    "name": "specmem_context",
    "description": "Get optimized context bundle for files",
    "inputSchema": {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files to get context for"
            },
            "token_budget": {
                "type": "integer",
                "default": 4000,
                "description": "Maximum tokens for context"
            }
        },
        "required": ["files"]
    }
}
```

### specmem_tldr

Get TL;DR summary of key specifications (useful for session_start re-injection; prefer hooks / specmem_cues for automatic delivery).

```python
{
    "name": "specmem_tldr",
    "description": "Get TL;DR summary of key specifications",
    "inputSchema": {
        "type": "object",
        "properties": {
            "token_budget": {
                "type": "integer",
                "default": 500,
                "description": "Maximum tokens for summary"
            }
        }
    }
}
```

### specmem_cues

Cue-anchored delivery of pinned and path-matched context without inventing a
natural-language query. Prefer Kiro hooks for automatic injection; this tool is
the voluntary-compatible twin (Towards #16).

```python
{
    "name": "specmem_cues",
    "description": "Cue-anchored delivery of pinned and path-matched blocks",
    "inputSchema": {
        "type": "object",
        "properties": {
            "cue": {
                "type": "string",
                "enum": ["session_start", "path", "event", "semantic", "symbol", "temporal"],
                "description": "Delivery cue"
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File paths for path-cue delivery"
            },
            "token_budget": {
                "type": "integer",
                "default": 4000,
                "description": "Token budget for path-cue context"
            },
            "tldr_budget": {
                "type": "integer",
                "default": 500,
                "description": "Token budget for session_start TL;DR"
            }
        }
    }
}
```

`cue=session_start` (or empty args) returns always-on guideline layers plus
TL;DR. `cue=path` with `files` returns file-scoped layers plus a context
bundle from `get_context_for_change()`.

See [Cue-Anchored Delivery](../advanced/cue-anchored-delivery.md).

### specmem_coverage

Get spec coverage analysis.

```python
{
    "name": "specmem_coverage",
    "description": "Get spec coverage analysis",
    "inputSchema": {
        "type": "object",
        "properties": {
            "feature": {
                "type": "string",
                "description": "Optional feature name"
            }
        }
    }
}
```

### specmem_validate

Validate specifications for quality issues.

```python
{
    "name": "specmem_validate",
    "description": "Validate specifications for quality issues",
    "inputSchema": {
        "type": "object",
        "properties": {
            "spec_id": {
                "type": "string",
                "description": "Optional spec ID to validate"
            }
        }
    }
}
```

## Response Format

### Success Response

```json
{
    "results": [...],
    "count": 5,
    "message": "Found 5 matching specifications"
}
```

### Error Response

```json
{
    "error": "error_type",
    "message": "Human-readable error message",
    "details": {...}
}
```

### Error Types

| Error | Description |
|-------|-------------|
| `not_initialized` | SpecMem not initialized for workspace |
| `unknown_tool` | Unknown tool name requested |
| `invalid_path` | One or more file paths don't exist |
| `tool_error` | Tool execution failed |

## Tool Helpers

### get_tool_by_name

```python
from specmem.mcp.tools import get_tool_by_name

tool = get_tool_by_name("specmem_query")
print(tool["description"])
```

### get_tool_names

```python
from specmem.mcp.tools import get_tool_names

names = get_tool_names()
# ['specmem_query', 'specmem_impact', 'specmem_context', ...]
```

## MCP Configuration

### Kiro Configuration

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "specmem": {
      "command": "uvx",
      "args": ["specmem-mcp"],
      "env": {
        "SPECMEM_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SPECMEM_LOG_LEVEL` | Logging level | INFO |
| `SPECMEM_WORKSPACE` | Override workspace path | Current directory |

## Protocol Details

The server uses stdio transport for communication:

1. Reads JSON-RPC requests from stdin
2. Writes JSON-RPC responses to stdout
3. Logs to stderr

### Request Format

```json
{
    "id": "request-id",
    "method": "tools/call",
    "params": {
        "name": "specmem_query",
        "arguments": {
            "query": "authentication"
        }
    }
}
```

### Response Format

```json
{
    "id": "request-id",
    "result": {
        "results": [...],
        "count": 5
    }
}
```

## See Also

- [Kiro Powers Integration](../user-guide/kiro-powers.md) - User guide for Kiro Powers
- [Agent Integration](../advanced/agent-integration.md) - General agent integration patterns
- [SpecMemClient](client.md) - Python client API
