# Design Document

## Overview

The Kiro Config Indexer extends SpecMem's existing Kiro adapter to comprehensively index all Kiro CLI configuration artifacts. This includes project-level steering files, MCP server configurations, hooks, and agent settings. The feature enables SpecMem to provide context-aware responses about project configuration and automatically include relevant guidelines when generating context bundles.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        .kiro/ Directory                         │
├─────────────────────────────────────────────────────────────────┤
│  steering/           settings/           hooks/                 │
│  ├── python.md       ├── mcp.json        ├── validate.json     │
│  ├── testing.md      └── agent.json      └── coverage.json     │
│  └── security.md                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KiroConfigIndexer                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Steering   │  │    MCP      │  │   Hooks     │             │
│  │   Parser    │  │   Parser    │  │   Parser    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          ▼                                      │
│              ┌───────────────────────┐                          │
│              │    SpecBlock Factory  │                          │
│              └───────────┬───────────┘                          │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Memory Bank                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SpecBlocks with tags: steering, mcp, hook, config      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### KiroConfigIndexer

Main class that orchestrates indexing of all Kiro configuration artifacts.

```python
@dataclass
class KiroConfigIndexer:
    """Indexes Kiro CLI configuration artifacts."""

    workspace_path: Path

    def index_all(self) -> list[SpecBlock]:
        """Index all Kiro configuration files."""
        ...

    def index_steering(self) -> list[SpecBlock]:
        """Index steering files from .kiro/steering/."""
        ...

    def index_mcp_config(self) -> list[SpecBlock]:
        """Index MCP configuration from .kiro/settings/mcp.json."""
        ...

    def index_hooks(self) -> list[SpecBlock]:
        """Index hooks from .kiro/hooks/."""
        ...

    def get_steering_for_file(self, file_path: str) -> list[SpecBlock]:
        """Get steering files applicable to a specific file."""
        ...

    def get_available_tools(self) -> list[MCPToolInfo]:
        """Get list of available (enabled) MCP tools."""
        ...

    def get_hooks_for_trigger(
        self,
        trigger: str,
        file_path: str | None = None
    ) -> list[HookInfo]:
        """Get hooks matching a trigger type and optional file pattern."""
        ...
```

### SteeringParser

Parses steering files with YAML frontmatter support.

```python
@dataclass
class SteeringFile:
    """Parsed steering file."""

    path: Path
    content: str
    inclusion: Literal["always", "fileMatch", "manual"]
    file_match_pattern: str | None
    title: str

    def matches_file(self, file_path: str) -> bool:
        """Check if this steering applies to a file."""
        ...


class SteeringParser:
    """Parses steering files with frontmatter."""

    def parse(self, file_path: Path) -> SteeringFile:
        """Parse a steering file."""
        ...

    def parse_frontmatter(self, content: str) -> dict[str, Any]:
        """Extract YAML frontmatter from content."""
        ...
```

### MCPConfigParser

Parses MCP server configuration.

```python
@dataclass
class MCPServerInfo:
    """Parsed MCP server configuration."""

    name: str
    command: str
    args: list[str]
    env: dict[str, str]
    disabled: bool
    auto_approve: list[str]


@dataclass
class MCPToolInfo:
    """Information about an MCP tool."""

    server_name: str
    tool_name: str
    description: str
    auto_approved: bool


class MCPConfigParser:
    """Parses MCP configuration."""

    def parse(self, config_path: Path) -> list[MCPServerInfo]:
        """Parse mcp.json configuration."""
        ...

    def get_tools(self, servers: list[MCPServerInfo]) -> list[MCPToolInfo]:
        """Extract tool information from servers."""
        ...
```

### HookParser

Parses hook configuration files.

```python
@dataclass
class HookInfo:
    """Parsed hook configuration."""

    name: str
    description: str
    trigger: Literal["file_save", "manual", "session_start"]
    file_pattern: str | None
    action: str
    enabled: bool

    def matches_file(self, file_path: str) -> bool:
        """Check if hook's file pattern matches a file."""
        ...


class HookParser:
    """Parses hook configuration files."""

    def parse(self, hook_path: Path) -> HookInfo:
        """Parse a hook JSON file."""
        ...
```

## Data Models

### SteeringFile

```python
@dataclass
class SteeringFile:
    path: Path
    content: str
    inclusion: Literal["always", "fileMatch", "manual"]
    file_match_pattern: str | None
    title: str
```

### MCPServerInfo

```python
@dataclass
class MCPServerInfo:
    name: str
    command: str
    args: list[str]
    env: dict[str, str]
    disabled: bool
    auto_approve: list[str]
```

### HookInfo

```python
@dataclass
class HookInfo:
    name: str
    description: str
    trigger: Literal["file_save", "manual", "session_start"]
    file_pattern: str | None
    action: str
    enabled: bool
```

### KiroConfigSummary

```python
@dataclass
class KiroConfigSummary:
    steering_files: list[SteeringFile]
    mcp_servers: list[MCPServerInfo]
    hooks: list[HookInfo]
    total_tools: int
    enabled_servers: int
    active_hooks: int
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Steering File Parsing Completeness

*For any* directory containing valid steering markdown files, parsing SHALL produce one SpecBlock per file, and each SpecBlock SHALL contain the file's content.

**Validates: Requirements 1.1**

### Property 2: Frontmatter Round-Trip

*For any* valid YAML frontmatter with `inclusion` and `fileMatchPattern` fields, parsing and re-serializing SHALL preserve the original values.

**Validates: Requirements 1.2**

### Property 3: File Pattern Matching Consistency

*For any* steering file with a `fileMatchPattern` and any file path, the `matches_file()` method SHALL return true if and only if the file path matches the glob pattern according to standard glob semantics.

**Validates: Requirements 1.3, 5.1, 5.2**

### Property 4: Inclusion Mode Priority Mapping

*For any* steering file, the resulting SpecBlock's priority SHALL be determined by its inclusion mode: "always" → high priority (pinned), "fileMatch" → normal priority, "manual" → low priority (not auto-included).

**Validates: Requirements 1.4, 1.5**

### Property 5: MCP Server Parsing Completeness

*For any* valid mcp.json configuration, parsing SHALL produce one SpecBlock per defined server, and each SpecBlock SHALL contain the server name and command.

**Validates: Requirements 2.1**

### Property 6: MCP Tool Extraction

*For any* MCP server with tool definitions, the parser SHALL extract all tools, and each tool's SpecBlock SHALL contain its name and description.

**Validates: Requirements 2.2**

### Property 7: Disabled Server Filtering

*For any* query for available tools, the result SHALL exclude tools from servers where `disabled: true`, and SHALL include tools from all enabled servers.

**Validates: Requirements 2.3, 2.4**

### Property 8: Hook Parsing Completeness

*For any* directory containing valid hook JSON files, parsing SHALL produce one SpecBlock per hook file.

**Validates: Requirements 3.1**

### Property 9: Hook Trigger Filtering

*For any* query for hooks by trigger type and file path, the result SHALL include only hooks where the trigger matches AND (file_pattern is null OR file_pattern matches the path).

**Validates: Requirements 3.2, 3.3**

### Property 10: Always-Included Steering

*For any* steering file with `inclusion: always`, querying steering for any file path SHALL include that steering file in the results.

**Validates: Requirements 5.3**

### Property 11: Context Bundle Steering Inclusion

*For any* context bundle generated for changed files, the bundle SHALL include content from all steering files where `inclusion: always` OR `fileMatchPattern` matches any changed file.

**Validates: Requirements 6.1, 6.2**

### Property 12: Context Bundle Hook Mention

*For any* context bundle generated for changed files, if a hook with `trigger: file_save` has a `filePattern` matching any changed file, the bundle SHALL mention this hook.

**Validates: Requirements 6.4**

## Error Handling

| Condition | Handling |
|-----------|----------|
| Missing `.kiro/steering/` directory | Return empty list, no error |
| Missing `.kiro/settings/mcp.json` | Return empty list, no error |
| Missing `.kiro/hooks/` directory | Return empty list, no error |
| Malformed YAML frontmatter | Log warning, parse content without frontmatter |
| Invalid JSON in mcp.json | Log error, return empty list |
| Invalid JSON in hook file | Log warning, skip that hook |
| Invalid glob pattern | Log warning, treat as non-matching |

## Testing Strategy

### Property-Based Testing

The implementation will use **Hypothesis** for property-based testing with a minimum of 100 iterations per property.

Each property test will be annotated with:
```python
# **Feature: kiro-config-indexer, Property N: Property Name**
# **Validates: Requirements X.Y**
```

### Test Strategies

1. **Steering files**: Generate random markdown content with valid/invalid frontmatter
2. **MCP config**: Generate random JSON with varying numbers of servers and tools
3. **Hooks**: Generate random hook configurations with different triggers and patterns
4. **File matching**: Generate random glob patterns and file paths to test matching

### Unit Tests

- Parse steering file with no frontmatter
- Parse steering file with partial frontmatter
- Parse MCP config with disabled servers
- Parse hook with missing optional fields
- CLI command output formatting
