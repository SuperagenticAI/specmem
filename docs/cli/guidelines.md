# specmem guidelines

Manage and convert coding guidelines from various sources.

## Usage

```bash
specmem guidelines [OPTIONS] [COMMAND]
```

## Commands

| Command | Description |
|---------|-------------|
| `show` | Show full content of a specific guideline |
| `convert` | Convert a guideline to another format |
| `convert-all` | Convert all guidelines to a target format |

## Options

| Option | Description |
|--------|-------------|
| `--source`, `-s` | Filter by source type (claude, cursor, steering, agents) |
| `--search`, `-q` | Search in title and content |
| `--file`, `-f` | Show guidelines that apply to a specific file |
| `--path`, `-p` | Workspace path (default: current directory) |
| `--robot`, `-r` | Output JSON for AI agents |
| `--no-samples` | Exclude sample guidelines |

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

# Search guidelines
specmem guidelines --search "testing"
specmem guidelines --search "error handling"

# Show guidelines for a file
specmem guidelines --file src/auth.py

# JSON output
specmem guidelines --robot
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

| Format | Output | Description |
|--------|--------|-------------|
| `steering` | `.kiro/steering/*.md` | Kiro steering files with frontmatter |
| `claude` | `CLAUDE.md` | Claude Code project context |
| `cursor` | `.cursorrules` | Cursor AI rules file |

## See Also

- [User Guide: Guidelines](../user-guide/guidelines.md)
- [API: Guidelines](../api/guidelines.md)
