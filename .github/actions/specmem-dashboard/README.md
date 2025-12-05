# SpecMem Dashboard Deploy Action

Deploy a static SpecMem dashboard to GitHub Pages for free hosting.

## ⚠️ Important Limitations

- **Static Dashboard**: This deploys a read-only snapshot of your spec data. No live search or real-time updates.
- **GitHub Pages Conflict**: If your repository already uses GitHub Pages for documentation (MkDocs, Jekyll, Docusaurus, etc.), this action will deploy to a subdirectory to avoid conflicts.
- **Data Freshness**: Dashboard data is only as fresh as the last CI run.

## Quick Start

```yaml
name: Deploy Dashboard
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: specmem/specmem/.github/actions/specmem-dashboard@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `deploy_path` | Path within GitHub Pages | `specmem-dashboard` |
| `force` | Force deployment even if conflicts detected | `false` |
| `include_history` | Include historical trend data | `true` |
| `history_limit` | Maximum history entries to keep | `30` |
| `install_from` | Installation source: `pypi` or `github` | `pypi` |
| `version` | SpecMem version or git ref | `latest` |
| `github_repo` | GitHub repo for installation | `specmem/specmem` |
| `github_token` | GitHub token for deployment | **required** |
| `python_version` | Python version to use | `3.11` |
| `working_directory` | Directory to run analysis in | `.` |

## Outputs

| Output | Description |
|--------|-------------|
| `dashboard_url` | URL of deployed dashboard |
| `export_path` | Path to exported data |

## Examples

### Basic Usage

```yaml
- uses: specmem/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

### Custom Deploy Path

```yaml
- uses: specmem/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    deploy_path: specs  # Deploy to /specs/ instead of /specmem-dashboard/
```

### With Historical Trends

```yaml
- uses: specmem/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    include_history: true
    history_limit: 50  # Keep last 50 data points
```

### Monorepo Support

```yaml
- uses: specmem/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    working_directory: packages/my-app
    deploy_path: my-app-specs
```

## GitHub Pages Conflicts

If your repository already uses GitHub Pages for documentation, the action will:

1. **Detect conflicts** - Check for `mkdocs.yml`, `_config.yml`, `docusaurus.config.js`, etc.
2. **Warn you** - Display a warning about potential conflicts
3. **Deploy to subdirectory** - By default, deploys to `/specmem-dashboard/` to avoid overwriting your docs

### Workarounds

**Option 1: Use a subdirectory (recommended)**
```yaml
deploy_path: specmem-dashboard  # Your docs stay at root, dashboard at /specmem-dashboard/
```

**Option 2: Force deployment (use with caution)**
```yaml
force: true  # May overwrite existing content
```

**Option 3: Use a different branch**
Configure GitHub Pages to serve from a different branch for your docs.

## Dashboard Features

The static dashboard includes:

- 📊 **Overview** - Coverage %, health grade, validation errors
- 📋 **Specs Browser** - Browse all specifications with client-side search
- 📈 **Trends** - Historical coverage and health charts (if history enabled)
- 📜 **Guidelines** - View coding guidelines from all formats

## License

MIT
