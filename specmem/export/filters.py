"""Client-side filtering utilities for static dashboard.

These functions are designed to be used both server-side (for testing)
and can be translated to JavaScript for client-side filtering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from specmem.export.models import SpecData


@dataclass
class FilterCriteria:
    """Criteria for filtering specs."""

    query: str | None = None
    feature: str | None = None
    status: str | None = None  # "complete", "in_progress", "not_started"
    health_grade: str | None = None  # "A", "B", "C", "D", "F"


def search_specs(specs: list[SpecData], query: str) -> list[SpecData]:
    """Filter specs by search query.

    Searches in spec name and content (requirements, design, tasks).
    Case-insensitive matching.

    Args:
        specs: List of specs to filter
        query: Search query string

    Returns:
        Filtered list of specs matching the query
    """
    if not query or not query.strip():
        return specs

    query_lower = query.lower().strip()
    results = []

    for spec in specs:
        # Search in name
        if query_lower in spec.name.lower():
            results.append(spec)
            continue

        # Search in path
        if query_lower in spec.path.lower():
            results.append(spec)
            continue

        # Search in requirements
        if query_lower in spec.requirements.lower():
            results.append(spec)
            continue

        # Search in design
        if spec.design and query_lower in spec.design.lower():
            results.append(spec)
            continue

        # Search in tasks
        if spec.tasks and query_lower in spec.tasks.lower():
            results.append(spec)
            continue

    return results


def filter_by_feature(specs: list[SpecData], feature: str) -> list[SpecData]:
    """Filter specs by feature name.

    Args:
        specs: List of specs to filter
        feature: Feature name to match

    Returns:
        Filtered list of specs matching the feature
    """
    if not feature:
        return specs

    feature_lower = feature.lower()
    return [s for s in specs if feature_lower in s.name.lower()]


def filter_by_status(specs: list[SpecData], status: str) -> list[SpecData]:
    """Filter specs by task completion status.

    Args:
        specs: List of specs to filter
        status: Status to filter by ("complete", "in_progress", "not_started")

    Returns:
        Filtered list of specs matching the status
    """
    if not status:
        return specs

    results = []
    for spec in specs:
        spec_status = get_spec_status(spec)
        if spec_status == status:
            results.append(spec)

    return results


def get_spec_status(spec: SpecData) -> str:
    """Determine the status of a spec based on task completion.

    Args:
        spec: The spec to check

    Returns:
        Status string: "complete", "in_progress", or "not_started"
    """
    if spec.task_total == 0:
        return "not_started"

    if spec.task_completed == spec.task_total:
        return "complete"

    if spec.task_completed > 0:
        return "in_progress"

    return "not_started"


def filter_by_health_grade(
    specs: list[SpecData],
    health_grade: str,
    health_data: dict[str, str] | None = None,
) -> list[SpecData]:
    """Filter specs by health grade.

    Args:
        specs: List of specs to filter
        health_grade: Grade to filter by ("A", "B", "C", "D", "F")
        health_data: Optional mapping of spec name to health grade

    Returns:
        Filtered list of specs matching the health grade
    """
    if not health_grade or not health_data:
        return specs

    grade_upper = health_grade.upper()
    return [s for s in specs if health_data.get(s.name, "N/A") == grade_upper]


def filter_specs(
    specs: list[SpecData],
    criteria: FilterCriteria,
    health_data: dict[str, str] | None = None,
) -> list[SpecData]:
    """Apply multiple filter criteria to specs.

    All criteria are combined with AND logic.

    Args:
        specs: List of specs to filter
        criteria: Filter criteria to apply
        health_data: Optional mapping of spec name to health grade

    Returns:
        Filtered list of specs matching all criteria
    """
    results = specs

    if criteria.query:
        results = search_specs(results, criteria.query)

    if criteria.feature:
        results = filter_by_feature(results, criteria.feature)

    if criteria.status:
        results = filter_by_status(results, criteria.status)

    if criteria.health_grade:
        results = filter_by_health_grade(results, criteria.health_grade, health_data)

    return results


def matches_all_criteria(
    spec: SpecData,
    criteria: FilterCriteria,
    health_data: dict[str, str] | None = None,
) -> bool:
    """Check if a spec matches all filter criteria.

    Args:
        spec: The spec to check
        criteria: Filter criteria to match
        health_data: Optional mapping of spec name to health grade

    Returns:
        True if spec matches all criteria
    """
    # Check query
    if criteria.query:
        query_lower = criteria.query.lower()
        if not any([
            query_lower in spec.name.lower(),
            query_lower in spec.path.lower(),
            query_lower in spec.requirements.lower(),
            spec.design and query_lower in spec.design.lower(),
            spec.tasks and query_lower in spec.tasks.lower(),
        ]):
            return False

    # Check feature
    if criteria.feature:
        if criteria.feature.lower() not in spec.name.lower():
            return False

    # Check status
    if criteria.status:
        if get_spec_status(spec) != criteria.status:
            return False

    # Check health grade
    if criteria.health_grade and health_data:
        if health_data.get(spec.name, "N/A") != criteria.health_grade.upper():
            return False

    return True
