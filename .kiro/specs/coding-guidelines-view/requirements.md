# Requirements Document

## Introduction

This feature adds a dedicated "Coding Guidelines" view to the SpecMem dashboard that aggregates and displays all team coding rules and standards from various sources including CLAUDE.md, .cursorrules, AGENTS.md, and Kiro steering files. It also provides conversion tools to transform guidelines between formats, enabling teams to migrate from vendor-specific formats to Kiro steering files or a SpecMem-native format.

## Glossary

- **Coding Guidelines**: Rules and standards that define how code should be written in a project
- **Steering Files**: Kiro-specific markdown files in `.kiro/steering/` that provide context to AI agents
- **CLAUDE.md**: Claude Code's project context file containing coding rules
- **AGENTS.md**: Generic agent instructions file used by various AI tools
- **.cursorrules**: Cursor's rules file for AI behavior customization
- **SpecMem Dashboard**: The web UI launched via `specmem demo`
- **Guidelines Converter**: Tool to transform guidelines between different formats

## Requirements

### Requirement 1

**User Story:** As a developer, I want to see all my team's coding guidelines in one place, so that I can quickly reference coding standards without searching multiple files.

#### Acceptance Criteria

1. WHEN a user navigates to the Coding Guidelines view THEN the system SHALL display all coding rules from CLAUDE.md, AGENTS.md, .cursorrules, and steering files
2. WHEN displaying guidelines THEN the system SHALL group them by source (Claude, Cursor, Kiro Steering, Agents)
3. WHEN a guideline has a file match pattern THEN the system SHALL display which files the guideline applies to
4. WHEN guidelines are loaded THEN the system SHALL show the total count of rules from each source

### Requirement 2

**User Story:** As a developer, I want to filter coding guidelines by source or category, so that I can find relevant rules quickly.

#### Acceptance Criteria

1. WHEN viewing guidelines THEN the system SHALL provide filter buttons for each source type (Claude, Cursor, Steering, Agents)
2. WHEN a filter is applied THEN the system SHALL show only guidelines from the selected source
3. WHEN no guidelines match the filter THEN the system SHALL display an appropriate empty state message

### Requirement 3

**User Story:** As a developer, I want to search within coding guidelines, so that I can find specific rules about a topic.

#### Acceptance Criteria

1. WHEN a user enters a search query THEN the system SHALL filter guidelines containing the search term
2. WHEN searching THEN the system SHALL search both the title and content of guidelines
3. WHEN search results are displayed THEN the system SHALL highlight matching terms

### Requirement 4

**User Story:** As a developer, I want to see the full content of a coding guideline, so that I can understand the complete rule.

#### Acceptance Criteria

1. WHEN a user clicks on a guideline card THEN the system SHALL display a modal with the full content
2. WHEN displaying full content THEN the system SHALL show the source file path
3. WHEN the guideline has code examples THEN the system SHALL display them with proper formatting

### Requirement 5

**User Story:** As a developer, I want the API to provide coding guidelines data, so that AI agents can access team rules programmatically.

#### Acceptance Criteria

1. WHEN the `/api/guidelines` endpoint is called THEN the system SHALL return all coding guidelines
2. WHEN returning guidelines THEN the system SHALL include source, title, content, and file patterns
3. WHEN guidelines are requested with a file path filter THEN the system SHALL return only guidelines that apply to that file

### Requirement 6

**User Story:** As a Kiro user, I want to convert CLAUDE.md and .cursorrules files to Kiro steering files, so that I can migrate my existing guidelines to the Kiro format.

#### Acceptance Criteria

1. WHEN a user clicks "Convert to Steering" on a guideline THEN the system SHALL generate a Kiro steering file with proper frontmatter
2. WHEN converting THEN the system SHALL preserve the original content and structure
3. WHEN converting THEN the system SHALL suggest appropriate inclusion mode (always, fileMatch, manual)
4. WHEN the conversion is complete THEN the system SHALL display the generated steering file content

### Requirement 7

**User Story:** As a developer migrating to Kiro, I want to convert all my existing guidelines at once, so that I can quickly adopt the Kiro format.

#### Acceptance Criteria

1. WHEN a user clicks "Convert All to Steering" THEN the system SHALL generate steering files for all detected guidelines
2. WHEN bulk converting THEN the system SHALL create separate steering files for each logical section
3. WHEN bulk converting THEN the system SHALL provide a preview before writing files
4. WHEN conversion is confirmed THEN the system SHALL write files to `.kiro/steering/` directory

### Requirement 8

**User Story:** As a developer, I want sample CLAUDE.md and .cursorrules files in the demo, so that I can see how the conversion feature works.

#### Acceptance Criteria

1. WHEN the demo workspace has no CLAUDE.md or .cursorrules THEN the system SHALL provide sample files for demonstration
2. WHEN displaying sample files THEN the system SHALL mark them as "Sample" to distinguish from real guidelines
3. WHEN sample files are converted THEN the system SHALL generate valid Kiro steering files

### Requirement 9

**User Story:** As a developer, I want to export Kiro steering files to CLAUDE.md or .cursorrules format, so that I can share guidelines with team members using other tools.

#### Acceptance Criteria

1. WHEN a user clicks "Export to Claude" THEN the system SHALL generate a CLAUDE.md file from steering files
2. WHEN a user clicks "Export to Cursor" THEN the system SHALL generate a .cursorrules file from steering files
3. WHEN exporting THEN the system SHALL combine related steering files into logical sections
