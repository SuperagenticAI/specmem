# Agent Memory Patterns

Coding-agent memory works best as a layered system. A single vector index is
useful for recall, but it should not be the only mechanism that decides what an
agent sees. Project instructions, file-scoped rules, procedural skills, and
structured specifications each need different routing rules.

## Architecture

| Layer | Purpose | SpecMem source |
|-------|---------|----------------|
| Project guidance | Always-on project intent, coding rules, and architectural constraints | `AGENTS.md`, `CLAUDE.md`, Copilot instructions, Kiro steering |
| File-scoped guidance | Rules that apply only to matching paths | Cursor `.mdc` rules, Copilot `applyTo`, Kiro file patterns |
| Procedural skills | Repeatable workflows loaded when relevant | `SKILL.md` files |
| Structured specifications | Requirements, decisions, tasks, and design notes | Kiro, Spec Kit, Tessl, Power specs |
| Session memory | Past implementation context and decisions | Session imports and generated notes |
| Retrieval index | Semantic recall over specs and knowledge | Qdrant, LanceDB, Chroma |

## Retrieval Strategy

Use deterministic routing before semantic search:

1. Include pinned project instructions first.
2. Select file-scoped rules by changed file path.
3. Select procedural skills by task intent.
4. Run vector search over specs, guidance, and prior knowledge.
5. Apply metadata filters for status, source, tags, and file scope.
6. Prefer active specs. Include deprecated or legacy memory only when requested.

This prevents a stale but semantically similar memory from outranking a small
rule that is always valid.

## Supported Agent Sources

SpecMem indexes common coding-agent guidance files during `specmem scan` and
`specmem build`.

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

Instruction files are pinned by default. Skills are indexed as procedural
memory, but they are not pinned because agents should load them only when the
task matches the skill.

## Demo Flow

Build the memory index:

```bash
specmem build
```

Preview deterministic context routing before vector search:

```bash
specmem guidelines context \
  --file src/auth.py \
  --task "change authentication flow and update tests"
```

Query memory and show the trace:

```bash
specmem query "What constraints apply before changing authentication?" \
  --file src/auth.py \
  --trace
```

The trace explains four layers:

| Layer | Meaning |
|-------|---------|
| `always_on` | Pinned project guidance that applies before semantic retrieval |
| `file_scoped` | Guidance whose file pattern matches `--file` |
| `skills` | Procedural memory matched to the query intent |
| `vector` | Top semantic matches from the configured vector backend |

## Qdrant Configuration

Qdrant is useful when you need server deployment, metadata filters, and room for
hybrid retrieval. SpecMem also supports LanceDB and Chroma for local or smaller
setups.

```toml
[vectordb]
backend = "qdrant"
path = ".specmem/qdrant"
qdrant_url = "http://localhost:6333"
qdrant_collection = "specmem"
```

For Qdrant Cloud:

```toml
[vectordb]
backend = "qdrant"
path = ".specmem/qdrant"
qdrant_url = "https://your-cluster.qdrant.io"
qdrant_api_key = "${QDRANT_API_KEY}"
qdrant_collection = "specmem"
```

Start with dense vectors and payload filters for `status`, `source`, `tags`,
and `pinned`. Add sparse vectors or reranking only after measuring retrieval
misses.

## References

- [AGENTS.md open format](https://github.com/openai/agents.md)
- [Cursor project rules](https://docs.cursor.com/context/rules)
- [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills)
- [GitHub Copilot custom instructions](https://github.blog/changelog/2025-07-23-github-copilot-coding-agent-now-supports-instructions-md-custom-instructions/)
- [Qdrant agentic vector search guide](https://qdrant.tech/articles/agentic-builders-guide/)
