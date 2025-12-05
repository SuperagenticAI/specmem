# Design Document: Pragmatic Spec Lifecycle

## Overview

This feature implements spec lifecycle management tools that embody the "Pragmatic SDD" philosophy. It provides mechanisms to prune stale/orphaned specs, generate specs from existing code, and compress verbose specs. These tools address the "Markdown Madness" criticism by keeping specs lean, relevant, and maintainable.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Spec Lifecycle Engine                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Pruner    │  │  Generator  │  │ Compressor  │             │
│  │   Engine    │  │   Engine    │  │   Engine    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          │                                      │
│                   ┌──────▼──────┐                               │
│                   │   Health    │                               │
│                   │  Analyzer   │                               │
│                   └──────┬──────┘                               │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         │                │                │                     │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐             │
│  │ SpecImpact  │  │  Vector DB  │  │   Adapters  │             │
│  │   Graph     │  │   Store     │  │   (Kiro)    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Health Analyzer

Calculates spec health scores based on multiple factors.

```python
@dataclass
class SpecHealthScore:
    spec_id: str
    spec_path: Path
    score: float  # 0.0 to 1.0
    code_references: int
    last_modified: datetime
    query_count: int
    is_orphaned: bool
    is_stale: bool
    compression_ratio: float | None
    recommendations: list[str]

class HealthAnalyzer:
    def __init__(
        self,
        impact_graph: SpecImpactGraph,
        vector_store: VectorStore,
        stale_threshold_days: int = 90
    ): ...

    def analyze_spec(self, spec_id: str) -> SpecHealthScore: ...
    def analyze_all(self) -> list[SpecHealthScore]: ...
    def get_orphaned_specs(self) -> list[SpecHealthScore]: ...
    def get_stale_specs(self) -> list[SpecHealthScore]: ...
```

### 2. Pruner Engine

Handles spec archival and deletion.

```python
@dataclass
class PruneResult:
    spec_id: str
    spec_path: Path
    action: Literal["archived", "deleted", "skipped"]
    archive_path: Path | None
    reason: str

class PrunerEngine:
    def __init__(
        self,
        health_analyzer: HealthAnalyzer,
        vector_store: VectorStore,
        archive_dir: Path = Path(".specmem/archive")
    ): ...

    def analyze(self) -> list[SpecHealthScore]: ...
    def prune_orphaned(
        self,
        mode: Literal["archive", "delete"] = "archive",
        dry_run: bool = True,
        force: bool = False
    ) -> list[PruneResult]: ...
    def prune_by_name(
        self,
        spec_names: list[str],
        mode: Literal["archive", "delete"] = "archive",
        dry_run: bool = True,
        force: bool = False
    ) -> list[PruneResult]: ...
    def prune_stale(
        self,
        threshold_days: int = 90,
        mode: Literal["archive", "delete"] = "archive",
        dry_run: bool = True
    ) -> list[PruneResult]: ...
```

### 3. Generator Engine

Creates specs from existing code.

```python
@dataclass
class GeneratedSpec:
    source_files: list[Path]
    spec_name: str
    spec_path: Path
    content: str
    adapter_format: str
    metadata: dict[str, Any]

class GeneratorEngine:
    def __init__(
        self,
        adapters: list[SpecAdapter],
        default_format: str = "kiro"
    ): ...

    def generate_from_file(
        self,
        file_path: Path,
        spec_name: str | None = None
    ) -> GeneratedSpec: ...
    def generate_from_directory(
        self,
        dir_path: Path,
        group_by: Literal["file", "directory", "module"] = "directory"
    ) -> list[GeneratedSpec]: ...
    def extract_metadata(self, file_path: Path) -> dict[str, Any]: ...
```

### 4. Compressor Engine

Condenses verbose specs.

```python
@dataclass
class CompressedSpec:
    spec_id: str
    original_path: Path
    original_size: int
    compressed_content: str
    compressed_size: int
    compression_ratio: float
    preserved_criteria: list[str]

class CompressorEngine:
    def __init__(
        self,
        max_summary_tokens: int = 500,
        preserve_acceptance_criteria: bool = True
    ): ...

    def compress_spec(self, spec_id: str) -> CompressedSpec: ...
    def compress_all(
        self,
        threshold_ratio: float = 0.5
    ) -> list[CompressedSpec]: ...
    def get_verbose_specs(
        self,
        threshold_tokens: int = 2000
    ) -> list[str]: ...
```

## Data Models

### Spec Health Score Calculation

```python
def calculate_health_score(
    code_references: int,
    days_since_modified: int,
    query_count: int,
    stale_threshold: int = 90
) -> float:
    # Base score from code references (0-40 points)
    ref_score = min(code_references * 10, 40)

    # Freshness score (0-30 points)
    if days_since_modified <= 7:
        fresh_score = 30
    elif days_since_modified <= 30:
        fresh_score = 20
    elif days_since_modified <= stale_threshold:
        fresh_score = 10
    else:
        fresh_score = 0

    # Usage score (0-30 points)
    usage_score = min(query_count * 5, 30)

    return (ref_score + fresh_score + usage_score) / 100.0
```

### Archive Metadata

```python
@dataclass
class ArchiveMetadata:
    original_path: str
    archived_at: datetime
    reason: str
    health_score: float
    code_references: int
    can_restore: bool
```

## Error Handling

| Error | Handling |
|-------|----------|
| Spec not found | Raise `SpecNotFoundError` with spec name |
| Permission denied | Raise `PermissionError` with path |
| Archive directory full | Warn and suggest cleanup |
| Generation failed | Return partial results with errors |
| Compression failed | Skip spec and log warning |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Health Score Bounds
*For any* spec with any combination of code references, modification date, and query count, the calculated health score SHALL always be between 0.0 and 1.0 inclusive.
**Validates: Requirements 1.2**

### Property 2: Orphan Detection Consistency
*For any* set of specs and impact graph, a spec is identified as orphaned if and only if it has zero code references in the graph, and the orphaned count in the summary matches the actual count of orphaned specs.
**Validates: Requirements 1.1, 1.4**

### Property 3: Archive Preservation
*For any* archived spec, the archive SHALL contain the original content, preserve the directory structure, and include valid metadata with archived_at timestamp and original_path.
**Validates: Requirements 2.2**

### Property 4: Prune Index Consistency
*For any* pruned spec (archived or deleted), the vector store SHALL no longer contain embeddings for that spec after the prune operation completes.
**Validates: Requirements 2.4**

### Property 5: Dry Run Immutability
*For any* prune operation with dry_run=True, the file system and vector store SHALL remain unchanged after the operation.
**Validates: Requirements 2.5**

### Property 6: Explicit Prune Targeting
*For any* prune operation with explicit spec names, only the specified specs SHALL be affected and all other specs SHALL remain unchanged.
**Validates: Requirements 2.6, 2.7**

### Property 7: Generated Spec Validity
*For any* code file, the generated spec SHALL be valid markdown, contain the auto-generated marker in metadata, and conform to the configured adapter format.
**Validates: Requirements 3.1, 3.3, 3.4**

### Property 8: Compression Preserves Criteria
*For any* compressed spec, all acceptance criteria from the original spec SHALL be present in the compressed version, and the compressed size SHALL be less than or equal to the original size.
**Validates: Requirements 4.1, 4.2**

### Property 9: Compression Storage
*For any* spec that has been compressed, both the original and compressed versions SHALL be retrievable.
**Validates: Requirements 4.3**

### Property 10: Verbose Flagging Consistency
*For any* spec with compression ratio exceeding the configured threshold, the spec SHALL be flagged as verbose in health reports.
**Validates: Requirements 4.5**

## Testing Strategy

### Unit Tests
- Health score calculation with various inputs
- Pruner archive/delete operations
- Generator output format validation
- Compressor ratio calculations

### Property-Based Tests
- Use Hypothesis library for Python property-based testing
- Configure minimum 100 iterations per property test
- Each property test tagged with format: **Feature: pragmatic-spec-lifecycle, Property {number}: {property_text}**
