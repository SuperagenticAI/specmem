# Design Document: Coding Guidelines View

## Overview

This feature adds a unified "Coding Guidelines" view to the SpecMem dashboard that aggregates coding rules from multiple sources (CLAUDE.md, AGENTS.md, .cursorrules, Kiro steering files) and provides bidirectional conversion between formats. This positions SpecMem as a "universal translator" for AI coding guidelines.

## Architecture

```mermaid
graph TB
    subgraph Sources
        CLAUDE[CLAUDE.md]
        AGENTS[AGENTS.md]
        CURSOR[.cursorrules]
        STEERING[.kiro/steering/*.md]
    end
    
    subgraph GuidelinesEngine
        SCANNER[GuidelinesScanner]
        PARSER[GuidelinesParser]
        CONVERTER[GuidelinesConverter]
        AGGREGATOR[GuidelinesAggregator]
    end
    
    subgraph API
        ENDPOINT[/api/guidelines]
        CONVERT_EP[/api/guidelines/convert]
        EXPORT_EP[/api/guidelines/export]
    end
    
    subgraph UI
        VIEW[Guidelines View]
        MODAL[Detail Modal]
        PREVIEW[Conversion Preview]
    end
    
    CLAUDE --> SCANNER
    AGENTS --> SCANNER
    CURSOR --> SCANNER
    STEERING --> SCANNER
    
    SCANNER --> PARSER
    PARSER --> AGGREGATOR
    AGGREGATOR --> ENDPOINT
    
    PARSER --> CONVERTER
    CONVERTER --> CONVERT_EP
    CONVERTER --> EXPORT_EP
    
    ENDPOINT --> VIEW
    VIEW --> MODAL
    CONVERT_EP --> PREVIEW
```

## Components and Interfaces

### 1. GuidelinesScanner

Scans the workspace for all guideline files.

```python
class GuidelinesScanner:
    """Scans workspace for coding guideline files."""
    
    FILE_PATTERNS = {
        "claude": ["**/CLAUDE.md", "**/Claude.md"],
        "agents": ["**/AGENTS.md", "**/Agents.md", "**/AGENT.md"],
        "cursor": ["**/.cursorrules", "**/cursor.rules"],
        "steering": [".kiro/steering/*.md"],
    }
    
    def scan(self, workspace_path: Path) -> dict[str, list[Path]]:
        """Scan for all guideline files grouped by source type."""
        ...
    
    def has_guidelines(self, workspace_path: Path) -> bool:
        """Check if any guideline files exist."""
        ...
```

### 2. GuidelinesParser

Parses guideline files into a unified format.

```python
@dataclass
class Guideline:
    """A single coding guideline."""
    id: str
    title: str
    content: str
    source_type: str  # claude, cursor, steering, agents
    source_file: str
    file_pattern: str | None  # Files this guideline applies to
    tags: list[str]
    is_sample: bool = False

class GuidelinesParser:
    """Parses guideline files into unified Guideline objects."""
    
    def parse_claude(self, file_path: Path) -> list[Guideline]:
        """Parse CLAUDE.md file into guidelines."""
        ...
    
    def parse_cursor(self, file_path: Path) -> list[Guideline]:
        """Parse .cursorrules file into guidelines."""
        ...
    
    def parse_steering(self, file_path: Path) -> list[Guideline]:
        """Parse Kiro steering file into guidelines."""
        ...
    
    def parse_agents(self, file_path: Path) -> list[Guideline]:
        """Parse AGENTS.md file into guidelines."""
        ...
```

### 3. GuidelinesConverter

Converts guidelines between formats.

```python
@dataclass
class ConversionResult:
    """Result of a guideline conversion."""
    filename: str
    content: str
    frontmatter: dict[str, Any]
    
class GuidelinesConverter:
    """Converts guidelines between different formats."""
    
    def to_steering(self, guideline: Guideline) -> ConversionResult:
        """Convert a guideline to Kiro steering format."""
        ...
    
    def to_claude(self, guidelines: list[Guideline]) -> str:
        """Convert guidelines to CLAUDE.md format."""
        ...
    
    def to_cursor(self, guidelines: list[Guideline]) -> str:
        """Convert guidelines to .cursorrules format."""
        ...
    
    def suggest_inclusion_mode(self, guideline: Guideline) -> str:
        """Suggest appropriate inclusion mode based on content."""
        ...
    
    def suggest_file_pattern(self, guideline: Guideline) -> str | None:
        """Suggest file pattern based on guideline content."""
        ...
```

### 4. GuidelinesAggregator

Aggregates guidelines from all sources with filtering and search.

```python
@dataclass
class GuidelinesResponse:
    """Response containing aggregated guidelines."""
    guidelines: list[Guideline]
    total_count: int
    counts_by_source: dict[str, int]
    
class GuidelinesAggregator:
    """Aggregates and filters guidelines from all sources."""
    
    def get_all(self, workspace_path: Path) -> GuidelinesResponse:
        """Get all guidelines from all sources."""
        ...
    
    def filter_by_source(self, source_type: str) -> list[Guideline]:
        """Filter guidelines by source type."""
        ...
    
    def filter_by_file(self, file_path: str) -> list[Guideline]:
        """Get guidelines that apply to a specific file."""
        ...
    
    def search(self, query: str) -> list[Guideline]:
        """Search guidelines by title and content."""
        ...
```

### 5. SampleGuidelinesProvider

Provides sample guidelines for demonstration.

```python
class SampleGuidelinesProvider:
    """Provides sample guideline files for demonstration."""
    
    def get_sample_claude(self) -> str:
        """Get sample CLAUDE.md content."""
        ...
    
    def get_sample_cursorrules(self) -> str:
        """Get sample .cursorrules content."""
        ...
    
    def get_sample_agents(self) -> str:
        """Get sample AGENTS.md content."""
        ...
```

## Data Models

```python
from dataclasses import dataclass
from enum import Enum

class SourceType(str, Enum):
    CLAUDE = "claude"
    CURSOR = "cursor"
    STEERING = "steering"
    AGENTS = "agents"
    SAMPLE = "sample"

class InclusionMode(str, Enum):
    ALWAYS = "always"
    FILE_MATCH = "fileMatch"
    MANUAL = "manual"

@dataclass
class Guideline:
    id: str
    title: str
    content: str
    source_type: SourceType
    source_file: str
    file_pattern: str | None
    tags: list[str]
    is_sample: bool = False

@dataclass
class ConversionResult:
    filename: str
    content: str
    frontmatter: dict[str, Any]
    source_guideline: Guideline

@dataclass
class GuidelinesResponse:
    guidelines: list[Guideline]
    total_count: int
    counts_by_source: dict[str, int]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing the acceptance criteria, I identified the following redundancies:
- Properties 1.1 and 5.1 both test that all guidelines are returned - combined into Property 1
- Properties 1.4 and counts verification can be combined
- Properties 6.1, 6.2, 6.3 can be combined into a single conversion property
- Properties 9.1 and 9.2 can be combined into a single export property

### Properties

**Property 1: Guidelines aggregation completeness**
*For any* set of guideline files (CLAUDE.md, .cursorrules, steering files, AGENTS.md), the aggregator SHALL return all guidelines from all sources with correct source type attribution.
**Validates: Requirements 1.1, 5.1**

**Property 2: Source grouping correctness**
*For any* set of guidelines with different source types, grouping by source SHALL produce groups where every guideline in a group has the matching source type.
**Validates: Requirements 1.2**

**Property 3: Count consistency**
*For any* set of guidelines, the total count SHALL equal the sum of counts by source, and each source count SHALL equal the number of guidelines with that source type.
**Validates: Requirements 1.4**

**Property 4: Filter correctness**
*For any* source type filter applied to a set of guidelines, the filtered result SHALL contain only guidelines with the matching source type, and SHALL contain all guidelines with that source type.
**Validates: Requirements 2.2**

**Property 5: Search coverage**
*For any* search query and set of guidelines, the search results SHALL include all guidelines where the query appears in either the title or content.
**Validates: Requirements 3.1, 3.2**

**Property 6: File pattern matching**
*For any* file path and set of guidelines with file patterns, filtering by file path SHALL return only guidelines whose pattern matches the file path.
**Validates: Requirements 5.3**

**Property 7: Conversion round-trip**
*For any* guideline converted to steering format, the content SHALL be preserved (modulo frontmatter), and the resulting steering file SHALL have valid frontmatter with an inclusion mode.
**Validates: Requirements 6.1, 6.2, 6.3**

**Property 8: Bulk conversion completeness**
*For any* set of guidelines, bulk conversion SHALL produce one steering file per logical section, and the union of all converted content SHALL cover all original content.
**Validates: Requirements 7.1, 7.2**

**Property 9: Sample marking**
*For any* sample guideline, the is_sample flag SHALL be True, distinguishing it from real guidelines.
**Validates: Requirements 8.2**

**Property 10: Export format validity**
*For any* set of steering files exported to Claude or Cursor format, the output SHALL be valid for the target format and SHALL contain all guideline content.
**Validates: Requirements 9.1, 9.2, 9.3**

## Error Handling

| Error Condition | Handling Strategy |
|-----------------|-------------------|
| Guideline file not found | Skip file, log warning, continue with other files |
| Malformed YAML frontmatter | Parse as plain markdown, log warning |
| Invalid file encoding | Try UTF-8, fallback to latin-1, skip if both fail |
| Conversion fails | Return error with details, don't write partial files |
| File write permission denied | Return error, suggest manual creation |

## Testing Strategy

### Unit Tests

- Test each parser (Claude, Cursor, Steering, Agents) with valid and malformed input
- Test converter output format validity
- Test aggregator filtering and search logic
- Test sample provider content validity

### Property-Based Tests

Use `hypothesis` library for property-based testing:

```python
from hypothesis import given, strategies as st

class TestGuidelinesProps:
    """Property tests for Guidelines feature.
    
    **Feature: coding-guidelines-view**
    """
    
    @given(st.lists(st.builds(Guideline, ...)))
    def test_aggregation_completeness(self, guidelines: list[Guideline]) -> None:
        """Property 1: All guidelines are returned."""
        ...
    
    @given(st.lists(st.builds(Guideline, ...)))
    def test_filter_correctness(self, guidelines: list[Guideline]) -> None:
        """Property 4: Filter returns correct subset."""
        ...
    
    @given(st.builds(Guideline, ...))
    def test_conversion_round_trip(self, guideline: Guideline) -> None:
        """Property 7: Content preserved through conversion."""
        ...
```

### Integration Tests

- Test full flow from file scanning to API response
- Test conversion and file writing
- Test UI rendering with sample data
