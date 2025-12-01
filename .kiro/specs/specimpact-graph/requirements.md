# Requirements Document

## Introduction

This feature enhances SpecMem with a dynamic SpecImpact Graph - a bidirectional relationship graph that connects specifications, code, and tests. The graph answers the critical question: "If this file changed, which specs and tests matter?" This enables selective testing, safe incremental development, and context-aware agents without Bazel-like complexity.

## Glossary

- **SpecImpact Graph**: A directed graph representing relationships between specs, code files, and tests
- **Node**: A vertex in the graph representing a spec, code file, or test
- **Edge**: A directed connection between nodes with a relationship type and confidence score
- **Traversal**: Walking the graph to find related nodes (e.g., code → specs → tests)
- **Impact Set**: The set of specs and tests affected by a code change
- **Bidirectional Query**: Ability to query both "what does this affect?" and "what affects this?"
- **Incremental Update**: Updating only changed portions of the graph without full rebuild

## Requirements

### Requirement 1

**User Story:** As a coding agent, I want to query which specs are affected by a code change, so that I can understand the impact before modifying code.

#### Acceptance Criteria

1. WHEN querying with a list of changed files THEN the system SHALL return all specs linked to those files
2. WHEN returning affected specs THEN the system SHALL include confidence scores for each relationship
3. WHEN specs have transitive relationships THEN the system SHALL include indirectly affected specs
4. WHEN no specs are affected THEN the system SHALL return an empty list with a message

### Requirement 2

**User Story:** As a coding agent, I want to query which tests should run for a code change, so that I can enable selective testing.

#### Acceptance Criteria

1. WHEN querying tests for changed files THEN the system SHALL traverse spec→test relationships
2. WHEN returning tests THEN the system SHALL include framework, path, and selector for each test
3. WHEN tests have varying relevance THEN the system SHALL order results by confidence descending
4. WHEN no tests are mapped THEN the system SHALL return an empty list

### Requirement 3

**User Story:** As a developer, I want to query which code implements a spec, so that I can trace specs to implementation.

#### Acceptance Criteria

1. WHEN querying code for a spec_id THEN the system SHALL return all linked code files
2. WHEN returning code refs THEN the system SHALL include file path, symbols, and line ranges
3. WHEN code has multiple links to a spec THEN the system SHALL return all links with confidence
4. WHEN no code is linked THEN the system SHALL return an empty list

### Requirement 4

**User Story:** As a developer, I want the graph to update incrementally, so that I don't need full rebuilds.

#### Acceptance Criteria

1. WHEN a spec file changes THEN the system SHALL update only affected graph nodes
2. WHEN a code file changes THEN the system SHALL re-analyze and update its relationships
3. WHEN updating incrementally THEN the system SHALL preserve unaffected relationships
4. WHEN conflicts occur THEN the system SHALL log warnings and use latest data

### Requirement 5

**User Story:** As a coding agent, I want to get the full impact set for a change, so that I can make informed decisions.

#### Acceptance Criteria

1. WHEN requesting impact set THEN the system SHALL return specs, code, and tests in one response
2. WHEN calculating impact THEN the system SHALL use configurable depth for transitive relationships
3. WHEN impact set is large THEN the system SHALL support pagination or limits
4. WHEN impact set is empty THEN the system SHALL indicate the change has no tracked impact

### Requirement 6

**User Story:** As a developer, I want to visualize the SpecImpact graph, so that I can understand relationships.

#### Acceptance Criteria

1. WHEN requesting graph visualization THEN the system SHALL return data in a graph-friendly format
2. WHEN exporting graph THEN the system SHALL support DOT, JSON, and Mermaid formats
3. WHEN filtering visualization THEN the system SHALL support filtering by node type
4. WHEN graph is large THEN the system SHALL support subgraph extraction around a focal node

### Requirement 7

**User Story:** As a developer, I want automatic code-to-spec linking, so that relationships are discovered without manual annotation.

#### Acceptance Criteria

1. WHEN building the graph THEN the system SHALL analyze code to find spec references
2. WHEN analyzing code THEN the system SHALL use naming conventions, imports, and semantic similarity
3. WHEN confidence is below threshold THEN the system SHALL mark links as "suggested"
4. WHEN manual links exist THEN the system SHALL preserve them with higher confidence

### Requirement 8

**User Story:** As a developer, I want a CLI command to query the impact graph, so that I can use it in scripts and CI.

#### Acceptance Criteria

1. WHEN running `specmem graph impact <files>` THEN the system SHALL display affected specs and tests
2. WHEN running `specmem graph show <node_id>` THEN the system SHALL display node relationships
3. WHEN running `specmem graph export` THEN the system SHALL output graph in specified format
4. WHEN running `specmem graph stats` THEN the system SHALL display graph statistics
