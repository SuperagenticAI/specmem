"""SpecMem - Unified Agent Memory Engine for Spec-Driven Development.

SpecMem creates a unified, normalized, agent-agnostic context layer for your
project's specs. Coding agents can be swapped at any time without losing
context or rewriting spec files.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version


try:
    # Always report the installed distribution's version so it never drifts
    # from pyproject.toml.
    __version__ = _package_version("specmem")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0"

# Export SpecMemClient for agent integration
from specmem.client import (
    ConfigurationError,
    ContextBundle,
    MemoryStoreError,
    Proposal,
    ProposalError,
    ProposalStatus,
    SpecMemClient,
    SpecMemError,
    SpecSummary,
    TestMapping,
)


__all__ = [
    "ConfigurationError",
    "ContextBundle",
    "MemoryStoreError",
    "Proposal",
    "ProposalError",
    "ProposalStatus",
    "SpecMemClient",
    "SpecMemError",
    "SpecSummary",
    "TestMapping",
    "__version__",
]
