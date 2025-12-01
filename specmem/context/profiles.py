"""Agent profile management for context preferences.

Handles per-agent configuration of context window sizes and preferences.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


logger = logging.getLogger(__name__)

FormatType = Literal["json", "markdown", "text"]

# Default profiles for common agents
DEFAULT_PROFILES = {
    "default": {
        "context_window": 8000,
        "token_budget": 4000,
        "preferred_format": "json",
        "type_filters": [],
    },
    "gpt-4": {
        "context_window": 128000,
        "token_budget": 8000,
        "preferred_format": "json",
        "type_filters": [],
    },
    "gpt-3.5": {
        "context_window": 16000,
        "token_budget": 4000,
        "preferred_format": "json",
        "type_filters": [],
    },
    "claude": {
        "context_window": 200000,
        "token_budget": 10000,
        "preferred_format": "markdown",
        "type_filters": [],
    },
    "kiro": {
        "context_window": 200000,
        "token_budget": 8000,
        "preferred_format": "json",
        "type_filters": [],
    },
}


@dataclass
class AgentProfile:
    """Profile defining agent context preferences."""

    name: str
    context_window: int = 8000  # Total context window
    token_budget: int = 4000  # Budget for spec memory
    preferred_format: str = "json"
    type_filters: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentProfile":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "default"),
            context_window=data.get("context_window", 8000),
            token_budget=data.get("token_budget", 4000),
            preferred_format=data.get("preferred_format", "json"),
            type_filters=data.get("type_filters", []),
        )

    @classmethod
    def get_default(cls, name: str = "default") -> "AgentProfile":
        """Get a default profile by name.

        Args:
            name: Profile name (default, gpt-4, gpt-3.5, claude, kiro)

        Returns:
            AgentProfile with default settings for that agent
        """
        defaults = DEFAULT_PROFILES.get(name, DEFAULT_PROFILES["default"])
        return cls(name=name, **defaults)


class ProfileManager:
    """Manages agent profile persistence and lookup."""

    PROFILES_FILE = "profiles.json"

    def __init__(self, storage_path: Path | str = ".specmem") -> None:
        """Initialize the profile manager.

        Args:
            storage_path: Directory for storing profiles
        """
        self.storage_path = Path(storage_path)
        self._profiles: dict[str, AgentProfile] = {}
        self._loaded = False

    @property
    def profiles_file(self) -> Path:
        """Path to profiles JSON file."""
        return self.storage_path / self.PROFILES_FILE

    def load(self) -> None:
        """Load profiles from storage."""
        if self._loaded:
            return

        # Load default profiles first
        for name, defaults in DEFAULT_PROFILES.items():
            self._profiles[name] = AgentProfile(name=name, **defaults)

        # Load custom profiles from file
        if self.profiles_file.exists():
            try:
                data = json.loads(self.profiles_file.read_text())
                for name, profile_data in data.items():
                    profile_data["name"] = name
                    self._profiles[name] = AgentProfile.from_dict(profile_data)
                logger.debug(f"Loaded {len(data)} custom profiles")
            except Exception as e:
                logger.warning(f"Failed to load profiles: {e}")

        self._loaded = True

    def save(self) -> None:
        """Save custom profiles to storage."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Only save non-default profiles
        custom_profiles = {
            name: {k: v for k, v in profile.to_dict().items() if k != "name"}
            for name, profile in self._profiles.items()
            if name not in DEFAULT_PROFILES
        }

        self.profiles_file.write_text(json.dumps(custom_profiles, indent=2))
        logger.debug(f"Saved {len(custom_profiles)} custom profiles")

    def get(self, name: str) -> AgentProfile:
        """Get a profile by name.

        Falls back to default profile if not found.

        Args:
            name: Profile name

        Returns:
            AgentProfile (default if not found)
        """
        self.load()

        if name in self._profiles:
            return self._profiles[name]

        logger.warning(f"Unknown profile '{name}', using default")
        return self._profiles.get("default", AgentProfile.get_default())

    def set(self, profile: AgentProfile) -> None:
        """Save or update a profile.

        Args:
            profile: Profile to save
        """
        self.load()
        self._profiles[profile.name] = profile
        self.save()

    def delete(self, name: str) -> bool:
        """Delete a custom profile.

        Cannot delete default profiles.

        Args:
            name: Profile name

        Returns:
            True if deleted, False if not found or is default
        """
        if name in DEFAULT_PROFILES:
            logger.warning(f"Cannot delete default profile '{name}'")
            return False

        self.load()
        if name in self._profiles:
            del self._profiles[name]
            self.save()
            return True
        return False

    def list_all(self) -> list[AgentProfile]:
        """List all profiles.

        Returns:
            List of all profiles (default + custom)
        """
        self.load()
        return list(self._profiles.values())

    def list_names(self) -> list[str]:
        """List all profile names.

        Returns:
            List of profile names
        """
        self.load()
        return list(self._profiles.keys())
