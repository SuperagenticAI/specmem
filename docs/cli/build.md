# specmem build

Build the Agent Experience Pack and vector memory index.

## Usage

```bash
specmem build [OPTIONS] [PATH]
```

## Description

`specmem build` loads structured specs and agent guidance, generates
embeddings, writes them to the configured vector backend, and creates the
`.specmem/` Agent Experience Pack.

The command uses `.specmem.toml` from the target repository when present.

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `PATH` | Repository path | `.` |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output`, `-o` | Output directory | `<PATH>/.specmem` |
| `--optimize-skills` | Use validated optimized skill artifacts from `.specmem/skillopt` when available | `false` |

## Inputs

`specmem build` includes:

- Structured specifications from enabled adapters, such as Kiro, Spec Kit, and Tessl
- Agent instruction files, such as `AGENTS.md`, `CLAUDE.md`, Cursor rules, and Copilot instructions
- Agent skills from `.codex/skills/*/SKILL.md` and `.claude/skills/*/SKILL.md`

Instruction files are pinned in memory by default. Skill files are indexed as
procedural memory and selected by task intent.

Optimized skill artifacts are opt-in. Run `specmem guidelines optimize` to
validate and promote a candidate skill, then build with `--optimize-skills` to
index the accepted `best_skill.md` instead of the raw source skill. Artifacts are
ignored if the source skill changed after validation.

See [Optimized Skills](../user-guide/optimized-skills.md) for the full workflow.

## Generated Files

| File | Purpose |
|------|---------|
| `.specmem/agent_memory.json` | Memory blocks with metadata |
| `.specmem/agent_context.md` | Human-readable project context |
| `.specmem/knowledge_index.json` | Keyword index for quick lookup |
| Configured vector path | Embeddings for semantic retrieval |

## Examples

### Build Current Repository

```bash
specmem build
```

### Build Another Repository

```bash
specmem build ../service-api
```

### Write Pack to a Custom Directory

```bash
specmem build . --output ./build/specmem
```

### Build With Validated Optimized Skills

```bash
specmem build --optimize-skills
```

### Build with Qdrant

Configure Qdrant in `.specmem.toml`:

```toml
[vectordb]
backend = "qdrant"
path = ".specmem/qdrant"
qdrant_url = "http://localhost:6333"
qdrant_collection = "specmem"
```

Then run:

```bash
specmem build
```

## See Also

- [specmem scan](scan.md)
- [specmem query](query.md)
- [Agent Memory Patterns](../advanced/agent-memory-patterns.md)
