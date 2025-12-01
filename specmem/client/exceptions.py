"""Exceptions for SpecMemClient API."""


class SpecMemError(Exception):
    """Base exception for SpecMem errors."""

    pass


class ConfigurationError(SpecMemError):
    """Configuration loading or validation error."""

    pass


class MemoryStoreError(SpecMemError):
    """Memory store access error."""

    pass


class ProposalError(SpecMemError):
    """Proposal operation error."""

    pass
