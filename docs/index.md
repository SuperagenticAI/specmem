---
title: Home
hide:
  - navigation
  - toc
---

<div class="hero">
  <div class="hero-logo">
    <img src="assets/logo.png" alt="SpecMem Logo" />
  </div>
  <h1 class="gradient-text">SpecMem</h1>
  <p class="hero-tagline gradient-text-light">Unified Agent Experience and Pragmatic Memory for Every Coding Agent</p>
  <p class="hero-description">AI coding agents forget everything between sessions, lock you into proprietary formats, and generate mountains of markdown nobody maintains. SpecMem fixes this: persistent memory, agent portability, and specs that stay alive.</p>
  <p class="hero-features">Executable Specs · Living Documentation · Impact-Aware Context</p>
  <p class="hero-badges">Open-source · Local-first · Agent-agnostic</p>
  <p class="hero-highlight">🏆 First ever Agent Experience tool built for Coding Agents</p>
  <div class="hero-buttons">
    <a href="getting-started/installation/" class="md-button md-button--primary">🚀 Get Started</a>
    <a href="https://github.com/SuperagenticAI/specmem" class="md-button md-button--secondary">📦 View on GitHub</a>
  </div>
</div>

## 🎯 The Problem

### 📄 Markdown Madness & Verbosity

Today's coding agents generate **mountains of markdown files**. Developers using Claude Code, Cursor, or any AI coding tool are drowning in `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `requirements.md`, `design.md`... **What happens to all these specs after features are built?** Nobody has figured out how to turn this chaos into better Agent Experience.

### 🔒 Vendor Lock-In & Format Fragmentation

Every coding agent uses **its own proprietary format**. Claude uses `CLAUDE.md`, Cursor uses `.cursorrules`, Kiro uses `.kiro/specs/`. This creates **massive IDE lock-in**. Switching agents means rewriting all your specs. Your project knowledge is trapped in one tool.

### 🧠 Agents Have Amnesia

Modern coding agents suffer from **catastrophic forgetting**. Sessions reset, context is lost, previous decisions vanish. Agents write code without knowing your specs, acceptance criteria, or earlier decisions. This causes regressions and misaligned implementations.

### ⚡ Wasted Compute & Slow CI

Without understanding **what changed**, agents trigger full test runs for every tiny change. This wastes compute, slows CI pipelines, and blocks development.

### 📉 No Agent Experience (AgentEx) Layer

We have **DevEx** (Developer Experience) for humans. But where is **AgentEx** for AI coding agents? There's no unified memory layer, no context optimization, no impact analysis, no spec-to-test mapping.

<div class="consequences">
<p><strong>These issues cause:</strong> regressions, misaligned implementations, slow CI pipelines, unpredictable agent behavior, and increased costs.</p>
<p><strong>The industry lacks a Pragmatic Memory + Agent Experience platform to fix this</strong></p>
</div>

## ⚖️ Pragmatic SDD: Not Waterfall, Not Chaos

Spec-Driven Development has real problems: verbose docs, waterfall vibes, spec rot. But pure "vibe coding" means agents forget everything and repeat mistakes.

**SpecMem strikes the balance:**

- **Specs as Memory**: Not bureaucratic gates, but searchable knowledge
- **Selective Context**: SpecImpact gives agents only relevant specs, not everything
- **Living Docs**: SpecDiff detects drift, SpecValidator finds contradictions
- **Gradual Adoption**: Start with any format, no big-bang migration

## 💡 The Solution: SpecMem

**SpecMem** is the **first-ever Agent Experience (AgentEx) platform**: a unified, embeddable memory layer for AI coding agents.

### How SpecMem Solves Each Problem

| Problem | SpecMem Solution |
|---------|------------------|
| **Markdown Madness** | Concise spec templates, auto TL;DRs, living documentation |
| **Vendor Lock-In** | Agent-agnostic adapters: read ANY format, output to ANY agent |
| **Agent Amnesia** | Persistent cognitive memory with semantic search |
| **Wasted Compute** | SpecImpact selects only impacted specs/tests to execute |
| **No AgentEx** | Complete Agent Experience layer with context optimization |

```bash
pip install specmem
```

```python
from specmem import SpecMemClient

sm = SpecMemClient()
bundle = sm.get_context_for_change(["auth/service.py"])
print(bundle.tldr)
```

<div class="feature-grid">
  <div class="feature-card">
    <h3><span class="emoji">🔌</span> Multi-Framework Adapters</h3>
    <p>Parse specs from Kiro, SpecKit, Tessl, Claude Code, Cursor, Codex, Factory, Warp, Gemini CLI and more. One unified format for all your specifications.</p>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">🧠</span> Intelligent Memory</h3>
    <p>Vector-based semantic search with LanceDB, ChromaDB, or Qdrant. Pinned memory, session search, and token-aware context optimization keep critical intent available.</p>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">📊</span> SpecImpact Graph</h3>
    <p>Bidirectional relationships between specs, code, and tests. Know exactly what's affected by your changes.</p>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">⏱️</span> SpecDiff Timeline</h3>
    <p>Track spec evolution, detect drift, find contradictions, and manage deprecations over time.</p>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">✅</span> SpecValidator</h3>
    <p>Quality assurance for specifications. Detect contradictions, missing criteria, and duplicates automatically.</p>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">🎯</span> Selective Testing</h3>
    <p>Run only the tests that matter. Save CI time and compute costs with intelligent test selection.</p>
  </div>
</div>

## ⚡ Built for Kiro

SpecMem was built during **Kiroween 2025** with first-class Kiro support. Your `.kiro/specs/` become living, searchable agent memory.

<div class="feature-grid">
  <div class="feature-card">
    <h3><span class="emoji">⚡</span> Kiro Powers</h3>
    <p>Install SpecMem as a Kiro Power for seamless IDE integration. Query specs, analyze impact, and get context-aware suggestions without leaving Kiro.</p>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">🔗</span> MCP Server</h3>
    <p>Full Model Context Protocol support. Kiro's agent can query your specs, analyze impact, and get optimized context automatically via MCP tools.</p>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">🔍</span> Session Memory</h3>
    <p>Index and search Kiro coding sessions to recover prior decisions, debugging history, and architectural context across long-running work.</p>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">📄</span> Native Kiro Adapter</h3>
    <p>First-class support for <code>.kiro/specs/</code> structure: requirements.md, design.md, tasks.md parsed into searchable, trackable memory.</p>
  </div>
</div>

```json
// Add to your mcp.json for instant Kiro integration
{
  "mcpServers": {
    "specmem": {
      "command": "uvx",
      "args": ["specmem-mcp"]
    }
  }
}
```

## 🔄 The Killer Feature

**Swap agents without losing context.** SpecMem creates a unified, normalized, agent-agnostic context layer.

Switch from Kiro → SpecKit → Tessl → Claude Code → Cursor without rewriting spec files or losing project knowledge.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Your Project                            │
├─────────────────────────────────────────────────────────────────┤
│  .kiro/specs/   .speckit/   .tessl/   Claude.md   cursor.json   │
│       │             │          │          │            │         │
│       └─────────────┴──────────┴──────────┴────────────┘         │
│                           │                                      │
│                    ┌──────▼──────┐                               │
│                    │   SpecMem   │                               │
│                    │  Adapters   │                               │
│                    └──────┬──────┘                               │
│                           │                                      │
│                    ┌──────▼──────┐                               │
│                    │   SpecIR    │  ← Canonical Representation   │
│                    └──────┬──────┘                               │
│                           │                                      │
│         ┌─────────────────┼─────────────────┐                    │
│         │                 │                 │                    │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐            │
│  │ Vector DB   │   │ SpecImpact  │   │  SpecDiff   │            │
│  │ (LanceDB)   │   │   Graph     │   │  Timeline   │            │
│  └─────────────┘   └─────────────┘   └─────────────┘            │
│                           │                                      │
│                    ┌──────▼──────┐                               │
│                    │ AgentXPack  │  ← Output for any agent       │
│                    └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Try It Now

```bash
# See SpecMem in action with its own specs (dogfooding!)
specmem demo
```

This launches the Web UI with SpecMem's own specifications - the best way to explore the features.

=== "CLI"

    ```bash
    # Initialize SpecMem in your project
    specmem init

    # Scan and index your specifications
    specmem scan

    # Build the Agent Experience Pack
    specmem build

    # Query your specs
    specmem query "What are the authentication requirements?"

    # Search previous Kiro sessions
    specmem sessions search "architecture decision"

    # Analyze impact of code changes
    specmem graph impact src/auth/service.py

    # Launch Web UI
    specmem serve
    ```

=== "Python"

    ```python
    from specmem import SpecMemClient

    # Initialize client
    sm = SpecMemClient()

    # Get context for code changes
    bundle = sm.get_context_for_change(["auth/service.py"])
    print(bundle.tldr)

    # Query specifications
    specs = sm.query("authentication requirements")

    # Get impacted specs for changes
    impacted = sm.get_impacted_specs(["auth/service.py"])

    # Check for spec drift
    drift = sm.get_drift_report()
    ```

## 📦 Output: Agent Experience Pack

SpecMem generates a `.specmem/` directory containing everything your agents need:

```
.specmem/
├── agent_memory.json      # All specs with metadata and rankings
├── agent_context.md       # Human-readable summary
├── knowledge_index.json   # Keyword → SpecBlock mapping
├── impact_graph.json      # Code ↔ Spec relationships
└── vectordb/              # Embedded vector storage
```

## 🏢 About

**SpecMem** is developed by [Superagentic AI](https://super-agentic.ai) as part of the Kiroween Hackathon, December 2025.
