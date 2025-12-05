# 🔄 Spec Lifecycle Management

Pragmatic tools for keeping your spec collection lean and relevant.

## Overview

As projects evolve, specifications can become outdated, orphaned, or overly verbose. SpecMem's lifecycle management tools help you:

- **Identify** specs that need attention
- **Prune** orphaned or stale specs
- **Generate** specs from existing code
- **Compress** verbose specs for efficient context

## Health Analysis

The health analyzer calculates scores based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Code References | 40% | How many code files reference the spec |
| Freshness | 30% | How recently the spec was modified |
| Usage | 30% | How often the spec is queried |

### Check Health

```bash
# View all specs
specmem health

# Analyze specific spec
specmem health auth-feature
```

### Health Statuses

| Status | Description |
|--------|-------------|
| **healthy** | Well-maintained, actively referenced |
| **orphaned** | No code references found |
| **stale** | Not modified within threshold (default: 90 days) |

## Pruning Specs

Remove specs that are no longer relevant.

### Preview Changes

```bash
# See what would be pruned
specmem prune --orphaned
```

### Archive Orphaned Specs

```bash
# Archive to .specmem/archive/
specmem prune --orphaned --no-dry-run
```

### Delete Specific Specs

```bash
# Permanently delete
specmem prune old-feature --mode delete --no-dry-run --force
```

### Prune Stale Specs

```bash
# Archive specs not modified in 60+ days
specmem prune --stale --stale-days 60 --no-dry-run
```

## Generating Specs

Bootstrap specs from existing code for brownfield adoption.

### From a File

```bash
specmem generate src/auth.py --write
```

### From a Directory

```bash
specmem generate src/features/ --write
```

### Grouping Options

```bash
# One spec per file
specmem generate src/ --group-by file --write

# One spec per directory (default)
specmem generate src/ --group-by directory --write

# One spec per module
specmem generate src/ --group-by module --write
```

Generated specs include:

- Inferred requirements from function purposes
- User stories based on module functionality
- Acceptance criteria from function signatures
- Auto-generated metadata marker

## Compressing Specs

Reduce verbose specs while preserving essential content.

### Find Verbose Specs

```bash
specmem compress
```

### Compress All Verbose

```bash
specmem compress --all --save
```

### Custom Threshold

```bash
# Lower threshold (3000 chars instead of 5000)
specmem compress --all --threshold 3000 --save
```

Compression preserves:

- All acceptance criteria
- Key requirements
- Essential structure

## Python API

Use lifecycle features programmatically:

```python
from specmem import SpecMemClient

sm = SpecMemClient()

# Health analysis
health = sm.get_spec_health()
print(f"Orphaned: {health['orphaned_count']}")

# Prune orphaned specs
results = sm.prune_specs(orphaned=True, dry_run=False)

# Generate specs from code
specs = sm.generate_specs(["src/auth/"], write=True)

# Compress verbose specs
compressed = sm.compress_specs(all_verbose=True, save=True)
```

## Workflow Integration

### CI Pipeline

```yaml
# Check for orphaned specs
- name: Spec Health Check
  run: |
    specmem health
    if specmem prune --orphaned | grep -q "orphaned"; then
      echo "Warning: Orphaned specs detected"
    fi
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: spec-health
      name: Check spec health
      entry: specmem health
      language: system
      pass_filenames: false
```

## Best Practices

!!! tip "Regular Health Checks"
    Run `specmem health` weekly to catch orphaned specs early.

!!! tip "Archive Before Delete"
    Use archive mode first. You can always delete later.

!!! tip "Review Generated Specs"
    Auto-generated specs are starting points; refine them manually.

!!! tip "Compress for Agents"
    Compressed specs reduce token usage when serving context.

## See Also

- [CLI: health](../cli/health.md)
- [CLI: prune](../cli/prune.md)
- [CLI: generate](../cli/generate.md)
- [CLI: compress](../cli/compress.md)
