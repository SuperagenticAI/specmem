# Implementation Plan

- [x] 1. Create data models and core interfaces
  - [x] 1.1 Create `specmem/guidelines/models.py` with Guideline, ConversionResult, GuidelinesResponse dataclasses
    - Define SourceType enum (claude, cursor, steering, agents, sample)
    - Define Guideline dataclass with id, title, content, source_type, source_file, file_pattern, tags, is_sample
    - Define ConversionResult and GuidelinesResponse dataclasses
    - _Requirements: 1.1, 5.2_

  - [x] 1.2 Write property test for data model invariants
    - **Property 3: Count consistency**
    - **Validates: Requirements 1.4**

- [x] 2. Implement GuidelinesScanner
  - [x] 2.1 Create `specmem/guidelines/scanner.py` with file detection logic
    - Implement FILE_PATTERNS for each source type
    - Implement `scan()` method to find all guideline files
    - Implement `has_guidelines()` method
    - _Requirements: 1.1_

  - [x] 2.2 Write property test for scanner completeness
    - **Property 1: Guidelines aggregation completeness**
    - **Validates: Requirements 1.1, 5.1**

- [x] 3. Implement GuidelinesParser
  - [x] 3.1 Create `specmem/guidelines/parser.py` with parsing logic
    - Implement `parse_claude()` for CLAUDE.md files
    - Implement `parse_cursor()` for .cursorrules files
    - Implement `parse_steering()` for Kiro steering files
    - Implement `parse_agents()` for AGENTS.md files
    - Extract sections, titles, and content from each format
    - _Requirements: 1.1, 1.2_

  - [x] 3.2 Write property test for source grouping
    - **Property 2: Source grouping correctness**
    - **Validates: Requirements 1.2**

- [x] 4. Implement GuidelinesAggregator
  - [x] 4.1 Create `specmem/guidelines/aggregator.py` with aggregation logic
    - Implement `get_all()` to aggregate from all sources
    - Implement `filter_by_source()` for source type filtering
    - Implement `filter_by_file()` for file pattern matching
    - Implement `search()` for title and content search
    - _Requirements: 1.1, 2.2, 3.1, 3.2, 5.3_

  - [x] 4.2 Write property test for filter correctness
    - **Property 4: Filter correctness**
    - **Validates: Requirements 2.2**

  - [x] 4.3 Write property test for search coverage
    - **Property 5: Search coverage**
    - **Validates: Requirements 3.1, 3.2**

  - [x] 4.4 Write property test for file pattern matching
    - **Property 6: File pattern matching**
    - **Validates: Requirements 5.3**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement GuidelinesConverter
  - [x] 6.1 Create `specmem/guidelines/converter.py` with conversion logic
    - Implement `to_steering()` to convert any guideline to Kiro steering format
    - Implement `to_claude()` to export guidelines to CLAUDE.md format
    - Implement `to_cursor()` to export guidelines to .cursorrules format
    - Implement `suggest_inclusion_mode()` based on content analysis
    - Implement `suggest_file_pattern()` based on content analysis
    - _Requirements: 6.1, 6.2, 6.3, 9.1, 9.2, 9.3_

  - [x] 6.2 Write property test for conversion round-trip
    - **Property 7: Conversion round-trip**
    - **Validates: Requirements 6.1, 6.2, 6.3**

  - [x] 6.3 Write property test for bulk conversion
    - **Property 8: Bulk conversion completeness**
    - **Validates: Requirements 7.1, 7.2**

  - [x] 6.4 Write property test for export format validity
    - **Property 10: Export format validity**
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [x] 7. Implement SampleGuidelinesProvider
  - [x] 7.1 Create `specmem/guidelines/samples.py` with sample content
    - Implement `get_sample_claude()` with realistic CLAUDE.md content
    - Implement `get_sample_cursorrules()` with realistic .cursorrules content
    - Implement `get_sample_agents()` with realistic AGENTS.md content
    - Mark all sample guidelines with is_sample=True
    - _Requirements: 8.1, 8.2_

  - [x] 7.2 Write property test for sample marking
    - **Property 9: Sample marking**
    - **Validates: Requirements 8.2**

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement API endpoints
  - [x] 9.1 Add `/api/guidelines` endpoint to `specmem/ui/api.py`
    - Return all guidelines with counts by source
    - Support `source` query parameter for filtering
    - Support `file` query parameter for file pattern matching
    - Support `q` query parameter for search
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 9.2 Add `/api/guidelines/convert` endpoint
    - Accept guideline ID and target format
    - Return ConversionResult with generated content
    - Support preview mode (don't write files)
    - _Requirements: 6.1, 6.4, 7.3_

  - [x] 9.3 Add `/api/guidelines/export` endpoint
    - Accept target format (claude, cursor)
    - Return generated file content
    - _Requirements: 9.1, 9.2_

  - [x] 9.4 Add TypeScript types to `specmem/ui/frontend/src/api.ts`
    - Add Guideline, GuidelinesResponse, ConversionResult types
    - Add API methods for guidelines endpoints
    - _Requirements: 5.1_

- [x] 10. Implement UI components
  - [x] 10.1 Add "Guidelines" nav item and view to `specmem/ui/frontend/src/App.tsx`
    - Add Guidelines icon and nav button
    - Create GuidelinesView component
    - Display guidelines grouped by source in card grid
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 10.2 Add filter buttons to GuidelinesView
    - Add filter buttons for each source type (Claude, Cursor, Steering, Agents)
    - Implement filter state and filtering logic
    - Show empty state when no guidelines match filter
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 10.3 Add search functionality to GuidelinesView
    - Add search input field
    - Implement search filtering
    - _Requirements: 3.1, 3.2_

  - [x] 10.4 Add guideline detail modal
    - Show full content when clicking a guideline card
    - Display source file path
    - Format code examples properly
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 10.5 Add conversion UI
    - Add "Convert to Steering" button on guideline cards
    - Add "Convert All" button in header
    - Show conversion preview modal
    - Add "Export to Claude/Cursor" buttons
    - _Requirements: 6.4, 7.3, 9.1, 9.2_

- [x] 11. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
