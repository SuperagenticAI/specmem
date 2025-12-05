# Static Dashboard

Generate a static, read-only SpecMem dashboard for viewing spec metrics.

## Overview

The static dashboard provides a read-only view of your spec data. It includes:

- 📊 Coverage and health metrics
- 📋 Spec browser with client-side search
- 📈 Historical trends (optional)
- 📜 Coding guidelines viewer

**Hosting is optional** - you can:
1. **View locally** - Just run a local server (no deployment needed)
2. **Host on GitHub Pages** - Optional, if you want to share with your team
3. **Host anywhere** - It's just static HTML/JS/CSS

## ⚠️ Important Limitations

!!! warning "Static Dashboard Limitations"
    - **Read-only**: No live search or real-time updates
    - **Data freshness**: Only as fresh as the last build
    - **No semantic search**: Requires embeddings server (not available in static mode)

## Quick Start (Local Only)

Generate and view the dashboard locally without any deployment:

```bash
# Export spec data
specmem export data

# Build static site
specmem export build

# Preview locally
python -m http.server -d .specmem/static 8080
# Open http://localhost:8080 in your browser
```

That's it! No GitHub Pages, no deployment, just local viewing.

## Optional: Deploy to GitHub Pages

If you want to share the dashboard with your team, you can optionally deploy to GitHub Pages.

### Using the GitHub Action

Add this workflow to your repository (`.github/workflows/specmem-dashboard.yml`):

```yaml
name: Deploy Dashboard
on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger

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

!!! note "GitHub Pages Conflicts"
    If your repo already uses GitHub Pages for docs, the dashboard deploys to `/specmem-dashboard/` by default to avoid conflicts.

## CLI Commands

### `specmem export data`

Export spec data to JSON for the static dashboard.

```bash
specmem export data [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--output`, `-o` | Output directory | `.specmem/export` |
| `--include-history/--no-history` | Include historical data | `true` |
| `--history-limit` | Max history entries | `30` |

### `specmem export build`

Build the static dashboard site.

```bash
specmem export build [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--data`, `-d` | Data directory | `.specmem/export` |
| `--output`, `-o` | Output directory | `.specmem/static` |
| `--base-path` | Base URL path | `/` (use `/specmem-dashboard/` for GitHub Pages subdirectory) |

## Hosting Options

### Option 1: Local Only (No Deployment)

Just serve the built files locally:

```bash
specmem export data
specmem export build
python -m http.server -d .specmem/static 8080
```

### Option 2: Any Static Host

Copy `.specmem/static/` to any static hosting service:
- Netlify, Vercel, Cloudflare Pages
- S3 + CloudFront
- Any web server (nginx, Apache)

### Option 3: GitHub Pages (Optional)

If you choose to use GitHub Pages, be aware of potential conflicts.

## GitHub Pages Conflicts

If your repository already uses GitHub Pages for documentation (MkDocs, Jekyll, Docusaurus, etc.), the dashboard action will:

1. **Detect conflicts** - Check for config files like `mkdocs.yml`, `_config.yml`
2. **Warn you** - Display a warning in the CI logs
3. **Deploy to subdirectory** - Use `/specmem-dashboard/` by default

### Conflict Resolution Options

**Option 1: Use a subdirectory (recommended)**

Your docs stay at the root, dashboard at `/specmem-dashboard/`:

```yaml
- uses: specmem/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    deploy_path: specmem-dashboard
```

**Option 2: Use a different path**

```yaml
- uses: specmem/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    deploy_path: specs  # Deploy to /specs/
```

**Option 3: Force deployment (use with caution)**

```yaml
- uses: specmem/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    force: true  # May overwrite existing content!
```

## Historical Trends

The dashboard can track metrics over time:

```yaml
- uses: specmem/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    include_history: true
    history_limit: 50  # Keep last 50 data points
```

History is stored in `.specmem/export/history.json` and persists across deployments.

## Dashboard Features

### Overview Page

Shows key metrics at a glance:

- Spec coverage percentage
- Health grade (A-F)
- Health score (0-100)
- Validation error count

### Specs Browser

Browse all specifications with:

- Client-side search (by name, path, content)
- Task completion progress bars
- Quick access to requirements, design, tasks

### Guidelines Page

View all coding guidelines from:

- Kiro steering files (`.kiro/steering/*.md`)
- Claude guidelines (`CLAUDE.md`)
- Cursor rules (`.cursorrules`)

### Trends Page

Historical charts showing:

- Coverage percentage over time
- Health score over time
- Validation errors over time

## Monorepo Support

For monorepos, specify the working directory:

```yaml
- uses: specmem/specmem/.github/actions/specmem-dashboard@main
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    working_directory: packages/my-app
    deploy_path: my-app-specs
```

## Example Workflows

### Basic Deployment

```yaml
name: Deploy SpecMem Dashboard
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy Dashboard
        uses: specmem/specmem/.github/actions/specmem-dashboard@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

### With Analysis Action

Combine with the analysis action for PR comments AND dashboard:

```yaml
name: Spec Analysis
on:
  pull_request:
  push:
    branches: [main]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Run analysis on PRs
      - uses: specmem/specmem/.github/actions/specmem@main
        if: github.event_name == 'pull_request'
        with:
          comment_on_pr: true

  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      
      # Deploy dashboard on main
      - uses: specmem/specmem/.github/actions/specmem-dashboard@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

## See Also

- [GitHub Action](github-action.md) - CI analysis action
- [CLI Reference](cli/index.md) - Full CLI documentation
- [Web UI](user-guide/web-ui.md) - Local interactive dashboard
