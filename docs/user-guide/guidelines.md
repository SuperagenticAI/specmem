# Coding Guidelines

SpecMem aggregates coding guidelines from multiple sources into a unified view, making it easy to discover, search, and convert team coding standards between different AI tool formats.

## Supported Sources

SpecMem detects and parses guidelines from:

| Source | File | Description |
|--------|------|-------------|
| **Claude** | `CLAUDE.md` | Claude Code project context file |
| **Cursor** | `.cursorrules` | Cursor AI rules file |
| **Kiro** | `.kiro/steering/*.md` | Kiro steering files |
| **Agents** | `AGENTS.md` | Generic agent instructions |

## Viewing Guidelines

### Web Dashboard

Launch the dashboard and navigate to the Guidelines view:

```bash
specmem demo
```

The Guidelines view shows:

- All guidelines grouped by source
- Filter buttons for each source type
- Search across title and content
- Click any guideline to see full content

### CLI

List all guidelines:

```bash
specmem guidelines
```

Filter by source:

```bash
specmem guidelines --source claude
specmem guidelines --source cursor
specmem guidelines --source steering
```

Search guidelines:

```bash
specmem guidelines --search "testing"
specmem guidelines --search "error handling"
```

Show guidelines for a specific file:

```bash
specmem guidelines --file src/auth.py
```

View full content of a guideline:

```bash
specmem guidelines show <guideline-id>
```

## Converting Guidelines

Convert guidelines between formats to share with team members using different tools.

### Supported Formats

- **steering** - Kiro steering files (`.kiro/steering/*.md`)
- **claude** - CLAUDE.md format
- **cursor** - .cursorrules format

### Single Guideline

Preview conversion:

```bash
specmem guidelines convert <id> steering
specmem guidelines convert <id> claude
specmem guidelines convert <id> cursor
```

Write the converted file:

```bash
specmem guidelines convert <id> steering --no-preview
```

### Bulk Conversion

Convert all guidelines to a format:

```bash
# Preview
specmem guidelines convert-all steering
specmem guidelines convert-all claude
specmem guidelines convert-all cursor

# Write files
specmem guidelines convert-all steering --no-preview
```

Convert only from a specific source:

```bash
specmem guidelines convert-all steering --source claude
```

### Web UI Conversion

1. Click on a guideline card to open the detail modal
2. Click "Convert to..." dropdown
3. Select target format (Kiro Steering, CLAUDE.md, or .cursorrules)
4. Preview the converted content

## JSON Output for AI Agents

Use `--robot` flag for machine-readable output:

```bash
specmem guidelines --robot
specmem guidelines --source claude --robot
specmem guidelines show <id> --robot
```

## API Endpoints

Guidelines are also available via the REST API:

```bash
# List guidelines
GET /api/guidelines
GET /api/guidelines?source=claude
GET /api/guidelines?q=testing

# Convert guideline
POST /api/guidelines/convert
{
  "guideline_id": "abc123",
  "format": "steering",  # or "claude", "cursor"
  "preview": true
}
```

## Sample Guidelines

When no real guidelines are found, SpecMem provides sample guidelines for demonstration. These are marked with a "Sample" badge in the UI and `is_sample: true` in the API response.

## Best Practices

1. **Centralize guidelines** - Keep team standards in one format and convert as needed
2. **Use file patterns** - Kiro steering files support `fileMatchPattern` for context-aware rules
3. **Regular sync** - Convert guidelines when team members switch tools
4. **Version control** - Commit converted guidelines to share with the team
