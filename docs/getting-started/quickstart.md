# 🚀 Quick Start

Get SpecMem running in under 2 minutes.

## Try the Demo (30 seconds)

See SpecMem in action with its own specifications:

```bash
pip install specmem[local]
specmem demo
```

This opens a dashboard showing SpecMem's own specs - you'll see:
- 📊 All indexed specifications
- 🔗 Relationships between specs and code
- 💚 Project health score
- 📈 Spec coverage metrics

## Set Up Your Project (2 minutes)

### Step 1: Install

```bash
pip install specmem[local]
```

### Step 2: Initialize

```bash
cd your-project
specmem init
```

This creates a `.specmem.toml` config file.

### Step 3: Scan Your Specs

```bash
specmem scan
```

SpecMem automatically detects and indexes specs from:
- `.kiro/specs/` (Kiro)
- `CLAUDE.md` (Claude Code)
- `.cursorrules` (Cursor)
- And more...

### Step 4: Launch Dashboard

```bash
specmem serve
```

Open http://localhost:8765 to see your specs!

## What You'll See

### Spec Overview
All your specifications in one place, searchable and organized.

### Health Score
A grade (A-F) showing your project's spec health:
- Are specs linked to code?
- Are specs up to date?
- Are acceptance criteria tested?

### Coverage Report
See which acceptance criteria have tests and which don't:
```bash
specmem cov
```

### Impact Analysis
Before changing code, see which specs are affected:
```bash
specmem impact --files src/auth/service.py
```

## Kiro Integration

If you use Kiro, add SpecMem as an MCP server for automatic spec awareness:

```json
// .kiro/settings/mcp.json
{
  "mcpServers": {
    "specmem": {
      "command": "specmem-mcp",
      "args": []
    }
  }
}
```

Now Kiro's agent can query your specs automatically!

## Next Steps

- [Core Concepts](../user-guide/concepts.md) - Understand how SpecMem works
- [CLI Reference](../cli/init.md) - All available commands
- [Web UI Guide](../user-guide/web-ui.md) - Dashboard features
- [MCP Integration](../api/mcp-server.md) - Agent integration
