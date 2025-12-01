"""File watcher for live updates in SpecMem UI."""

import asyncio
from collections.abc import Callable
from pathlib import Path

from watchfiles import awatch


class SpecFileWatcher:
    """Watch spec files for changes and trigger callbacks."""

    # File patterns to watch
    SPEC_PATTERNS = {
        "*.md",
        "requirements.md",
        "design.md",
        "tasks.md",
    }

    # Directories to watch
    SPEC_DIRS = {
        ".kiro",
        ".tessl",
        "specs",
    }

    def __init__(
        self,
        workspace_path: Path,
        on_change: Callable[[], None] | None = None,
    ):
        """Initialize the file watcher.

        Args:
            workspace_path: Root path of the workspace to watch
            on_change: Callback to invoke when spec files change
        """
        self.workspace_path = workspace_path
        self.on_change = on_change
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    def _should_watch_path(self, path: Path) -> bool:
        """Check if a path should trigger updates."""
        # Check if it's in a spec directory
        path_str = str(path)
        for spec_dir in self.SPEC_DIRS:
            if spec_dir in path_str:
                return True

        # Check if it's a markdown file
        return path.suffix == ".md"

    async def start(self):
        """Start watching for file changes."""
        self._stop_event.clear()

        async for changes in awatch(
            self.workspace_path,
            stop_event=self._stop_event,
            recursive=True,
        ):
            # Filter to only spec-related changes
            relevant_changes = [
                (change_type, path)
                for change_type, path in changes
                if self._should_watch_path(Path(path))
            ]

            if relevant_changes and self.on_change:
                self.on_change()

    def stop(self):
        """Stop watching for file changes."""
        self._stop_event.set()
        if self._task:
            self._task.cancel()

    async def run_in_background(self):
        """Run the watcher as a background task."""
        self._task = asyncio.create_task(self.start())
        return self._task
