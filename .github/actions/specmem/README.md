# SpecMem GitHub Action

Analyze spec coverage, health, and quality in your CI/CD pipeline.

## Features

- 📊 **Spec Coverage** - Track acceptance criteria test coverage
- 💚 **Health Score** - Get a letter grade (A-F) for spec quality
- ✅ **Validation** - Check specs for structural issues
- 💬 **PR Comments** - Automatic results posted to PRs
- 🚦 **Threshold Checks** - Fail builds on quality drops

## Quick Start

```yaml
name: Spec Analysis
on: [pull_request]

jobs:
  specmem:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: specmem/specmem/.github/actions/specmem@main
```

## Installation Options

### From PyPI (default)

```yaml
- uses: specmem/specmem/.github/actions/specmem@main
  with:
    install_from: pypi
    version: latest  # or specific version like "0.1.0"
```

### From GitHub

```yaml
- uses: specmem/specmem/.github/actions/specmem@main
  with:
    install_from: github
    github_repo: specmem/specmem
    version: main  # or tag/commit SHA
```

## Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `commands` | Commands to run (comma-separated) | `cov,health` |
| `install_from` | Installation source: `pypi` or `github` | `pypi` |
| `version` | Version (PyPI) or ref (GitHub) | `latest` |
| `github_repo` | GitHub repo for installation | `specmem/specmem` |
| `working_directory` | Directory to run analysis in | `.` |
| `comment_on_pr` | Post results as PR comment | `true` |
| `coverage_threshold` | Minimum coverage percentage | `0` |
| `health_threshold` | Minimum health grade (A/B/C/D) | `` |
| `fail_on_validation_errors` | Fail on validation errors | `false` |
| `github_token` | Token for PR comments | `${{ github.token }}` |
| `python_version` | Python version to use | `3.11` |

## Outputs

| Output | Description |
|--------|-------------|
| `coverage_percentage` | Spec coverage percentage |
| `health_grade` | Health grade (A-F) |
| `health_score` | Health score (0-100) |
| `validation_errors` | Number of validation errors |
| `results_json` | Full results as JSON |

## Examples

### Basic Usage

```yaml
- uses: specmem/specmem/.github/actions/specmem@main
```

### With Thresholds

```yaml
- uses: specmem/specmem/.github/actions/specmem@main
  with:
    coverage_threshold: 80
    health_threshold: B
    fail_on_validation_errors: true
```

### All Commands

```yaml
- uses: specmem/specmem/.github/actions/specmem@main
  with:
    commands: cov,health,validate
```

### Monorepo (Subdirectory)

```yaml
- uses: specmem/specmem/.github/actions/specmem@main
  with:
    working_directory: packages/my-app
```

### Use Outputs in Subsequent Steps

```yaml
- uses: specmem/specmem/.github/actions/specmem@main
  id: specmem

- name: Check Coverage
  run: |
    echo "Coverage: ${{ steps.specmem.outputs.coverage_percentage }}%"
    echo "Health: ${{ steps.specmem.outputs.health_grade }}"
```

### Without PR Comments

```yaml
- uses: specmem/specmem/.github/actions/specmem@main
  with:
    comment_on_pr: false
```

## PR Comment Example

The action posts a formatted comment on PRs:

```
## 📊 SpecMem Analysis

| Metric | Value | Status |
|--------|-------|--------|
| Spec Coverage | 85.0% | ✅ |
| Health Grade | B (78/100) | ✅ |
| Validation Errors | 0 | ✅ |
```

## How It Works

The action runs these steps:

1. **Setup Python** - Configures Python environment
2. **Cache pip** - Caches packages for faster runs
3. **Install SpecMem** - From PyPI or GitHub
4. **Run Commands** - Executes specmem with `--robot` flag
5. **Post PR Comment** - Formats and posts results
6. **Check Thresholds** - Fails if thresholds not met

## Documentation

For full documentation including:

- Best practices
- Integration examples (Slack, Dependabot, etc.)
- Troubleshooting guide
- Architecture details

See the [full documentation](https://superagenticai.github.io/specmem/github-action/).

## License

MIT
