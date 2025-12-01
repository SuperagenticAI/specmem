# 🔗 Agent Integration

Integrate SpecMem with AI coding agents for enhanced context awareness.

## Overview

SpecMem provides context to AI agents through:

1. **Agent Experience Pack** - Pre-built context files
2. **Python API** - Direct integration
3. **REST API** - HTTP-based integration
4. **MCP Server** - Model Context Protocol

## Agent Experience Pack

The simplest integration - agents read from `.specmem/` directory.

### Build the Pack

```bash
specmem build
```

### Pack Contents

```
.specmem/
├── agent_memory.json      # All specs with metadata
├── agent_context.md       # Human-readable summary
├── knowledge_index.json   # Keyword mappings
├── impact_graph.json      # Relationships
└── vectordb/              # Vector embeddings
```

### Agent Instructions

Add to your agent's system prompt:

```markdown
## Project Context

This project uses SpecMem for specification management.
Read `.specmem/agent_context.md` for project overview.
Query `.specmem/agent_memory.json` for detailed specifications.

Before making changes:
1. Check relevant specs in `.specmem/agent_memory.json`
2. Verify your changes align with requirements
3. Update specs if requirements change
```

## Python Integration

### Direct API Usage

```python
from specmem import SpecMemClient

def get_context_for_agent(files: list[str]) -> str:
    """Get context for AI agent."""
    sm = SpecMemClient()

    # Get context bundle
    bundle = sm.get_context_for_change(files)

    # Format for agent
    context = f"""
## Relevant Specifications

{bundle.tldr}

### Impacted Specs
{chr(10).join(f"- {s.path}: {s.summary}" for s in bundle.impacted)}

### Pinned Constraints
{chr(10).join(f"- {s.title}: {s.content[:200]}" for s in bundle.pinned)}

### Recommended Tests
{chr(10).join(f"- {t}" for t in bundle.recommended_tests)}

### Warnings
{chr(10).join(f"- {w}" for w in bundle.warnings)}
"""
    return context
```

### Cursor Integration

Create a Cursor rule that uses SpecMem:

```python
# .cursor/rules/specmem.py
import subprocess
import json

def get_specmem_context(files: list[str]) -> dict:
    """Get SpecMem context for changed files."""
    result = subprocess.run(
        ["specmem", "impact", "--files"] + files + ["--format", "json"],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)

# In cursor.json
{
    "rules": [
        "Before modifying code, check SpecMem for relevant specifications",
        "Run: specmem impact --files <changed_files> --tests"
    ]
}
```

### Claude Code Integration

Add to `Claude.md`:

```markdown
# SpecMem Integration

This project uses SpecMem for specification management.

## Before Making Changes

1. Query relevant specs:
   ```bash
   specmem query "<your change description>"
   ```

2. Check impact:
   ```bash
   specmem impact --files <files_to_change>
   ```

3. Validate after changes:
   ```bash
   specmem validate
   ```

## Context Files

- `.specmem/agent_context.md` - Project overview
- `.specmem/agent_memory.json` - All specifications
```

## REST API Integration

### Start the Server

```bash
specmem serve --host 0.0.0.0 --port 8000
```

### API Endpoints

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Query specs
response = requests.get(f"{BASE_URL}/specs/search", params={
    "q": "authentication",
    "top_k": 5,
})
specs = response.json()

# Analyze impact
response = requests.post(f"{BASE_URL}/impact", json={
    "files": ["src/auth/service.py"],
})
impact = response.json()

# Validate
response = requests.post(f"{BASE_URL}/validate")
issues = response.json()
```

### Agent HTTP Client

```python
class SpecMemAgent:
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url

    def get_context(self, files: list[str]) -> dict:
        response = requests.post(
            f"{self.base_url}/context",
            json={"files": files},
        )
        return response.json()

    def query(self, query: str, top_k: int = 5) -> list[dict]:
        response = requests.get(
            f"{self.base_url}/specs/search",
            params={"q": query, "top_k": top_k},
        )
        return response.json()
```

## MCP Server (Model Context Protocol)

### Configuration

Add to your MCP config:

```json
{
  "mcpServers": {
    "specmem": {
      "command": "specmem",
      "args": ["mcp-serve"],
      "env": {}
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `specmem_query` | Search specifications |
| `specmem_impact` | Analyze change impact |
| `specmem_validate` | Validate specifications |
| `specmem_context` | Get context for files |

### Usage in Agent

```
User: What are the authentication requirements?

Agent: [calls specmem_query("authentication requirements")]

SpecMem Response:
- auth/requirements.md: JWT-based authentication with refresh tokens
- security/constraints.md: All endpoints require authentication
```

## Kiro Integration

### Steering File

Create `.kiro/steering/specmem.md`:

```markdown
---
inclusion: always
---

# SpecMem Integration

This project uses SpecMem for specification management.

## Commands

- `specmem query "<query>"` - Search specifications
- `specmem impact --files <files>` - Analyze impact
- `specmem validate` - Check spec quality

## Before Changes

Always check relevant specifications before modifying code:

1. Query specs related to your change
2. Verify alignment with requirements
3. Run impact analysis
4. Update specs if needed
```

### Hook

Create `.kiro/hooks/specmem-check.json`:

```json
{
  "name": "SpecMem Check",
  "trigger": "on_file_save",
  "pattern": "*.py",
  "action": {
    "type": "shell",
    "command": "specmem impact --files ${file} --tests --format list"
  }
}
```

## Best Practices

### 1. Keep Context Fresh

```bash
# Add to pre-commit hook
specmem scan
specmem build
```

### 2. Validate Before Commit

```yaml
# .github/workflows/validate.yml
- name: Validate Specs
  run: specmem validate --strict
```

### 3. Include in Agent Prompts

```markdown
## Context Awareness

Before making changes:
1. Check `.specmem/agent_context.md` for project overview
2. Query relevant specs with `specmem query`
3. Verify changes align with specifications
```

### 4. Track Spec Drift

```bash
# Weekly drift check
specmem diff drift
```
