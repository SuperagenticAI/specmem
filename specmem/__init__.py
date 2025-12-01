"""SpecMem - Unified Agent Memory Engine for Spec-Driven Development.

SpecMem creates a unified, normalized, agent-agnostic context layer for your
project's specs. Coding agents can be swapped at any time without losing
context or rewriting spec files.
"""

__version__ = "0.1.0"

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
