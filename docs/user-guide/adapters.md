# 🔌 Adapters

SpecMem adapters parse specifications from various AI coding agent frameworks.

## Supported Frameworks

### Spec-Driven Development Frameworks (Priority)

| Framework | Adapter | File Patterns |
|-----------|---------|---------------|
| Kiro | `kiro` | `.kiro/specs/**/*.md` |
| SpecKit | `speckit` | `.speckit/**/*.yaml` |
| Tessl | `tessl` | `.tessl/**/*.md` |

### Commercial Coding Agents

| Framework | Adapter | File Patterns |
|-----------|---------|---------------|
| **AGENTS.md** (AAIF) | `agents.md` | `**/AGENTS.md`, `**/AGENT.md` |
| Claude Code | `claude` | `Claude.md`, `CLAUDE.md` |
| Cursor | `cursor` | `cursor.json`, `.cursorrules` |

Codex, Factory, Warp, Cursor, OpenCode, Amp, and Aider consume **AGENTS.md**.
SpecMem indexes those files through the AGENTS.md adapter rather than invented
vendor trees (`.codex/**/*.md`, `.factory/**/*.yaml`, `.warp/**`). Gemini CLI's
`GEMINI.md` is found by the guidelines scanner, not a separate SpecAdapter.

---

## Spec-Driven Development Frameworks

These frameworks prioritize formal specifications and structured development workflows.

---

## Kiro Adapter

Parses Kiro's spec-driven development format. Kiro is the recommended framework for teams adopting Spec-Driven Development.

### Structure

```
.kiro/
└── specs/
    └── feature-name/
        ├── requirements.md
        ├── design.md
        └── tasks.md
```

### Example

```markdown
# Requirements Document

## Introduction
User authentication system for the application.

## Requirements

### Requirement 1
**User Story:** As a user, I want to log in securely.

#### Acceptance Criteria
1. WHEN a user enters valid credentials THEN the system SHALL authenticate
2. WHEN a user enters invalid credentials THEN the system SHALL reject
```

### Configuration

```toml
[adapters]
kiro = true

[adapters.kiro]
spec_dir = ".kiro/specs"
```

---

## SpecKit Adapter

Parses SpecKit's YAML-based specifications. SpecKit provides structured, machine-readable specs.

### Structure

```
.speckit/
├── features/
│   └── auth.yaml
├── constraints/
│   └── security.yaml
└── config.yaml
```

### Example

```yaml
# .speckit/features/auth.yaml
feature: user-authentication
version: 1.0.0

requirements:
  - id: AUTH-001
    title: User Login
    description: Users can log in with email and password
    priority: critical
    acceptance_criteria:
      - Valid credentials grant access
      - Invalid credentials show error
      - Account lockout after 5 failures

  - id: AUTH-002
    title: Password Reset
    description: Users can reset forgotten passwords
    priority: high
```

### Configuration

```toml
[adapters]
speckit = true

[adapters.speckit]
spec_dir = ".speckit"
```

---

## Tessl Adapter

Parses Tessl's markdown specifications. Tessl focuses on test-driven specifications.

### Structure

```
.tessl/
├── specs/
│   └── feature.md
└── config.toml
```

### Configuration

```toml
[adapters]
tessl = true

[adapters.tessl]
spec_dir = ".tessl/specs"
```

---

## Commercial Coding Agents

These adapters support popular commercial AI coding assistants.

---

## Claude Code Adapter

Parses Claude Code's markdown-based specifications.

### Files

- `Claude.md` or `CLAUDE.md` - Project context and rules

### Example

```markdown
# Project Context

## Overview
E-commerce platform built with Python and FastAPI.

## Architecture
- Backend: FastAPI with SQLAlchemy
- Database: PostgreSQL
- Cache: Redis
- Queue: Celery

## Coding Standards
- Type hints required for all functions
- Docstrings in Google format
- 100% test coverage for business logic

## Security Requirements
- All endpoints require authentication
- Input validation on all user data
- SQL injection prevention via ORM
```

### Configuration

```toml
[adapters]
claude = true

[adapters.claude]
files = ["Claude.md", "CLAUDE.md"]
```

---

## Cursor Adapter

Parses Cursor's configuration and rules.

### Files

- `cursor.json` - Project configuration
- `.cursorrules` - Custom rules and constraints

### Example cursor.json

```json
{
  "rules": [
    "Always use TypeScript strict mode",
    "Follow React best practices",
    "Use functional components with hooks"
  ],
  "context": {
    "framework": "Next.js",
    "styling": "Tailwind CSS"
  }
}
```

### Example .cursorrules

```
# Project Rules

## Code Style
- Use 2-space indentation
- Prefer const over let
- Use async/await over promises

## Architecture
- Follow clean architecture principles
- Keep components under 200 lines
- Extract reusable logic to hooks
```

### Configuration

```toml
[adapters]
cursor = true

[adapters.cursor]
config_file = "cursor.json"
rules_file = ".cursorrules"
```

---

## AGENTS.md Adapter

Parses the AAIF / Linux Foundation `AGENTS.md` standard. This is a **stable**
adapter (not experimental). Codex, Factory, Warp, Cursor, OpenCode, Amp, and
Aider all consume these files.

### Files

- `AGENTS.md` or `Agents.md` — official filename (repo root or nested)
- `AGENT.md` or `Agent.md` — aliases also accepted by the guidelines scanner

Closest-file-wins: a nested `AGENTS.md` applies to that subtree.

### Example

```markdown
# Project Rules

Keep pull requests focused and scoped to one change.

## Testing

Run unit tests before opening a PR.

## Style

Prefer typed Python.
```

Heading sections become knowledge SpecBlocks tagged `agents` / `agents.md`
plus a slug of the heading. A file with no headings becomes one pinned block.

### Configuration

```toml
[adapters]
# Auto-discovered; no extra config required
```

There are no first-class Codex, Factory, Warp, or Gemini SpecAdapters. Those
tools are covered by AGENTS.md (and, for Gemini CLI, the guidelines scanner's
`GEMINI.md` support). Do not invent `.codex/`, `.factory/`, or `.warp/` trees.

---

## Using Multiple Adapters

SpecMem can use multiple adapters simultaneously:

```toml
[adapters]
# Spec-Driven Development (recommended)
kiro = true
speckit = true
tessl = true

# Commercial agents
claude = true
cursor = true
```

When scanning, SpecMem merges specs from all enabled adapters:

```bash
specmem scan
```

```
🔍 Scanning for specifications...
✅ [kiro] Found 12 specs in .kiro/specs/
✅ [speckit] Found 5 specs in .speckit/
✅ [tessl] Found 3 specs in .tessl/
✅ [claude] Found 1 spec in Claude.md
✅ [cursor] Found 3 specs in cursor.json
📊 Total: 24 specifications indexed
```

## Adapter Priority

When specs conflict, priority is determined by:

1. **Explicit priority** in the spec
2. **Framework order** (configurable)
3. **Timestamp** (newer wins)

```toml
[adapters]
# Framework priority (first = highest)
# Spec-Driven Development frameworks take precedence
priority = ["kiro", "speckit", "tessl", "agents.md", "claude", "cursor"]
```

## Custom Adapters

See [Writing Adapters](../advanced/writing-adapters.md) for creating custom adapters.
