#!/usr/bin/env python3
"""Run SpecMem commands and collect results.

This script executes SpecMem CLI commands and outputs results
in a format suitable for GitHub Actions.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CommandResult:
    """Result from running a single command."""

    command: str
    success: bool
    output: str
    data: dict


def run_command(cmd: str, working_dir: str) -> CommandResult:
    """Run a specmem command and parse results.

    Args:
        cmd: The specmem subcommand to run (e.g., 'cov', 'health')
        working_dir: Directory to run the command in

    Returns:
        CommandResult with parsed output
    """
    full_cmd = f"specmem {cmd} --robot"

    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Try to parse JSON output
        try:
            data = json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            data = {"raw_output": result.stdout}

        return CommandResult(
            command=cmd,
            success=result.returncode == 0,
            output=result.stdout + result.stderr,
            data=data,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(
            command=cmd,
            success=False,
            output="Command timed out after 5 minutes",
            data={"error": "timeout"},
        )
    except Exception as e:
        return CommandResult(
            command=cmd,
            success=False,
            output=str(e),
            data={"error": str(e)},
        )


def validate_working_directory(path: str) -> bool:
    """Validate that the working directory exists.

    Args:
        path: Path to validate

    Returns:
        True if valid, False otherwise
    """
    if not Path(path).exists():
        print(f"::error::Working directory does not exist: {path}")
        return False
    if not Path(path).is_dir():
        print(f"::error::Working directory is not a directory: {path}")
        return False
    return True


def set_output(name: str, value: str) -> None:
    """Set a GitHub Actions output variable.

    Args:
        name: Output variable name
        value: Output value
    """
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            # Handle multiline values
            if "\n" in str(value):
                delimiter = "EOF"
                f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                f.write(f"{name}={value}\n")
    else:
        # Fallback for local testing
        print(f"::set-output name={name}::{value}")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Get inputs from environment
    commands_str = os.environ.get("COMMANDS", "cov,health")
    working_dir = os.environ.get("WORKING_DIR", ".")

    # Parse commands
    commands = [cmd.strip() for cmd in commands_str.split(",") if cmd.strip()]

    if not commands:
        print("::error::No commands specified")
        return 1

    # Validate working directory
    if not validate_working_directory(working_dir):
        return 1

    print(f"::group::Running SpecMem commands: {', '.join(commands)}")
    print(f"Working directory: {working_dir}")

    # Run each command
    results: dict[str, CommandResult] = {}
    for cmd in commands:
        print(f"\n--- Running: specmem {cmd} ---")
        result = run_command(cmd, working_dir)
        results[cmd] = result

        if result.success:
            print(f"✅ {cmd} completed successfully")
        else:
            print(f"⚠️ {cmd} had issues (continuing with other commands)")
            print(f"Output: {result.output[:500]}")

    print("::endgroup::")

    # Extract key metrics
    cov_data = results.get("cov", CommandResult("cov", False, "", {})).data
    health_data = results.get("health", CommandResult("health", False, "", {})).data
    validate_data = results.get("validate", CommandResult("validate", False, "", {})).data

    coverage_percentage = cov_data.get("coverage_percentage", 0)
    health_grade = health_data.get("letter_grade", "N/A")
    health_score = health_data.get("overall_score", 0)
    validation_errors = len(validate_data.get("errors", []))

    # Build full results
    full_results = {
        "coverage_percentage": coverage_percentage,
        "health_grade": health_grade,
        "health_score": health_score,
        "validation_errors": validation_errors,
        "commands": {k: v.data for k, v in results.items()},
    }

    # Set outputs
    set_output("coverage_percentage", str(coverage_percentage))
    set_output("health_grade", str(health_grade))
    set_output("health_score", str(health_score))
    set_output("validation_errors", str(validation_errors))
    set_output("results_json", json.dumps(full_results))

    # Print summary
    print("\n📊 SpecMem Analysis Results:")
    print(f"  Coverage: {coverage_percentage}%")
    print(f"  Health: {health_grade} ({health_score}/100)")
    print(f"  Validation Errors: {validation_errors}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
