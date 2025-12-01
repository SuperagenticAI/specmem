"""Adapter discovery and registration for SpecMem.

This module handles automatic discovery of adapters and provides
a registry for accessing them.
"""

import importlib
import logging
import pkgutil
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from specmem.adapters.base import SpecAdapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for spec framework adapters.

    Handles automatic discovery and registration of adapters from
    the specmem.adapters package.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, SpecAdapter] = {}
        self._discovered = False

    def discover(self) -> None:
        """Auto-discover and register all adapters in specmem/adapters/.

        This method imports all modules in the adapters package and
        registers any SpecAdapter subclasses found.
        """
        if self._discovered:
            return

        import specmem.adapters as adapters_pkg
        from specmem.adapters.base import SpecAdapter

        # Iterate through all modules in the adapters package
        for module_info in pkgutil.iter_modules(adapters_pkg.__path__):
            if module_info.name in ("base", "registry"):
                continue

            try:
                module = importlib.import_module(f"specmem.adapters.{module_info.name}")

                # Find all SpecAdapter subclasses in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, SpecAdapter)
                        and attr is not SpecAdapter
                    ):
                        adapter = attr()
                        self.register(adapter)
                        logger.debug(f"Discovered adapter: {adapter.name}")

            except Exception as e:
                logger.warning(f"Failed to load adapter module {module_info.name}: {e}")

        self._discovered = True

    def register(self, adapter: "SpecAdapter") -> None:
        """Register an adapter.

        Args:
            adapter: SpecAdapter instance to register
        """
        self._adapters[adapter.name.lower()] = adapter

    def get(self, name: str) -> "SpecAdapter | None":
        """Get an adapter by name.

        Args:
            name: Adapter name (case-insensitive)

        Returns:
            SpecAdapter instance or None if not found
        """
        return self._adapters.get(name.lower())

    def all(self) -> list["SpecAdapter"]:
        """Get all registered adapters.

        Returns:
            List of all registered SpecAdapter instances
        """
        return list(self._adapters.values())

    def names(self) -> list[str]:
        """Get names of all registered adapters.

        Returns:
            List of adapter names
        """
        return list(self._adapters.keys())

    def detect_all(self, repo_path: str) -> list["SpecAdapter"]:
        """Detect which adapters are applicable for a repository.

        Args:
            repo_path: Path to the repository root

        Returns:
            List of adapters that detected their framework in the repo
        """
        detected = []
        for adapter in self._adapters.values():
            try:
                if adapter.detect(repo_path):
                    detected.append(adapter)
                    logger.debug(f"Detected {adapter.name} in {repo_path}")
            except Exception as e:
                logger.warning(f"Error during detection for {adapter.name}: {e}")
        return detected


# Global registry instance
_registry: AdapterRegistry | None = None


def get_registry() -> AdapterRegistry:
    """Get the global adapter registry.

    Initializes and discovers adapters on first call.

    Returns:
        The global AdapterRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
        _registry.discover()
    return _registry


def get_adapter(name: str) -> "SpecAdapter | None":
    """Get an adapter by name from the global registry.

    Args:
        name: Adapter name (case-insensitive)

    Returns:
        SpecAdapter instance or None if not found
    """
    return get_registry().get(name)


def get_all_adapters() -> list["SpecAdapter"]:
    """Get all registered adapters from the global registry.

    Returns:
        List of all registered SpecAdapter instances
    """
    return get_registry().all()


def detect_adapters(repo_path: str) -> list["SpecAdapter"]:
    """Detect which adapters are applicable for a repository.

    Args:
        repo_path: Path to the repository root

    Returns:
        List of adapters that detected their framework in the repo
    """
    return get_registry().detect_all(repo_path)


def get_experimental_adapters() -> list["SpecAdapter"]:
    """Get all experimental adapters from the global registry.

    Returns:
        List of adapters that are marked as experimental
    """
    return [adapter for adapter in get_registry().all() if adapter.is_experimental()]
