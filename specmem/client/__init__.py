"""SpecMemClient - Python API for agent integration.

Provides a simple interface for coding agents to interact with SpecMem.
"""

from specmem.client.client import SpecMemClient
from specmem.client.exceptions import (
    ConfigurationError,
    MemoryStoreError,
    ProposalError,
    SpecMemError,
)
from specmem.client.models import (
    ContextBundle,
    Proposal,
    ProposalStatus,
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
]
