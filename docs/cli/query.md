# specmem query

Search the indexed memory store with a natural language question.

## Usage

```bash
specmem query [OPTIONS] QUESTION
```

## Description

`specmem query` embeds the question, searches the configured vector backend, and
returns the most relevant memory blocks. Results can include structured specs,
living documentation, and indexed agent guidance.

Run `specmem build` before querying. The command uses the vector backend
configured in `.specmem.toml`.

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `QUESTION` | Natural language query to search for | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--top`, `-k` | Number of results to return | `5` |
| `--path`, `-p` | Repository path | `.` |
| `--file`, `-f` | Changed file path for trace output. Repeat for multiple files. | none |
| `--trace` | Explain memory routing and result metadata | off |

## Examples

### Basic Query

```bash
specmem query "authentication requirements"
```

Example output:

```text
Results for: authentication requirements

1. [requirement] (score: 0.921)
   .kiro/specs/auth/requirements.md
   # Requirement 1

   Users must authenticate with a valid session token...
```

### Return More Results

```bash
specmem query "database schema" --top 10
```

### Query Another Repository

```bash
specmem query "release process" --path ../service-api
```

### Show Memory Trace

Use `--trace` when you want to explain why memory was loaded for a task.
Pass changed files with `--file` so SpecMem can show file-scoped guidance.

```bash
specmem query "What constraints apply before changing authentication?" \
  --file src/auth.py \
  --trace
```

The trace includes:

| Layer | Meaning |
|-------|---------|
| `always_on` | Pinned project guidance that applies before semantic retrieval |
| `file_scoped` | Guidance whose file pattern matches `--file` |
| `skills` | Procedural memory whose title, tags, or body match the query intent |
| `vector` | Top semantic matches from the configured vector backend |

Each result also includes trace metadata such as `vector-match`,
`status:active`, `pinned`, and relevant tags.

## Lifecycle Filtering

The vector store excludes obsolete memory by default. Deprecated and legacy
memory are included only when the calling API requests them. The CLI currently
uses the default active-memory query behavior.

## See Also

- [specmem build](build.md)
- [specmem guidelines](guidelines.md)
- [Agent Memory Patterns](../advanced/agent-memory-patterns.md)
