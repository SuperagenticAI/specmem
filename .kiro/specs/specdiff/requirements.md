# Requirements Document

## Introduction

SpecDiff is a temporal intelligence system that tracks specification evolution over time. It enables agents and developers to understand what changed in requirements, why it changed, and what parts of the codebase are now invalid due to spec drift. SpecDiff serves as "git blame for requirements" - providing historical context, change tracking, and staleness detection for specifications.

## Glossary

- **SpecDiff**: The temporal spec intelligence system that tracks spec evolution
- **Spec Version**: A snapshot of a specification at a point in time
- **Spec Change**: A detected modification between two spec versions
- **Semantic Diff**: Comparison of spec meaning beyond textual changes
- **Spec Drift**: When code implementation diverges from current spec
- **Stale Memory**: A cached spec that no longer reflects current requirements
- **Contradiction**: Conflicting statements between old and new specs
- **Change Reason**: Inferred rationale for why a spec changed
- **Deprecation**: A spec or feature marked as no longer recommended
- **Spec Timeline**: Chronological history of a spec's evolution

## Requirements

### Requirement 1

**User Story:** As a coding agent, I want to see what changed in a specification, so that I can understand the evolution of requirements.

#### Acceptance Criteria

1. WHEN querying a spec's history THEN the system SHALL return a chronological list of versions
2. WHEN comparing two spec versions THEN the system SHALL show added, removed, and modified content
3. WHEN displaying changes THEN the system SHALL include timestamps and commit references
4. WHEN a spec has no history THEN the system SHALL indicate it is a new specification
5. WHEN changes are semantic (meaning changed) vs cosmetic (formatting) THEN the system SHALL distinguish between them

### Requirement 2

**User Story:** As a coding agent, I want to understand why a specification changed, so that I can make informed implementation decisions.

#### Acceptance Criteria

1. WHEN a spec change is detected THEN the system SHALL attempt to infer the change reason
2. WHEN inferring reasons THEN the system SHALL analyze commit messages and related diffs
3. WHEN a reason cannot be inferred THEN the system SHALL mark it as "unknown"
4. WHEN displaying change reasons THEN the system SHALL include confidence scores
5. WHEN multiple possible reasons exist THEN the system SHALL list them ranked by likelihood

### Requirement 3

**User Story:** As a developer, I want to know which code is invalid due to spec drift, so that I can prioritize refactoring.

#### Acceptance Criteria

1. WHEN a spec changes THEN the system SHALL identify code that implemented the old spec
2. WHEN code is identified as drifted THEN the system SHALL calculate a drift severity score
3. WHEN displaying drift THEN the system SHALL show the specific spec changes causing it
4. WHEN drift is detected THEN the system SHALL suggest which code sections need updates
5. WHEN no drift is detected THEN the system SHALL confirm code is aligned with current spec

### Requirement 4

**User Story:** As a coding agent, I want to be warned if I'm using stale memories, so that I don't implement outdated requirements.

#### Acceptance Criteria

1. WHEN an agent accesses a spec THEN the system SHALL check if newer versions exist
2. WHEN a stale memory is detected THEN the system SHALL emit a warning with details
3. WHEN warning about staleness THEN the system SHALL show what changed since the cached version
4. WHEN staleness is critical (breaking changes) THEN the system SHALL flag it as high priority
5. WHEN the agent acknowledges staleness THEN the system SHALL record the acknowledgment

### Requirement 5

**User Story:** As a developer, I want to detect contradictions between old and new specs, so that I can resolve conflicts.

#### Acceptance Criteria

1. WHEN comparing spec versions THEN the system SHALL identify contradictory statements
2. WHEN a contradiction is found THEN the system SHALL highlight the conflicting text
3. WHEN displaying contradictions THEN the system SHALL show both old and new versions
4. WHEN contradictions exist THEN the system SHALL suggest resolution approaches
5. WHEN no contradictions exist THEN the system SHALL confirm spec consistency

### Requirement 6

**User Story:** As a developer, I want to automatically detect deprecated features, so that I can plan migrations.

#### Acceptance Criteria

1. WHEN a spec is marked deprecated THEN the system SHALL track the deprecation date
2. WHEN code references deprecated specs THEN the system SHALL flag it for migration
3. WHEN displaying deprecations THEN the system SHALL show replacement recommendations
4. WHEN a deprecation has a deadline THEN the system SHALL calculate time remaining
5. WHEN querying deprecations THEN the system SHALL return them sorted by urgency

### Requirement 7

**User Story:** As a developer, I want a CLI to query spec history and drift, so that I can integrate it into my workflow.

#### Acceptance Criteria

1. WHEN running `specmem diff <spec_id>` THEN the system SHALL show recent changes
2. WHEN running `specmem history <spec_id>` THEN the system SHALL show version timeline
3. WHEN running `specmem drift` THEN the system SHALL show all detected drift
4. WHEN running `specmem stale` THEN the system SHALL show stale memories
5. WHEN running `specmem deprecations` THEN the system SHALL list deprecated specs

### Requirement 8

**User Story:** As a coding agent, I want to query spec changes via API, so that I can programmatically access temporal intelligence.

#### Acceptance Criteria

1. WHEN calling `get_spec_history(spec_id)` THEN the system SHALL return version list
2. WHEN calling `get_spec_diff(spec_id, from_version, to_version)` THEN the system SHALL return changes
3. WHEN calling `check_staleness(spec_ids)` THEN the system SHALL return staleness status
4. WHEN calling `get_drift_report()` THEN the system SHALL return drift analysis
5. WHEN calling `get_contradictions(spec_id)` THEN the system SHALL return conflicts

### Requirement 9

**User Story:** As a developer, I want spec changes to be tracked automatically, so that I don't need manual version management.

#### Acceptance Criteria

1. WHEN a spec file is modified THEN the system SHALL automatically create a new version
2. WHEN creating versions THEN the system SHALL use git commits as version identifiers
3. WHEN git is unavailable THEN the system SHALL use timestamps as fallback
4. WHEN tracking changes THEN the system SHALL store minimal diffs to save space
5. WHEN the history grows large THEN the system SHALL support pruning old versions
