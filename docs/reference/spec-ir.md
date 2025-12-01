# Spec IR Format

SpecIR (Specification Intermediate Representation) is the canonical format used internally by SpecMem.

## Overview

All specifications from different frameworks are normalized to SpecIR format, enabling:

- Unified querying across frameworks
- Consistent validation rules
- Framework-agnostic impact analysis
- Portable agent context

## SpecBlock Schema

```python
@dataclass
class SpecBlock:
    # Unique identifier
    id: str

    # Source file path
    path: str

    # Source framework (kiro, cursor, claude, etc.)
    framework: str

    # Specification type
    spec_type: SpecType

    # Human-readable title
    title: str

    # Full content
    content: str

    # Brief summary (for context)
    summary: str

    # Categorization tags
    tags: list[str]

    # Lifecycle stage
    lifecycle: Lifecycle

    # Priority level
    priority: Priority

    # Creation timestamp
    created_at: datetime

    # Last update timestamp
    updated_at: datetime

    # Additional metadata
    metadata: dict
```

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "path", "framework", "spec_type", "title", "content"],
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique identifier"
    },
    "path": {
      "type": "string",
      "description": "Source file path"
    },
    "framework": {
      "type": "string",
      "enum": ["kiro", "cursor", "claude", "speckit", "tessl", "custom"]
    },
    "spec_type": {
      "type": "string",
      "enum": ["requirement", "design", "task", "constraint"]
    },
    "title": {
      "type": "string"
    },
    "content": {
      "type": "string"
    },
    "summary": {
      "type": "string",
      "maxLength": 500
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"}
    },
    "lifecycle": {
      "type": "string",
      "enum": ["active", "deprecated", "legacy", "obsolete"],
      "default": "active"
    },
    "priority": {
      "type": "string",
      "enum": ["critical", "high", "medium", "low"],
      "default": "medium"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    },
    "metadata": {
      "type": "object"
    }
  }
}
```

## Enumerations

### SpecType

| Value | Description | Example |
|-------|-------------|---------|
| `requirement` | What the system should do | User stories, acceptance criteria |
| `design` | How the system works | Architecture, data models |
| `task` | Implementation steps | Coding tasks, TODOs |
| `constraint` | Limitations and rules | Performance, security rules |

### Lifecycle

| Value | Weight | Description |
|-------|--------|-------------|
| `active` | 1.0 | Current, in-use specification |
| `deprecated` | 0.5 | Being phased out |
| `legacy` | 0.2 | Old but still referenced |
| `obsolete` | 0.0 | No longer relevant |

### Priority

| Value | Weight | Description |
|-------|--------|-------------|
| `critical` | 1.0 | Must be addressed immediately |
| `high` | 0.8 | Important, address soon |
| `medium` | 0.5 | Normal priority |
| `low` | 0.3 | Nice to have |

## Example SpecBlock

```json
{
  "id": "auth-req-001",
  "path": ".kiro/specs/auth/requirements.md",
  "framework": "kiro",
  "spec_type": "requirement",
  "title": "User Authentication",
  "content": "# User Authentication\n\n## User Story\nAs a user, I want to log in securely...",
  "summary": "JWT-based authentication with refresh tokens",
  "tags": ["auth", "security", "jwt"],
  "lifecycle": "active",
  "priority": "critical",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-20T14:30:00Z",
  "metadata": {
    "author": "team",
    "version": "1.2",
    "related_specs": ["auth-design-001", "security-constraint-001"]
  }
}
```

## Metadata Fields

Common metadata fields used by adapters:

| Field | Type | Description |
|-------|------|-------------|
| `author` | string | Spec author |
| `version` | string | Spec version |
| `related_specs` | string[] | Related spec IDs |
| `code_refs` | string[] | Referenced code files |
| `test_refs` | string[] | Referenced test files |
| `acceptance_criteria` | object[] | Parsed acceptance criteria |
| `ears_patterns` | object[] | EARS-formatted requirements |

## Conversion Examples

### From Kiro

```markdown
# Requirements Document

## Requirement 1
**User Story:** As a user, I want to log in.

### Acceptance Criteria
1. WHEN valid credentials THEN authenticate
```

Converts to:

```json
{
  "id": "kiro-auth-requirements-req1",
  "spec_type": "requirement",
  "title": "Requirement 1",
  "metadata": {
    "user_story": "As a user, I want to log in.",
    "acceptance_criteria": [
      {"pattern": "event_driven", "trigger": "valid credentials", "response": "authenticate"}
    ]
  }
}
```

### From Cursor

```json
{
  "rules": ["Use TypeScript strict mode"]
}
```

Converts to:

```json
{
  "id": "cursor-rule-0",
  "spec_type": "constraint",
  "title": "Cursor Rule: Use TypeScript strict mode",
  "content": "Use TypeScript strict mode",
  "tags": ["cursor", "typescript"]
}
```

### From Claude.md

```markdown
# Project Context

## Security
All endpoints require authentication.
```

Converts to:

```json
{
  "id": "claude-security",
  "spec_type": "constraint",
  "title": "Security",
  "content": "All endpoints require authentication.",
  "tags": ["claude", "security"]
}
```

## Validation

SpecIR blocks are validated for:

1. **Required fields** - id, path, framework, spec_type, title, content
2. **Valid enums** - spec_type, lifecycle, priority
3. **Timestamp format** - ISO 8601
4. **Summary length** - Max 500 characters
5. **Unique IDs** - No duplicates within a project
