# 💻 CLI Reference

SpecMem provides a comprehensive command-line interface for all operations.

## Installation

```bash
pip install specmem
```

## Global Options

```bash
specmem [OPTIONS] COMMAND [ARGS]...

Options:
  --version        Show version and exit
  --config PATH    Path to config file
  --verbose, -v    Enable verbose output
  --quiet, -q      Suppress output
  --help           Show help and exit
```

## Commands Overview

| Command | Description |
|---------|-------------|
| [`init`](init.md) | Initialize SpecMem in a project |
| [`scan`](scan.md) | Scan and index specifications |
| [`build`](build.md) | Build the Agent Experience Pack |
| [`query`](query.md) | Search specifications |
| [`impact`](impact.md) | Analyze impact of changes |
| [`validate`](validate.md) | Validate specifications |
| [`cov`](cov.md) | Analyze spec coverage |
| [`guidelines`](guidelines.md) | Manage coding guidelines |
| [`serve`](serve.md) | Start the web UI |
| [`demo`](demo.md) | Launch demo with SpecMem's own specs |

### Lifecycle Commands

| Command | Description |
|---------|-------------|
| [`health`](health.md) | Display spec health scores |
| [`prune`](prune.md) | Archive or delete orphaned specs |
| [`generate`](generate.md) | Generate specs from code |
| [`compress`](compress.md) | Compress verbose specs |

## Quick Reference

```bash
# Initialize
specmem init

# Scan specs
specmem scan

# Build pack
specmem build

# Query
specmem query "authentication"

# Impact analysis
specmem impact --files src/auth.py

# Validate
specmem validate

# Spec coverage
specmem cov

# Coding guidelines
specmem guidelines                # List all guidelines
specmem guidelines --source claude  # Filter by source
specmem guidelines convert <id> steering  # Convert format

# Web UI
specmem serve

# Demo (try SpecMem instantly)
specmem demo

# Lifecycle management
specmem health                    # View spec health scores
specmem prune --orphaned          # Archive orphaned specs
specmem generate src/             # Generate specs from code
specmem compress --all            # Compress verbose specs
```

## Configuration

SpecMem looks for configuration in this order:

1. `--config` flag
2. `.specmem.toml` in current directory
3. `.specmem.local.toml` (local overrides)
4. Environment variables

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Validation errors found |
| 4 | No specs found |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SPECMEM_CONFIG` | Path to config file |
| `SPECMEM_LOG_LEVEL` | Log level (debug, info, warning, error) |
| `SPECMEM_NO_COLOR` | Disable colored output |
