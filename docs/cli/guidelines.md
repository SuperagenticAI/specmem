# specmem guidelines

Manage and convert coding guidelines from various sources.

## Usage

```bash
specmem guidelines [OPTIONS] [COMMAND]
```

## Commands

| Command | Description |
|---------|-------------|
| `context` | Show the layered memory context an agent should load for a task |
| `show` | Show full content of a specific guideline |
| `convert` | Convert a guideline to another format |
| `convert-all` | Convert all guidelines to a target format |
| `score-skill` | Score a skill document with static optimization checks |
| `optimize` | Validate and promote an optimized skill artifact |
| `optimized-status` | Show optimized-skill artifact status |

## Options

| Option | Description |
|--------|-------------|
| `--source`, `-s` | Filter by source type |
| `--search`, `-q` | Search in title and content |
| `--file`, `-f` | Show guidelines that apply to a specific file |
| `--path`, `-p` | Workspace path (default: current directory) |
| `--robot`, `-r` | Output JSON for AI agents |
| `--no-samples` | Exclude sample guidelines |

Valid source types include `agents`, `claude`, `codex_skill`, `claude_skill`,
`copilot`, `cursor`, `gemini`, `opencode`, `qwen`, and `steering`.

## Examples

### List Guidelines

```bash
# List all guidelines
specmem guidelines

# Filter by source
specmem guidelines --source claude
specmem guidelines --source cursor
specmem guidelines --source steering
specmem guidelines --source agents
specmem guidelines --source codex_skill
specmem guidelines --source copilot

# Search guidelines
specmem guidelines --search "testing"
specmem guidelines --search "error handling"

# Show guidelines for a file
specmem guidelines --file src/auth.py

# JSON output
specmem guidelines --robot
```

### Build Agent Context

Use `context` to preview the memory layers an agent should load before editing
code. This is deterministic routing before semantic vector search.

```bash
specmem guidelines context \
  --file src/auth.py \
  --task "change authentication flow and update tests"
```

The command returns three layers:

| Layer | Description |
|-------|-------------|
| Always-on Project Guidance | Repository instructions that apply to all changes |
| File-scoped Guidance | Rules whose glob patterns match the supplied files |
| Candidate Skills | Procedural skills matched to the task intent |

Use `--robot` for JSON output:

```bash
specmem guidelines context \
  --file src/auth.py \
  --task "change authentication flow" \
  --robot
```

### Show Guideline

```bash
specmem guidelines show <guideline-id>
specmem guidelines show abc123 --robot
```

### Convert Single Guideline

```bash
# Preview conversion
specmem guidelines convert <id> steering
specmem guidelines convert <id> claude
specmem guidelines convert <id> cursor

# Write file
specmem guidelines convert <id> steering --no-preview
specmem guidelines convert <id> claude -o custom-rules.md --no-preview
```

### Convert All Guidelines

```bash
# Preview all conversions
specmem guidelines convert-all steering
specmem guidelines convert-all claude
specmem guidelines convert-all cursor

# Write files
specmem guidelines convert-all steering --no-preview
specmem guidelines convert-all claude --no-preview

# Convert only from specific source
specmem guidelines convert-all steering --source claude --no-preview
```

### Optimize Skill Artifacts

Use `optimize` to generate or promote a candidate `SKILL.md` into
`.specmem/skillopt/`. Accepted artifacts are consumed only when
`specmem build --optimize-skills` is used.

```bash
specmem guidelines score-skill .codex/skills/review/SKILL.md

specmem guidelines optimize .codex/skills/review/SKILL.md \
  --instruction "tighten this for code review tasks and make retrieval keywords explicit"

specmem guidelines optimize .codex/skills/review/SKILL.md \
  --candidate /tmp/review-best-skill.md \
  --score-before 0.62 \
  --score-after 0.74 \
  --evaluator codex-rollout
```

`--instruction` mode uses the optional OpenAI dependency and requires
`OPENAI_API_KEY`. It accepts changed candidates that pass static checks without
regressing. `--candidate` mode accepts only when the candidate improves the
provided scores, or the static score when no scores are supplied.

For a complete guide, see [Optimized Skills](../user-guide/optimized-skills.md).

Check optimized artifact status:

```bash
specmem guidelines optimized-status
specmem guidelines optimized-status --robot
```

Accepted optimized skills can also be written back to the source skill when you
want the optimized document to become canonical:

```bash
specmem guidelines optimize .codex/skills/review/SKILL.md \
  --candidate /tmp/review-best-skill.md \
  --score-before 0.62 \
  --score-after 0.74 \
  --write-source
```

The command writes:

| File | Purpose |
|------|---------|
| `.specmem/skillopt/<skill>/initial_skill.md` | Source skill snapshot |
| `.specmem/skillopt/<skill>/candidate_skill.md` | Candidate snapshot |
| `.specmem/skillopt/<skill>/best_skill.md` | Accepted optimized skill |
| `.specmem/skillopt/<skill>/evaluation_report.json` | Gate result and provenance |

## Output Formats

### Table (default)

```
Guidelines by Source:
  claude: 5
  steering: 3

                    Coding Guidelines (8 total)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Source   ┃ Title                         ┃ Pattern       ┃ Sample ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ claude   │ Python Code Style             │ **/*.py       │        │
│ steering │ Testing Guidelines            │ tests/**/*.py │        │
└──────────┴───────────────────────────────┴───────────────┴────────┘
```

### JSON (--robot)

```json
{
  "count": 8,
  "guidelines": [
    {
      "id": "abc123def456",
      "title": "Python Code Style",
      "source_type": "claude",
      "source_file": "CLAUDE.md",
      "file_pattern": "**/*.py",
      "is_sample": false,
      "content_preview": "Use type hints for all..."
    }
  ]
}
```

## Supported Formats

SpecMem reads these agent guidance sources:

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

Instruction files are pinned by default when converted into memory blocks.
Skill files are indexed as procedural memory and are selected by task intent.

## Conversion Targets

| Format | Output | Description |
|--------|--------|-------------|
| `steering` | `.kiro/steering/*.md` | Kiro steering files with frontmatter |
| `claude` | `CLAUDE.md` | Claude Code project context |
| `cursor` | `.cursorrules` | Cursor AI rules file |

## See Also

- [User Guide: Guidelines](../user-guide/guidelines.md)
- [API: Guidelines](../api/guidelines.md)
