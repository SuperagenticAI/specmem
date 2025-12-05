#!/usr/bin/env python3
"""Check results against configured thresholds.

This script evaluates SpecMem analysis results against
user-configured thresholds and fails the action if needed.
"""

from __future__ import annotations

import json
import os
import sys


# Grade ordering for comparison (higher is better)
GRADE_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1, "N/A": 0}


def check_coverage_threshold(coverage: float, threshold: float) -> str | None:
    """Check if coverage meets threshold.

    Args:
        coverage: Current coverage percentage
        threshold: Minimum required coverage

    Returns:
        Error message if failed, None if passed
    """
    if threshold > 0 and coverage < threshold:
        return f"Coverage {coverage:.1f}% is below threshold {threshold}%"
    return None


def check_health_threshold(grade: str, threshold: str) -> str | None:
    """Check if health grade meets threshold.

    Args:
        grade: Current health grade
        threshold: Minimum required grade

    Returns:
        Error message if failed, None if passed
    """
    if not threshold:
        return None

    current_order = GRADE_ORDER.get(grade.upper(), 0)
    threshold_order = GRADE_ORDER.get(threshold.upper(), 0)

    if current_order < threshold_order:
        return f"Health grade {grade} is below threshold {threshold}"
    return None


def check_validation_errors(error_count: int, fail_on_errors: bool) -> str | None:
    """Check if validation errors should fail the build.

    Args:
        error_count: Number of validation errors
        fail_on_errors: Whether to fail on any errors

    Returns:
        Error message if failed, None if passed
    """
    if fail_on_errors and error_count > 0:
        return f"Found {error_count} validation error(s)"
    return None


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for threshold failure)
    """
    # Get inputs from environment
    results_json = os.environ.get("RESULTS_JSON", "{}")
    coverage_threshold = os.environ.get("COVERAGE_THRESHOLD", "0")
    health_threshold = os.environ.get("HEALTH_THRESHOLD", "")
    fail_on_validation = os.environ.get("FAIL_ON_VALIDATION", "false").lower() == "true"

    # Parse results
    try:
        results = json.loads(results_json)
    except json.JSONDecodeError:
        print("::warning::Failed to parse results JSON, skipping threshold checks")
        return 0

    # Extract values
    coverage = float(results.get("coverage_percentage", 0))
    health_grade = str(results.get("health_grade", "N/A"))
    validation_errors = int(results.get("validation_errors", 0))

    # Parse threshold
    try:
        cov_threshold = float(coverage_threshold)
    except ValueError:
        cov_threshold = 0

    # Run checks
    failures: list[str] = []

    cov_check = check_coverage_threshold(coverage, cov_threshold)
    if cov_check:
        failures.append(cov_check)

    health_check = check_health_threshold(health_grade, health_threshold)
    if health_check:
        failures.append(health_check)

    val_check = check_validation_errors(validation_errors, fail_on_validation)
    if val_check:
        failures.append(val_check)

    # Report results
    if failures:
        print("::group::❌ Threshold Check Failed")
        for failure in failures:
            print(f"::error::{failure}")
        print("::endgroup::")
        return 1

    print("✅ All threshold checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
