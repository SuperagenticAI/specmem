# Requirements Document

## Introduction

This feature provides a GitHub Action that enables users to run SpecMem analysis (coverage, health, validation) as part of their CI/CD pipeline. The action supports flexible installation via PyPI or direct GitHub URL, posts results as PR comments, creates status checks, and can fail builds based on configurable thresholds.

## Glossary

- **GitHub Action**: A reusable workflow component that runs in GitHub's CI/CD environment
- **Composite Action**: A GitHub Action defined using shell commands and other actions (no Docker required)
- **PR Comment**: A comment posted on a Pull Request with analysis results
- **Status Check**: A pass/fail indicator shown on PRs and commits
- **Coverage**: Percentage of acceptance criteria that have corresponding tests
- **Health Score**: Overall project health grade (A-F) based on spec quality metrics
- **Validation**: Checking specs for structural issues, contradictions, and quality problems

## Requirements

### Requirement 1

**User Story:** As a developer, I want to add SpecMem analysis to my CI pipeline with minimal configuration, so that I can automatically check spec quality on every PR.

#### Acceptance Criteria

1. WHEN a user adds the action to their workflow THEN the Action SHALL install SpecMem and run the specified commands
2. WHEN the action runs THEN the Action SHALL support installation from PyPI using `pip install specmem`
3. WHEN the action runs with `install_from: github` THEN the Action SHALL install from the GitHub repository URL
4. WHEN no install source is specified THEN the Action SHALL default to PyPI installation

### Requirement 2

**User Story:** As a developer, I want to run multiple SpecMem commands in a single action step, so that I can get comprehensive analysis without multiple workflow steps.

#### Acceptance Criteria

1. WHEN a user specifies multiple commands THEN the Action SHALL run each command sequentially
2. WHEN running commands THEN the Action SHALL support `cov`, `health`, and `validate` commands
3. WHEN a command fails THEN the Action SHALL continue running remaining commands and report all results
4. WHEN all commands complete THEN the Action SHALL aggregate results into a single output

### Requirement 3

**User Story:** As a developer, I want to see SpecMem results as a PR comment, so that I can quickly review spec quality without checking logs.

#### Acceptance Criteria

1. WHEN the action runs on a PR THEN the Action SHALL post a comment with formatted results
2. WHEN posting a comment THEN the Action SHALL include coverage percentage, health grade, and validation summary
3. WHEN a previous comment exists THEN the Action SHALL update the existing comment instead of creating a new one
4. WHEN `comment_on_pr` is set to false THEN the Action SHALL skip posting comments

### Requirement 4

**User Story:** As a developer, I want the action to fail my build when spec quality drops below thresholds, so that I can enforce quality standards.

#### Acceptance Criteria

1. WHEN `fail_on_coverage_drop` is enabled THEN the Action SHALL fail if coverage decreases from the base branch
2. WHEN `coverage_threshold` is set THEN the Action SHALL fail if coverage is below the threshold percentage
3. WHEN `health_threshold` is set THEN the Action SHALL fail if health grade is below the threshold (e.g., "B")
4. WHEN `fail_on_validation_errors` is enabled THEN the Action SHALL fail if validation finds errors

### Requirement 5

**User Story:** As a developer, I want to see SpecMem results in GitHub's checks UI, so that I can see pass/fail status at a glance.

#### Acceptance Criteria

1. WHEN the action completes THEN the Action SHALL create a check run with the analysis summary
2. WHEN creating a check THEN the Action SHALL include annotations for files with issues
3. WHEN the check fails THEN the Action SHALL provide a clear reason in the check summary

### Requirement 6

**User Story:** As a developer, I want the action to output results in a machine-readable format, so that I can use them in subsequent workflow steps.

#### Acceptance Criteria

1. WHEN the action completes THEN the Action SHALL set output variables for coverage, health grade, and validation count
2. WHEN setting outputs THEN the Action SHALL include `coverage_percentage`, `health_grade`, `health_score`, and `validation_errors`
3. WHEN JSON output is requested THEN the Action SHALL provide a `results_json` output with full details

### Requirement 7

**User Story:** As a developer, I want to specify a custom working directory, so that I can analyze specs in monorepos or subdirectories.

#### Acceptance Criteria

1. WHEN `working_directory` is specified THEN the Action SHALL run commands in that directory
2. WHEN no working directory is specified THEN the Action SHALL use the repository root
3. WHEN the directory does not exist THEN the Action SHALL fail with a clear error message

### Requirement 8

**User Story:** As a developer, I want to pin a specific version of SpecMem, so that I can ensure reproducible builds.

#### Acceptance Criteria

1. WHEN `version` is specified THEN the Action SHALL install that specific version from PyPI
2. WHEN `version` is "latest" THEN the Action SHALL install the latest version
3. WHEN installing from GitHub THEN the Action SHALL support specifying a branch, tag, or commit SHA

### Requirement 9

**User Story:** As a developer, I want the action to cache SpecMem installation, so that subsequent runs are faster.

#### Acceptance Criteria

1. WHEN the action runs THEN the Action SHALL cache the pip installation
2. WHEN a cache hit occurs THEN the Action SHALL skip installation and use cached packages
3. WHEN the version changes THEN the Action SHALL invalidate the cache and reinstall

