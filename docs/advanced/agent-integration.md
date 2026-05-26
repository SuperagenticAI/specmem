# Agent Integration

Integrate SpecMem with AI coding agents for enhanced context awareness.

## Overview

SpecMem provides context to AI agents through several integration paths:

1. **Agent Experience Pack**: Pre-built context files under `.specmem/`
2. **Guidance routing**: Deterministic context selection from agent instruction files
3. **Python API**: Direct integration for custom tools and agents
4. **REST API**: HTTP-based integration
5. **MCP Server**: Model Context Protocol integration

## Agent Experience Pack

The simplest integration is to let agents read from the `.specmem/` directory.

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

### Agent Guidance Sources

SpecMem indexes repository-level agent guidance as first-class memory blocks
during `specmem scan` and `specmem build`. Supported sources include:

| Source | Files |
|--------|-------|
| Generic agents | `AGENTS.md`, `AGENT.md` |
| Codex skills | `.codex/skills/*/SKILL.md` |
| Claude | `CLAUDE.md`, `.claude/skills/*/SKILL.md` |
| Cursor | `.cursorrules`, `cursor.rules`, `.cursor/rules/*.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` |
| Gemini CLI | `GEMINI.md` |
| OpenCode | `OPENCODE.md` |
| Qwen Code | `QWEN.md` |
| Kiro | `.kiro/steering/*.md` |

Instruction files are pinned by default so core architectural intent survives
ordinary vector ranking. Skills are indexed as procedural memory but are not
pinned, because agents should retrieve them when the task matches the skill.

### Preview Agent Context

Use `specmem guidelines context` to show what an agent should load for a task
before semantic vector search runs:

```bash
specmem guidelines context \
  --file src/auth.py \
  --task "change authentication flow and update tests"
```

The command groups memory into always-on guidance, file-scoped guidance, and
candidate skills. Add `--robot` to return JSON for agent tooling.

### Trace Query Results

Use `--trace` on `specmem query` to explain memory routing and result metadata:

```bash
specmem query "What constraints apply before changing authentication?" \
  --file src/auth.py \
  --trace
```

The trace shows deterministic guidance layers and the semantic vector results
used for recall.

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

- `.specmem/agent_context.md`: Project overview
- `.specmem/agent_memory.json`: All specifications
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

SpecMem provides a full MCP server for integration with Kiro and other MCP-compatible tools.

### Configuration

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

### Available Tools

| Tool | Description |
|------|-------------|
| `specmem_query` | Search specifications by natural language |
| `specmem_impact` | Analyze change impact on specs and tests |
| `specmem_context` | Get optimized context bundle for files |
| `specmem_tldr` | Get TL;DR summary of key specs |
| `specmem_coverage` | Analyze spec coverage and test gaps |
| `specmem_validate` | Validate specifications for quality issues |

### Usage in Agent

```
User: What are the authentication requirements?

Agent: [calls specmem_query("authentication requirements")]

SpecMem Response:
- auth/requirements.md: JWT-based authentication with refresh tokens
- security/constraints.md: All endpoints require authentication
```

### Workflow Example

```
# Before making changes
specmem_impact(files: ["src/auth/service.py"])
specmem_context(files: ["src/auth/service.py"], token_budget: 4000)

# After changes
specmem_validate()
specmem_coverage(feature: "authentication")
```

For detailed MCP server documentation, see [MCP Server API](../api/mcp-server.md).

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
