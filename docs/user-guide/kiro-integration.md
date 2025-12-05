# Kiro IDE Integration

SpecMem integrates with Kiro IDE through MCP servers, hooks, and steering files to provide AI-powered specification management.

## Quick Start

```bash
# Install SpecMem
pip install -e ".[all]"

# Launch the demo dashboard
specmem demo
```

## Configuration Overview

SpecMem uses the `.kiro/` directory structure:

```
.kiro/
├── settings/
│   └── mcp.json          # MCP server configuration
├── hooks/
│   ├── spec-coverage.yaml
│   ├── spec-validation.yaml
│   └── impact-analysis.yaml
├── steering/
│   ├── specmem-development.md
│   ├── spec-writing.md
│   ├── python-style.md
│   └── testing-guide.md
└── specs/
    └── {feature-name}/
        ├── requirements.md
        ├── design.md
        └── tasks.md
```

## MCP Server

The SpecMem MCP server exposes tools for AI agents to query and analyze specifications.

### Configuration

`.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "specmem": {
      "command": "specmem-mcp",
      "args": [],
      "env": {
        "SPECMEM_WORKSPACE": "${workspaceFolder}"
      },
      "disabled": false,
      "autoApprove": [
        "specmem_query",
        "specmem_tldr",
        "specmem_coverage"
      ]
    }
  }
}
```

### Available Tools

| Tool | Description | Auto-Approve |
|------|-------------|--------------|
| `specmem_query` | Search specs by natural language | ✅ |
| `specmem_tldr` | Get summary of key specifications | ✅ |
| `specmem_coverage` | Analyze spec coverage gaps | ✅ |
| `specmem_impact` | Find affected specs for file changes | ❌ |
| `specmem_context` | Get optimized context bundle | ❌ |
| `specmem_validate` | Validate spec quality | ❌ |

### Running Manually

```bash
# Start MCP server
specmem-mcp --workspace .

# With debug logging
specmem-mcp --workspace . --log-level DEBUG
```

## Hooks

Hooks automate spec-related tasks when files change.

### spec-coverage.json

Triggers when test files are saved:
```json
{
  "name": "spec-coverage-check",
  "description": "Check spec coverage when test files change",
  "trigger": "file_save",
  "filePattern": "tests/**/*.py",
  "action": "Check spec coverage after test changes",
  "enabled": true
}
```

### spec-validation.json

Triggers when spec files are modified:
```json
{
  "name": "spec-validation",
  "description": "Validate specifications when spec files are modified",
  "trigger": "file_save",
  "filePattern": ".kiro/specs/**/*.md",
  "action": "Validate specification changes",
  "enabled": true
}
```

### impact-analysis.json

Triggers when source code changes:
```json
{
  "name": "impact-analysis",
  "description": "Analyze spec impact when source files change",
  "trigger": "file_save",
  "filePattern": "specmem/**/*.py",
  "action": "Analyze impact on specifications",
  "enabled": true
}
```

## Steering Files

Steering files provide context-aware guidance to AI agents.

### Inclusion Modes

| Mode | Front-matter | When Included |
|------|--------------|---------------|
| Always | `inclusion: always` | Every conversation |
| File Match | `inclusion: fileMatch` | When matching files are open |
| Manual | `inclusion: manual` | When explicitly referenced |

### specmem-development.md (Always)

Project overview, key commands, architecture summary. Included in every conversation.

### spec-writing.md (File Match)

EARS patterns and spec structure guide. Included when editing `.kiro/specs/**/*.md`.

### python-style.md (File Match)

Code style and formatting rules. Included when editing `**/*.py`.

### testing-guide.md (File Match)

Property-based testing patterns. Included when editing `tests/**/*.py`.

## CLI Commands

```bash
# Launch web dashboard
specmem demo

# Search specifications
specmem query "authentication flow"

# Check spec coverage
specmem cov

# Check spec health
specmem health

# Build memory index
specmem build

# Validate specifications
specmem validate
```

## Web Dashboard

The demo dashboard provides a visual interface for:

- Browsing specifications by type and source
- Semantic search across all specs
- Health score visualization
- Coverage analysis
- Impact graph visualization
- Session history (if Kiro sessions exist)

Access at `http://127.0.0.1:8765` after running `specmem demo`.

## Workflow Example

1. **Start Development**
   ```bash
   specmem demo  # Launch dashboard in background
   ```

2. **Query Specs** (via MCP or CLI)
   ```bash
   specmem query "user authentication"
   ```

3. **Check Coverage**
   ```bash
   specmem cov --feature user-auth
   ```

4. **Analyze Impact**
   - Edit source files
   - Hook triggers impact analysis
   - AI suggests related specs to update

5. **Validate Changes**
   - Edit spec files
   - Hook triggers validation
   - AI checks EARS compliance

## Troubleshooting

### MCP Server Not Starting

```bash
# Check if specmem-mcp is installed
which specmem-mcp

# Test manually
specmem-mcp --workspace . --log-level DEBUG
```

### No Specs Found

```bash
# Verify specs exist
ls -la .kiro/specs/

# Check adapter detection
python -c "from specmem.adapters.kiro import KiroAdapter; print(KiroAdapter().detect('.'))"
```

### Dashboard Shows No Data

```bash
# Rebuild memory index
specmem build

# Check block count
python -c "from specmem.adapters.kiro import KiroAdapter; print(len(KiroAdapter().load('.')))"
```
