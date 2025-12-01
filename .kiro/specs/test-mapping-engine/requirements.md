# Requirements Document

## Introduction

This feature provides a Test Mapping Engine that enables SpecMem to output which tests to run based on code changes, enhanced SpecIR with test mappings and code references, and a reverse mapping capability (`specmem infer`) to discover specs from code. The engine is framework-agnostic, supporting pytest, jest, playwright, and other test frameworks through a unified interface.

## Glossary

- **Test Mapping Engine**: System that maps specifications to their corresponding tests and vice versa
- **TestMapping**: Framework-agnostic reference to a test (framework, path, selector)
- **CodeRef**: Reference linking a specification to implementation code (file, symbols, line range)
- **Confidence Score**: Float 0.0-1.0 indicating certainty of a mapping relationship
- **Test Framework**: Testing tool (pytest, jest, playwright, vitest, etc.)
- **Test Selector**: Framework-specific test identifier (e.g., `test_auth::test_login` for pytest)
- **Reverse Mapping**: Process of inferring specs from code analysis
- **SpecIR**: Specification Intermediate Representation - the core data model

## Requirements

### Requirement 1

**User Story:** As a coding agent, I want to get a list of tests to run for changed files, so that I can validate my code changes efficiently.

#### Acceptance Criteria

1. WHEN requesting tests for changed files THEN the system SHALL return a list of TestMapping objects
2. WHEN returning test mappings THEN the system SHALL include framework, path, and selector for each test
3. WHEN multiple frameworks are detected THEN the system SHALL return tests grouped by framework
4. WHEN no tests are mapped to changed files THEN the system SHALL return an empty list with a message
5. WHEN test mappings have varying confidence THEN the system SHALL order results by confidence descending

### Requirement 2

**User Story:** As a developer, I want SpecIR blocks to include test mappings, so that I can see which tests validate each specification.

#### Acceptance Criteria

1. WHEN a SpecBlock is created THEN the system SHALL support an optional test_mappings field
2. WHEN test_mappings is provided THEN the system SHALL validate each mapping has framework, path, and selector
3. WHEN serializing a SpecBlock THEN the system SHALL include test_mappings in the output
4. WHEN deserializing a SpecBlock THEN the system SHALL restore test_mappings correctly

### Requirement 3

**User Story:** As a developer, I want SpecIR blocks to include code references, so that I can trace specs to implementation.

#### Acceptance Criteria

1. WHEN a SpecBlock is created THEN the system SHALL support an optional code_refs field
2. WHEN code_refs is provided THEN the system SHALL validate each ref has language, file_path, and symbols
3. WHEN a code_ref includes line_range THEN the system SHALL validate it as a tuple of (start, end)
4. WHEN serializing a SpecBlock THEN the system SHALL include code_refs in the output
5. WHEN deserializing a SpecBlock THEN the system SHALL restore code_refs correctly

### Requirement 4

**User Story:** As a developer, I want SpecIR blocks to include confidence scores, so that I can understand mapping certainty.

#### Acceptance Criteria

1. WHEN a SpecBlock is created THEN the system SHALL support an optional confidence field
2. WHEN confidence is provided THEN the system SHALL validate it is between 0.0 and 1.0
3. WHEN confidence is not provided THEN the system SHALL default to 1.0
4. WHEN querying specs THEN the system SHALL include confidence in relevance calculations

### Requirement 5

**User Story:** As a coding agent, I want to infer specs from code files, so that I can discover undocumented specifications.

#### Acceptance Criteria

1. WHEN running `specmem infer <file>` THEN the system SHALL analyze the code file
2. WHEN analyzing code THEN the system SHALL extract function/class definitions and docstrings
3. WHEN specs are inferred THEN the system SHALL return SpecCandidate objects with suggested content
4. WHEN inferred specs match existing specs THEN the system SHALL link them with confidence scores
5. WHEN no specs can be inferred THEN the system SHALL return an empty list with a message

### Requirement 6

**User Story:** As a developer, I want the test mapping engine to support multiple frameworks, so that I can use it with any test setup.

#### Acceptance Criteria

1. WHEN detecting test frameworks THEN the system SHALL recognize pytest, jest, vitest, playwright, and mocha
2. WHEN parsing test files THEN the system SHALL extract test names using framework-specific patterns
3. WHEN a framework is unknown THEN the system SHALL use generic test file detection
4. WHEN test files are found THEN the system SHALL create TestMapping objects with correct selectors

### Requirement 7

**User Story:** As a coding agent, I want to get suggested tests via the SpecMemClient API, so that I can integrate test suggestions into my workflow.

#### Acceptance Criteria

1. WHEN calling get_context_for_change THEN the system SHALL include suggested_tests in the ContextBundle
2. WHEN calling get_impacted_specs THEN the system SHALL include test_mappings for each ImpactedSpec
3. WHEN test mappings are returned THEN the system SHALL include confidence scores
4. WHEN no test mappings exist THEN the system SHALL return empty lists without errors

### Requirement 8

**User Story:** As a developer, I want a CLI command to show test mappings, so that I can see which tests cover my specs.

#### Acceptance Criteria

1. WHEN running `specmem tests <spec_id>` THEN the system SHALL display tests mapped to that spec
2. WHEN running `specmem tests --file <path>` THEN the system SHALL display tests for specs related to that file
3. WHEN displaying tests THEN the system SHALL show framework, path, selector, and confidence
4. WHEN no tests are found THEN the system SHALL display a helpful message
