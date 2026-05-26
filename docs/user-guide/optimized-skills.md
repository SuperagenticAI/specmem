# Optimized Skills

SpecMem can index optimized versions of agent skills without modifying the
original `SKILL.md` files. This is useful when a skill is too verbose, hard to
retrieve by task intent, or needs a cleaner workflow before it becomes memory.

Optimized skills are opt-in. A normal `specmem build` still indexes the source
skill files. To use optimized artifacts, run:

```bash
specmem build --optimize-skills
```

## How It Works

SpecMem keeps optimized skill artifacts under `.specmem/skillopt/`:

```text
.specmem/skillopt/<skill-slug>/
├── initial_skill.md
├── candidate_skill.md
├── best_skill.md
└── evaluation_report.json
```

The source `SKILL.md` remains the source of truth. SpecMem indexes
`best_skill.md` only when all of these are true:

- The artifact was accepted by the optimization gate.
- The candidate differs from the source skill.
- Static checks pass.
- The source `SKILL.md` has not changed since the artifact was accepted.
- `specmem build --optimize-skills` is used.

If the source skill changes, the optimized artifact is ignored until it is
validated again.

## Prerequisites

Instruction-based optimization uses the optional OpenAI dependency:

```bash
pip install "specmem[openai]"
export OPENAI_API_KEY="sk-..."
```

You can also skip OpenAI entirely and provide a candidate file yourself with
`--candidate`.

## Quick Start

Score the current skill with static checks:

```bash
specmem guidelines score-skill .codex/skills/review/SKILL.md
```

Generate and gate an optimized candidate:

```bash
specmem guidelines optimize .codex/skills/review/SKILL.md \
  --instruction "tighten this for code review tasks and make retrieval keywords explicit"
```

Build memory with accepted optimized skills:

```bash
specmem build --optimize-skills
```

Check which skill artifacts will be used:

```bash
specmem guidelines optimized-status
```

## Using an Existing Candidate

If another tool or a manual edit already produced a candidate skill, promote it
through the same gate:

```bash
specmem guidelines optimize .codex/skills/review/SKILL.md \
  --candidate /tmp/review-best-skill.md \
  --score-before 0.62 \
  --score-after 0.74 \
  --evaluator codex-rollout
```

When explicit scores are supplied, the candidate must strictly improve
`--score-after` over `--score-before`.

## Dry Run

Use `--dry-run` to generate a candidate without accepting it:

```bash
specmem guidelines optimize .codex/skills/review/SKILL.md \
  --instruction "make this skill shorter and easier to route" \
  --dry-run
```

The generated candidate is written to:

```text
.specmem/skillopt/<skill-slug>/candidate_skill.md
```

Review or edit that file, then promote it:

```bash
specmem guidelines optimize .codex/skills/review/SKILL.md \
  --candidate .specmem/skillopt/<skill-slug>/candidate_skill.md
```

## Status

Use `optimized-status` before building to see what SpecMem will do:

```bash
specmem guidelines optimized-status
specmem guidelines optimized-status --robot
```

States:

| State | Meaning |
|-------|---------|
| `raw` | No optimized artifact exists; the source `SKILL.md` will be indexed |
| `optimized` | Current accepted artifact exists and can be indexed with `--optimize-skills` |
| `stale` | Source `SKILL.md` changed after validation; artifact will be ignored |
| `rejected` | Last candidate did not pass the gate |
| `invalid` | Artifact files are missing or inconsistent |

## Gate Behavior

The gate is deliberately conservative.

| Mode | Acceptance rule |
|------|-----------------|
| `--instruction` | Candidate must change the skill and not regress static checks |
| `--candidate` with scores | `--score-after` must be greater than `--score-before` |
| `--candidate` without scores | Static score must improve |

Static checks reject empty skills, merge conflict markers, extreme bloat, and
very repetitive content. These checks are not a substitute for real rollout
evaluation, but they prevent broken candidates from entering memory.

## Indexing Tags

When an optimized skill is indexed, SpecMem adds provenance tags:

```text
optimized-skill
skillopt:validated
skillopt:score:<before>-><after>
skillopt:artifact:<artifact-id>
```

These tags make optimized memory visible in `agent_memory.json` and available
for filtering in downstream tools.

## Writing Back To The Source Skill

By default, SpecMem does not edit the source `SKILL.md`. To promote an accepted
optimized skill back into the source file, use `--write-source`:

```bash
specmem guidelines optimize .codex/skills/review/SKILL.md \
  --instruction "make this skill shorter and easier to route" \
  --write-source
```

Use this when you want the optimized skill to become the canonical skill in
version control. Without `--write-source`, the optimized version remains an
artifact used only by `specmem build --optimize-skills`.

## Version Control

Choose one policy per repository:

| Policy | What to commit | When to use |
|--------|----------------|-------------|
| Source-only | Commit only `SKILL.md`; ignore `.specmem/skillopt/` | Optimizations are local experiments |
| Shared artifacts | Commit `.specmem/skillopt/*/best_skill.md` and `evaluation_report.json` | Team wants reproducible optimized memory |
| Promoted source | Use `--write-source` and commit the changed `SKILL.md` | Optimized skill should become canonical |

For most teams, start with source-only while experimenting. Move to promoted
source once a skill consistently improves agent behavior.

## Recommended Workflow

1. Keep original skills in `.codex/skills/*/SKILL.md` or `.claude/skills/*/SKILL.md`.
2. Use `specmem guidelines optimize --instruction` for small improvements.
3. Review `.specmem/skillopt/<skill>/candidate_skill.md` when the change is important.
4. Build with `specmem build --optimize-skills`.
5. Re-run optimization after changing the source `SKILL.md`.

Do not use optimized artifacts to bypass review for high-impact project rules.
Always-on guidance such as `AGENTS.md` and `CLAUDE.md` remains separate and is
not optimized by this feature.
