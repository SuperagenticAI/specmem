# Design Document: SpecMem Web UI

## Overview

The SpecMem Web UI is a lightweight web dashboard that provides visual access to the SpecMem memory layer. It consists of a FastAPI backend serving a REST API and static frontend assets, with a React + Tailwind CSS frontend for the user interface. The UI is launched via `specmem serve` and enables developers to browse, filter, search, and export their project's specification memory.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        specmem serve                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐     ┌──────────────────────────────────┐  │
│  │   FastAPI App    │     │      React Frontend              │  │
│  │                  │     │                                  │  │
│  │  /api/blocks     │◄────│  Dashboard Component             │  │
│  │  /api/stats      │     │  ├── SummaryCard                 │  │
│  │  /api/search     │     │  ├── BlockList                   │  │
│  │  /api/pinned     │     │  ├── FilterBar                   │  │
│  │  /api/export     │     │  ├── SearchBox                   │  │
│  │  /api/ws         │     │  ├── StatsPanel                  │  │
│  │                  │     │  └── BlockDetail                 │  │
│  └────────┬─────────┘     └──────────────────────────────────┘  │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    SpecMem Core                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │   │
│  │  │ MemoryBank  │  │ VectorStore │  │ PackBuilder     │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Backend Components

#### 1. WebServer (specmem/ui/server.py)

```python
class WebServer:
    """FastAPI-based web server for SpecMem UI."""

    def __init__(self, config: SpecMemConfig, port: int = 8765):
        self.config = config
        self.port = port
        self.app = FastAPI(title="SpecMem UI")
        self._setup_routes()
        self._setup_static_files()

    def start(self) -> None:
        """Start the web server."""

    def stop(self) -> None:
        """Gracefully stop the server."""
```

#### 2. API Router (specmem/ui/api.py)

```python
# REST API Endpoints
GET  /api/blocks          # List all blocks with optional filters
GET  /api/blocks/{id}     # Get single block details
GET  /api/stats           # Get memory statistics
GET  /api/search          # Semantic search
GET  /api/pinned          # Get all pinned blocks
POST /api/export          # Trigger pack export
WS   /api/ws              # WebSocket for live updates
```

#### 3. API Models (specmem/ui/models.py)

```python
class BlockListResponse(BaseModel):
    blocks: List[BlockSummary]
    total: int
    active_count: int
    legacy_count: int

class BlockSummary(BaseModel):
    id: str
    type: str
    text_preview: str  # Truncated to 200 chars
    source: str
    status: str
    pinned: bool

class BlockDetail(BaseModel):
    id: str
    type: str
    text: str  # Full text
    source: str
    status: str
    pinned: bool
    tags: List[str]
    links: List[str]

class StatsResponse(BaseModel):
    total_blocks: int
    active_count: int
    legacy_count: int
    pinned_count: int
    by_type: Dict[str, int]
    by_source: Dict[str, int]
    memory_size_bytes: int

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str

class SearchResult(BaseModel):
    block: BlockSummary
    score: float

class ExportResponse(BaseModel):
    success: bool
    output_path: str
    message: str
```

### Frontend Components

#### 1. Dashboard Layout
- Header with SpecMem branding and dark mode toggle
- Sidebar with navigation (Dashboard, Search, Pinned, Stats)
- Main content area with responsive grid

#### 2. Component Hierarchy
```
App
├── Header
│   ├── Logo
│   ├── DarkModeToggle
│   └── ExportButton
├── Sidebar
│   └── NavLinks
└── MainContent
    ├── SummaryCards (total, active, legacy, pinned)
    ├── FilterBar
    │   ├── StatusFilter (All/Active/Legacy)
    │   └── TypeFilter (All/Requirement/Design/Task/...)
    ├── SearchBox
    ├── BlockList
    │   └── BlockCard (repeating)
    └── BlockDetailModal
```

#### 3. State Management
- React Query for server state (API calls with caching)
- Local state for UI filters and selections
- WebSocket connection for live updates

## Data Models

### API Request/Response Flow

```
Frontend                    Backend                     Core
   │                           │                          │
   │  GET /api/blocks?         │                          │
   │  status=active&type=req   │                          │
   │ ─────────────────────────►│                          │
   │                           │  memory_bank.get_blocks()│
   │                           │ ────────────────────────►│
   │                           │◄────────────────────────│
   │                           │  List[SpecBlock]         │
   │◄─────────────────────────│                          │
   │  BlockListResponse        │                          │
   │                           │                          │
   │  GET /api/search?q=auth   │                          │
   │ ─────────────────────────►│                          │
   │                           │  vector_store.query()    │
   │                           │ ────────────────────────►│
   │                           │◄────────────────────────│
   │◄─────────────────────────│                          │
   │  SearchResponse           │                          │
```

### Filter Logic

```python
def filter_blocks(
    blocks: List[SpecBlock],
    status: Optional[str] = None,
    block_type: Optional[str] = None
) -> List[SpecBlock]:
    """Apply filters with AND logic."""
    result = blocks
    if status and status != "all":
        result = [b for b in result if b.status == status]
    if block_type and block_type != "all":
        result = [b for b in result if b.type == block_type]
    return result
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Server Port Configuration
*For any* valid port number between 1024 and 65535, when the server is started with that port, it SHALL listen on exactly that port.
**Validates: Requirements 1.1, 1.3**

### Property 2: Block Response Completeness
*For any* SpecBlock in the memory bank, when serialized for API response, the response SHALL contain all required fields: id, type, text (or text_preview), source, status, and pinned indicator.
**Validates: Requirements 2.3**

### Property 3: Text Truncation Consistency
*For any* SpecBlock with text longer than 200 characters, the text_preview field SHALL be exactly 200 characters followed by ellipsis, and the full text SHALL be available in the detail endpoint.
**Validates: Requirements 2.4**

### Property 4: Filter Correctness
*For any* set of SpecBlocks and any combination of status and type filters, the filtered result SHALL contain only blocks that match ALL specified filter criteria (AND logic), and the count SHALL equal the length of the filtered list.
**Validates: Requirements 3.2, 3.3, 3.4, 3.5, 4.2, 4.3, 4.4**

### Property 5: Search Result Ordering
*For any* search query that returns results, the results SHALL be ordered by descending relevance score, and each result SHALL include a non-negative score value.
**Validates: Requirements 5.3, 5.4**

### Property 6: Pinned Block Retrieval
*For any* set of SpecBlocks where some are pinned, the pinned endpoint SHALL return exactly all blocks with pinned=True, and each SHALL include the pinned indicator.
**Validates: Requirements 6.1, 6.3**

### Property 7: Statistics Accuracy
*For any* set of SpecBlocks, the statistics endpoint SHALL return counts that exactly match: total = len(blocks), active_count = count where status="active", legacy_count = count where status="legacy", and by_type counts SHALL sum to total.
**Validates: Requirements 2.1, 8.1, 8.2**

## Error Handling

### HTTP Error Responses

| Status Code | Scenario | Response |
|-------------|----------|----------|
| 400 | Invalid filter parameter | `{"error": "Invalid status filter: xyz"}` |
| 404 | Block not found | `{"error": "Block not found: {id}"}` |
| 500 | Internal error | `{"error": "Internal server error", "detail": "..."}` |
| 503 | Memory not initialized | `{"error": "SpecMem not initialized. Run 'specmem build' first."}` |

### Port Conflict Handling

```python
def find_available_port(preferred: int, max_attempts: int = 10) -> int:
    """Find an available port starting from preferred."""
    for offset in range(max_attempts):
        port = preferred + offset
        if is_port_available(port):
            return port
    raise PortNotAvailableError(f"No available port found near {preferred}")
```

## Testing Strategy

### Dual Testing Approach

#### Unit Tests
- Test API endpoint handlers with mocked MemoryBank
- Test filter logic with various input combinations
- Test response serialization
- Test port availability checking

#### Property-Based Tests (Hypothesis)
- Use Hypothesis to generate random SpecBlock sets
- Test filter properties hold for all generated inputs
- Test statistics accuracy for all generated inputs
- Test search result ordering invariants

### Property-Based Testing Framework
- Library: **Hypothesis** (already in project dependencies)
- Minimum iterations: 100 per property
- Test annotation format: `# **Feature: specmem-web-ui, Property {N}: {description}**`

### Test Structure
```
tests/
├── unit/
│   └── test_ui_api.py       # API endpoint unit tests
└── property/
    └── test_ui_props.py     # Property-based tests for UI backend
```
