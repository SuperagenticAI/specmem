# Design Document

## Overview

This design document outlines the technical approach for polishing SpecMem to create compelling demo experiences and improve overall user experience. The focus is on visual impact, seamless Kiro integration, and zero-friction onboarding.

## Architecture

The polish features integrate with existing SpecMem components:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web UI (React)                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Dashboard   │  │ Impact Graph │  │  Tour Mode   │          │
│  │  - Stats     │  │  - D3.js     │  │  - Steps     │          │
│  │  - Health    │  │  - Force     │  │  - Highlight │          │
│  │  - Actions   │  │  - Tooltips  │  │  - Progress  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                           │                                     │
│                    ┌──────▼──────┐                              │
│                    │  WebSocket  │  ← Live Updates              │
│                    └──────┬──────┘                              │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                     Backend (FastAPI)                           │
├───────────────────────────┼─────────────────────────────────────┤
│  ┌──────────────┐  ┌──────▼──────┐  ┌──────────────┐           │
│  │ Health Score │  │ File Watcher│  │ Demo Command │           │
│  │   Engine     │  │  (watchdog) │  │   Handler    │           │
│  └──────────────┘  └─────────────┘  └──────────────┘           │
│                                                                 │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐           │
│  │ Quick Action │  │ Kiro Hooks  │  │ Graph Data   │           │
│  │   Executor   │  │  Generator  │  │   Builder    │           │
│  └──────────────┘  └─────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Health Score Engine

```python
@dataclass
class HealthScore:
    overall_score: float  # 0-100
    letter_grade: str  # A, B, C, D, F
    coverage_score: float
    validation_score: float
    freshness_score: float
    completeness_score: float
    suggestions: list[str]

class HealthScoreEngine:
    def calculate(self, workspace_path: Path) -> HealthScore:
        """Calculate overall health score for specifications."""

    def get_suggestions(self, score: HealthScore) -> list[str]:
        """Get actionable suggestions for improvement."""
```

### 2. File Watcher Service

```python
class SpecFileWatcher:
    def __init__(self, workspace_path: Path, callback: Callable):
        """Initialize file watcher for spec files."""

    def start(self) -> None:
        """Start watching for file changes."""

    def stop(self) -> None:
        """Stop watching."""

    def on_change(self, path: Path) -> None:
        """Handle file change with debouncing."""
```

### 3. Impact Graph Builder

```python
@dataclass
class GraphNode:
    id: str
    type: str  # spec, code, test
    label: str
    metadata: dict

@dataclass
class GraphEdge:
    source: str
    target: str
    relationship: str

@dataclass
class ImpactGraphData:
    nodes: list[GraphNode]
    edges: list[GraphEdge]

class ImpactGraphBuilder:
    def build(self, workspace_path: Path) -> ImpactGraphData:
        """Build graph data for visualization."""
```

### 4. Demo Command Handler

```python
class DemoHandler:
    def setup_demo(self, workspace_path: Path) -> None:
        """Set up demo environment with sample specs."""

    def copy_specmem_specs(self, target_path: Path) -> None:
        """Copy SpecMem's own specs for dogfooding demo."""

    def launch_ui(self, port: int = 8765) -> None:
        """Launch Web UI and open browser."""
```

### 5. Kiro Hooks Generator

```python
@dataclass
class KiroHook:
    name: str
    trigger: str  # file_save, manual, etc.
    file_pattern: str
    action: str

class KiroHooksGenerator:
    def generate_hooks(self, workspace_path: Path) -> list[KiroHook]:
        """Generate Kiro hook configurations."""

    def write_hooks(self, hooks: list[KiroHook], output_path: Path) -> None:
        """Write hooks to .kiro/hooks/ directory."""
```

### 6. Quick Actions API

```python
class QuickActionsAPI:
    async def scan(self) -> dict:
        """Execute scan and return results."""

    async def build(self) -> dict:
        """Execute build and return results."""

    async def validate(self) -> dict:
        """Execute validation and return results."""

    async def coverage(self) -> dict:
        """Execute coverage analysis and return results."""
```

### 7. Tour Mode Component (React)

```typescript
interface TourStep {
  id: string;
  title: string;
  description: string;
  targetSelector: string;
  action?: () => void;
}

interface TourState {
  isActive: boolean;
  currentStep: number;
  steps: TourStep[];
}
```

## Data Models

### Health Score Response

```json
{
  "overall_score": 85.5,
  "letter_grade": "B",
  "breakdown": {
    "coverage": { "score": 90, "weight": 0.3 },
    "validation": { "score": 80, "weight": 0.25 },
    "freshness": { "score": 85, "weight": 0.2 },
    "completeness": { "score": 87, "weight": 0.25 }
  },
  "suggestions": [
    "Add tests for 3 uncovered acceptance criteria",
    "Update 2 specs that haven't changed in 30+ days"
  ]
}
```

### Impact Graph Response

```json
{
  "nodes": [
    { "id": "spec-1", "type": "spec", "label": "User Auth", "x": 100, "y": 200 },
    { "id": "code-1", "type": "code", "label": "auth/service.py", "x": 200, "y": 150 },
    { "id": "test-1", "type": "test", "label": "test_auth.py", "x": 300, "y": 200 }
  ],
  "edges": [
    { "source": "spec-1", "target": "code-1", "relationship": "implements" },
    { "source": "code-1", "target": "test-1", "relationship": "tested_by" }
  ]
}
```

### Kiro Hook Configuration

```json
{
  "name": "specmem-validate-on-save",
  "trigger": "file_save",
  "filePattern": "**/*.md",
  "action": "specmem validate --file ${file}"
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Health Score Grade Mapping

*For any* health score value between 0-100, the letter grade SHALL be deterministically mapped as: A (90-100), B (80-89), C (70-79), D (60-69), F (0-59).

**Validates: Requirements 1.2, 6.2**

### Property 2: Health Score Calculation Consistency

*For any* set of coverage, validation, freshness, and completeness scores, the overall health score SHALL be a weighted average that is reproducible given the same inputs.

**Validates: Requirements 6.1**

### Property 3: Low Score Suggestions

*For any* health score below 80 (grade B), the system SHALL return at least one actionable suggestion for improvement.

**Validates: Requirements 6.3**

### Property 4: WebSocket Update on Change

*For any* spec file modification, the system SHALL emit a WebSocket message containing the updated spec data.

**Validates: Requirements 3.2**

### Property 5: Debounce Rapid Changes

*For any* sequence of N file changes within 500ms, the system SHALL emit at most 1 WebSocket update after the debounce period.

**Validates: Requirements 3.4**

### Property 6: Graph Filter Consistency

*For any* filter applied to the impact graph, the visible nodes SHALL be exactly those matching the filter criteria, and all edges between visible nodes SHALL remain visible.

**Validates: Requirements 2.5**

### Property 7: Tour Step Advancement

*For any* tour with N steps, completing step K SHALL advance the tour to step K+1, and completing step N SHALL end the tour.

**Validates: Requirements 10.3**

## Error Handling

| Error Scenario | Handling Strategy |
|----------------|-------------------|
| File watcher fails | Log error, continue with manual refresh |
| Health score calculation fails | Return default score with error flag |
| WebSocket disconnects | Auto-reconnect with exponential backoff |
| Demo setup fails | Show error with manual setup instructions |
| Hook generation fails | Log error, skip hook creation |
| Graph data too large | Paginate or cluster nodes |

## Testing Strategy

### Unit Tests

- Health score calculation with various inputs
- Letter grade mapping edge cases
- Debounce logic timing
- Hook configuration generation
- Graph data transformation

### Property-Based Tests

Using Hypothesis for Python property tests:

1. **Health Score Properties**: Test grade mapping and calculation consistency
2. **Debounce Properties**: Test that rapid changes are properly debounced
3. **Graph Filter Properties**: Test filter logic preserves graph integrity
4. **Tour Properties**: Test step advancement logic

### Integration Tests

- File watcher triggers re-indexing
- WebSocket updates reach UI
- Demo command creates complete environment
- Kiro hooks execute correctly

### UI Tests

- Dashboard renders with correct statistics
- Impact graph displays nodes and edges
- Tour mode highlights correct elements
- Quick actions execute and show results
