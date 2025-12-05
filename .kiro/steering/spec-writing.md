---
inclusion: fileMatch
fileMatchPattern: ".kiro/specs/**/*.md"
---

# Specification Writing Guidelines

## Requirements (requirements.md)

Use EARS patterns for acceptance criteria:
- **Ubiquitous**: THE <system> SHALL <response>
- **Event-driven**: WHEN <trigger>, THE <system> SHALL <response>
- **State-driven**: WHILE <condition>, THE <system> SHALL <response>
- **Unwanted**: IF <condition>, THEN THE <system> SHALL <response>

### Example
```markdown
### Requirement 1

**User Story:** As a developer, I want to search specs, so that I can find relevant context.

#### Acceptance Criteria

1. WHEN a user enters a search query THEN the System SHALL return matching specifications
2. WHEN no results are found THEN the System SHALL display a helpful message
```

## Design (design.md)

Include:
- Overview
- Architecture
- Components and Interfaces
- Data Models
- Correctness Properties (for property-based testing)
- Error Handling
- Testing Strategy

## Tasks (tasks.md)

Format as numbered checkboxes:
```markdown
- [ ] 1. Implement core feature
  - [ ] 1.1 Create data models
  - [ ] 1.2 Implement business logic
  - [ ]* 1.3 Write property tests (optional)
```

Tasks marked with `*` are optional (tests, docs).
