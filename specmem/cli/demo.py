"""Demo command for SpecMem - one-command showcase."""

import shutil
import webbrowser
from pathlib import Path
from time import sleep

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn


console = Console()
app = typer.Typer()


class DemoHandler:
    """Handles demo environment setup and launch."""

    def __init__(self, workspace_path: Path):
        """Initialize demo handler.

        Args:
            workspace_path: Path to the workspace root
        """
        self.workspace_path = workspace_path
        self.specs_path = workspace_path / ".kiro" / "specs"

    def has_specs(self) -> bool:
        """Check if workspace has existing specs."""
        return self.specs_path.exists() and any(self.specs_path.iterdir())

    def setup_demo_specs(self, use_dogfood: bool = True) -> int:
        """Set up demo specifications.

        Args:
            use_dogfood: If True, copy SpecMem's own specs

        Returns:
            Number of specs created
        """
        if use_dogfood:
            return self._copy_specmem_specs()
        else:
            return self._create_sample_specs()

    def _copy_specmem_specs(self) -> int:
        """Copy SpecMem's own specs for dogfooding demo."""
        # Find SpecMem's own specs directory
        specmem_root = Path(__file__).parent.parent.parent
        specmem_specs = specmem_root / ".kiro" / "specs"

        if not specmem_specs.exists():
            console.print("[yellow]SpecMem specs not found, creating samples[/yellow]")
            return self._create_sample_specs()

        # Create target directory
        self.specs_path.mkdir(parents=True, exist_ok=True)

        # Copy specs
        count = 0
        for feature_dir in specmem_specs.iterdir():
            if feature_dir.is_dir():
                target_dir = self.specs_path / feature_dir.name
                if not target_dir.exists():
                    shutil.copytree(feature_dir, target_dir)
                    count += 1

        return count

    def _create_sample_specs(self) -> int:
        """Create sample specifications for demo."""
        self.specs_path.mkdir(parents=True, exist_ok=True)

        # Create a sample feature spec
        sample_feature = self.specs_path / "sample-feature"
        sample_feature.mkdir(exist_ok=True)

        # Requirements
        (sample_feature / "requirements.md").write_text("""# Requirements Document

## Introduction

This is a sample feature specification for demonstrating SpecMem capabilities.

## Glossary

- **Sample Feature**: A demonstration feature for SpecMem
- **User**: A person interacting with the system

## Requirements

### Requirement 1: User Authentication

**User Story:** As a user, I want to log in securely, so that my data is protected.

#### Acceptance Criteria

1. WHEN a user provides valid credentials THEN the System SHALL authenticate the user
2. WHEN a user provides invalid credentials THEN the System SHALL reject the login attempt
3. WHEN a user is authenticated THEN the System SHALL create a session token
""")

        # Design
        (sample_feature / "design.md").write_text("""# Design Document

## Overview

This document describes the technical design for the sample feature.

## Architecture

The feature uses a layered architecture with:
- Presentation layer (UI)
- Business logic layer (Services)
- Data access layer (Repositories)

## Components

### AuthService

Handles user authentication logic.

### SessionManager

Manages user sessions and tokens.
""")

        # Tasks
        (sample_feature / "tasks.md").write_text("""# Implementation Plan

- [ ] 1. Set up authentication service
  - [ ] 1.1 Create AuthService class
  - [ ] 1.2 Implement credential validation
  - _Requirements: 1.1, 1.2_

- [ ] 2. Implement session management
  - [ ] 2.1 Create SessionManager class
  - [ ] 2.2 Implement token generation
  - _Requirements: 1.3_
""")

        return 1

    def build_memory(self) -> bool:
        """Build the SpecMem memory index.

        Returns:
            True if successful
        """
        try:
            from specmem.adapters.kiro import KiroAdapter
            from specmem.core.memory_bank import MemoryBank
            from specmem.vectordb.embeddings import get_embedding_provider
            from specmem.vectordb.lancedb_store import LanceDBStore

            # Load specs
            adapter = KiroAdapter()
            if not adapter.detect(self.workspace_path):
                return False

            blocks = adapter.load(self.workspace_path)

            # Create vector store
            db_path = self.workspace_path / ".specmem" / "vectordb"
            db_path.mkdir(parents=True, exist_ok=True)

            embedding_provider = get_embedding_provider()
            vector_store = LanceDBStore(db_path=str(db_path))

            # Build memory
            memory_bank = MemoryBank(vector_store, embedding_provider)
            memory_bank.add_blocks(blocks)

            return True

        except Exception as e:
            console.print(f"[red]Build failed: {e}[/red]")
            return False

    def launch_ui(self, port: int = 8765, open_browser: bool = True) -> None:
        """Launch the Web UI.

        Args:
            port: Port to run the server on
            open_browser: Whether to open browser automatically
        """
        from specmem.adapters.kiro import KiroAdapter
        from specmem.ui.server import WebServer

        # Load specs
        adapter = KiroAdapter()
        blocks = []
        if adapter.detect(self.workspace_path):
            blocks = adapter.load(self.workspace_path)

        # Create and start server
        server = WebServer(
            blocks=blocks,
            port=port,
            workspace_path=self.workspace_path,
            enable_file_watcher=True,
        )

        # Pre-warm cache by calling API endpoints (populates server-side cache)
        def prewarm_cache():
            """Pre-compute expensive data by calling API endpoints."""
            import urllib.request
            import urllib.error

            sleep(3)  # Wait for server to fully start
            base_url = f"http://127.0.0.1:{port}/api"

            endpoints = [
                ("health", "Health score"),
                ("coverage", "Coverage"),
                ("graph", "Impact graph"),
            ]

            for endpoint, name in endpoints:
                try:
                    url = f"{base_url}/{endpoint}"
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        if resp.status == 200:
                            console.print(f"[dim]✓ {name} cached[/dim]")
                except urllib.error.URLError:
                    pass  # Server not ready yet or endpoint failed
                except Exception:
                    pass

        import threading
        threading.Thread(target=prewarm_cache, daemon=True).start()

        if open_browser:
            # Open browser after a short delay
            def open_browser_delayed():
                sleep(1.5)
                webbrowser.open(f"http://127.0.0.1:{port}")

            threading.Thread(target=open_browser_delayed, daemon=True).start()

        server.start()




@app.command()
def demo(
    port: int = typer.Option(8765, "--port", "-p", help="Port for Web UI"),
    open_browser: bool = typer.Option(False, "--open", "-o", help="Open browser automatically"),
    sample: bool = typer.Option(False, "--sample", help="Use sample specs instead of dogfooding"),
):
    """Launch SpecMem demo with one command.

    This command:
    1. Creates sample specs if none exist (using SpecMem's own specs)
    2. Builds the memory index
    3. Launches the Web UI

    Copy the URL and paste in your browser to view the dashboard.
    Use --open to auto-launch browser.
    """
    console.print(
        Panel.fit(
            "[bold cyan]🚀 SpecMem Demo[/bold cyan]\n[dim]One command to showcase everything[/dim]",
            border_style="cyan",
        )
    )

    handler = DemoHandler(Path.cwd())

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Check/create specs
        if not handler.has_specs():
            task = progress.add_task("Creating demo specifications...", total=None)
            count = handler.setup_demo_specs(use_dogfood=not sample)
            progress.remove_task(task)
            console.print(f"[green]✓[/green] Created {count} feature spec(s)")
        else:
            console.print("[green]✓[/green] Using existing specifications")

        # Step 2: Build memory
        task = progress.add_task("Building memory index...", total=None)
        success = handler.build_memory()
        progress.remove_task(task)
        if success:
            console.print("[green]✓[/green] Memory index built")
        else:
            console.print("[yellow]![/yellow] Memory build skipped (will use basic mode)")

        # Step 3: Launch UI
        console.print("[green]✓[/green] Launching Web UI...")
        console.print()

    # Show dogfooding message if applicable
    if handler.has_specs():
        specmem_root = Path(__file__).parent.parent.parent
        if (specmem_root / ".kiro" / "specs").exists():
            console.print(
                Panel.fit(
                    "[bold green]🐕 Eating Our Own Dogfood![/bold green]\n"
                    "[dim]SpecMem is managing its own specifications[/dim]",
                    border_style="green",
                )
            )

    handler.launch_ui(port=port, open_browser=open_browser)


if __name__ == "__main__":
    app()
