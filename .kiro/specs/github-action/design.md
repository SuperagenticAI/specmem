# Design Document

## Overview

The SpecMem GitHub Action is a composite action that runs SpecMem analysis commands in CI/CD pipelines. It uses a composite action approach (shell-based) rather than Docker for faster startup and simpler maintenance. The action installs SpecMem via pip (from PyPI or GitHub), runs analysis commands, formats results, posts PR comments, and sets outputs for downstream steps.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions Runner                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Composite Action                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │   Setup     │  │   Runner    │  │   Reporter      │  │   │
│  │  │  (install)  │──│  (execute)  │──│  (format/post)  │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    SpecMem CLI                           │   │
│  │  specmem cov | specmem health | specmem validate        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GitHub API                                  │
│  - PR Comments (issues/comments)                                │
│  - Check Runs (checks API)                                      │
│  - Action Outputs                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Action Definition (action.yml)

The main action metadata file defining inputs, outputs, and execution steps.

```yaml
name: 'SpecMem Analysis'
description: 'Analyze spec coverage, health, and quality'
branding:
  icon: 'check-circle'
  color: 'purple'

inputs:
  commands:
    description: 'Commands to run (comma-separated: cov,health,validate)'
    required: false
    default: 'cov,health'
  install_from:
    description: 'Installation source: pypi or github'
    required: false
    default: 'pypi'
  version:
    description: 'SpecMem version (PyPI) or ref (GitHub)'
    required: false
    default: 'latest'
  github_repo:
    description: 'GitHub repo for installation (owner/repo)'
    required: false
    default: 'your-org/specmem'
  working_directory:
    description: 'Directory to run analysis in'
    required: false
    default: '.'
  comment_on_pr:
    description: 'Post results as PR comment'
    required: false
    default: 'true'
  fail_on_coverage_drop:
    description: 'Fail if coverage decreases'
    required: false
    default: 'false'
  coverage_threshold:
    description: 'Minimum coverage percentage'
    required: false
    default: '0'
  health_threshold:
    description: 'Minimum health grade (A, B, C, D)'
    required: false
    default: ''
  fail_on_validation_errors:
    description: 'Fail if validation finds errors'
    required: false
    default: 'false'
  github_token:
    description: 'GitHub token for API calls'
    required: false
    default: ${{ github.token }}

outputs:
  coverage_percentage:
    description: 'Spec coverage percentage'
  health_grade:
    description: 'Health grade (A-F)'
  health_score:
    description: 'Health score (0-100)'
  validation_errors:
    description: 'Number of validation errors'
  results_json:
    description: 'Full results as JSON'
```

### 2. Setup Script (scripts/setup.sh)

Handles SpecMem installation with caching support.

```bash
#!/bin/bash
set -e

INSTALL_FROM="${1:-pypi}"
VERSION="${2:-latest}"
GITHUB_REPO="${3:-your-org/specmem}"

# Create cache key based on install source and version
if [ "$INSTALL_FROM" = "pypi" ]; then
    if [ "$VERSION" = "latest" ]; then
        pip install specmem
    else
        pip install "specmem==$VERSION"
    fi
else
    # Install from GitHub
    if [ "$VERSION" = "latest" ] || [ "$VERSION" = "main" ]; then
        pip install "git+https://github.com/$GITHUB_REPO.git"
    else
        pip install "git+https://github.com/$GITHUB_REPO.git@$VERSION"
    fi
fi

# Verify installation
specmem --version
```

### 3. Runner Script (scripts/run.py)

Executes SpecMem commands and collects results.

```python
#!/usr/bin/env python3
"""Run SpecMem commands and collect results."""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    command: str
    success: bool
    output: str
    data: dict


def run_command(cmd: str, working_dir: str) -> CommandResult:
    """Run a specmem command and parse results."""
    full_cmd = f"specmem {cmd} --robot"
    
    result = subprocess.run(
        full_cmd,
        shell=True,
        cwd=working_dir,
        capture_output=True,
        text=True,
    )
    
    try:
        data = json.loads(result.stdout) if result.stdout else {}
    except json.JSONDecodeError:
        data = {"raw_output": result.stdout}
    
    return CommandResult(
        command=cmd,
        success=result.returncode == 0,
        output=result.stdout + result.stderr,
        data=data,
    )


def main():
    commands = sys.argv[1].split(",")
    working_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    results = {}
    for cmd in commands:
        cmd = cmd.strip()
        if cmd:
            results[cmd] = run_command(cmd, working_dir)
    
    # Output results as JSON
    output = {
        "coverage_percentage": results.get("cov", {}).data.get("coverage_percentage", 0),
        "health_grade": results.get("health", {}).data.get("letter_grade", "N/A"),
        "health_score": results.get("health", {}).data.get("overall_score", 0),
        "validation_errors": len(results.get("validate", {}).data.get("errors", [])),
        "commands": {k: v.data for k, v in results.items()},
    }
    
    print(json.dumps(output))


if __name__ == "__main__":
    main()
```

### 4. Reporter Script (scripts/report.py)

Formats results and posts PR comments.

```python
#!/usr/bin/env python3
"""Format results and post PR comment."""

import json
import os
import sys
from pathlib import Path

import requests


def format_markdown(results: dict) -> str:
    """Format results as markdown for PR comment."""
    coverage = results.get("coverage_percentage", 0)
    health_grade = results.get("health_grade", "N/A")
    health_score = results.get("health_score", 0)
    validation_errors = results.get("validation_errors", 0)
    
    # Determine status emoji
    cov_emoji = "✅" if coverage >= 80 else "⚠️" if coverage >= 50 else "❌"
    health_emoji = "✅" if health_grade in ["A", "B"] else "⚠️" if health_grade == "C" else "❌"
    val_emoji = "✅" if validation_errors == 0 else "❌"
    
    md = f"""## 📊 SpecMem Analysis

| Metric | Value | Status |
|--------|-------|--------|
| Spec Coverage | {coverage:.1f}% | {cov_emoji} |
| Health Grade | {health_grade} ({health_score:.0f}/100) | {health_emoji} |
| Validation Errors | {validation_errors} | {val_emoji} |

"""
    
    # Add details if available
    if "commands" in results:
        if "cov" in results["commands"]:
            cov_data = results["commands"]["cov"]
            if "features" in cov_data:
                md += "\n<details>\n<summary>📋 Coverage by Feature</summary>\n\n"
                md += "| Feature | Coverage |\n|---------|----------|\n"
                for f in cov_data.get("features", [])[:10]:
                    md += f"| {f['feature_name']} | {f['coverage_percentage']:.0f}% |\n"
                md += "\n</details>\n"
    
    md += f"\n---\n*Generated by [SpecMem](https://github.com/your-org/specmem)*"
    
    return md


def post_comment(markdown: str, token: str, repo: str, pr_number: int):
    """Post or update PR comment."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    # Check for existing comment
    comments_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    response = requests.get(comments_url, headers=headers)
    
    existing_comment_id = None
    for comment in response.json():
        if "SpecMem Analysis" in comment.get("body", ""):
            existing_comment_id = comment["id"]
            break
    
    if existing_comment_id:
        # Update existing comment
        update_url = f"https://api.github.com/repos/{repo}/issues/comments/{existing_comment_id}"
        requests.patch(update_url, headers=headers, json={"body": markdown})
    else:
        # Create new comment
        requests.post(comments_url, headers=headers, json={"body": markdown})


def main():
    results = json.loads(sys.argv[1])
    comment_on_pr = sys.argv[2].lower() == "true"
    
    markdown = format_markdown(results)
    
    if comment_on_pr and os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY")
        
        # Get PR number from event
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if event_path:
            with open(event_path) as f:
                event = json.load(f)
                pr_number = event.get("pull_request", {}).get("number")
                if pr_number:
                    post_comment(markdown, token, repo, pr_number)
    
    # Print markdown for logs
    print(markdown)


if __name__ == "__main__":
    main()
```

### 5. Threshold Checker (scripts/check_thresholds.py)

Evaluates results against configured thresholds.

```python
#!/usr/bin/env python3
"""Check results against thresholds."""

import json
import sys


GRADE_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}


def main():
    results = json.loads(sys.argv[1])
    coverage_threshold = float(sys.argv[2]) if sys.argv[2] else 0
    health_threshold = sys.argv[3] if len(sys.argv) > 3 else ""
    fail_on_validation = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else False
    
    failures = []
    
    # Check coverage threshold
    coverage = results.get("coverage_percentage", 0)
    if coverage_threshold > 0 and coverage < coverage_threshold:
        failures.append(f"Coverage {coverage:.1f}% is below threshold {coverage_threshold}%")
    
    # Check health threshold
    if health_threshold:
        health_grade = results.get("health_grade", "F")
        if GRADE_ORDER.get(health_grade, 0) < GRADE_ORDER.get(health_threshold, 0):
            failures.append(f"Health grade {health_grade} is below threshold {health_threshold}")
    
    # Check validation errors
    if fail_on_validation:
        validation_errors = results.get("validation_errors", 0)
        if validation_errors > 0:
            failures.append(f"Found {validation_errors} validation errors")
    
    if failures:
        print("::error::Threshold check failed:")
        for f in failures:
            print(f"::error::{f}")
        sys.exit(1)
    
    print("All threshold checks passed")


if __name__ == "__main__":
    main()
```

## Data Models

### ActionInputs

```python
@dataclass
class ActionInputs:
    commands: list[str]  # ["cov", "health", "validate"]
    install_from: str  # "pypi" or "github"
    version: str  # Version or git ref
    github_repo: str  # "owner/repo"
    working_directory: str
    comment_on_pr: bool
    fail_on_coverage_drop: bool
    coverage_threshold: float
    health_threshold: str  # "A", "B", "C", "D", or ""
    fail_on_validation_errors: bool
    github_token: str
```

### AnalysisResults

```python
@dataclass
class AnalysisResults:
    coverage_percentage: float
    health_grade: str
    health_score: float
    validation_errors: int
    commands: dict[str, dict]  # Raw command outputs
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Installation source selection
*For any* valid `install_from` value ("pypi" or "github"), the action SHALL install SpecMem from the correct source and the `specmem --version` command SHALL succeed.
**Validates: Requirements 1.2, 1.3**

### Property 2: Command execution completeness
*For any* list of valid commands, the action SHALL execute all commands and the results SHALL contain output for each command.
**Validates: Requirements 2.1, 2.2**

### Property 3: Markdown formatting consistency
*For any* valid AnalysisResults, the formatted markdown SHALL contain the coverage percentage, health grade, and validation error count.
**Validates: Requirements 3.2**

### Property 4: Threshold evaluation correctness
*For any* coverage value and threshold, the action SHALL fail if and only if coverage < threshold.
**Validates: Requirements 4.2**

### Property 5: Health grade comparison
*For any* health grade and threshold grade, the action SHALL fail if and only if the grade is strictly lower than the threshold in the ordering A > B > C > D > F.
**Validates: Requirements 4.3**

### Property 6: Output completeness
*For any* successful action run, all output variables (coverage_percentage, health_grade, health_score, validation_errors) SHALL be set.
**Validates: Requirements 6.2**

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| Installation fails | Exit with error, log pip output |
| Command not found | Skip command, log warning, continue |
| Invalid working directory | Exit with clear error message |
| GitHub API rate limit | Retry with backoff, then warn |
| Malformed JSON output | Use raw output, log warning |
| PR comment fails | Log warning, don't fail action |

## Testing Strategy

### Unit Tests
- Test markdown formatting with various result combinations
- Test threshold checking logic
- Test grade comparison ordering

### Property-Based Tests
- Use `hypothesis` to generate random results and verify formatting
- Test threshold boundary conditions
- Test command list parsing

### Integration Tests
- Test full action execution in a test workflow
- Verify PR comment posting (in test repo)
- Test caching behavior

