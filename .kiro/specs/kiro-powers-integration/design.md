# Design Document: Kiro Powers Integration

## Overview

This design describes the integration between SpecMem and Kiro Powers, enabling:
1. SpecMem to be distributed as a Kiro Power with MCP server tools
2. SpecMem to parse and index Power documentation (POWER.md, steering files)
3. SpecImpact graph to track Power relationships with specs and code

The integration creates a bidirectional relationship: SpecMem enhances Kiro with spec memory capabilities, while Kiro Powers become first-class citizens in the spec memory.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Kiro IDE                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐     ┌──────────────────────────────────────┐  │
│  │  Kiro Powers     │     │         SpecMem Power                │  │
│  │  Management      │────▶│  ┌────────────────────────────────┐  │  │
│  └──────────────────┘     │  │     MCP Server (specmem-mcp)   │  │  │
│                           │  │  ┌──────────┐ ┌──────────────┐ │  │  │
│                           │  │  │  Tools   │ │   Handlers   │ │  │  │
│                           │  │  │ - query  │ │ - initialize │ │  │  │
│                           │  │  │ - impact │ │ - query      │ │  │  │
│                           │  │  │ - tldr   │ │ - impact     │ │  │  │
│                           │  │  │ - cov    │ │ - coverage   │ │  │  │
│                           │  │  │ - valid  │ │ - validate   │ │  │  │
│                           │  │  └──────────┘ └──────────────┘ │  │  │
│                           │  └────────────────────────────────┘  │  │
│                           └──────────────────────────────────────┘  │
│                                          │                          │
│                                          ▼                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    SpecMem Core                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │MemoryBank   │  │SpecImpact   │  │ PowerAdapter        │   │  │
│  │  │             │  │Graph        │  │ (new)               │   │  │
│  │  │ - query()   │  │ - nodes     │  │ - detect()          │   │  │
│  │  │ - add()     │  │ - edges     │  │ - load()            │   │  │
│  │  │ - search()  │  │ - impact()  │  │ - parse_power_md()  │   │  │
│  │  └─────────────┘  └─────────────┘  │ - parse_steering()  │   │  │
│  │                                     └─────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    .kiro/powers/                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                    │  │
│  │  │ aws-docs/       │  │ specmem/        │                    │  │
│  │  │ - POWER.md      │  │ - POWER.md      │                    │  │
│  │  │ - mcp.json      │  │ - mcp.json      │                    │  │
│  │  │ - steering/     │  │ - steering/     │                    │  │
│  │  └─────────────────┘  └─────────────────┘                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. SpecMem MCP Server (`specmem/mcp/`)

The MCP server exposes SpecMem functionality as tools that Kiro can invoke.

```python
# specmem/mcp/server.py
class SpecMemMCPServer:
    """MCP server exposing SpecMem tools to Kiro."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.client: SpecMemClient | None = None

    async def initialize(self) -> dict:
        """Initialize spec memory for the workspace."""
        ...

    async def handle_tool_call(self, tool_name: str, arguments: dict) -> dict:
        """Route tool calls to appropriate handlers."""
        ...

# Tool definitions
TOOLS = [
    {
        "name": "specmem_query",
        "description": "Query specifications by natural language",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language query"},
                "top_k": {"type": "integer", "default": 10},
                "include_legacy": {"type": "boolean", "default": False}
            },
            "required": ["query"]
        }
    },
    {
        "name": "specmem_impact",
        "description": "Get specs and tests affected by file changes",
        "inputSchema": {
            "type": "object",
            "properties": {
                "files": {"type": "array", "items": {"type": "string"}},
                "depth": {"type": "integer", "default": 2}
            },
            "required": ["files"]
        }
    },
    {
        "name": "specmem_context",
        "description": "Get optimized context bundle for files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "files": {"type": "array", "items": {"type": "string"}},
                "token_budget": {"type": "integer", "default": 4000}
            },
            "required": ["files"]
        }
    },
    {
        "name": "specmem_tldr",
        "description": "Get TL;DR summary of key specifications",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token_budget": {"type": "integer", "default": 500}
            }
        }
    },
    {
        "name": "specmem_coverage",
        "description": "Get spec coverage analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string", "description": "Optional feature name"}
            }
        }
    },
    {
        "name": "specmem_validate",
        "description": "Validate specifications for quality issues",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_id": {"type": "string", "description": "Optional spec ID to validate"}
            }
        }
    }
]
```

### 2. Power Adapter (`specmem/adapters/power.py`)

A new adapter that detects and parses Kiro Power configurations.

```python
# specmem/adapters/power.py
class PowerAdapter(SpecAdapter):
    """Adapter for Kiro Power configurations.

    Detects and parses:
    - .kiro/powers/*/POWER.md - Power documentation
    - .kiro/powers/*/steering/*.md - Steering files
    - .kiro/powers/*/mcp.json - MCP configuration (for tool metadata)
    """

    @property
    def name(self) -> str:
        return "KiroPower"

    def detect(self, repo_path: str) -> bool:
        """Check if any Powers are installed."""
        powers_dir = Path(repo_path) / ".kiro" / "powers"
        return powers_dir.exists() and any(powers_dir.iterdir())

    def load(self, repo_path: str) -> list[SpecBlock]:
        """Load all Power documentation as SpecBlocks."""
        ...

    def _parse_power_md(self, power_path: Path) -> list[SpecBlock]:
        """Parse POWER.md file into SpecBlocks."""
        ...

    def _parse_steering_files(self, power_path: Path) -> list[SpecBlock]:
        """Parse steering files into SpecBlocks."""
        ...

    def _parse_mcp_config(self, power_path: Path) -> dict:
        """Parse mcp.json for tool metadata."""
        ...
```

### 3. Power Graph Integration (`specmem/impact/power_builder.py`)

Extends the SpecImpact graph builder to handle Power relationships.

```python
# specmem/impact/power_builder.py
class PowerGraphBuilder:
    """Builds graph nodes and edges for Kiro Powers."""

    def build_power_nodes(self, powers: list[PowerInfo]) -> list[GraphNode]:
        """Create graph nodes for each installed Power."""
        ...

    def build_power_edges(
        self,
        power: PowerInfo,
        code_files: list[Path],
        specs: list[SpecBlock]
    ) -> list[GraphEdge]:
        """Create edges linking Powers to code and specs."""
        ...

    def extract_code_patterns(self, steering_content: str) -> list[str]:
        """Extract code patterns from steering file content."""
        ...
```

## Data Models

### PowerInfo

```python
@dataclass
class PowerInfo:
    """Information about an installed Kiro Power."""
    name: str
    path: Path
    description: str
    tools: list[ToolInfo]
    steering_files: list[Path]
    keywords: list[str]
    version: str | None = None

@dataclass
class ToolInfo:
    """Information about an MCP tool."""
    name: str
    description: str
    input_schema: dict
```

### Power SpecBlock Types

Powers will create SpecBlocks with the following types:
- `SpecType.KNOWLEDGE` - For POWER.md overview and documentation
- `SpecType.DESIGN` - For tool descriptions and architecture
- `SpecType.TASK` - For workflow guides in steering files

### Graph Node Types

New node type for Powers:
```python
class NodeType(Enum):
    SPEC = "spec"
    CODE = "code"
    TEST = "test"
    POWER = "power"  # New
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: MCP Tool Exposure
*For any* initialized SpecMem MCP server, the server SHALL expose all defined tools (query, impact, context, tldr, coverage, validate) with valid input schemas.
**Validates: Requirements 1.1**

### Property 2: Query Relevance
*For any* query string and spec database with at least one matching spec, the `specmem_query` tool SHALL return results where each result contains terms from the query or is semantically related.
**Validates: Requirements 1.2**

### Property 3: Impact Completeness
*For any* set of file paths that exist in the SpecImpact graph, the `specmem_impact` tool SHALL return all specs and tests that are connected to those files within the specified depth.
**Validates: Requirements 1.3**

### Property 4: Context Token Budget
*For any* file paths and token budget, the `specmem_context` tool SHALL return a context bundle where the total tokens do not exceed the specified budget.
**Validates: Requirements 1.5**

### Property 5: Power Detection
*For any* repository with a `.kiro/powers/` directory containing at least one Power with a POWER.md file, the PowerAdapter SHALL detect the Power.
**Validates: Requirements 2.1**

### Property 6: Power Parsing Completeness
*For any* valid POWER.md file, parsing SHALL produce SpecBlocks containing the Power name, description, and tool information. *For any* Power with steering files, each steering file SHALL produce at least one SpecBlock.
**Validates: Requirements 2.2, 2.3, 2.4**

### Property 7: Power Update Consistency
*For any* Power whose POWER.md content changes, rescanning SHALL produce SpecBlocks with updated content that differs from the previous scan.
**Validates: Requirements 2.5**

### Property 8: Power Graph Nodes
*For any* set of installed Powers, building the SpecImpact graph SHALL create exactly one node of type POWER for each Power.
**Validates: Requirements 3.1**

### Property 9: Power-Code Edge Creation
*For any* Power steering file that contains file path patterns (e.g., `*.py`, `src/**/*.ts`), the graph SHALL contain edges from the Power node to all matching code files.
**Validates: Requirements 3.2**

### Property 10: Power Impact Query
*For any* Power node in the graph, querying impact for that Power SHALL return all directly and transitively connected specs, code, and tests.
**Validates: Requirements 3.4**

### Property 11: Invalid Path Error
*For any* file path that does not exist in the workspace, the impact tool SHALL return an error response that identifies the invalid path.
**Validates: Requirements 4.4**

### Property 12: TL;DR Structure
*For any* spec database with pinned specifications, the `specmem_tldr` tool SHALL return a summary where pinned specs appear before non-pinned specs, and the total tokens do not exceed the budget.
**Validates: Requirements 5.1, 5.2, 5.3**

### Property 13: Validation Completeness
*For any* spec database, the `specmem_validate` tool SHALL run all registered validation rules and return a result containing the count of specs validated.
**Validates: Requirements 6.1, 6.3**

## Error Handling

### MCP Server Errors

| Error Condition | Response |
|----------------|----------|
| Memory not initialized | `{"error": "not_initialized", "message": "Run specmem init first"}` |
| No results found | `{"results": [], "message": "No matching specifications found"}` |
| Invalid file path | `{"error": "invalid_path", "paths": ["path/to/invalid"]}` |
| Vector DB unavailable | Falls back to keyword search, logs warning |
| Internal error | `{"error": "internal", "message": "..."}`, logs full error |

### Adapter Errors

- Missing POWER.md: Log warning, skip Power
- Malformed POWER.md: Log warning, extract what's possible
- Missing steering directory: Continue without steering files
- Invalid mcp.json: Log warning, skip tool metadata

## Testing Strategy

### Unit Tests
- Test MCP tool handlers with mock SpecMemClient
- Test PowerAdapter parsing with sample POWER.md files
- Test graph builder with mock Power data

### Property-Based Tests
Using Hypothesis for Python:

1. **MCP Tool Schema Validation**: Generate random valid inputs, verify outputs match expected schema
2. **Query Relevance**: Generate random specs and queries, verify result relevance
3. **Token Budget Compliance**: Generate random budgets, verify output never exceeds
4. **Power Detection**: Generate random directory structures, verify detection accuracy
5. **Graph Node Creation**: Generate random Power sets, verify node count matches

### Integration Tests
- End-to-end test: Install Power → Scan → Query → Verify results
- MCP server integration with actual Kiro (manual testing)

## File Structure

```
specmem/
├── mcp/
│   ├── __init__.py
│   ├── server.py          # MCP server implementation
│   ├── tools.py           # Tool definitions
│   └── handlers.py        # Tool handlers
├── adapters/
│   ├── power.py           # PowerAdapter (new)
│   └── ...
├── impact/
│   ├── power_builder.py   # Power graph builder (new)
│   └── ...
└── ...

# SpecMem Power distribution
specmem-power/
├── POWER.md               # Power documentation
├── mcp.json               # MCP server configuration
└── steering/
    ├── getting-started.md
    └── workflows.md
```

## MCP Server Configuration

The SpecMem Power's `mcp.json`:

```json
{
  "name": "specmem",
  "displayName": "SpecMem - Spec Memory",
  "description": "Unified agent memory for spec-driven development",
  "keywords": ["specs", "memory", "context", "impact", "coverage", "testing"],
  "command": "uvx",
  "args": ["specmem-mcp"],
  "env": {
    "SPECMEM_LOG_LEVEL": "INFO"
  }
}
```
