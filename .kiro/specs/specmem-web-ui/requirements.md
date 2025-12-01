# Requirements Document

## Introduction

SpecMem Web UI provides a lightweight, developer-friendly web dashboard for visualizing and interacting with the SpecMem memory layer. The UI enables developers to browse structured memory, filter by status, search knowledge, and export Agent Experience Packs. It is launched via `specmem serve` and serves as the "Living Documentation Layer" for spec-driven development projects.

## Glossary

- **SpecMem**: The unified agent-agnostic memory engine for spec-driven development
- **SpecBlock**: The canonical representation of a specification unit (requirement, design, task, etc.)
- **Agent Experience Pack**: The output folder (.specmem/) containing agent_memory.json, agent_context.md, and knowledge_index.json
- **Memory Bank**: The collection of all SpecBlocks stored in the vector database
- **Active Memory**: SpecBlocks with status "active" that are included in queries
- **Legacy Memory**: SpecBlocks marked as "legacy" that are excluded from normal retrieval
- **Pinned Memory**: Critical SpecBlocks that are always included in context regardless of query

## Requirements

### Requirement 1

**User Story:** As a developer, I want to launch a web UI from the command line, so that I can visually explore my project's specification memory.

#### Acceptance Criteria

1. WHEN a user runs `specmem serve` THEN the System SHALL start a local HTTP server on a configurable port (default 8765)
2. WHEN the server starts successfully THEN the System SHALL display the URL in the terminal with Rich formatting
3. WHEN the user specifies `--port <number>` THEN the System SHALL use the specified port for the server
4. WHEN the specified port is already in use THEN the System SHALL display an error message and suggest an alternative port
5. WHEN the user presses Ctrl+C THEN the System SHALL gracefully shutdown the server

### Requirement 2

**User Story:** As a developer, I want to view all my specifications in a structured dashboard, so that I can understand my project's knowledge at a glance.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN the System SHALL display a summary card showing total SpecBlocks count, active count, and legacy count
2. WHEN the dashboard loads THEN the System SHALL display SpecBlocks grouped by type (requirement, design, task, decision, knowledge)
3. WHEN displaying a SpecBlock THEN the System SHALL show its id, type, text preview, source file, status, and pinned indicator
4. WHEN a SpecBlock text exceeds 200 characters THEN the System SHALL truncate with ellipsis and provide expand functionality
5. WHEN the user clicks on a SpecBlock THEN the System SHALL display the full details in a side panel or modal

### Requirement 3

**User Story:** As a developer, I want to filter specifications by status, so that I can focus on active or legacy items separately.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN the System SHALL display filter controls for status (All, Active, Legacy)
2. WHEN the user selects "Active" filter THEN the System SHALL display only SpecBlocks with status "active"
3. WHEN the user selects "Legacy" filter THEN the System SHALL display only SpecBlocks with status "legacy"
4. WHEN the user selects "All" filter THEN the System SHALL display all SpecBlocks regardless of status
5. WHEN filters are applied THEN the System SHALL update the summary counts to reflect filtered results

### Requirement 4

**User Story:** As a developer, I want to filter specifications by type, so that I can focus on specific categories like requirements or tasks.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN the System SHALL display filter controls for type (All, Requirement, Design, Task, Decision, Knowledge)
2. WHEN the user selects a type filter THEN the System SHALL display only SpecBlocks of that type
3. WHEN multiple filters are active (status + type) THEN the System SHALL apply all filters with AND logic
4. WHEN the user clears filters THEN the System SHALL reset to showing all SpecBlocks

### Requirement 5

**User Story:** As a developer, I want to search my specifications semantically, so that I can find relevant knowledge using natural language queries.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN the System SHALL display a search input field prominently
2. WHEN the user enters a search query and submits THEN the System SHALL perform a semantic vector search
3. WHEN search results are returned THEN the System SHALL display matching SpecBlocks ordered by relevance score
4. WHEN displaying search results THEN the System SHALL show the relevance score for each result
5. WHEN no results match the query THEN the System SHALL display a "No results found" message with suggestions

### Requirement 6

**User Story:** As a developer, I want to view pinned specifications separately, so that I can see critical items that are always included in agent context.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN the System SHALL display a "Pinned" section or tab showing all pinned SpecBlocks
2. WHEN a SpecBlock is pinned THEN the System SHALL display a visual indicator (icon or badge)
3. WHEN viewing pinned items THEN the System SHALL show why each item is pinned (e.g., contains SHALL keyword)

### Requirement 7

**User Story:** As a developer, I want to export the Agent Experience Pack from the UI, so that I can generate fresh context for my coding agents.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN the System SHALL display an "Export Pack" button
2. WHEN the user clicks "Export Pack" THEN the System SHALL trigger a rebuild of the .specmem/ folder
3. WHEN the export completes THEN the System SHALL display a success message with the output path
4. WHEN the export fails THEN the System SHALL display an error message with details

### Requirement 8

**User Story:** As a developer, I want to view memory statistics, so that I can understand the composition of my specification memory.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN the System SHALL display statistics showing block counts by type
2. WHEN the dashboard loads THEN the System SHALL display statistics showing block counts by source file
3. WHEN the dashboard loads THEN the System SHALL display the total vector memory size
4. WHEN statistics are displayed THEN the System SHALL use visual charts or graphs for clarity

### Requirement 9

**User Story:** As a developer, I want the UI to auto-refresh when specs change, so that I always see the latest state without manual reload.

#### Acceptance Criteria

1. WHEN spec files change on disk THEN the System SHALL detect the changes within 2 seconds
2. WHEN changes are detected THEN the System SHALL refresh the displayed data automatically
3. WHEN auto-refresh occurs THEN the System SHALL display a subtle notification indicating refresh
4. WHERE the user prefers manual refresh THEN the System SHALL provide a toggle to disable auto-refresh

### Requirement 10

**User Story:** As a developer, I want a clean, modern UI design, so that the tool feels professional and is pleasant to use.

#### Acceptance Criteria

1. WHEN the UI renders THEN the System SHALL use a consistent color scheme with dark mode support
2. WHEN the UI renders THEN the System SHALL be responsive and work on different screen sizes
3. WHEN the UI renders THEN the System SHALL use clear typography and adequate spacing
4. WHEN the UI loads THEN the System SHALL display within 2 seconds on localhost
