# Guidelines API

REST API endpoints for managing coding guidelines.

## Endpoints

### List Guidelines

```http
GET /api/guidelines
```

Query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `source` | string | Filter by source type (claude, cursor, steering, agents) |
| `file` | string | Filter by file path (returns guidelines that apply to the file) |
| `q` | string | Search in title and content |

Response:

```json
{
  "guidelines": [
    {
      "id": "abc123def456",
      "title": "Python Code Style",
      "content": "# Python Code Style\n\nUse type hints...",
      "source_type": "claude",
      "source_file": "CLAUDE.md",
      "file_pattern": "**/*.py",
      "tags": ["python", "style"],
      "is_sample": false
    }
  ],
  "total_count": 8,
  "counts_by_source": {
    "claude": 5,
    "steering": 3
  }
}
```

### Convert Guideline

```http
POST /api/guidelines/convert
```

Request body:

```json
{
  "guideline_id": "abc123def456",
  "format": "steering",
  "preview": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `guideline_id` | string | Yes | ID of the guideline to convert |
| `format` | string | Yes | Target format: `steering`, `claude`, or `cursor` |
| `preview` | boolean | No | If true (default), don't write files |

Response:

```json
{
  "filename": "python-code-style.md",
  "content": "---\ninclusion: fileMatch\nfileMatchPattern: '**/*.py'\n---\n\n# Python Code Style\n\n...",
  "frontmatter": {
    "inclusion": "fileMatch",
    "fileMatchPattern": "**/*.py"
  },
  "source_id": "abc123def456"
}
```

### Export Guidelines

```http
POST /api/guidelines/export
```

Request body:

```json
{
  "format": "claude"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `format` | string | Yes | Export format: `claude` or `cursor` |

Response:

```json
{
  "filename": "CLAUDE.md",
  "content": "# Project Guidelines\n\n## Python Code Style\n\n..."
}
```

## Data Models

### Guideline

```typescript
interface Guideline {
  id: string;              // Unique identifier (hash-based)
  title: string;           // Title or heading
  content: string;         // Full content
  source_type: SourceType; // Source type enum
  source_file: string;     // Path to source file
  file_pattern?: string;   // Glob pattern for applicable files
  tags: string[];          // Tags for categorization
  is_sample: boolean;      // Whether this is a sample guideline
}
```

### SourceType

```typescript
type SourceType = 'claude' | 'cursor' | 'steering' | 'agents' | 'sample';
```

### ConversionResult

```typescript
interface ConversionResult {
  filename: string;        // Suggested output filename
  content: string;         // Converted content
  frontmatter: object;     // YAML frontmatter (for steering)
  source_id: string;       // Original guideline ID
}
```

## Examples

### List all guidelines

```bash
curl http://localhost:8765/api/guidelines
```

### Filter by source

```bash
curl "http://localhost:8765/api/guidelines?source=claude"
```

### Search guidelines

```bash
curl "http://localhost:8765/api/guidelines?q=testing"
```

### Convert to steering format

```bash
curl -X POST http://localhost:8765/api/guidelines/convert \
  -H "Content-Type: application/json" \
  -d '{"guideline_id": "abc123", "format": "steering", "preview": true}'
```

### Convert to CLAUDE.md format

```bash
curl -X POST http://localhost:8765/api/guidelines/convert \
  -H "Content-Type: application/json" \
  -d '{"guideline_id": "abc123", "format": "claude", "preview": true}'
```

### Export all to .cursorrules

```bash
curl -X POST http://localhost:8765/api/guidelines/export \
  -H "Content-Type: application/json" \
  -d '{"format": "cursor"}'
```

## See Also

- [User Guide: Guidelines](../user-guide/guidelines.md)
- [CLI: guidelines](../cli/guidelines.md)
