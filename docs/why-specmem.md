# Why SpecMem?

## The Problem

Modern AI coding agents are powerful but have critical limitations:

### 🧠 Agents Have Amnesia
Every session starts fresh. Your agent doesn't remember:
- What you built yesterday
- Your project's requirements
- Previous design decisions
- Which tests cover which features

### 📄 Markdown Chaos
AI agents generate mountains of markdown:
- `requirements.md`, `design.md`, `tasks.md`
- `CLAUDE.md`, `.cursorrules`, `AGENTS.md`

**What happens to all these specs after features are built?** They sit there, forgotten, while your agent writes code that contradicts them.

### 🔒 Vendor Lock-In
Each agent uses its own format:
- Kiro: `.kiro/specs/`
- Claude Code: `CLAUDE.md`
- Cursor: `.cursorrules`

Switch agents? Rewrite everything.

### ⚡ Wasted CI Time
Without knowing what changed, agents trigger full test runs for every tiny change.

## The Solution

**SpecMem gives your AI coding agent a memory.**

```
┌─────────────────────────────────────────────────────────────────┐
│                         Your Project                            │
├─────────────────────────────────────────────────────────────────┤
│  .kiro/specs/   CLAUDE.md   .cursorrules   requirements.md      │
│       │             │            │              │                │
│       └─────────────┴────────────┴──────────────┘                │
│                           │                                      │
│                    ┌──────▼──────┐                               │
│                    │   SpecMem   │  ← Unified Memory             │
│                    └──────┬──────┘                               │
│                           │                                      │
│              ┌────────────┼────────────┐                         │
│              │            │            │                         │
│         Dashboard    MCP Server    CLI                           │
│              │            │            │                         │
│           You         Agents      Scripts                        │
└─────────────────────────────────────────────────────────────────┘
```

## Key Benefits

### 1. Persistent Memory
Your specs are indexed and searchable. Agents can query them via MCP:
```
Agent: "What are the authentication requirements?"
SpecMem: Returns relevant specs with context
```

### 2. Agent-Agnostic
One unified format. Switch from Kiro to Claude Code to Cursor without losing context.

### 3. Visibility
See your project's spec health at a glance:
- Which specs are tested?
- Which specs are stale?
- Which specs have no code references?

### 4. Smart Testing
Know which tests to run when code changes:
```bash
specmem impact --files src/auth/service.py
# Shows: auth-requirements.md, auth-design.md
# Suggests: test_auth.py, test_login.py
```

## Who Is SpecMem For?

### Kiro Users
Your `.kiro/specs/` become living, searchable memory. The agent knows your requirements when writing code.

### Multi-Agent Teams
Use Kiro for specs, Claude Code for implementation, Cursor for debugging - all sharing the same context.

### Team Leads
Dashboard shows project health. See which specs need attention before they become problems.

## Quick Comparison

| Without SpecMem | With SpecMem |
|-----------------|--------------|
| Agent forgets specs | Agent queries specs |
| Specs rot in folders | Specs are living docs |
| Full test runs | Targeted test runs |
| Manual context sharing | Automatic context |
| One agent's format | Any agent's format |

## Get Started

```bash
pip install specmem[local]
specmem demo  # See it in action
```

Then for your project:
```bash
cd your-project
specmem init
specmem scan
specmem serve  # Open dashboard
```

[→ Quick Start Guide](getting-started/quickstart.md)
