# ✅ SpecValidator

SpecValidator ensures your specifications are high-quality, consistent, and complete.

## Overview

SpecValidator runs a suite of validation rules against your specifications:

```bash
specmem validate
```

Output:

```
✅ SpecValidator Results

📊 Summary:
   • Specs checked: 24
   • Errors: 2
   • Warnings: 5
   • Info: 3

❌ Errors:
   • auth/requirements.md:45 - Missing acceptance criteria for requirement
   • api/design.md:12 - Invalid constraint format

⚠️  Warnings:
   • auth/design.md:78 - Vague term "quickly" in requirement
   • security/constraints.md:23 - Duplicate constraint detected
```

## Validation Rules

### 📐 Structure Rules

Validates specification structure and format.

| Rule | Description |
|------|-------------|
| `valid_markdown` | Spec is valid Markdown |
| `required_sections` | Required sections present |
| `valid_yaml_frontmatter` | YAML frontmatter is valid |
| `consistent_headings` | Heading hierarchy is correct |

### ⏱️ Timeline Rules

Validates temporal consistency.

| Rule | Description |
|------|-------------|
| `valid_dates` | Dates are valid and logical |
| `no_future_completion` | Completed tasks not in future |
| `deadline_order` | Deadlines follow dependencies |

### 🔄 Duplicate Rules

Detects duplicate specifications.

| Rule | Description |
|------|-------------|
| `no_duplicate_ids` | Spec IDs are unique |
| `no_duplicate_content` | No copy-pasted content |
| `no_redundant_specs` | No specs that duplicate others |

### 🔒 Constraint Rules

Validates constraints and requirements.

| Rule | Description |
|------|-------------|
| `valid_constraint_format` | Constraints follow EARS format |
| `measurable_criteria` | Criteria are measurable |
| `no_vague_terms` | No vague terms like "fast", "good" |
| `no_absolutes` | No absolutes like "always", "never" |

### ✓ Acceptance Criteria Rules

Validates acceptance criteria completeness.

| Rule | Description |
|------|-------------|
| `has_acceptance_criteria` | Requirements have criteria |
| `criteria_testable` | Criteria are testable |
| `criteria_complete` | All scenarios covered |

### ⚔️ Contradiction Rules

Detects conflicting specifications.

| Rule | Description |
|------|-------------|
| `no_numeric_conflicts` | No conflicting numbers |
| `no_boolean_conflicts` | No conflicting booleans |
| `no_scope_conflicts` | No conflicting scopes |

## Using the Validator

### CLI

```bash
# Validate all specs
specmem validate

# Validate specific spec
specmem validate --spec auth/requirements.md

# Only show errors
specmem validate --severity error

# Output as JSON
specmem validate --format json

# Fail on warnings (for CI)
specmem validate --strict
```

### Python API

```python
from specmem import SpecMemClient

sm = SpecMemClient()

# Validate all specs
issues = sm.validate()

for issue in issues:
    print(f"[{issue.severity}] {issue.spec}:{issue.line}")
    print(f"  Rule: {issue.rule}")
    print(f"  Message: {issue.message}")
    if issue.suggestion:
        print(f"  Suggestion: {issue.suggestion}")

# Validate specific spec
issues = sm.validate_spec("auth/requirements.md")

# Check if valid
is_valid = sm.is_valid()
```

## Severity Levels

| Level | Description | CI Behavior |
|-------|-------------|-------------|
| `error` | Must be fixed | Fails build |
| `warning` | Should be fixed | Fails with `--strict` |
| `info` | Suggestion | Never fails |

## Configuration

```toml
[validation]
# Enable/disable specific rules
rules = [
    "structure",
    "timeline",
    "duplicates",
    "constraints",
    "acceptance_criteria",
    "contradiction",
]

# Minimum severity to report
min_severity = "warning"

# Custom vague terms to flag
vague_terms = [
    "fast",
    "slow",
    "good",
    "bad",
    "quickly",
    "adequate",
    "appropriate",
]

# Custom absolutes to flag
absolutes = [
    "always",
    "never",
    "all",
    "none",
    "100%",
    "0%",
]
```

## Custom Rules

Create custom validation rules:

```python
from specmem.validator import ValidationRule, Issue, Severity

class NoTodoRule(ValidationRule):
    """Flag TODO comments in specs."""

    name = "no_todos"
    description = "Specs should not contain TODO comments"

    def validate(self, spec: SpecBlock) -> list[Issue]:
        issues = []
        for i, line in enumerate(spec.content.split("\n")):
            if "TODO" in line.upper():
                issues.append(Issue(
                    rule=self.name,
                    spec=spec.path,
                    line=i + 1,
                    severity=Severity.WARNING,
                    message="TODO found in spec",
                    suggestion="Complete or remove the TODO"
                ))
        return issues

# Register custom rule
sm.register_validation_rule(NoTodoRule())
```

## CI Integration

### GitHub Actions

```yaml
# .github/workflows/validate-specs.yml
name: Validate Specs

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install SpecMem
        run: pip install specmem

      - name: Validate Specifications
        run: specmem validate --strict --format json > validation.json

      - name: Upload Results
        uses: actions/upload-artifact@v4
        with:
          name: validation-results
          path: validation.json
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: specmem-validate
        name: Validate Specs
        entry: specmem validate --strict
        language: system
        pass_filenames: false
        files: \.(md|yaml|json)$
```

## Auto-fix

Some issues can be automatically fixed:

```bash
# Preview fixes
specmem validate --fix --dry-run

# Apply fixes
specmem validate --fix
```

Fixable issues:

- Trailing whitespace
- Missing newlines
- Inconsistent heading levels
- Duplicate blank lines
