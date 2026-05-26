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
from specmem.guidelines.models import Guideline, SourceType
from specmem.guidelines.optimizer import (
    OptimizedSkillStore,
    rewrite_skill_with_openai,
    score_skill_static,
)


app = typer.Typer(
    name="guidelines",
    help="Manage and convert coding guidelines from various sources",
)

console = Console()


def _guideline_summary(guideline: Guideline) -> dict:
    return {
        "id": guideline.id,
        "title": guideline.title,
        "source_type": guideline.source_type.value,
        "source_file": guideline.source_file,
        "file_pattern": guideline.file_pattern,
        "tags": guideline.tags,
        "content_preview": guideline.content[:240] + "..."
        if len(guideline.content) > 240
        else guideline.content,
    }


@app.command("optimize")
def optimize_skill(
    skill: str = typer.Argument(..., help="Source SKILL.md to optimize"),
    candidate: str | None = typer.Option(
        None,
        "--candidate",
        "-c",
        help="Candidate optimized SKILL.md produced by a rollout/reflection process",
    ),
    instruction: str | None = typer.Option(
        None,
        "--instruction",
        "-i",
        help="Rewrite instruction for generating a candidate with OpenAI",
    ),
    model: str = typer.Option(
        "gpt-5-mini",
        "--model",
        help="OpenAI model for --instruction mode",
    ),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
    score_before: float | None = typer.Option(
        None,
        "--score-before",
        help="Baseline validation score for the source skill",
    ),
    score_after: float | None = typer.Option(
        None,
        "--score-after",
        help="Validation score for the candidate skill",
    ),
    evaluator: str = typer.Option("static", "--evaluator", help="Evaluation method name"),
    notes: str = typer.Option("", "--notes", help="Optional provenance notes"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Generate/write the candidate but do not promote it through the gate",
    ),
    write_source: bool = typer.Option(
        False,
        "--write-source",
        help="After acceptance, copy best_skill.md back to the source SKILL.md",
    ),
) -> None:
    """Validate and promote an optimized skill artifact for future indexing.

    With --candidate, the gate requires score improvement unless no explicit
    scores are supplied and static checks improve. With --instruction, SpecMem
    generates a candidate and accepts changed candidates that do not regress
    static checks. Accepted artifacts are consumed by
    ``specmem build --optimize-skills``.
    """
    workspace_path = Path(path)
    store = OptimizedSkillStore(workspace_path)

    candidate_path: Path
    if candidate:
        candidate_path = Path(candidate)
    elif instruction:
        source_path = Path(skill)
        if not source_path.is_absolute():
            source_path = workspace_path / source_path
        source_content = source_path.read_text(encoding="utf-8")
        console.print("[bold]Generating optimized skill candidate...[/bold]")
        candidate_content = rewrite_skill_with_openai(
            source_content,
            instruction,
            model=model,
        )
        candidate_path = store.write_generated_candidate(Path(skill), candidate_content)
        console.print(f"[green]✓[/green] Wrote candidate to {candidate_path}")
    else:
        console.print("[red]Error:[/red] provide either --candidate or --instruction")
        raise typer.Exit(1)

    if dry_run:
        console.print("[yellow]![/yellow] Dry run: candidate was not promoted")
        return

    result = store.promote_candidate(
        Path(skill),
        candidate_path,
        score_before=score_before,
        score_after=score_after,
        evaluator=evaluator if candidate else f"openai:{model}",
        notes=notes,
        allow_static_non_regression=bool(instruction and not candidate),
    )

    if result.accepted:
        console.print("[green]✓[/green] Accepted optimized skill candidate")
        if write_source:
            written = store.write_best_to_source(Path(skill))
            console.print(f"[green]✓[/green] Wrote accepted skill back to {written}")
    else:
        console.print("[yellow]![/yellow] Rejected optimized skill candidate")

    table = Table(title="Skill Optimization Gate")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Score before", f"{result.score_before:.4f}")
    table.add_row("Score after", f"{result.score_after:.4f}")
    table.add_row("Artifact", str(result.artifact_dir))
    table.add_row("Best skill", str(result.best_skill_path))
    table.add_row("Report", str(result.report_path))
    console.print(table)

    if result.issues:
        console.print("\n[bold]Gate notes:[/bold]")
        for issue in result.issues:
            console.print(f"  - {issue}")


@app.command("score-skill")
def score_skill(
    skill: str = typer.Argument(..., help="SKILL.md to score with static checks"),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
) -> None:
    """Score a skill document using SpecMem's static optimization checks."""
    skill_path = Path(skill)
    if not skill_path.is_absolute():
        skill_path = Path(path) / skill_path
    content = skill_path.read_text(encoding="utf-8")
    score, issues = score_skill_static(content)

    console.print(f"[bold]Static score:[/bold] {score:.4f}")
    if issues:
        console.print("[bold]Issues:[/bold]")
        for issue in issues:
            console.print(f"  - {issue}")


@app.command("optimized-status")
def optimized_status(
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
    robot: bool = typer.Option(False, "--robot", "-r", help="Output JSON for AI agents"),
) -> None:
    """Show optimized-skill artifact status for discovered skills."""
    workspace_path = Path(path)
    aggregator = GuidelinesAggregator(workspace_path)
    response = aggregator.get_all(include_samples=False)
    skills = [
        guideline
        for guideline in response.guidelines
        if guideline.source_type in {SourceType.CODEX_SKILL, SourceType.CLAUDE_SKILL}
    ]
    store = OptimizedSkillStore(workspace_path)
    rows = [(guideline, store.status(Path(guideline.source_file))) for guideline in skills]

    if robot:
        output = {
            "count": len(rows),
            "skills": [
                {
                    "title": guideline.title,
                    "source_type": guideline.source_type.value,
                    "source_file": str(status.source_path),
                    "state": status.state,
                    "reason": status.reason,
                    "artifact_dir": str(status.artifact_dir),
                    "best_skill_path": str(status.best_skill_path)
                    if status.best_skill_path
                    else None,
                    "report_path": str(status.report_path) if status.report_path else None,
                    "score_before": status.score_before,
                    "score_after": status.score_after,
                }
                for guideline, status in rows
            ],
        }
        print(json.dumps(output, indent=2))
        return

    if not rows:
        console.print("[yellow]No skill files found.[/yellow]")
        return

    table = Table(title="Optimized Skill Status")
    table.add_column("State", style="cyan", width=12)
    table.add_column("Skill", style="white")
    table.add_column("Source", style="dim")
    table.add_column("Score", style="green", width=15)
    table.add_column("Reason", style="dim")

    for guideline, status in rows:
        score = "-"
        if status.score_before is not None and status.score_after is not None:
            score = f"{status.score_before:.4f}->{status.score_after:.4f}"
        table.add_row(
            status.state,
            guideline.title,
            str(status.source_path),
            score,
            status.reason,
        )

    console.print(table)


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
                    "content_preview": g.content[:200] + "..."
                    if len(g.content) > 200
                    else g.content,
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
        console.print(
            f"\n[dim]Showing 20 of {len(guidelines)} guidelines. Use --robot for full list.[/dim]"
        )


@app.command("context")
def context(
    task: str | None = typer.Option(None, "--task", "-t", help="Task intent for skill routing"),
    files: list[str] | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Changed file path; repeat for multiple files",
    ),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
    robot: bool = typer.Option(False, "--robot", "-r", help="Output JSON for AI agents"),
) -> None:
    """Show the layered memory context an agent should load for a task.

    This is a deterministic routing view: always-on guidance first, file-scoped
    guidance for changed files second, and procedural skills only when the task
    intent matches.
    """
    workspace_path = Path(path)
    aggregator = GuidelinesAggregator(workspace_path)
    layers = aggregator.build_context(files=files or [], task=task)

    if robot:
        output = {
            "task": task,
            "files": files or [],
            "layers": {
                name: [_guideline_summary(guideline) for guideline in guidelines]
                for name, guidelines in layers.items()
            },
        }
        print(json.dumps(output, indent=2))
        return

    console.print("[bold]Agent Memory Context[/bold]\n")
    if task:
        console.print(f"[bold]Task:[/bold] {task}")
    if files:
        console.print(f"[bold]Files:[/bold] {', '.join(files)}")
    if task or files:
        console.print()

    labels = {
        "always_on": "1. Always-on Project Guidance",
        "file_scoped": "2. File-scoped Guidance",
        "skills": "3. Candidate Skills",
    }

    for layer_name, title in labels.items():
        guidelines = layers[layer_name]
        table = Table(title=f"{title} ({len(guidelines)})")
        table.add_column("Source", style="cyan", width=14)
        table.add_column("Title", style="white")
        table.add_column("Pattern", style="dim")
        table.add_column("File", style="dim")

        for guideline in guidelines[:10]:
            table.add_row(
                guideline.source_type.value,
                guideline.title[:48] + ("..." if len(guideline.title) > 48 else ""),
                guideline.file_pattern or "-",
                guideline.source_file,
            )

        console.print(table)
        if len(guidelines) > 10:
            console.print(f"[dim]Showing 10 of {len(guidelines)} in this layer.[/dim]")
        console.print()


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
        console.print("[bold]Format:[/bold] Kiro Steering")
        console.print(f"[bold]Output file:[/bold] {default_filename}")
        console.print(
            f"[bold]Inclusion mode:[/bold] {result.frontmatter.get('inclusion', 'always')}"
        )
        if result.frontmatter.get("fileMatchPattern"):
            console.print(f"[bold]File pattern:[/bold] {result.frontmatter['fileMatchPattern']}")
    elif format_lower == "claude":
        content = converter.to_claude([guideline])
        default_filename = "CLAUDE.md"
        default_output_dir = workspace_path

        console.print(f"\n[bold]Converting:[/bold] {guideline.title}")
        console.print("[bold]Format:[/bold] CLAUDE.md")
        console.print(f"[bold]Output file:[/bold] {default_filename}")
    else:  # cursor
        content = converter.to_cursor([guideline])
        default_filename = ".cursorrules"
        default_output_dir = workspace_path

        console.print(f"\n[bold]Converting:[/bold] {guideline.title}")
        console.print("[bold]Format:[/bold] .cursorrules")
        console.print(f"[bold]Output file:[/bold] {default_filename}")

    console.print("\n[bold]Generated content:[/bold]\n")
    console.print(
        Panel(content[:1000] + ("..." if len(content) > 1000 else ""), title=default_filename)
    )

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

        console.print(
            f"\n[bold]Converting {len(guidelines)} guidelines to {default_filename}:[/bold]\n"
        )
        console.print(
            Panel(content[:1000] + ("..." if len(content) > 1000 else ""), title=default_filename)
        )

        if preview:
            console.print("\n[dim]Use --no-preview to write the file.[/dim]")
            return

        output_path = Path(output) if output else workspace_path / default_filename
        output_path.write_text(content, encoding="utf-8")
        console.print(f"\n[green]✓[/green] Written to {output_path}")
