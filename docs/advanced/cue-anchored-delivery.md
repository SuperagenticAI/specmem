# Cue-Anchored Delivery

Experiment note for harness-owned SpecMem injection (Towards
[#16](https://github.com/SuperagenticAI/specmem/issues/16)).

## Problem

[Delivery, Not Storage: Cue-Anchored Working Memory](https://arxiv.org/abs/2607.20972)
shows that voluntary memory tools are often unused even when seeded. Facts held
only in the conversation are lost under compaction. Harness-owned deterministic
injection on cues `{path, symbol, semantic, event, temporal}` survives
compaction better than agent-initiated lookup.

SpecMem already has pinned and path-scoped routing plus MCP tools
(`specmem_query`, `specmem_impact`, `specmem_context`, `specmem_tldr`,
`specmem_coverage`, `specmem_validate`). Those MCP surfaces remain
**voluntary**. The weak `session_start` hook previously ran a vague natural
language `specmem query`, which still required the agent to treat the result as
optional context.

## Design principle: delivery, not storage

This experiment does **not** invent new SpecIR trigger fields or a new on-disk
memory format. It reuses existing SpecMem surfaces and changes **who owns
injection**:

| Cue (paper) | SpecMem delivery surface |
|-------------|--------------------------|
| event (`session_start`) | Kiro hook `specmem-session-context` runs `specmem guidelines context`; MCP `specmem_cues` with `cue=session_start` returns always-on layers + `get_tldr()` |
| path (file open/save) | Kiro hook `specmem-path-context` runs `specmem guidelines context --file ${file}`; MCP `specmem_cues` with `cue=path` + `files` returns file-scoped layers + `get_context_for_change()` |
| semantic / symbol / temporal | Vocabulary reserved on `specmem_cues`; currently falls back to session or path when files are present. No SpecIR schema changes. |

Hooks are the **primary** delivery story. MCP `specmem_cues` (and strengthened
docs on `specmem_context` / `specmem_tldr`) stay voluntary-compatible for
agents that prefer tools.

## Map to existing surfaces

- **Guidelines routing**: `GuidelinesAggregator.build_context()` (always_on,
  file_scoped, skills) already mirrors deterministic agent memory layers.
- **Pinned TL;DR**: `SpecMemClient.get_tldr()` prioritizes pinned blocks.
- **Path context bundle**: `SpecMemClient.get_context_for_change()` packs
  specs/designs within a token budget.
- **Impact (manual)**: `specmem graph impact ${file}` remains available for
  graph-shaped reminders.

## Non-goals (deferred)

- No new SpecIR cue / trigger fields until there is a schema proposal.
- No full PROJECTMEM port or failed-attempt event log.
- No `specmem_precheck` / memory-as-governance gate yet (tracked on #16).
- No version bump or PyPI publish for this experiment.

## Install

```bash
specmem init --hooks
```

Existing user hooks under `.kiro/hooks/` are not overwritten.

## Related

- [Agent Memory Patterns](agent-memory-patterns.md)
- [Agent Integration](agent-integration.md)
- [Kiro Integration](../user-guide/kiro-integration.md)
- Issue #16, arXiv:2607.20972
