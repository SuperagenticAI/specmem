"""SpecDiff - Temporal Spec Intelligence for SpecMem.

Tracks specification evolution over time, enabling agents to understand
what changed, why it changed, and what code is now invalid due to spec drift.
"""

from specmem.diff.models import (
    ChangeReason,
    ChangeType,
    Contradiction,
    Deprecation,
    DriftItem,
    DriftReport,
    ModifiedSection,
    Severity,
    SpecChange,
    SpecVersion,
    StalenessWarning,
)
from specmem.diff.specdiff import SpecDiff
from specmem.diff.storage import VersionStore


__all__ = [
    "ChangeReason",
    "ChangeType",
    "Contradiction",
    "Deprecation",
    "DriftItem",
    "DriftReport",
    "ModifiedSection",
    "Severity",
    "SpecChange",
    "SpecDiff",
    "SpecVersion",
    "StalenessWarning",
    "VersionStore",
]
