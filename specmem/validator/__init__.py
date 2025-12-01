"""SpecValidator - Specification Quality Assurance.

Validates specifications for correctness, completeness, and consistency.
Detects contradictions, missing acceptance criteria, invalid constraints,
duplicate features, and impossible timelines.
"""

from specmem.validator.config import RuleConfig, ValidationConfig
from specmem.validator.engine import ValidationEngine
from specmem.validator.models import (
    IssueSeverity,
    ValidationIssue,
    ValidationResult,
)
from specmem.validator.rules import (
    AcceptanceCriteriaRule,
    ConstraintRule,
    ContradictionRule,
    DuplicateRule,
    StructureRule,
    TimelineRule,
    ValidationRule,
)


__all__ = [
    "AcceptanceCriteriaRule",
    "ConstraintRule",
    "ContradictionRule",
    "DuplicateRule",
    "IssueSeverity",
    "RuleConfig",
    "StructureRule",
    "TimelineRule",
    "ValidationConfig",
    "ValidationEngine",
    "ValidationIssue",
    "ValidationResult",
    "ValidationRule",
]
