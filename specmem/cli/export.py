"""CLI commands for static dashboard export.

This module provides CLI commands for exporting spec data
and building static dashboards.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from specmem.export.exporter import StaticExporter
from specmem.export.history import HistoryManager

app = typer.Typer(help="Export spec data for static dashboard deployment")
console = Console()


@app.command("data")
def export_data(
    output: Path = typer.Option(
        Path(".specmem/export"),
        "--output", "-o",
        help="Output directory for export",
    ),
    include_history: bool = typer.Option(
        True,
        "--include-history/--no-history",
        help="Include and append to history file",
    ),
    history_limit: int = typer.Option(
        30,
        "--history-limit",
        help="Maximum number of history entries to keep",
    ),
) -> None:
    """Export spec data to JSON for static dashboard.

    This command collects coverage, health, validation, and spec data
    and exports it to a JSON file that can be used by the static dashboard.
    """
    workspace = Path.cwd()

    console.print("[bold blue]📦 Exporting spec data...[/bold blue]")

    # Create exporter and generate bundle
    exporter = StaticExporter(workspace, output)
    bundle = exporter.export()

    # Handle history
    if include_history:
        history_file = output / "history.json"
        history_manager = HistoryManager(history_file, limit=history_limit)
        history_entries = history_manager.append(bundle)
        bundle.history = history_entries
        console.print(f"  📈 History: {len(history_entries)} entries")

    # Save the bundle
    output_file = exporter.save(bundle)

    # Print summary
    console.print()
    console.print("[bold green]✅ Export complete![/bold green]")
    console.print()
    console.print(f"  📁 Output: {output_file}")
    console.print(f"  📊 Coverage: {bundle.coverage_percentage:.1f}%")
    console.print(f"  💚 Health: {bundle.health_grade} ({bundle.health_score:.0f}/100)")
    console.print(f"  📋 Specs: {len(bundle.specs)}")
    console.print(f"  📜 Guidelines: {len(bundle.guidelines)}")

    if bundle.validation_errors:
        console.print(f"  ⚠️  Validation errors: {len(bundle.validation_errors)}")


@app.command("build")
def build_static(
    data_dir: Path = typer.Option(
        Path(".specmem/export"),
        "--data", "-d",
        help="Directory containing exported data",
    ),
    output: Path = typer.Option(
        Path(".specmem/static"),
        "--output", "-o",
        help="Output directory for static site",
    ),
    base_path: str = typer.Option(
        "/specmem-dashboard/",
        "--base-path",
        help="Base path for the static site (for subdirectory deployment)",
    ),
) -> None:
    """Build static dashboard site from exported data.

    This command takes the exported JSON data and builds a static
    React site that can be deployed to GitHub Pages.
    """
    import json
    import shutil

    console.print("[bold blue]🔨 Building static dashboard...[/bold blue]")

    # Check data file exists
    data_file = data_dir / "data.json"
    if not data_file.exists():
        console.print(f"[red]Error: Data file not found: {data_file}[/red]")
        console.print("Run 'specmem export data' first to generate the data.")
        raise typer.Exit(1)

    # Create output directory
    output.mkdir(parents=True, exist_ok=True)

    # Load data
    with open(data_file, encoding="utf-8") as f:
        data = json.load(f)

    # Generate static HTML
    html_content = _generate_static_html(data, base_path)

    # Write index.html
    index_file = output / "index.html"
    index_file.write_text(html_content, encoding="utf-8")

    # Copy data.json to output
    shutil.copy(data_file, output / "data.json")

    console.print()
    console.print("[bold green]✅ Static site built![/bold green]")
    console.print()
    console.print(f"  📁 Output: {output}")
    console.print(f"  🌐 Base path: {base_path}")
    console.print()
    console.print("To preview locally:")
    console.print(f"  python -m http.server -d {output} 8080")


def _generate_static_html(data: dict, base_path: str) -> str:
    """Generate static HTML with embedded data.

    Args:
        data: The export data dictionary
        base_path: Base path for the site

    Returns:
        HTML content as string
    """
    import json

    metadata = data.get("metadata", {})
    coverage = data.get("coverage", {})
    health = data.get("health", {})
    validation = data.get("validation", {})
    specs = data.get("specs", [])
    guidelines = data.get("guidelines", [])
    history = data.get("history", [])

    # Escape data for embedding in HTML
    data_json = json.dumps(data).replace("</", "<\\/")

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpecMem Dashboard</title>
    <base href="{base_path}">
    <style>
        :root {{
            --primary: #7c3aed;
            --primary-light: #a78bfa;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg: #0f172a;
            --bg-card: #1e293b;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #334155;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        .header h1 {{ color: var(--primary-light); }}
        .static-badge {{
            background: var(--warning);
            color: #000;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .meta {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 2rem;
        }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: var(--bg-card);
            border-radius: 0.75rem;
            padding: 1.5rem;
            border: 1px solid var(--border);
        }}
        .card-title {{
            color: var(--text-muted);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}
        .card-value {{
            font-size: 2.5rem;
            font-weight: 700;
        }}
        .card-value.success {{ color: var(--success); }}
        .card-value.warning {{ color: var(--warning); }}
        .card-value.danger {{ color: var(--danger); }}
        .section {{ margin-bottom: 2rem; }}
        .section-title {{
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: var(--primary-light);
        }}
        .spec-list {{
            display: grid;
            gap: 1rem;
        }}
        .spec-item {{
            background: var(--bg-card);
            border-radius: 0.5rem;
            padding: 1rem;
            border: 1px solid var(--border);
        }}
        .spec-name {{
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}
        .spec-path {{
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        .progress-bar {{
            height: 0.5rem;
            background: var(--border);
            border-radius: 9999px;
            margin-top: 0.5rem;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: var(--success);
            border-radius: 9999px;
        }}
        .search-box {{
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            color: var(--text);
            font-size: 1rem;
            margin-bottom: 1rem;
        }}
        .search-box:focus {{
            outline: none;
            border-color: var(--primary);
        }}
        .hidden {{ display: none !important; }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📊 SpecMem Dashboard</h1>
            <span class="static-badge">⚡ Static Snapshot</span>
        </header>

        <div class="meta">
            Generated: {metadata.get('generated_at', 'Unknown')} |
            Commit: {metadata.get('commit_sha', 'N/A')} |
            Branch: {metadata.get('branch', 'N/A')} |
            Version: {metadata.get('specmem_version', 'Unknown')}
        </div>

        <div class="cards">
            <div class="card">
                <div class="card-title">Spec Coverage</div>
                <div class="card-value {'success' if coverage.get('coverage_percentage', 0) >= 80 else 'warning' if coverage.get('coverage_percentage', 0) >= 50 else 'danger'}">
                    {coverage.get('coverage_percentage', 0):.1f}%
                </div>
            </div>
            <div class="card">
                <div class="card-title">Health Grade</div>
                <div class="card-value {'success' if health.get('letter_grade', 'N/A') in ['A', 'B'] else 'warning' if health.get('letter_grade', 'N/A') == 'C' else 'danger'}">
                    {health.get('letter_grade', 'N/A')}
                </div>
            </div>
            <div class="card">
                <div class="card-title">Health Score</div>
                <div class="card-value">{health.get('overall_score', 0):.0f}</div>
            </div>
            <div class="card">
                <div class="card-title">Validation Errors</div>
                <div class="card-value {'success' if len(validation.get('errors', [])) == 0 else 'danger'}">
                    {len(validation.get('errors', []))}
                </div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📋 Specifications ({len(specs)})</h2>
            <input type="text" class="search-box" placeholder="Search specs..." id="spec-search">
            <div class="spec-list" id="spec-list">
                {''.join(_render_spec_item(spec) for spec in specs)}
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📜 Guidelines ({len(guidelines)})</h2>
            <div class="spec-list">
                {''.join(_render_guideline_item(g) for g in guidelines)}
            </div>
        </div>
    </div>

    <script>
        const specData = {data_json};

        // Client-side search
        document.getElementById('spec-search').addEventListener('input', function(e) {{
            const query = e.target.value.toLowerCase();
            const items = document.querySelectorAll('#spec-list .spec-item');
            items.forEach(item => {{
                const name = item.dataset.name.toLowerCase();
                const path = item.dataset.path.toLowerCase();
                if (name.includes(query) || path.includes(query)) {{
                    item.classList.remove('hidden');
                }} else {{
                    item.classList.add('hidden');
                }}
            }});
        }});
    </script>
</body>
</html>'''


def _render_spec_item(spec: dict) -> str:
    """Render a single spec item."""
    total = spec.get('task_total', 0)
    completed = spec.get('task_completed', 0)
    progress = (completed / total * 100) if total > 0 else 0

    return f'''
        <div class="spec-item" data-name="{spec.get('name', '')}" data-path="{spec.get('path', '')}">
            <div class="spec-name">{spec.get('name', 'Unknown')}</div>
            <div class="spec-path">{spec.get('path', '')}</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {progress}%"></div>
            </div>
            <div class="spec-path">{completed}/{total} tasks complete</div>
        </div>
    '''


def _render_guideline_item(guideline: dict) -> str:
    """Render a single guideline item."""
    return f'''
        <div class="spec-item">
            <div class="spec-name">{guideline.get('name', 'Unknown')}</div>
            <div class="spec-path">{guideline.get('path', '')} ({guideline.get('source_format', 'unknown')})</div>
        </div>
    '''
