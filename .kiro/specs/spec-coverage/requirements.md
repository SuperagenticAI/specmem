# Requirements Document

## Introduction

This feature provides Spec Coverage Analysis for SpecMem, enabling developers and coding agents to analyze the gap between specification acceptance criteria and existing tests. The system scans specs to extract acceptance criteria, scans test files to find test functions, uses semantic matching to link criteria to tests, and reports coverage gaps with actionable suggestions. The feature is accessed via the `specmem cov` command with subcommands for different operations.

## Glossary

- **Spec Coverage**: Measurement of how many acceptance criteria have corresponding tests
- **Acceptance Criteria (AC)**: Testable conditions in EARS format from requirements.md files
- **Coverage Report**: Summary showing which criteria are tested and which have gaps
- **Coverage Gap**: An acceptance criterion without a corresponding test
- **Semantic Matching**: Using text similarity to link acceptance criteria to test functions
- **Test Suggestion**: Recommended test approach for an untested criterion
- **Coverage Badge**: Visual indicator of coverage percentage for README files
- **CoverageResult**: Data structure containing coverage analysis results

## Requirements

### Requirement 1

**User Story:** As a developer, I want to see a coverage summary for all my specs, so that I can understand overall test coverage at a glance.

#### Acceptance Criteria

1. WHEN running `specmem cov` THEN the system SHALL display overall coverage percentage
2. WHEN running `specmem cov` THEN the system SHALL display a table of features with tested/total criteria counts
3. WHEN displaying coverage THEN the system SHALL show gap percentage for each feature
4. WHEN coverage is below 50% THEN the system SHALL display a warning indicator
5. WHEN coverage is 100% THEN the system SHALL display a success indicator

### Requirement 2

**User Story:** As a developer, I want to see detailed coverage for a specific feature, so that I can identify exactly which criteria need tests.

#### Acceptance Criteria

1. WHEN running `specmem cov report <feature>` THEN the system SHALL display all acceptance criteria for that feature
2. WHEN displaying criteria THEN the system SHALL show test status (covered/uncovered) for each
3. WHEN a criterion is covered THEN the system SHALL show the linked test file and selector
4. WHEN a criterion is uncovered THEN the system SHALL display a gap indicator
5. WHEN the feature has no specs THEN the system SHALL display a helpful message

### Requirement 3

**User Story:** As a developer, I want the system to extract acceptance criteria from my spec files, so that coverage can be calculated accurately.

#### Acceptance Criteria

1. WHEN parsing requirements.md THEN the system SHALL extract all numbered acceptance criteria
2. WHEN extracting criteria THEN the system SHALL preserve the EARS format text
3. WHEN extracting criteria THEN the system SHALL capture the requirement number (e.g., 1.3)
4. WHEN extracting criteria THEN the system SHALL link criteria to their parent user story
5. WHEN a spec file has no acceptance criteria THEN the system SHALL return an empty list

### Requirement 4

**User Story:** As a developer, I want the system to scan my test files and extract test functions, so that they can be matched to criteria.

#### Acceptance Criteria

1. WHEN scanning test files THEN the system SHALL detect pytest, jest, vitest, playwright, and mocha tests
2. WHEN extracting tests THEN the system SHALL capture test name, file path, and line number
3. WHEN extracting tests THEN the system SHALL capture docstrings or comments describing the test
4. WHEN a test references a requirement (e.g., "Validates: 1.3") THEN the system SHALL capture that link
5. WHEN no test files are found THEN the system SHALL return an empty list with a message

### Requirement 5

**User Story:** As a developer, I want the system to match acceptance criteria to tests using semantic similarity, so that coverage is detected even without explicit links.

#### Acceptance Criteria

1. WHEN matching criteria to tests THEN the system SHALL use text similarity scoring
2. WHEN a test explicitly references a requirement THEN the system SHALL assign confidence 1.0
3. WHEN matching by similarity THEN the system SHALL assign confidence between 0.0 and 1.0
4. WHEN confidence is below 0.5 THEN the system SHALL treat the criterion as uncovered
5. WHEN multiple tests match a criterion THEN the system SHALL select the highest confidence match

### Requirement 6

**User Story:** As a developer, I want to get test suggestions for uncovered criteria, so that I know what tests to write.

#### Acceptance Criteria

1. WHEN running `specmem cov suggest <feature>` THEN the system SHALL list all uncovered criteria
2. WHEN suggesting tests THEN the system SHALL recommend a test file location
3. WHEN suggesting tests THEN the system SHALL recommend a test function name
4. WHEN suggesting tests THEN the system SHALL list what to verify based on the criterion
5. WHEN all criteria are covered THEN the system SHALL display a success message

### Requirement 7

**User Story:** As a developer, I want to generate a coverage badge for my README, so that I can display coverage status publicly.

#### Acceptance Criteria

1. WHEN running `specmem cov badge` THEN the system SHALL output a badge URL or markdown
2. WHEN generating badge THEN the system SHALL include the coverage percentage
3. WHEN coverage is below 50% THEN the badge SHALL be red
4. WHEN coverage is between 50-80% THEN the badge SHALL be yellow
5. WHEN coverage is above 80% THEN the badge SHALL be green

### Requirement 8

**User Story:** As a developer, I want to export coverage data in different formats, so that I can integrate with other tools.

#### Acceptance Criteria

1. WHEN running `specmem cov export --format json` THEN the system SHALL output valid JSON
2. WHEN running `specmem cov export --format markdown` THEN the system SHALL output markdown table
3. WHEN exporting THEN the system SHALL include all features, criteria, and test mappings
4. WHEN exporting THEN the system SHALL include confidence scores for each mapping
5. WHEN exporting to file THEN the system SHALL support --output flag for file path

### Requirement 9

**User Story:** As a coding agent, I want to access coverage data via the SpecMemClient API, so that I can integrate coverage checks into my workflow.

#### Acceptance Criteria

1. WHEN calling get_coverage() THEN the system SHALL return a CoverageResult object
2. WHEN calling get_coverage(feature) THEN the system SHALL return coverage for that specific feature
3. WHEN returning coverage THEN the system SHALL include criteria, tests, and confidence scores
4. WHEN returning coverage THEN the system SHALL include suggestions for uncovered criteria
5. WHEN no specs exist THEN the system SHALL return an empty CoverageResult without errors
