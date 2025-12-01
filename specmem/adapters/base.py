"""Base interface for spec framework adapters.

All adapters must implement the SpecAdapter interface to be discovered
and used by SpecMem.
"""

import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock


class ExperimentalAdapterWarning(UserWarning):
    """Warning for experimental adapter usage.

    This warning is issued when an experimental adapter is used,
    indicating that the adapter may have limited functionality
    or breaking changes in future versions.
    """

    pass


class SpecAdapter(ABC):
    """Base interface for all spec framework adapters.

    Each SDD framework (Kiro, SpecKit, Tessl, etc.) has a dedicated adapter
    that conforms to this interface. Adapters are responsible for:
    1. Detecting if their framework is present in a repository
    2. Loading and parsing spec files into normalized SpecBlocks

    Example:
        class KiroAdapter(SpecAdapter):
            @property
            def name(self) -> str:
                return "Kiro"

            def detect(self, repo_path: str) -> bool:
                kiro_dir = Path(repo_path) / ".kiro"
                return kiro_dir.exists()

            def load(self, repo_path: str) -> list[SpecBlock]:
                # Parse .kiro/requirements.md, design.md, tasks.md
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name.

        Returns:
            Name of the spec framework this adapter handles
        """
        pass

    @abstractmethod
    def detect(self, repo_path: str) -> bool:
        """Check if this adapter's framework is present in the repository.

        This method should be fast and only check for the presence of
        framework-specific files or directories.

        Args:
            repo_path: Path to the repository root

        Returns:
            True if the framework is detected, False otherwise
        """
        pass

    @abstractmethod
    def load(self, repo_path: str) -> list["SpecBlock"]:
        """Load and parse specs, returning normalized SpecBlocks.

        This method should:
        1. Find all spec files for this framework
        2. Parse the content
        3. Convert to SpecBlock format
        4. Handle malformed content gracefully (log warning, skip invalid)

        Args:
            repo_path: Path to the repository root

        Returns:
            List of SpecBlock instances extracted from the specs

        Raises:
            AdapterError: If a critical error occurs during loading
        """
        pass

    def is_experimental(self) -> bool:
        """Check if this adapter is experimental.

        Experimental adapters may have limited functionality or
        breaking changes in future versions. Override this method
        to return True for experimental adapters.

        Returns:
            True if adapter is experimental, False otherwise
        """
        return False

    def warn_if_experimental(self) -> None:
        """Issue warning if adapter is experimental.

        Call this method at the start of load() to warn users
        about experimental adapter usage.
        """
        if self.is_experimental():
            warnings.warn(
                f"Adapter '{self.name}' is experimental and may have "
                f"limited functionality or breaking changes in future versions.",
                ExperimentalAdapterWarning,
                stacklevel=3,
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
