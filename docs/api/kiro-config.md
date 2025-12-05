# Kiro Configuration API

The `specmem.kiro` module provides programmatic access to Kiro CLI configuration artifacts including steering files, MCP servers, and hooks.

## KiroConfigIndexer

Main class for indexing all Kiro configuration.

```python
from pathlib import Path
from specmem.kiro import KiroConfigIndexer

indexer = KiroConfigIndexer(Path("."))
```

### Methods

#### index_all()

Index all Kiro configuration files.

```python
blocks = indexer.index_all()
# Returns list of SpecBlocks from steering, MCP, and hooks
```

#### index_steering()

Index steering files from `.kiro/steering/`.

```python
blocks = indexer.index_steering()
```

#### index_mcp_config()

Index MCP configuration from `.kiro/settings/mcp.json`.

```python
blocks = indexer.index_mcp_config()
```

#### index_hooks()

Index hooks from `.kiro/hooks/`.

```python
blocks = indexer.index_hooks()
```

#### get_steering_for_file(file_path)

Get steering files applicable to a specific file.

```python
applicable = indexer.get_steering_for_file("src/auth.py")
for steering in applicable:
    print(f"{steering.title}: {steering.inclusion}")
```

#### get_available_tools()

Get list of available (enabled) MCP tools.

```python
tools = indexer.get_available_tools()
for tool in tools:
    print(f"{tool.server_name}/{tool.tool_name}")
```

#### get_hooks_for_trigger(trigger, file_path=None)

Get hooks matching a trigger type and optional file pattern.

```python
hooks = indexer.get_hooks_for_trigger("file_save", "main.py")
for hook in hooks:
    print(f"{hook.name}: {hook.action}")
```

#### get_summary()

Get summary of all Kiro configuration.

```python
summary = indexer.get_summary()
print(f"Steering: {len(summary.steering_files)}")
print(f"MCP Servers: {summary.enabled_servers}/{len(summary.mcp_servers)}")
print(f"Hooks: {summary.active_hooks}/{len(summary.hooks)}")
```

## Data Models

### SteeringFile

Parsed steering file with frontmatter metadata.

```python
from specmem.kiro import SteeringFile

@dataclass
class SteeringFile:
    path: Path
    content: str           # Full content including frontmatter
    body: str              # Content without frontmatter
    inclusion: str         # "always", "fileMatch", or "manual"
    file_match_pattern: str | None
    title: str

    def matches_file(self, file_path: str) -> bool:
        """Check if this steering applies to a file."""
```

### MCPServerInfo

Parsed MCP server configuration.

```python
from specmem.kiro import MCPServerInfo

@dataclass
class MCPServerInfo:
    name: str
    command: str
    args: list[str]
    env: dict[str, str]
    disabled: bool
    auto_approve: list[str]
```

### MCPToolInfo

Information about an MCP tool.

```python
from specmem.kiro import MCPToolInfo

@dataclass
class MCPToolInfo:
    server_name: str
    tool_name: str
    description: str
    auto_approved: bool
```

### HookInfo

Parsed hook configuration.

```python
from specmem.kiro import HookInfo

@dataclass
class HookInfo:
    name: str
    description: str
    trigger: str           # "file_save", "manual", or "session_start"
    file_pattern: str | None
    action: str
    enabled: bool

    def matches_file(self, file_path: str) -> bool:
        """Check if hook's file pattern matches a file."""
```

### KiroConfigSummary

Summary of all Kiro configuration.

```python
from specmem.kiro import KiroConfigSummary

@dataclass
class KiroConfigSummary:
    steering_files: list[SteeringFile]
    mcp_servers: list[MCPServerInfo]
    hooks: list[HookInfo]
    total_tools: int
    enabled_servers: int
    active_hooks: int
```

## Parsers

### SteeringParser

Parses steering files with YAML frontmatter support.

```python
from specmem.kiro import SteeringParser

parser = SteeringParser()

# Parse single file
steering = parser.parse(Path(".kiro/steering/python.md"))

# Parse directory
all_steering = parser.parse_directory(Path(".kiro/steering"))

# Extract frontmatter
frontmatter = parser.parse_frontmatter(content)

# Serialize back to markdown
markdown = parser.serialize_frontmatter(steering)
```

### MCPConfigParser

Parses MCP server configuration.

```python
from specmem.kiro import MCPConfigParser

parser = MCPConfigParser()

# Parse mcp.json
servers = parser.parse(Path(".kiro/settings/mcp.json"))

# Get tools from servers
tools = parser.get_tools(servers)

# Filter enabled/disabled
enabled = parser.get_enabled_servers(servers)
disabled = parser.get_disabled_servers(servers)

# Serialize back to JSON
json_str = parser.serialize(servers)
```

### HookParser

Parses hook configuration files.

```python
from specmem.kiro import HookParser

parser = HookParser()

# Parse single hook
hook = parser.parse(Path(".kiro/hooks/validate.json"))

# Parse directory
all_hooks = parser.parse_directory(Path(".kiro/hooks"))

# Filter by trigger
file_save_hooks = parser.get_hooks_for_trigger(
    all_hooks, "file_save", "main.py"
)

# Serialize back to JSON
json_str = parser.serialize(hook)
```

## Context Bundle Integration

The Kiro config is automatically included in context bundles:

```python
from specmem import SpecMemClient

sm = SpecMemClient()
bundle = sm.get_context_for_change(["src/auth.py"])

# Steering files applicable to changed files
for steering in bundle.steering:
    print(f"{steering.title}: {steering.content}")

# Hooks that would trigger
for hook in bundle.triggered_hooks:
    print(f"{hook.name}: {hook.action}")
```

## See Also

- [User Guide: Kiro Configuration](../user-guide/kiro-config.md)
- [CLI: kiro-config](../cli/kiro-config.md)
- [CLI: steering](../cli/steering.md)
