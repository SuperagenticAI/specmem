# specmem sessions

Configure, index, search, list, and view Kiro coding sessions.

Session search helps agents and developers recover context from previous work: design decisions, debugging history, migration notes, and prior implementation attempts.

## Configure

```bash
specmem sessions config
```

Auto-discover Kiro sessions without prompting:

```bash
specmem sessions config --auto
```

Configure an explicit sessions path:

```bash
specmem sessions config --path /path/to/workspace-sessions
```

Limit session search to the current workspace:

```bash
specmem sessions config --auto --workspace-only
```

## Index

```bash
specmem sessions index
```

Index only sessions for the current workspace:

```bash
specmem sessions index --workspace-only
```

Indexed sessions are stored in `.specmem/sessions.db`.

## Search

```bash
specmem sessions search "qdrant migration"
```

Options:

| Option | Description |
|--------|-------------|
| `--limit`, `-n` | Maximum results |
| `--days`, `-d` | Only include sessions from the last N days |
| `--robot`, `-r` | Return JSON for tools or agents |

Examples:

```bash
specmem sessions search "auth architecture decision" --days 30 --limit 5
specmem sessions search "test coverage issue" --robot
```

## List

```bash
specmem sessions list
```

Options:

| Option | Description |
|--------|-------------|
| `--limit`, `-n` | Maximum sessions |
| `--workspace-only`, `-w` | Only list sessions for the current workspace |
| `--robot`, `-r` | Return JSON |

## View

```bash
specmem sessions view <session-id>
```

Return JSON:

```bash
specmem sessions view <session-id> --robot
```

## Retrieval Behavior

Session search can use semantic search when a session vector store is configured. If not, it falls back to text search over indexed session messages. This keeps the feature useful for local workflows while still allowing richer retrieval in production memory setups.
