"""SpecMem CLI - Command Line Interface.

Provides commands for scanning, building, and querying specification memory.
"""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from specmem import __version__
from specmem.adapters import detect_adapters, get_registry
from specmem.agentx import PackBuilder
from specmem.cli.cov import app as cov_app
from specmem.cli.demo import demo as demo_command
from specmem.cli.guidelines import app as guidelines_app
from specmem.cli.kiro_config import steering_command
from specmem.cli.lifecycle import app as lifecycle_app
from specmem.cli.sessions import app as sessions_app
from specmem.core import SpecMemConfig
from specmem.core.memory_bank import MemoryBank
from specmem.vectordb import SUPPORTED_BACKENDS, LanceDBStore, get_embedding_provider


app = typer.Typer(
    name="specmem",
    help="SpecMem - Unified Agent Memory for Spec-Driven Development",
    add_completion=False,
)

# Register subcommands
app.add_typer(cov_app, name="cov")
app.add_typer(guidelines_app, name="guidelines")
app.add_typer(sessions_app, name="sessions")
app.add_typer(lifecycle_app, name="lifecycle")

# Register export commands for static dashboard
from specmem.cli.export import app as export_app

app.add_typer(export_app, name="export")

# Register demo command
app.command(name="demo")(demo_command)

# Register lifecycle commands as top-level aliases
from specmem.cli.lifecycle import compress, generate, health, prune


app.command(name="prune")(prune)
app.command(name="generate")(generate)
app.command(name="compress")(compress)
app.command(name="health")(health)

# Register kiro-config commands using click adapter


# Create a click-based kiro-config command
@app.command(name="kiro-config")
def kiro_config_cmd(
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
) -> None:
    """Display summary of all Kiro configuration."""
    from specmem.cli.kiro_config import show_config

    show_config.callback(Path(path))


@app.command(name="steering")
def steering_cmd(
    file: str = typer.Option(None, "--file", "-f", help="Show steering for this file"),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path"),
) -> None:
    """Query steering files applicable to a file."""
    steering_command.callback(file, Path(path))


console = Console()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_time=False, show_path=False)],
    )


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """SpecMem - Unified Agent Memory for Spec-Driven Development."""
    setup_logging(verbose)


@app.command()
def version() -> None:
    """Show SpecMem version."""
    console.print(f"SpecMem version {__version__}")


@app.command()
def init(
    path: str = typer.Argument(".", help="Path to initialize"),
    hooks: bool = typer.Option(False, "--hooks", help="Install Kiro hooks for automation"),
) -> None:
    """Initialize SpecMem configuration in a directory.

    Use --hooks to also install Kiro hooks for:
    - Auto-validate specs on save
    - Update coverage when tests change
    - Context reminders for agents
    """
    target_path = Path(path)
    config_path = target_path / ".specmem.toml"

    if config_path.exists():
        console.print(f"[yellow]Configuration already exists at {config_path}[/yellow]")
        if not hooks:
            raise typer.Exit(1)
    else:
        config = SpecMemConfig()
        config.save(config_path)
        console.print(f"[green]✓[/green] Initialized SpecMem at {config_path}")

    # Install Kiro hooks if requested
    if hooks:
        from specmem.hooks.generator import KiroHooksGenerator

        generator = KiroHooksGenerator(target_path)
        count = generator.write_hooks()
        if count > 0:
            console.print(f"[green]✓[/green] Installed {count} Kiro hook(s)")
        else:
            console.print("[yellow]![/yellow] Hooks already exist")

    console.print("\nNext steps:")
    console.print("  1. Run [bold]specmem scan[/bold] to detect specifications")
    console.print("  2. Run [bold]specmem build[/bold] to create the Agent Experience Pack")
    if hooks:
        console.print("  3. Kiro hooks are ready - specs will auto-validate on save!")


@app.command("vector-backend")
def vector_backend(
    backend: str = typer.Argument(None, help="Backend name to switch to"),
) -> None:
    """View or change the vector database backend.

    Supported backends: lancedb, chroma, qdrant, weaviate, milvus, agentvectordb

    Examples:
        specmem vector-backend          # Show current backend
        specmem vector-backend chroma   # Switch to ChromaDB
    """
    config = SpecMemConfig.load()

    if backend is None:
        # Display current backend
        console.print(f"Current vector backend: [bold]{config.vectordb.backend}[/bold]")
        console.print("\nSupported backends:")
        for name in sorted(SUPPORTED_BACKENDS):
            marker = " [green]✓[/green]" if name == config.vectordb.backend else ""
            console.print(f"  • {name}{marker}")
        return

    # Validate backend
    if backend not in SUPPORTED_BACKENDS:
        console.print(f"[red]Error:[/red] Unsupported backend: {backend}")
        console.print(f"\nSupported backends: {', '.join(sorted(SUPPORTED_BACKENDS))}")
        raise typer.Exit(1)

    # Warn about data migration
    if backend != config.vectordb.backend:
        console.print(
            f"[yellow]Warning:[/yellow] Switching from {config.vectordb.backend} to {backend}"
        )
        console.print("  • Existing vector data will not be migrated automatically")
        console.print("  • Run [bold]specmem build[/bold] to rebuild the vector store")

    # Update config
    config.vectordb.backend = backend
    config_path = Path.cwd() / ".specmem.toml"
    config.save(config_path)

    console.print(f"\n[green]✓[/green] Vector backend set to [bold]{backend}[/bold]")


@app.command()
def scan(path: str = typer.Argument(".", help="Repository path to scan")) -> None:
    """Scan repository for specifications."""
    repo_path = path

    console.print(f"Scanning [bold]{repo_path}[/bold] for specifications...\n")

    registry = get_registry()
    detected = detect_adapters(repo_path)

    if not detected:
        console.print("[yellow]No specification frameworks detected.[/yellow]")
        console.print("\nSupported frameworks:")
        for name in registry.names():
            console.print(f"  • {name}")
        raise typer.Exit(1)

    all_blocks = []
    for adapter in detected:
        console.print(f"[green]✓[/green] Detected [bold]{adapter.name}[/bold]")
        blocks = adapter.load(repo_path)
        all_blocks.extend(blocks)
        console.print(f"  Loaded {len(blocks)} specification blocks")

    console.print(f"\n[bold]Total:[/bold] {len(all_blocks)} specification blocks")

    if all_blocks:
        table = Table(title="Specifications by Type")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")

        type_counts: dict[str, int] = {}
        for block in all_blocks:
            type_counts[block.type.value] = type_counts.get(block.type.value, 0) + 1

        for spec_type, count in sorted(type_counts.items()):
            table.add_row(spec_type, str(count))

        console.print(table)


@app.command()
def build(
    path: str = typer.Argument(".", help="Repository path"),
    output: str = typer.Option("", "--output", "-o", help="Output directory"),
) -> None:
    """Build Agent Experience Pack from specifications."""
    repo_path = path
    output_dir = output or str(Path(repo_path) / ".specmem")

    console.print(f"Building Agent Experience Pack from [bold]{repo_path}[/bold]...\n")

    config = SpecMemConfig.load()
    detected = detect_adapters(repo_path)

    if not detected:
        console.print("[red]No specification frameworks detected.[/red]")
        raise typer.Exit(1)

    all_blocks = []
    for adapter in detected:
        blocks = adapter.load(repo_path)
        all_blocks.extend(blocks)
        console.print(f"[green]✓[/green] Loaded {len(blocks)} blocks from {adapter.name}")

    if not all_blocks:
        console.print("[yellow]No specification blocks found.[/yellow]")
        raise typer.Exit(1)

    console.print("\nGenerating embeddings...")
    vector_store = LanceDBStore(db_path=config.vectordb.path)
    embedding_provider = get_embedding_provider(
        provider=config.embedding.provider,
        model=config.embedding.model,
        api_key=config.embedding.get_api_key(),
    )

    memory_bank = MemoryBank(vector_store, embedding_provider)
    memory_bank.initialize()
    memory_bank.add_blocks(all_blocks)

    console.print("Building Agent Experience Pack...")
    pack_builder = PackBuilder(output_dir=output_dir)
    pack_builder.build(all_blocks)

    console.print(f"\n[green]✓[/green] Built Agent Experience Pack at [bold]{output_dir}[/bold]")
    console.print("\nGenerated files:")
    console.print(f"  • {output_dir}/agent_memory.json")
    console.print(f"  • {output_dir}/agent_context.md")
    console.print(f"  • {output_dir}/knowledge_index.json")


@app.command()
def info(path: str = typer.Argument(".", help="Repository path")) -> None:
    """Display memory statistics."""
    import json

    repo_path = Path(path)
    specmem_dir = repo_path / ".specmem"

    if not specmem_dir.exists():
        console.print("[yellow]No SpecMem data found. Run 'specmem build' first.[/yellow]")
        raise typer.Exit(1)

    memory_path = specmem_dir / "agent_memory.json"
    if not memory_path.exists():
        console.print("[red]agent_memory.json not found.[/red]")
        raise typer.Exit(1)

    with open(memory_path) as f:
        memory_data = json.load(f)

    stats = memory_data.get("statistics", {})

    console.print("[bold]SpecMem Memory Statistics[/bold]\n")

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Blocks", str(stats.get("total", 0)))
    table.add_row("Pinned Blocks", str(stats.get("pinned", 0)))
    table.add_row("Generated At", memory_data.get("generated_at", "Unknown"))

    console.print(table)

    by_type = stats.get("by_type", {})
    if by_type:
        console.print("\n[bold]By Type:[/bold]")
        for spec_type, count in sorted(by_type.items()):
            console.print(f"  {spec_type}: {count}")


@app.command()
def query(
    question: str = typer.Argument(..., help="Query to search for"),
    top_k: int = typer.Option(5, "--top", "-k", help="Number of results"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Query memory for relevant specifications."""
    config = SpecMemConfig.load()

    vector_store = LanceDBStore(db_path=config.vectordb.path)
    vector_store.initialize()

    if vector_store.count() == 0:
        console.print("[yellow]No data in memory. Run 'specmem build' first.[/yellow]")
        raise typer.Exit(1)

    embedding_provider = get_embedding_provider(
        provider=config.embedding.provider,
        model=config.embedding.model,
        api_key=config.embedding.get_api_key(),
    )

    memory_bank = MemoryBank(vector_store, embedding_provider)
    results = memory_bank.query(question, top_k=top_k)

    if not results:
        console.print("[yellow]No matching specifications found.[/yellow]")
        return

    console.print(f"\n[bold]Results for:[/bold] {question}\n")

    for i, result in enumerate(results, 1):
        block = result.block
        score = result.score

        console.print(f"[bold]{i}.[/bold] [{block.type.value}] (score: {score:.3f})")
        console.print(f"   [dim]{block.source}[/dim]")

        text = block.text[:200]
        if len(block.text) > 200:
            text += "..."
        console.print(f"   {text}\n")


@app.command()
def impact(
    path: str = typer.Argument(".", help="Repository path"),
    base_ref: str = typer.Option("HEAD~1", "--base", "-b", help="Git reference"),
) -> None:
    """Analyze impact of code changes on specifications."""
    from specmem.impact import SpecImpactAnalyzer

    repo_path = path

    console.print(f"Analyzing impact in [bold]{repo_path}[/bold]...\n")

    detected = detect_adapters(repo_path)
    if not detected:
        console.print("[yellow]No specification frameworks detected.[/yellow]")
        raise typer.Exit(1)

    all_blocks = []
    for adapter in detected:
        blocks = adapter.load(repo_path)
        all_blocks.extend(blocks)

    analyzer = SpecImpactAnalyzer(repo_path)
    result = analyzer.analyze(all_blocks, base_ref)

    if not result.changed_files:
        console.print("[green]No changed files detected.[/green]")
        return

    console.print(f"[bold]Changed Files:[/bold] {len(result.changed_files)}")
    for f in result.changed_files[:10]:
        console.print(f"  • {f}")
    if len(result.changed_files) > 10:
        console.print(f"  ... and {len(result.changed_files) - 10} more")

    console.print(f"\n[bold]Affected Specifications:[/bold] {len(result.affected_specs)}")
    for spec in result.affected_specs[:5]:
        console.print(f"  • [{spec.type.value}] {spec.text[:60]}...")

    if result.uncovered_files:
        console.print(f"\n[yellow]Uncovered Files:[/yellow] {len(result.uncovered_files)}")
        for f in result.uncovered_files[:5]:
            console.print(f"  • {f}")


@app.command()
def tests(
    spec_id: str = typer.Argument(None, help="Spec ID to get tests for"),
    file: str = typer.Option(None, "--file", "-f", help="File path to get tests for"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Show tests mapped to specifications.

    Examples:
        specmem tests auth.login          # Tests for a specific spec
        specmem tests --file src/auth.py  # Tests for a file
    """
    from specmem.testing import TestMappingEngine

    repo_path = Path(path)
    engine = TestMappingEngine(repo_path)

    if spec_id:
        # Get tests for a specific spec
        detected = detect_adapters(str(repo_path))
        all_blocks = []
        for adapter in detected:
            blocks = adapter.load(str(repo_path))
            all_blocks.extend(blocks)

        # Find the spec
        spec = None
        for block in all_blocks:
            if block.id == spec_id or spec_id in block.id:
                spec = block
                break

        if not spec:
            console.print(f"[red]Spec not found:[/red] {spec_id}")
            raise typer.Exit(1)

        mappings = engine.get_tests_for_spec(spec)

        if not mappings:
            console.print(f"[yellow]No tests mapped to spec:[/yellow] {spec_id}")
            return

        console.print(f"\n[bold]Tests for spec:[/bold] {spec_id}\n")

    elif file:
        # Get tests for a file
        mappings = engine.get_tests_for_files([file])

        if not mappings:
            console.print(f"[yellow]No tests found for file:[/yellow] {file}")
            return

        console.print(f"\n[bold]Tests for file:[/bold] {file}\n")

    else:
        console.print("[red]Please provide either a spec_id or --file option[/red]")
        raise typer.Exit(1)

    # Display results
    table = Table()
    table.add_column("Framework", style="cyan")
    table.add_column("Path")
    table.add_column("Selector")
    table.add_column("Confidence", justify="right")

    for mapping in mappings:
        table.add_row(
            mapping.framework,
            mapping.path,
            mapping.selector,
            f"{mapping.confidence:.2f}",
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(mappings)} tests")


@app.command()
def infer(
    file: str = typer.Argument(..., help="Code file to analyze"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Infer specifications from code.

    Analyzes a code file and suggests potential specifications
    based on function/class definitions and documentation.

    Examples:
        specmem infer src/auth.py
        specmem infer lib/utils.ts
    """
    from specmem.testing import CodeAnalyzer

    repo_path = Path(path)
    analyzer = CodeAnalyzer(repo_path)

    file_path = Path(file)
    if not file_path.is_absolute():
        file_path = repo_path / file_path

    if not file_path.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    console.print(f"Analyzing [bold]{file}[/bold]...\n")

    # Load existing specs for matching
    detected = detect_adapters(str(repo_path))
    existing_specs = []
    for adapter in detected:
        blocks = adapter.load(str(repo_path))
        existing_specs.extend(blocks)

    # Infer specs
    candidates = analyzer.infer_specs(file_path, existing_specs)

    if not candidates:
        console.print("[yellow]No specifications could be inferred from this file.[/yellow]")
        console.print("\nThis might be because:")
        console.print("  • The file contains no public functions or classes")
        console.print("  • The file uses unsupported syntax")
        return

    console.print(f"[bold]Inferred Specifications:[/bold] {len(candidates)}\n")

    for i, candidate in enumerate(candidates, 1):
        matched = "✓ Matched" if candidate.matched_spec_id else "New"
        confidence_color = (
            "green"
            if candidate.confidence >= 0.7
            else "yellow"
            if candidate.confidence >= 0.5
            else "red"
        )

        console.print(f"[bold]{i}.[/bold] {candidate.title}")
        console.print(f"   Type: [{candidate.spec_type.value}]")
        console.print(
            f"   Confidence: [{confidence_color}]{candidate.confidence:.2f}[/{confidence_color}]"
        )
        console.print(f"   Status: {matched}")
        if candidate.matched_spec_id:
            console.print(f"   Matched to: {candidate.matched_spec_id}")
        console.print(f"   Rationale: {candidate.rationale}")

        if candidate.code_refs:
            ref = candidate.code_refs[0]
            console.print(f"   Location: {ref.file_path}")
            if ref.line_range:
                console.print(f"   Lines: {ref.line_range[0]}-{ref.line_range[1]}")

        console.print()


# =============================================================================
# Graph Commands
# =============================================================================

graph_app = typer.Typer(
    name="graph",
    help="SpecImpact Graph commands for impact analysis",
)
app.add_typer(graph_app, name="graph")


@graph_app.command("impact")
def graph_impact(
    files: list[str] = typer.Argument(..., help="Files to analyze"),
    depth: int = typer.Option(2, "--depth", "-d", help="Traversal depth"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json)"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Show specs and tests affected by file changes.

    Examples:
        specmem graph impact src/auth.py
        specmem graph impact src/auth.py src/user.py --depth 3
        specmem graph impact src/auth.py --format json
    """
    import json as json_module

    from specmem.impact import GraphBuilder, SpecImpactGraph

    repo_path = Path(path)
    graph_path = repo_path / ".specmem" / "impact_graph.json"

    # Load or build graph
    if graph_path.exists():
        graph = SpecImpactGraph(graph_path)
    else:
        console.print("[yellow]Building impact graph...[/yellow]")
        detected = detect_adapters(str(repo_path))
        all_blocks = []
        for adapter in detected:
            blocks = adapter.load(str(repo_path))
            all_blocks.extend(blocks)

        builder = GraphBuilder(repo_path)
        graph = builder.build(all_blocks, storage_path=graph_path)

    # Query impact
    impact = graph.query_impact(files, depth=depth)

    if format == "json":
        console.print(json_module.dumps(impact.to_dict(), indent=2))
        return

    # Table format
    console.print("\n[bold]Impact Analysis[/bold]")
    console.print(f"Changed files: {', '.join(files)}")
    console.print(f"Depth: {depth}")
    console.print(f"\n{impact.message}\n")

    if impact.specs:
        table = Table(title="Affected Specs")
        table.add_column("ID", style="cyan")
        table.add_column("Confidence", justify="right")

        for spec in impact.specs[:10]:
            table.add_row(spec.id, f"{spec.confidence:.2f}")

        console.print(table)

    if impact.tests:
        table = Table(title="Tests to Run")
        table.add_column("Test", style="green")
        table.add_column("Framework")
        table.add_column("Confidence", justify="right")

        for test in impact.tests[:10]:
            framework = test.data.get("framework", "unknown")
            table.add_row(test.id, framework, f"{test.confidence:.2f}")

        console.print(table)

    if impact.is_empty():
        console.print("[yellow]No tracked impact found for these files.[/yellow]")


@graph_app.command("show")
def graph_show(
    node_id: str = typer.Argument(..., help="Node ID to show"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Show relationships for a specific node.

    Examples:
        specmem graph show spec:auth.login
        specmem graph show code:src/auth.py
    """
    from specmem.impact import SpecImpactGraph

    repo_path = Path(path)
    graph_path = repo_path / ".specmem" / "impact_graph.json"

    if not graph_path.exists():
        console.print("[red]No impact graph found. Run 'specmem graph impact' first.[/red]")
        raise typer.Exit(1)

    graph = SpecImpactGraph(graph_path)
    node = graph.get_node(node_id)

    if not node:
        console.print(f"[red]Node not found:[/red] {node_id}")
        raise typer.Exit(1)

    console.print(f"\n[bold]Node:[/bold] {node.id}")
    console.print(f"Type: {node.type.value}")
    console.print(f"Confidence: {node.confidence:.2f}")
    if node.suggested:
        console.print("[yellow]Suggested (low confidence)[/yellow]")

    if node.data:
        console.print("\n[bold]Data:[/bold]")
        for key, value in node.data.items():
            console.print(f"  {key}: {value}")

    # Show outgoing edges
    outgoing = graph.get_edges_from(node_id)
    if outgoing:
        console.print(f"\n[bold]Outgoing Edges:[/bold] ({len(outgoing)})")
        for edge in outgoing:
            manual = " [manual]" if edge.manual else ""
            console.print(
                f"  → {edge.target_id} ({edge.relationship.value}, {edge.confidence:.2f}){manual}"
            )

    # Show incoming edges
    incoming = graph.get_edges_to(node_id)
    if incoming:
        console.print(f"\n[bold]Incoming Edges:[/bold] ({len(incoming)})")
        for edge in incoming:
            manual = " [manual]" if edge.manual else ""
            console.print(
                f"  ← {edge.source_id} ({edge.relationship.value}, {edge.confidence:.2f}){manual}"
            )


@graph_app.command("export")
def graph_export(
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, dot, mermaid)"),
    output: str = typer.Option(None, "--output", "-o", help="Output file"),
    filter_type: str = typer.Option(
        None, "--filter", help="Filter by node type (spec, code, test)"
    ),
    focal: str = typer.Option(None, "--focal", help="Extract subgraph around this node"),
    depth: int = typer.Option(2, "--depth", "-d", help="Depth for subgraph extraction"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Export the impact graph.

    Examples:
        specmem graph export --format dot -o graph.dot
        specmem graph export --format mermaid --focal spec:auth
        specmem graph export --filter spec
    """
    from specmem.impact import NodeType, SpecImpactGraph

    repo_path = Path(path)
    graph_path = repo_path / ".specmem" / "impact_graph.json"

    if not graph_path.exists():
        console.print("[red]No impact graph found. Run 'specmem graph impact' first.[/red]")
        raise typer.Exit(1)

    graph = SpecImpactGraph(graph_path)

    # Parse filter type
    node_type = None
    if filter_type:
        try:
            node_type = NodeType(filter_type)
        except ValueError:
            console.print(f"[red]Invalid filter type:[/red] {filter_type}")
            console.print("Valid types: spec, code, test")
            raise typer.Exit(1)

    # Export
    result = graph.export(
        format=format,
        filter_type=node_type,
        focal_node=focal,
        max_depth=depth if focal else None,
    )

    if output:
        Path(output).write_text(result)
        console.print(f"[green]✓[/green] Exported to {output}")
    else:
        console.print(result)


@graph_app.command("stats")
def graph_stats(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Display graph statistics.

    Examples:
        specmem graph stats
    """
    from specmem.impact import SpecImpactGraph

    repo_path = Path(path)
    graph_path = repo_path / ".specmem" / "impact_graph.json"

    if not graph_path.exists():
        console.print("[red]No impact graph found. Run 'specmem graph impact' first.[/red]")
        raise typer.Exit(1)

    graph = SpecImpactGraph(graph_path)
    stats = graph.get_stats()

    console.print("\n[bold]SpecImpact Graph Statistics[/bold]\n")

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Nodes", str(stats["total_nodes"]))
    table.add_row("Total Edges", str(stats["total_edges"]))

    console.print(table)

    if stats["nodes_by_type"]:
        console.print("\n[bold]Nodes by Type:[/bold]")
        for node_type, count in sorted(stats["nodes_by_type"].items()):
            console.print(f"  {node_type}: {count}")

    if stats["edges_by_type"]:
        console.print("\n[bold]Edges by Type:[/bold]")
        for edge_type, count in sorted(stats["edges_by_type"].items()):
            console.print(f"  {edge_type}: {count}")


# =============================================================================
# SpecDiff Commands - Temporal Spec Intelligence
# =============================================================================


@app.command("diff")
def spec_diff(
    spec_id: str = typer.Argument(..., help="Spec ID to show diff for"),
    from_version: str = typer.Option(None, "--from", help="Starting version"),
    to_version: str = typer.Option(None, "--to", help="Ending version"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Show recent changes to a specification.

    Examples:
        specmem diff auth.login
        specmem diff auth.login --from v1 --to v2
    """
    from specmem.diff import SpecDiff

    repo_path = Path(path)
    db_path = repo_path / ".specmem" / "specdiff.db"

    if not db_path.exists():
        console.print("[yellow]No SpecDiff history found. Track specs first.[/yellow]")
        raise typer.Exit(1)

    diff = SpecDiff(db_path)

    change = diff.get_diff(spec_id, from_version, to_version)

    if not change:
        console.print(f"[yellow]No changes found for spec:[/yellow] {spec_id}")
        diff.close()
        return

    console.print(f"\n[bold]Spec Diff:[/bold] {spec_id}")
    console.print(f"From: {change.from_version} → To: {change.to_version}")
    console.print(f"Type: {change.change_type.value}")
    console.print(f"Time: {change.timestamp}")

    if change.added:
        console.print("\n[green]Added:[/green]")
        for line in change.added[:10]:
            console.print(f"  + {line}")

    if change.removed:
        console.print("\n[red]Removed:[/red]")
        for line in change.removed[:10]:
            console.print(f"  - {line}")

    if change.inferred_reason:
        console.print(f"\n[bold]Reason:[/bold] {change.inferred_reason.reason}")
        console.print(f"Confidence: {change.inferred_reason.confidence:.2f}")

    diff.close()


@app.command("history")
def spec_history(
    spec_id: str = typer.Argument(..., help="Spec ID to show history for"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum versions to show"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Show version timeline for a specification.

    Examples:
        specmem history auth.login
        specmem history auth.login --limit 5
    """
    from specmem.diff import SpecDiff

    repo_path = Path(path)
    db_path = repo_path / ".specmem" / "specdiff.db"

    if not db_path.exists():
        console.print("[yellow]No SpecDiff history found.[/yellow]")
        raise typer.Exit(1)

    diff = SpecDiff(db_path)
    history = diff.get_history(spec_id, limit)

    if not history:
        console.print(f"[yellow]No history found for spec:[/yellow] {spec_id}")
        diff.close()
        return

    console.print(f"\n[bold]Version History:[/bold] {spec_id}\n")

    table = Table()
    table.add_column("Version", style="cyan")
    table.add_column("Timestamp")
    table.add_column("Commit")
    table.add_column("Hash")

    for version in history:
        table.add_row(
            version.version_id,
            version.timestamp.strftime("%Y-%m-%d %H:%M"),
            version.commit_ref or "-",
            version.content_hash[:8],
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(history)} versions")

    diff.close()


@app.command("drift")
def spec_drift(
    severity: float = typer.Option(0.0, "--severity", "-s", help="Minimum severity"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Show code that has drifted from specifications.

    Examples:
        specmem drift
        specmem drift --severity 0.5
    """
    from specmem.diff import SpecDiff
    from specmem.impact import SpecImpactGraph

    repo_path = Path(path)
    db_path = repo_path / ".specmem" / "specdiff.db"
    graph_path = repo_path / ".specmem" / "impact_graph.json"

    if not db_path.exists():
        console.print("[yellow]No SpecDiff history found.[/yellow]")
        raise typer.Exit(1)

    # Load impact graph if available
    impact_graph = None
    if graph_path.exists():
        impact_graph = SpecImpactGraph(graph_path)

    diff = SpecDiff(db_path, impact_graph)
    report = diff.get_drift_report()

    drifted = report.get_by_severity(severity)

    if not drifted:
        console.print("[green]No code drift detected.[/green]")
        diff.close()
        return

    console.print("\n[bold]Drift Report[/bold]\n")
    console.print(f"Total drift score: {report.total_drift_score:.2f}")
    console.print(f"Generated: {report.generated_at}\n")

    table = Table()
    table.add_column("Code Path", style="cyan")
    table.add_column("Spec")
    table.add_column("Severity", justify="right")
    table.add_column("Action")

    for item in drifted[:20]:
        sev_color = "red" if item.severity >= 0.8 else "yellow" if item.severity >= 0.5 else "green"
        table.add_row(
            item.code_path,
            item.spec_id,
            f"[{sev_color}]{item.severity:.2f}[/{sev_color}]",
            item.suggested_action[:40] + "..."
            if len(item.suggested_action) > 40
            else item.suggested_action,
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(drifted)} drifted files")

    diff.close()


@app.command("stale")
def spec_stale(
    acknowledge: str = typer.Option(
        None, "--acknowledge", "-a", help="Acknowledge staleness for spec:version"
    ),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Show stale specification memories.

    Examples:
        specmem stale
        specmem stale --acknowledge auth.login:v1
    """
    from specmem.diff import SpecDiff

    repo_path = Path(path)
    db_path = repo_path / ".specmem" / "specdiff.db"

    if not db_path.exists():
        console.print("[yellow]No SpecDiff history found.[/yellow]")
        raise typer.Exit(1)

    diff = SpecDiff(db_path)

    if acknowledge:
        parts = acknowledge.split(":")
        if len(parts) == 2:
            diff.acknowledge_staleness(parts[0], parts[1])
            console.print(f"[green]✓[/green] Acknowledged staleness for {acknowledge}")
        else:
            console.print("[red]Invalid format. Use spec_id:version[/red]")
        diff.close()
        return

    # Show stale warnings (would need cached versions from somewhere)
    console.print("[yellow]Staleness check requires cached version information.[/yellow]")
    console.print("Use the SpecMemClient API to check staleness programmatically.")

    diff.close()


@app.command("deprecations")
def spec_deprecations(
    include_expired: bool = typer.Option(False, "--expired", help="Include expired deprecations"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """List deprecated specifications.

    Examples:
        specmem deprecations
        specmem deprecations --expired
    """
    from specmem.diff import SpecDiff

    repo_path = Path(path)
    db_path = repo_path / ".specmem" / "specdiff.db"

    if not db_path.exists():
        console.print("[yellow]No SpecDiff history found.[/yellow]")
        raise typer.Exit(1)

    diff = SpecDiff(db_path)
    deprecations = diff.get_deprecations(include_expired)

    if not deprecations:
        console.print("[green]No deprecated specifications.[/green]")
        diff.close()
        return

    console.print("\n[bold]Deprecated Specifications[/bold]\n")

    table = Table()
    table.add_column("Spec ID", style="cyan")
    table.add_column("Deprecated")
    table.add_column("Deadline")
    table.add_column("Replacement")
    table.add_column("Urgency", justify="right")

    for dep in deprecations:
        days = dep.days_remaining()
        deadline_str = f"{days} days" if days is not None else "-"
        urg_color = "red" if dep.urgency >= 0.8 else "yellow" if dep.urgency >= 0.5 else "green"

        table.add_row(
            dep.spec_id,
            dep.deprecated_at.strftime("%Y-%m-%d"),
            deadline_str,
            dep.replacement_spec_id or "-",
            f"[{urg_color}]{dep.urgency:.2f}[/{urg_color}]",
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(deprecations)} deprecated specs")

    diff.close()


# =============================================================================
# Validate Command - Specification Quality Assurance
# =============================================================================


@app.command()
def validate(
    spec_id: str = typer.Option(None, "--spec", "-s", help="Validate specific spec ID"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json)"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix simple issues"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Validate specifications for quality issues.

    Checks for:
    - Contradictory requirements
    - Missing acceptance criteria
    - Invalid constraints (negative counts, >100%, min>max)
    - Duplicate specifications
    - Timeline issues (past deadlines)
    - Structure problems

    Examples:
        specmem validate
        specmem validate --spec auth.login
        specmem validate --format json
        specmem validate --fix
    """
    import json as json_module

    from specmem.validator import (
        AcceptanceCriteriaRule,
        ConstraintRule,
        ContradictionRule,
        DuplicateRule,
        StructureRule,
        TimelineRule,
        ValidationConfig,
        ValidationEngine,
    )

    repo_path = Path(path)

    console.print(f"Validating specifications in [bold]{repo_path}[/bold]...\n")

    # Load specs
    detected = detect_adapters(str(repo_path))

    if not detected:
        console.print("[yellow]No specification frameworks detected.[/yellow]")
        raise typer.Exit(1)

    all_blocks = []
    for adapter in detected:
        blocks = adapter.load(str(repo_path))
        all_blocks.extend(blocks)

    if not all_blocks:
        console.print("[yellow]No specification blocks found.[/yellow]")
        raise typer.Exit(1)

    # Filter by spec_id if provided
    if spec_id:
        all_blocks = [b for b in all_blocks if spec_id in b.id]
        if not all_blocks:
            console.print(f"[red]No specs found matching:[/red] {spec_id}")
            raise typer.Exit(1)

    console.print(f"Validating {len(all_blocks)} specifications...")

    # Load config
    try:
        config = SpecMemConfig.load()
        validation_config = ValidationConfig.from_toml(config.to_dict())
    except Exception:
        validation_config = ValidationConfig()

    # Create engine and register rules
    engine = ValidationEngine(validation_config)
    engine.register_rules(
        [
            ContradictionRule(),
            AcceptanceCriteriaRule(),
            ConstraintRule(),
            DuplicateRule(),
            TimelineRule(),
            StructureRule(),
        ]
    )

    # Run validation
    result = engine.validate(all_blocks)

    # Output results
    if format == "json":
        console.print(json_module.dumps(result.to_dict(), indent=2))
    else:
        # Table format
        if result.is_valid:
            console.print("\n[green]✓ Validation passed[/green]")
        else:
            console.print("\n[red]✗ Validation failed[/red]")

        console.print(f"\nSpecs validated: {result.specs_validated}")
        console.print(f"Rules run: {result.rules_run}")
        console.print(f"Duration: {result.duration_ms:.2f}ms")

        if result.issues:
            console.print(f"\n[bold]Issues Found:[/bold] {len(result.issues)}")
            console.print(f"  Errors: {result.error_count}")
            console.print(f"  Warnings: {result.warning_count}")
            console.print(f"  Info: {result.info_count}")

            # Show issues table
            table = Table()
            table.add_column("Severity", style="bold")
            table.add_column("Rule")
            table.add_column("Spec ID", style="cyan")
            table.add_column("Message")

            for issue in result.issues[:20]:
                sev_color = (
                    "red"
                    if issue.severity.value == "error"
                    else "yellow"
                    if issue.severity.value == "warning"
                    else "blue"
                )
                table.add_row(
                    f"[{sev_color}]{issue.severity.value}[/{sev_color}]",
                    issue.rule_id,
                    issue.spec_id[:30] + "..." if len(issue.spec_id) > 30 else issue.spec_id,
                    issue.message[:60] + "..." if len(issue.message) > 60 else issue.message,
                )

            console.print(table)

            if len(result.issues) > 20:
                console.print(f"\n[dim]... and {len(result.issues) - 20} more issues[/dim]")

            # Show suggestions for first few issues
            issues_with_suggestions = [i for i in result.issues if i.suggestion][:3]
            if issues_with_suggestions:
                console.print("\n[bold]Suggestions:[/bold]")
                for issue in issues_with_suggestions:
                    console.print(f"  • {issue.spec_id}: {issue.suggestion}")
        else:
            console.print("\n[green]No issues found![/green]")

    # Exit with error code if validation failed
    if not result.is_valid:
        raise typer.Exit(1)


@app.command()
def serve(
    path: str = typer.Argument(".", help="Repository path"),
    port: int = typer.Option(8765, "--port", "-p", help="Port to listen on"),
) -> None:
    """Launch the SpecMem Web UI.

    Starts a local web server providing a dashboard to browse, filter,
    search, and export your project's specification memory.
    """
    from specmem.agentx import PackBuilder
    from specmem.ui import WebServer

    repo_path = Path(path)

    console.print(f"Loading specifications from [bold]{repo_path}[/bold]...\n")

    # Detect and load specs
    detected = detect_adapters(str(repo_path))

    if not detected:
        console.print("[yellow]No specification frameworks detected.[/yellow]")
        console.print("Run [bold]specmem scan[/bold] to check for supported frameworks.")
        raise typer.Exit(1)

    all_blocks = []
    for adapter in detected:
        blocks = adapter.load(str(repo_path))
        all_blocks.extend(blocks)
        console.print(f"[green]✓[/green] Loaded {len(blocks)} blocks from {adapter.name}")

    if not all_blocks:
        console.print("[yellow]No specification blocks found.[/yellow]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Total:[/bold] {len(all_blocks)} specification blocks")

    # Initialize vector store if available
    vector_store = None
    try:
        config = SpecMemConfig.load()
        vector_store = LanceDBStore(db_path=config.vectordb.path)
        vector_store.initialize()
    except Exception:
        console.print("[dim]Vector search not available (run 'specmem build' first)[/dim]")

    # Create pack builder for export
    pack_builder = PackBuilder(output_dir=str(repo_path / ".specmem"))

    # Start web server
    server = WebServer(
        blocks=all_blocks,
        port=port,
        vector_store=vector_store,
        pack_builder=pack_builder,
        workspace_path=repo_path,
    )

    server.start()


# Export for entry point
cli = app

if __name__ == "__main__":
    app()
