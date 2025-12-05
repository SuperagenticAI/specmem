"""CLI commands for coding guidelines.

Provides commands for listing, searching, and converting coding guidelines
from CLAUDE.md, .cursorrules, AGENTS.md, and Kiro steering files.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specmem.guidelines.aggregator import GuidelinesAggregator
from specmem.guidelines.converter import GuidelinesConverter
from specmem.guidelines.models import SourceType


app = typer.Typer(
    name="guidelines",
    help="Manage and convert coding guidelines from various sources",
)

console = Console()


@app.callback(invoke_without_command=True)
def list_guidelines(
    ctx: typer.Context,
    source: str | None = typer.Option(None, "--source", "-s", help="Filter by source type"),
    search: str | None = typer.Option(None, "--search", "-q", help="Search in title and content"),
    file: str | None = typer.Option(None, "--file", "-f", help="Show guidelines for a file"),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
    robot: bool = typer.Option(False, "--robot", "-r", help="Output JSON for AI agents"),
    no_samples: bool = typer.Option(False, "--no-samples", help="Exclude sample guidelines"),
) -> None:
    """List all coding guidelines.

    Without arguments, shows all guidelines with counts by source.
    Use --source to filter by type (claude, cursor, steering, agents).
    Use --search to find guidelines containing specific text.
    Use --file to show guidelines that apply to a specific file.

    Examples:
        specmem guidelines                    # List all guidelines
        specmem guidelines --source claude    # Only CLAUDE.md guidelines
        specmem guidelines --search testing   # Search for "testing"
        specmem guidelines --file src/auth.py # Guidelines for auth.py
    """
    if ctx.invoked_subcommand is not None:
        return

    workspace_path = Path(path)
    aggregator = GuidelinesAggregator(workspace_path)

    # Get guidelines based on filters
    if source:
        try:
            source_type = SourceType(source.lower())
            guidelines = aggregator.filter_by_source(source_type)
        except ValueError:
            console.print(f"[red]Invalid source type:[/red] {source}")
            console.print(f"Valid types: {', '.join(s.value for s in SourceType)}")
            raise typer.Exit(1)
    elif search:
        guidelines = aggregator.search(search)
    elif file:
        guidelines = aggregator.filter_by_file(file)
    else:
        response = aggregator.get_all(include_samples=not no_samples)
        guidelines = response.guidelines

    if robot:
        output = {
            "count": len(guidelines),
            "guidelines": [
                {
                    "id": g.id,
                    "title": g.title,
                    "source_type": g.source_type.value,
                    "source_file": g.source_file,
                    "file_pattern": g.file_pattern,
                    "is_sample": g.is_sample,
                    "content_preview": g.content[:200] + "..." if len(g.content) > 200 else g.content,
                }
                for g in guidelines
            ],
        }
        print(json.dumps(output, indent=2))
        return

    if not guidelines:
        console.print("[yellow]No guidelines found.[/yellow]")
        console.print("\nTry running without filters or check that guideline files exist:")
        console.print("  • CLAUDE.md")
        console.print("  • .cursorrules")
        console.print("  • AGENTS.md")
        console.print("  • .kiro/steering/*.md")
        return

    # Show summary
    response = aggregator.get_all(include_samples=not no_samples)
    if response.counts_by_source:
        console.print("\n[bold]Guidelines by Source:[/bold]")
        for src, count in sorted(response.counts_by_source.items()):
            console.print(f"  {src}: {count}")
        console.print()

    # Display guidelines table
    table = Table(title=f"Coding Guidelines ({len(guidelines)} total)")
    table.add_column("Source", style="cyan", width=10)
    table.add_column("Title", style="white")
    table.add_column("Pattern", style="dim")
    table.add_column("Sample", style="yellow", width=6)

    for g in guidelines[:20]:  # Limit display
        sample_marker = "✓" if g.is_sample else ""
        pattern = g.file_pattern or "-"
        title = g.title[:40] + ("..." if len(g.title) > 40 else "")
        table.add_row(g.source_type.value, title, pattern, sample_marker)

    console.print(table)

    if len(guidelines) > 20:
        console.print(f"\n[dim]Showing 20 of {len(guidelines)} guidelines. Use --robot for full list.[/dim]")



@app.command("show")
def show_guideline(
    guideline_id: str = typer.Argument(..., help="Guideline ID to show"),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
    robot: bool = typer.Option(False, "--robot", "-r", help="Output JSON for AI agents"),
) -> None:
    """Show full content of a specific guideline.

    Examples:
        specmem guidelines show abc123def456
    """
    workspace_path = Path(path)
    aggregator = GuidelinesAggregator(workspace_path)
    response = aggregator.get_all(include_samples=True)

    # Find guideline by ID (partial match)
    guideline = None
    for g in response.guidelines:
        if g.id.startswith(guideline_id) or guideline_id in g.id:
            guideline = g
            break

    if not guideline:
        console.print(f"[red]Guideline not found:[/red] {guideline_id}")
        raise typer.Exit(1)

    if robot:
        output = {
            "id": guideline.id,
            "title": guideline.title,
            "content": guideline.content,
            "source_type": guideline.source_type.value,
            "source_file": guideline.source_file,
            "file_pattern": guideline.file_pattern,
            "tags": guideline.tags,
            "is_sample": guideline.is_sample,
        }
        print(json.dumps(output, indent=2))
        return

    # Display full guideline
    sample_note = " [yellow](Sample)[/yellow]" if guideline.is_sample else ""
    console.print(
        Panel(
            f"[bold]{guideline.title}[/bold]{sample_note}\n\n"
            f"ID: {guideline.id}\n"
            f"Source: {guideline.source_type.value}\n"
            f"File: {guideline.source_file}\n"
            f"Pattern: {guideline.file_pattern or 'All files'}",
            title="Guideline Details",
        )
    )

    console.print("\n[bold]Content:[/bold]\n")
    console.print(guideline.content)


@app.command("convert")
def convert_guideline(
    guideline_id: str = typer.Argument(..., help="Guideline ID to convert"),
    format: str = typer.Argument(..., help="Target format: steering, claude, or cursor"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    preview: bool = typer.Option(True, "--preview/--no-preview", help="Preview before writing"),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
) -> None:
    """Convert a guideline to another format.

    Supported formats:
      - steering: Kiro steering file (.kiro/steering/*.md)
      - claude: CLAUDE.md format
      - cursor: .cursorrules format

    Examples:
        specmem guidelines convert abc123 steering   # Preview as steering
        specmem guidelines convert abc123 claude     # Preview as CLAUDE.md
        specmem guidelines convert abc123 cursor --no-preview  # Write .cursorrules
    """
    format_lower = format.lower()
    if format_lower not in ("steering", "claude", "cursor"):
        console.print(f"[red]Invalid format:[/red] {format}")
        console.print("Valid formats: steering, claude, cursor")
        raise typer.Exit(1)

    workspace_path = Path(path)
    aggregator = GuidelinesAggregator(workspace_path)
    converter = GuidelinesConverter()
    response = aggregator.get_all(include_samples=True)

    # Find guideline
    guideline = None
    for g in response.guidelines:
        if g.id.startswith(guideline_id) or guideline_id in g.id:
            guideline = g
            break

    if not guideline:
        console.print(f"[red]Guideline not found:[/red] {guideline_id}")
        raise typer.Exit(1)

    # Convert based on format
    if format_lower == "steering":
        result = converter.to_steering(guideline)
        content = result.content
        default_filename = result.filename
        default_output_dir = workspace_path / ".kiro" / "steering"

        console.print(f"\n[bold]Converting:[/bold] {guideline.title}")
        console.print(f"[bold]Format:[/bold] Kiro Steering")
        console.print(f"[bold]Output file:[/bold] {default_filename}")
        console.print(f"[bold]Inclusion mode:[/bold] {result.frontmatter.get('inclusion', 'always')}")
        if result.frontmatter.get("fileMatchPattern"):
            console.print(f"[bold]File pattern:[/bold] {result.frontmatter['fileMatchPattern']}")
    elif format_lower == "claude":
        content = converter.to_claude([guideline])
        default_filename = "CLAUDE.md"
        default_output_dir = workspace_path

        console.print(f"\n[bold]Converting:[/bold] {guideline.title}")
        console.print(f"[bold]Format:[/bold] CLAUDE.md")
        console.print(f"[bold]Output file:[/bold] {default_filename}")
    else:  # cursor
        content = converter.to_cursor([guideline])
        default_filename = ".cursorrules"
        default_output_dir = workspace_path

        console.print(f"\n[bold]Converting:[/bold] {guideline.title}")
        console.print(f"[bold]Format:[/bold] .cursorrules")
        console.print(f"[bold]Output file:[/bold] {default_filename}")

    console.print("\n[bold]Generated content:[/bold]\n")
    console.print(Panel(content[:1000] + ("..." if len(content) > 1000 else ""), title=default_filename))

    if preview:
        console.print("\n[dim]Use --no-preview to write the file.[/dim]")
        return

    # Write file
    output_path = Path(output) if output else default_output_dir / default_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    console.print(f"\n[green]✓[/green] Written to {output_path}")


@app.command("convert-all")
def convert_all_guidelines(
    format: str = typer.Argument(..., help="Target format: steering, claude, or cursor"),
    source: str | None = typer.Option(None, "--source", "-s", help="Only convert from this source"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file/directory path"),
    preview: bool = typer.Option(True, "--preview/--no-preview", help="Preview before writing"),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
) -> None:
    """Convert all guidelines to a target format.

    Supported formats:
      - steering: Individual Kiro steering files (.kiro/steering/*.md)
      - claude: Single CLAUDE.md file
      - cursor: Single .cursorrules file

    Examples:
        specmem guidelines convert-all steering              # Preview as steering files
        specmem guidelines convert-all claude                # Preview as CLAUDE.md
        specmem guidelines convert-all cursor --no-preview   # Write .cursorrules
        specmem guidelines convert-all steering --source claude  # Only from CLAUDE.md
    """
    format_lower = format.lower()
    if format_lower not in ("steering", "claude", "cursor"):
        console.print(f"[red]Invalid format:[/red] {format}")
        console.print("Valid formats: steering, claude, cursor")
        raise typer.Exit(1)

    workspace_path = Path(path)
    aggregator = GuidelinesAggregator(workspace_path)
    converter = GuidelinesConverter()

    # Get guidelines
    if source:
        try:
            source_type = SourceType(source.lower())
            guidelines = aggregator.filter_by_source(source_type)
        except ValueError:
            console.print(f"[red]Invalid source type:[/red] {source}")
            raise typer.Exit(1)
    else:
        response = aggregator.get_all(include_samples=False)
        guidelines = [g for g in response.guidelines if not g.is_sample]

    if not guidelines:
        console.print("[yellow]No guidelines to convert.[/yellow]")
        return

    # Convert based on format
    if format_lower == "steering":
        results = converter.bulk_convert_to_steering(guidelines)

        console.print(f"\n[bold]Converting {len(results)} guidelines to steering files:[/bold]\n")

        table = Table()
        table.add_column("Source", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Output File", style="green")
        table.add_column("Mode", style="dim")

        for result in results:
            table.add_row(
                result.source_guideline.source_type.value,
                result.source_guideline.title[:30] + "...",
                result.filename,
                result.frontmatter.get("inclusion", "always"),
            )

        console.print(table)

        if preview:
            console.print("\n[dim]Use --no-preview to write all files.[/dim]")
            return

        # Write files
        output_dir = Path(output) if output else workspace_path / ".kiro" / "steering"
        written = converter.write_steering_files(results, output_dir)
        console.print(f"\n[green]✓[/green] Written {len(written)} steering files to {output_dir}")

    else:
        # Single file output (claude or cursor)
        if format_lower == "claude":
            content = converter.to_claude(guidelines)
            default_filename = "CLAUDE.md"
        else:  # cursor
            content = converter.to_cursor(guidelines)
            default_filename = ".cursorrules"

        console.print(f"\n[bold]Converting {len(guidelines)} guidelines to {default_filename}:[/bold]\n")
        console.print(Panel(content[:1000] + ("..." if len(content) > 1000 else ""), title=default_filename))

        if preview:
            console.print("\n[dim]Use --no-preview to write the file.[/dim]")
            return

        output_path = Path(output) if output else workspace_path / default_filename
        output_path.write_text(content, encoding="utf-8")
        console.print(f"\n[green]✓[/green] Written to {output_path}")
