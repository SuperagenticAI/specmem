"""Session directory discovery.

Handles platform-specific auto-discovery of Kiro session directories.
"""

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Platform(str, Enum):
    """Supported platforms for session discovery."""

    MACOS = "darwin"
    LINUX = "linux"
    WINDOWS = "win32"


@dataclass
class DiscoveryResult:
    """Result of auto-discovery attempt.

    Attributes:
        found_paths: List of valid session directories found
        platform: The platform discovery was run on
        checked_paths: All paths that were checked
        error: Error message if discovery failed
    """

    found_paths: list[Path] = field(default_factory=list)
    platform: Platform | None = None
    checked_paths: list[Path] = field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        """Return True if at least one valid path was found."""
        return len(self.found_paths) > 0


class SessionDiscovery:
    """Discovers Kiro session directories on the local system.

    Supports macOS, Linux, and Windows with platform-specific default paths.
    """

    # Platform-specific default paths for Kiro sessions
    PLATFORM_PATHS: dict[Platform, list[str]] = {
        Platform.MACOS: [
            "~/Library/Application Support/Kiro/workspace-sessions",
        ],
        Platform.LINUX: [
            "~/.config/Kiro/workspace-sessions",
            "~/.local/share/Kiro/workspace-sessions",
        ],
        Platform.WINDOWS: [
            "%APPDATA%/Kiro/workspace-sessions",
        ],
    }

    def __init__(self) -> None:
        """Initialize the session discovery."""
        self._platform: Platform | None = None

    @property
    def platform(self) -> Platform:
        """Get the current platform.

        Returns:
            The detected platform.

        Raises:
            ValueError: If platform is not supported.
        """
        if self._platform is not None:
            return self._platform

        platform_str = sys.platform

        if platform_str == "darwin":
            self._platform = Platform.MACOS
        elif platform_str.startswith("linux"):
            self._platform = Platform.LINUX
        elif platform_str == "win32":
            self._platform = Platform.WINDOWS
        else:
            raise ValueError(f"Unsupported platform: {platform_str}")

        return self._platform

    def get_platform_paths(self, platform: Platform | None = None) -> list[Path]:
        """Get default paths for a specific platform.

        Args:
            platform: Platform to get paths for. Defaults to current platform.

        Returns:
            List of expanded paths for the platform.
        """
        target_platform = platform or self.platform
        path_templates = self.PLATFORM_PATHS.get(target_platform, [])

        paths = []
        for template in path_templates:
            # Expand environment variables and user home
            expanded = os.path.expandvars(template)
            paths.append(Path(expanded).expanduser())

        return paths

    def validate_directory(self, path: Path) -> bool:
        """Check if directory contains valid session data.

        A valid session directory must:
        1. Exist and be a directory
        2. Contain at least one subdirectory (workspace directories)
        3. Have at least one JSON file in any subdirectory

        Args:
            path: Path to validate.

        Returns:
            True if directory contains valid session data.
        """
        if not path.exists() or not path.is_dir():
            return False

        # Check for subdirectories (workspace directories are base64-encoded)
        subdirs = [d for d in path.iterdir() if d.is_dir()]
        if not subdirs:
            return False

        # Check for JSON files in any subdirectory
        for subdir in subdirs:
            json_files = list(subdir.glob("*.json"))
            if json_files:
                return True

        return False

    def discover(self, platform: Platform | None = None) -> DiscoveryResult:
        """Auto-discover Kiro session directories.

        Searches platform-specific default locations for valid session directories.

        Args:
            platform: Platform to discover for. Defaults to current platform.

        Returns:
            DiscoveryResult with found paths and metadata.
        """
        target_platform = platform or self.platform
        paths_to_check = self.get_platform_paths(target_platform)

        result = DiscoveryResult(
            platform=target_platform,
            checked_paths=paths_to_check,
        )

        for path in paths_to_check:
            if self.validate_directory(path):
                result.found_paths.append(path)

        if not result.found_paths:
            result.error = (
                f"No valid Kiro sessions directory found on {target_platform.value}. "
                f"Checked: {', '.join(str(p) for p in paths_to_check)}"
            )

        return result

    def find_sessions_path(self) -> Path | None:
        """Find the first valid sessions directory.

        Convenience method that returns the first found path from discover().

        Returns:
            Path to sessions directory, or None if not found.
        """
        result = self.discover()
        if result.found_paths:
            return result.found_paths[0]
        return None

    def get_help_text(self) -> str:
        """Get help text showing default paths for all platforms.

        Returns:
            Formatted help text with platform-specific paths.
        """
        lines = [
            "Kiro sessions are typically stored in:",
            "",
            "macOS:",
        ]
        for path in self.PLATFORM_PATHS[Platform.MACOS]:
            lines.append(f"  {path}")

        lines.extend(["", "Linux:"])
        for path in self.PLATFORM_PATHS[Platform.LINUX]:
            lines.append(f"  {path}")

        lines.extend(["", "Windows:"])
        for path in self.PLATFORM_PATHS[Platform.WINDOWS]:
            lines.append(f"  {path}")

        lines.extend(
            [
                "",
                "You can also find the path in Kiro settings or by checking",
                "where your IDE stores its data.",
            ]
        )

        return "\n".join(lines)
