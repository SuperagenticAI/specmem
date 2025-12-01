# Requirements Document

## Introduction

This feature provides a Python client API (`SpecMemClient`) that enables coding agents to programmatically interact with SpecMem. The client provides a simple, intuitive interface for agents to fetch context bundles, query impacted specs, propose edits, and access cognitive memory - making SpecMem the AgentEx (Agent Experience) layer for any coding agent.

## Glossary

- **SpecMemClient**: Python class providing programmatic access to SpecMem functionality
- **Context Bundle**: Optimized collection of specs, designs, tests, and TL;DR for agent consumption
- **Impacted Specs**: Specifications affected by code changes (via SpecImpact)
- **Proposal**: Agent-suggested edit to a specification awaiting human approval
- **AgentEx**: Agent Experience - the developer experience layer for coding agents
- **TL;DR**: Concise summary of specifications for quick agent comprehension

## Requirements

### Requirement 1

**User Story:** As a coding agent, I want to initialize a SpecMemClient with a repository path, so that I can access the project's specification memory.

#### Acceptance Criteria

1. WHEN initializing SpecMemClient with a path THEN the system SHALL load configuration from .specmem.toml if present
2. WHEN initializing without explicit path THEN the system SHALL use the current working directory
3. WHEN the memory store does not exist THEN the system SHALL create it automatically
4. WHEN initialization fails THEN the system SHALL raise a descriptive SpecMemError

### Requirement 2

**User Story:** As a coding agent, I want to get a context bundle for changed files, so that I can understand the relevant specs before writing code.

#### Acceptance Criteria

1. WHEN requesting context for changed files THEN the system SHALL return specs, designs, tests, and TL;DR
2. WHEN generating context THEN the system SHALL optimize for the specified token budget
3. WHEN no token budget is specified THEN the system SHALL use a default of 4000 tokens
4. WHEN changed files have no related specs THEN the system SHALL return an empty bundle with a message

### Requirement 3

**User Story:** As a coding agent, I want to get impacted specs from a code change, so that I know which specifications are affected.

#### Acceptance Criteria

1. WHEN requesting impacted specs for files THEN the system SHALL return ranked SpecIR objects
2. WHEN specs are impacted THEN the system SHALL include test mappings if available
3. WHEN using git diff THEN the system SHALL parse the diff to extract changed files
4. WHEN no specs are impacted THEN the system SHALL return an empty list

### Requirement 4

**User Story:** As a coding agent, I want to query specs by natural language, so that I can find relevant specifications for my task.

#### Acceptance Criteria

1. WHEN querying with natural language THEN the system SHALL return semantically similar specs
2. WHEN querying THEN the system SHALL respect the top_k limit parameter
3. WHEN querying THEN the system SHALL exclude legacy specs unless explicitly requested
4. WHEN the query matches pinned specs THEN the system SHALL include them with high priority

### Requirement 5

**User Story:** As a coding agent, I want to propose spec edits, so that humans can review and approve my suggestions.

#### Acceptance Criteria

1. WHEN proposing an edit THEN the system SHALL store the proposal with diff and rationale
2. WHEN a proposal is stored THEN the system SHALL assign a unique proposal ID
3. WHEN listing proposals THEN the system SHALL show pending, accepted, and rejected proposals
4. WHEN accepting a proposal THEN the system SHALL update the spec and mark proposal as accepted

### Requirement 6

**User Story:** As a coding agent, I want to get a TL;DR summary of specs, so that I can quickly understand the project context.

#### Acceptance Criteria

1. WHEN requesting TL;DR THEN the system SHALL return concise summaries of key specs
2. WHEN generating TL;DR THEN the system SHALL prioritize pinned and high-relevance specs
3. WHEN TL;DR exceeds token limit THEN the system SHALL truncate lower-priority content
4. WHEN no specs exist THEN the system SHALL return a message indicating empty memory

### Requirement 7

**User Story:** As a developer, I want to import SpecMemClient from the specmem package, so that integration is simple.

#### Acceptance Criteria

1. WHEN importing from specmem THEN the system SHALL expose SpecMemClient at package level
2. WHEN using the client THEN the system SHALL provide type hints for IDE support
3. WHEN errors occur THEN the system SHALL raise typed exceptions (SpecMemError subclasses)
4. WHEN the client is used THEN the system SHALL log operations at DEBUG level
