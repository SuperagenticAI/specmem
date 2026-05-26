# specmem scan

Scan a repository for specs and agent guidance.

## Usage

```bash
specmem scan [OPTIONS] [PATH]
```

## Description

`specmem scan` detects supported specification frameworks and agent guidance
files in a repository. It reports how many memory blocks SpecMem can load, but
it does not write the vector index. Use `specmem build` to create the Agent
Experience Pack and embeddings.

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `PATH` | Repository path to scan | `.` |

## Supported Specification Sources

| Source | Files |
|--------|-------|
| Kiro | `.kiro/specs/**/*.md` |
| Cursor specs | `cursor.json`, `.cursorrules` |
| Claude context | `Claude.md`, `CLAUDE.md` |
| Spec Kit | `.speckit` files |
| Tessl | `.tessl` files |

## Supported Agent Guidance Sources

| Source | Files |
|--------|-------|
| Generic agents | `AGENTS.md`, `AGENT.md` |
| Codex skills | `.codex/skills/*/SKILL.md` |
| Claude skills | `.claude/skills/*/SKILL.md` |
| Cursor rules | `.cursorrules`, `cursor.rules`, `.cursor/rules/*.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` |
| Gemini CLI | `GEMINI.md` |
| OpenCode | `OPENCODE.md` |
| Qwen Code | `QWEN.md` |
| Kiro steering | `.kiro/steering/*.md` |

## Examples

### Scan Current Repository

```bash
specmem scan
```

### Scan Another Repository

```bash
specmem scan ../service-api
```

### Guidance-only Repository

`specmem scan` works even when no structured spec framework is present, as long
as the repository contains supported agent guidance files.

```bash
specmem scan ./agent-guidance-repo
```

## Output

The command prints detected adapters, detected agent guidance, and a count of
memory blocks by type. If no specs or guidance files are found, it exits with a
non-zero status and lists supported inputs.

## See Also

- [specmem build](build.md)
- [specmem guidelines](guidelines.md)
- [Agent Integration](../advanced/agent-integration.md)
