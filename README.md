<p align="center">
  <img src="docs/assets/logo.png" alt="SpecMem Logo" width="200" />
</p>

<h1 align="center">SpecMem</h1>

<p align="center">
  <strong>🧠 Unified Agent Experience and Pragmatic Memory for Every Coding Agent</strong>
</p>

<p align="center">
  <em>The first-ever Agent Experience (AgentEx) platform built for AI coding agents</em>
</p>

<p align="center">
  <a href="https://superagenticai.github.io/specmem/">📚 Documentation</a> •
  <a href="https://superagenticai.github.io/specmem/getting-started/installation/">🚀 Getting Started</a> •
  <a href="https://github.com/SuperagenticAI/specmem">⭐ GitHub</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="License" />
  <img src="https://img.shields.io/badge/status-alpha-orange.svg" alt="Status" />
</p>

---

## 🎯 The Problem

Modern coding agents (Kiro, SpecKit, Tessl, Claude Code, Cursor, etc.) can **generate files**, **follow tasks**, and **implement features**, but the industry faces critical challenges:

### 📄 Markdown Madness & Verbosity

Today's coding agents generate **mountains of markdown files**. Developers are drowning in `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `requirements.md`, `design.md`... **What happens to all these specs after features are built?** Nobody has figured out how to turn this chaos into better Agent Experience.

### 🔒 Vendor Lock-In & Format Fragmentation

Every coding agent uses **its own proprietary format**. Claude uses `CLAUDE.md`, Cursor uses `.cursorrules`, Kiro uses `.kiro/specs/`. This creates **massive IDE lock-in**. Switching agents means rewriting all your specs. Your project knowledge is trapped in one tool.

### 🧠 Agents Have Amnesia

Modern coding agents suffer from **catastrophic forgetting**. Sessions reset, context is lost, previous decisions vanish. Agents write code without knowing your specs, acceptance criteria, or earlier decisions.

### ⚡ Wasted Compute & Slow CI

Without understanding **what changed**, agents trigger full test runs for every tiny change, wasting compute and slowing CI pipelines.

### 📉 No Agent Experience (AgentEx) Layer

We have **DevEx** (Developer Experience) for humans. But where is **AgentEx** for AI coding agents? There's no unified memory layer, no context optimization, no impact analysis.

> **These issues cause:** regressions, misaligned implementations, slow CI pipelines, unpredictable agent behavior, and increased costs.
>
> **The industry lacks a Cognitive Memory + AgentEx platform to fix this. Until now.**

---

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
# Using pip
pip install specmem

# Using uv (recommended - faster)
uv pip install specmem

# Or run directly with uvx
uvx specmem --help
```

```python
from specmem import SpecMemClient

sm = SpecMemClient()
bundle = sm.get_context_for_change(["auth/service.py"])
print(bundle.tldr)
```

---

## ✨ Key Features

### Core Features

| Feature | Description |
|---------|-------------|
| **🔌 Multi-Framework Adapters** | Parse specs from Kiro, SpecKit, Tessl, Claude Code, Cursor, Codex, Factory, Warp, Gemini CLI |
| **🧠 Intelligent Memory** | Vector-based semantic search with LanceDB, ChromaDB, Qdrant, or AgentVectorDB |
| **📊 SpecImpact Graph** | Bidirectional relationships between specs, code, and tests |
| **⏱️ SpecDiff Timeline** | Track spec evolution, detect drift, find contradictions |
| **✅ SpecValidator** | Quality assurance with 6 validation rules (structure, timeline, duplicates, constraints, acceptance criteria, contradictions) |
| **📈 Spec Coverage** | Analyze gaps between acceptance criteria and tests with suggestions |
| **🎯 Test Mapping Engine** | Map tests to specs across pytest, jest, vitest, and more |
| **💚 Health Score** | Project health grades (A-F) with improvement suggestions |
| **🌐 Web UI** | Interactive dashboard with live sync, filtering, and WebSocket updates |

### Advanced Features

| Feature | Description |
|---------|-------------|
| **☁️ Cloud Embeddings** | Support for OpenAI, Google, Together AI embedding providers |
| **📜 Coding Guidelines** | Aggregate and view guidelines from Kiro steering, CLAUDE.md, .cursorrules |
| **🔄 Spec Lifecycle** | Prune stale specs, generate specs from code, compress verbose specs |
| **🔍 Kiro Session Search** | Index and search Kiro chat sessions for context |
| **⚙️ Kiro Config Indexer** | Index hooks, steering files, and MCP configurations |
| **📤 Static Dashboard** | Export specs to a static HTML dashboard for GitHub Pages |
| **🤖 GitHub Action** | CI integration with coverage thresholds and PR comments |
| **🔌 MCP Server** | Model Context Protocol server for AI agent integration |
| **⚡ Kiro Powers** | Native Kiro IDE integration as a Power |
| **🌊 Streaming Context API** | Token-aware context optimization with streaming support |

---

## 🔄 The Killer Feature

**Swap agents without losing context.** SpecMem creates a unified, normalized, agent-agnostic context layer.

Switch from **Kiro → SpecKit → Tessl → Claude Code → Cursor** without rewriting spec files or losing project knowledge.

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

---

## 🧠 Living Documentation & Memory

SpecMem transforms your specifications into **living documentation** that:

1. **Stays in sync** - File watcher detects changes and re-indexes automatically
2. **Provides context** - AI agents query specs via MCP to understand your project
3. **Tracks coverage** - See which acceptance criteria have tests
4. **Shows relationships** - Impact graph connects specs ↔ code ↔ tests

**How it acts as "memory" for agents:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Agent asks: "What are the auth requirements?"                  │
│                           │                                      │
│                    ┌──────▼──────┐                               │
│                    │   SpecMem   │  ← Semantic search            │
│                    │   Memory    │                               │
│                    └──────┬──────┘                               │
│                           │                                      │
│  Returns: Relevant specs, related code, suggested tests         │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Try It Now (Demo)

```bash
# See SpecMem in action with its own specs
specmem demo
```

This launches the Web UI with SpecMem's own specifications - dogfooding at its finest!

### CLI

```bash
# Initialize SpecMem in your project
specmem init

# Initialize with Kiro hooks for automation
specmem init --hooks

# Scan and index your specifications
specmem scan

# Build the Agent Experience Pack
specmem build

# Query your specs
specmem query "What are the authentication requirements?"

# Analyze impact of code changes
specmem impact --files src/auth/service.py

# Check spec coverage
specmem cov

# Get test suggestions for uncovered criteria
specmem cov suggest auth-feature

# Check project health score
specmem health

# Validate spec quality
specmem validate

# View spec diff/history
specmem diff auth.login
specmem history auth.login

# Lifecycle management
specmem prune --orphaned          # Archive orphaned specs
specmem generate src/             # Generate specs from code
specmem compress --all            # Compress verbose specs

# View coding guidelines
specmem guidelines

# Kiro configuration
specmem kiro-config               # Show all Kiro config
specmem steering --file src/app.py  # Get applicable steering

# Session search (Kiro)
specmem sessions search "auth"    # Search chat sessions
specmem sessions link             # Link sessions to specs

# Export static dashboard
specmem export data               # Export spec data to JSON
specmem export build              # Build static HTML dashboard

# Graph commands
specmem graph impact src/auth.py  # Show affected specs/tests
specmem graph show spec:auth      # Show node relationships
specmem graph export --format dot # Export graph

# Launch Web UI
specmem demo
```

### Python API

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

# Analyze spec coverage
coverage = sm.get_coverage()
print(f"Coverage: {coverage.coverage_percentage:.1f}%")
```

---

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

---

## ⚡ Built for Kiro

SpecMem was built during **Kiroween 2025** with first-class Kiro support. Your `.kiro/specs/` become living, searchable agent memory.

### ⚡ Kiro Powers Integration

Install SpecMem as a **Kiro Power** for seamless IDE integration:

- Query specs without leaving Kiro
- Get context-aware suggestions in real-time
- Analyze impact of changes instantly

### 🔗 MCP Server

Full **Model Context Protocol** support. Kiro's agent can query your specs, analyze impact, and get optimized context automatically.

```json
// .kiro/settings/mcp.json
{
  "mcpServers": {
    "specmem": {
      "command": "specmem-mcp",
      "args": [],
      "env": { "SPECMEM_WORKSPACE": "${workspaceFolder}" },
      "autoApprove": ["specmem_query", "specmem_tldr", "specmem_coverage"]
    }
  }
}
```

**Available MCP Tools:**

| Tool | Description |
|------|-------------|
| `specmem_query` | Search specifications by natural language |
| `specmem_impact` | Analyze change impact on specs and tests |
| `specmem_context` | Get optimized context bundle for files |
| `specmem_tldr` | Get TL;DR summary of key specs |
| `specmem_coverage` | Analyze spec coverage and test gaps |
| `specmem_validate` | Validate specifications for quality issues |

### 📄 Native Kiro Adapter

First-class support for `.kiro/specs/` structure:

| File | What SpecMem Extracts |
|------|----------------------|
| `requirements.md` | User stories, acceptance criteria, constraints |
| `design.md` | Architecture decisions, component interfaces |
| `tasks.md` | Implementation checklist, progress tracking |

### 🎣 Hooks & Steering

SpecMem includes pre-configured hooks and steering files:

```
.kiro/
├── settings/mcp.json       # MCP server config
├── hooks/
│   ├── spec-coverage.yaml  # Check coverage on test save
│   ├── spec-validation.yaml # Validate on spec edit
│   └── impact-analysis.yaml # Analyze impact on code change
└── steering/
    ├── specmem-development.md  # Always included
    ├── spec-writing.md         # When editing specs
    └── python-style.md         # When editing Python
```

See [Kiro Integration Guide](https://superagenticai.github.io/specmem/user-guide/kiro-integration/) for details.

---

## 🤖 GitHub Action

Integrate SpecMem into your CI/CD pipeline:

```yaml
# .github/workflows/specmem.yml
name: Spec Analysis
on: [pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: SuperagenticAI/specmem/.github/actions/specmem@main
        with:
          commands: cov,health,validate
          comment_on_pr: true
          coverage_threshold: 80
          health_threshold: B
```

**Features:**
- 📊 Coverage, health, and validation checks
- 💬 Automatic PR comments with results
- 🚦 Configurable thresholds for quality gates
- 📈 Static dashboard deployment to GitHub Pages

---

## 📤 Static Dashboard

Export your specs to a static HTML dashboard:

```bash
# Generate and preview locally
specmem export data
specmem export build
python -m http.server -d .specmem/static 8080
```

Or deploy to GitHub Pages with the dashboard action:

```yaml
- uses: SuperagenticAI/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

---

## 🔌 Supported Frameworks

### Spec-Driven Development (Priority)

| Framework | Adapter | File Patterns |
|-----------|---------|---------------|
| **Kiro** | `kiro` | `.kiro/specs/**/*.md` |
| **SpecKit** | `speckit` | `.speckit/**/*.yaml` |
| **Tessl** | `tessl` | `.tessl/**/*.md` |

### Commercial Coding Agents

| Framework | Adapter | File Patterns |
|-----------|---------|---------------|
| Claude Code | `claude` | `Claude.md`, `CLAUDE.md` |
| Cursor | `cursor` | `cursor.json`, `.cursorrules` |
| Codex | `codex` | `.codex/**/*.md` |
| Factory | `factory` | `.factory/**/*.yaml` |
| Warp | `warp` | `.warp/**/*.md` |
| Gemini CLI | `gemini` | `GEMINI.md`, `.gemini/**/*.md` |

---

## 🗄️ Vector Database Backends

SpecMem supports multiple vector database backends:

| Backend | Install | Best For |
|---------|---------|----------|
| **LanceDB** (default) | `pip install specmem[local]` | Local development, no server needed |
| **ChromaDB** | `pip install specmem[chroma]` | Local/embedded with persistence |
| **Qdrant** | `pip install specmem[qdrant]` | Production, distributed deployments |
| **AgentVectorDB** | Built-in | Lightweight, in-memory |

Switch backends:
```bash
specmem vector-backend chroma
```

---

## ☁️ Cloud Embedding Providers

Use cloud embedding providers for better semantic search:

| Provider | Install | Model |
|----------|---------|-------|
| **OpenAI** | `pip install specmem[openai]` | text-embedding-3-small |
| **Google** | `pip install specmem[google]` | embedding-001 |
| **Together AI** | `pip install specmem[together]` | togethercomputer/m2-bert |

Configure in `.specmem.toml`:
```toml
[embedding]
provider = "openai"
model = "text-embedding-3-small"
```

---

## ✅ Spec Validation Rules

SpecMem validates your specifications with 6 built-in rules:

| Rule | What It Checks |
|------|----------------|
| **Structure** | Required sections (requirements, design, tasks) exist |
| **Timeline** | Tasks follow logical order, no circular dependencies |
| **Duplicates** | No duplicate acceptance criteria or requirements |
| **Constraints** | Acceptance criteria are testable and measurable |
| **Acceptance Criteria** | EARS pattern compliance, INCOSE quality rules |
| **Contradictions** | No conflicting requirements across specs |

Run validation:
```bash
specmem validate
specmem validate --spec auth-feature --format json
```

---

## 📖 Documentation

Full documentation is available at **[superagenticai.github.io/specmem](https://superagenticai.github.io/specmem/)**

- [Installation Guide](https://superagenticai.github.io/specmem/getting-started/installation/)
- [Quick Start](https://superagenticai.github.io/specmem/getting-started/quickstart/)
- [User Guide](https://superagenticai.github.io/specmem/user-guide/concepts/)
- [CLI Reference](https://superagenticai.github.io/specmem/cli/init/)
- [Python API](https://superagenticai.github.io/specmem/api/client/)
- [Advanced Topics](https://superagenticai.github.io/specmem/advanced/)

---

## 🛠️ Development

```bash
# Clone the repository
git clone https://github.com/SuperagenticAI/specmem.git
cd specmem

# Using uv (recommended)
uv sync --dev
uv run pytest

# Or using pip
pip install -e ".[dev]"
pytest
```

### Using uv

SpecMem supports [uv](https://docs.astral.sh/uv/) for fast dependency management:

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies from lock file
uv sync

# Run specmem commands
uv run specmem --help

# Run tests
uv run pytest

# Add a new dependency
uv add <package>
```

---

## 📄 License

AGPL-3.0 - see [LICENSE](LICENSE) for details.

For commercial licensing options, contact team@super-agentic.ai

---

## 🏢 About

**SpecMem** is developed by [Superagentic AI](https://super-agentic.ai) as part of the Kiroween Hackathon, December 2025.
