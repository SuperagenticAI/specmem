# Requirements Document

## Introduction

SpecMem is a unified, embeddable memory layer for AI coding agents built on top of Spec-Driven Development (SDD) metadata. It scans project specifications from various frameworks (Kiro, SpecKit, Tessl, Cursor, Claude Code, Factory, Windsurf, Warp, AMP, Codex), normalizes them into a canonical representation called SpecIR, indexes them using vector storage with deterministic memory for critical items, and outputs an optimized "Agent Experience Pack" that any coding agent can consume.

**The Killer Feature:** SpecMem creates a unified, normalized, agent-agnostic context layer for your project's specs. Coding agents can be swapped at any time (Cursor → Claude Code → Windsurf → Warp → Kiro → Factory → Codex) without losing context or rewriting spec files. This eliminates the fragmentation of maintaining separate Agent.md, Claude.md, cursor.json, warp.md, kiro/requirements.md, factory/spec.md files.

## Glossary

- **SpecMem**: The unified memory engine system being developed
- **SpecBlock**: The canonical data structure representing a single unit of specification knowledge
- **SpecIR**: Spec Intermediate Representation - the normalized internal format for all specifications
- **Adapter**: A modular component that reads specs from a specific framework and converts them to SpecIR
- **Agent Experience Pack (AgentXPack)**: The output bundle containing optimized memory for coding agents (stored in `.specmem/`)
- **Vector Memory**: Semantic search-enabled storage using embeddings for similarity retrieval
- **Deterministic Memory**: Pinned memory for critical items (constraints, rules) with guaranteed recall
- **Legacy Memory**: SpecBlocks marked as outdated, excluded from retrieval unless explicitly requested
- **LanceDB**: The default vector database backend for storing embeddings
- **AgentVectorDB**: Advanced vector database from Superagentic AI with deep integration support
- **SDD**: Spec-Driven Development - methodology using structured specification files
- **SpecImpact**: Module that maps code files to related specifications for targeted execution
- **VectorStore**: Abstract interface for pluggable vector database backends
- **Embedding Provider**: Service that converts text to vector embeddings (local or cloud-based)

## Requirements

### Requirement 1: Spec Ingestion via Adapters

**User Story:** As a developer, I want SpecMem to automatically detect and parse specification files from my project using modular adapters, so that I can build a unified memory without manual configuration.

#### Acceptance Criteria

1. WHEN SpecMem scans a repository THEN the System SHALL detect the presence of supported spec frameworks by checking for framework-specific file patterns
2. WHEN a Kiro project is detected (`.kiro/` directory with `requirements.md`, `design.md`, or `tasks.md`) THEN the System SHALL load and parse all Kiro specification files
3. WHEN parsing specification files THEN the System SHALL extract structured content including requirements, acceptance criteria, design decisions, and tasks
4. WHEN a spec file contains malformed content THEN the System SHALL log a warning and continue processing valid sections
5. WHEN multiple spec frameworks are detected in the same repository THEN the System SHALL process all detected frameworks and merge results into a unified SpecIR
6. WHEN implementing a new adapter THEN the Adapter SHALL conform to the SpecAdapter interface with `detect(repo_path) -> bool` and `load(repo_path) -> List[SpecBlock]` methods
7. WHEN SpecMem initializes THEN the System SHALL automatically discover and register all adapters in the `specmem/adapters/` directory
8. WHEN an adapter's `detect()` method returns true THEN the System SHALL invoke that adapter's `load()` method during scanning
9. WHEN an adapter encounters an error THEN the System SHALL catch the exception, log it, and continue with other adapters

### Requirement 2: Canonical Representation (SpecIR)

**User Story:** As a developer, I want all my specifications normalized into a consistent format, so that I can query and retrieve them uniformly regardless of their source.

#### Acceptance Criteria

1. WHEN a spec is ingested from any adapter THEN the System SHALL convert it to a SpecBlock with fields: id, type, text, source, status, tags, and links
2. WHEN creating a SpecBlock THEN the System SHALL assign a unique deterministic ID based on source file path and content hash
3. WHEN normalizing specs THEN the System SHALL categorize each block into one of these types: requirement, design, task, decision, knowledge, or md
4. WHEN a SpecBlock is created THEN the System SHALL set its status to "active" by default
5. WHEN validating a SpecBlock THEN the System SHALL reject blocks with empty text content or missing required fields
6. WHEN serializing SpecBlocks THEN the System SHALL produce valid JSON that can be deserialized back to equivalent SpecBlock objects
7. WHEN printing SpecBlocks THEN the System SHALL produce formatted output that can be parsed back to equivalent SpecBlock objects

### Requirement 3: Vector Memory Storage

**User Story:** As a developer, I want my specifications stored in a searchable vector database, so that I can perform semantic queries to find relevant context.

#### Acceptance Criteria

1. WHEN building memory THEN the System SHALL generate embeddings for each SpecBlock using the configured embedding provider
2. WHEN storing SpecBlocks THEN the System SHALL persist both the vector embeddings and the original content to the configured vector store
3. WHEN querying memory THEN the System SHALL return SpecBlocks ranked by semantic similarity to the query
4. WHEN the vector store is not initialized THEN the System SHALL create the necessary database schema automatically
5. WHEN LanceDB is configured as the backend THEN the System SHALL use LanceDB for vector storage operations
6. WHEN a different vector backend is configured (Chroma, Qdrant, SQLite-vec, AgentVectorDB) THEN the System SHALL use the specified backend through the VectorStore interface
7. WHEN AgentVectorDB is configured THEN the System SHALL use optimized schema and deep integration features

### Requirement 4: Deterministic Memory (Pinned Memory)

**User Story:** As a developer, I want critical specifications (constraints, architecture rules) to have guaranteed recall, so that important context is never missed due to similarity thresholds.

#### Acceptance Criteria

1. WHEN a SpecBlock is tagged as "pinned" THEN the System SHALL store it in deterministic memory with guaranteed retrieval
2. WHEN querying memory THEN the System SHALL always include pinned SpecBlocks in results regardless of similarity score
3. WHEN a requirement contains keywords "MUST", "SHALL", or "constraint" THEN the System SHALL automatically suggest pinning the block
4. WHEN deterministic memory is queried THEN the System SHALL return results in constant time without vector similarity computation

### Requirement 5: Memory Lifecycle Management

**User Story:** As a developer, I want to manage specification lifecycle states, so that outdated specs don't pollute my active context while remaining available for historical reference.

#### Acceptance Criteria

1. WHEN a SpecBlock is created THEN the System SHALL assign it the "active" lifecycle state
2. WHEN a user marks a SpecBlock as "deprecated" THEN the System SHALL update its status and include a deprecation warning in retrieval results
3. WHEN a user marks a SpecBlock as "legacy" THEN the System SHALL update its status and exclude it from standard retrieval
4. WHEN a user marks a SpecBlock as "obsolete" THEN the System SHALL update its status and exclude it from all retrieval including legacy queries
5. WHEN querying with the "include_legacy" flag THEN the System SHALL include legacy SpecBlocks in results
6. WHEN displaying memory statistics THEN the System SHALL show counts for each lifecycle state separately
7. WHEN a SpecBlock status changes THEN the System SHALL preserve the change in persistent storage

### Requirement 6: Memory Bank Processing

**User Story:** As a developer, I want SpecMem to intelligently chunk, rank, and score my specifications, so that the most relevant context is prioritized for agents.

#### Acceptance Criteria

1. WHEN processing large specification documents THEN the System SHALL chunk content into semantically coherent blocks
2. WHEN ranking SpecBlocks THEN the System SHALL compute relevance scores based on query similarity and structural importance
3. WHEN multiple SpecBlocks match a query THEN the System SHALL return results ordered by relevance score descending
4. WHEN building memory THEN the System SHALL attach lifecycle metadata to each chunk for filtering

### Requirement 7: Agent Experience Pack Output

**User Story:** As a developer, I want SpecMem to produce an optimized memory pack, so that any coding agent can consume my project's context without framework-specific configuration.

#### Acceptance Criteria

1. WHEN building an Agent Experience Pack THEN the System SHALL create a `.specmem/` directory containing `agent_memory.json`, `agent_context.md`, and `knowledge_index.json`
2. WHEN generating `agent_memory.json` THEN the System SHALL include all active SpecBlocks with their metadata, relationships, and relevance rankings
3. WHEN generating `agent_context.md` THEN the System SHALL produce a human-readable summary of the project's specifications
4. WHEN generating `knowledge_index.json` THEN the System SHALL create a searchable index mapping keywords to SpecBlock IDs
5. WHEN the `.specmem/` directory already exists THEN the System SHALL update existing files while preserving user modifications to `agent_context.md`
6. WHEN generating the pack THEN the System SHALL include top-ranked chunks and structural dependencies
7. WHEN optimizing for context windows THEN the System SHALL compress and prioritize content based on agent requirements

### Requirement 8: Command Line Interface

**User Story:** As a developer, I want to interact with SpecMem through a CLI, so that I can integrate it into my development workflow and automation scripts.

#### Acceptance Criteria

1. WHEN running `specmem init` THEN the System SHALL create a configuration file with default settings in the current directory
2. WHEN running `specmem scan` THEN the System SHALL detect spec frameworks, parse files, and display a summary of discovered specifications
3. WHEN running `specmem build` THEN the System SHALL process all specs, build vector memory, and generate the Agent Experience Pack
4. WHEN running `specmem info` THEN the System SHALL display memory statistics including block counts by type, status, and source
5. WHEN running `specmem query "<question>"` THEN the System SHALL search memory and return relevant SpecBlocks matching the query
6. WHEN a CLI command fails THEN the System SHALL display a descriptive error message and exit with a non-zero status code
7. WHEN running any command with `--verbose` flag THEN the System SHALL display detailed progress information
8. WHEN running commands THEN the CLI SHALL delegate all business logic to core modules

### Requirement 9: SpecImpact Dependency Analyzer

**User Story:** As a developer, I want to understand which specifications are affected by code changes, so that I can focus on relevant context during development.

#### Acceptance Criteria

1. WHEN running `specmem impact` THEN the System SHALL detect changed files in the repository
2. WHEN analyzing impact THEN the System SHALL map changed code files to related SpecIR blocks
3. WHEN displaying impact results THEN the System SHALL produce a targeted list of specifications requiring attention
4. WHEN a code file has no mapped specifications THEN the System SHALL indicate the file is not covered by specs

### Requirement 10: Embedding Configuration

**User Story:** As a developer, I want to configure embedding providers, so that I can choose between local processing and cloud-based services based on my needs.

#### Acceptance Criteria

1. WHEN local embeddings are configured THEN the System SHALL use SentenceTransformers for generating embeddings
2. WHEN cloud embeddings are configured (OpenAI, Anthropic, Gemini, Together) THEN the System SHALL use the specified provider's API
3. WHEN switching embedding providers THEN the System SHALL re-index existing SpecBlocks with the new provider
4. WHEN an embedding provider is unavailable THEN the System SHALL fall back to local embeddings and log a warning

### Requirement 11: Configuration Management

**User Story:** As a developer, I want to configure SpecMem's behavior through a config file, so that I can customize embedding providers, vector backends, and other settings.

#### Acceptance Criteria

1. WHEN a `.specmem.toml` or `.specmem.json` config file exists THEN the System SHALL load settings from that file
2. WHEN no config file exists THEN the System SHALL use default settings (LanceDB backend, local SentenceTransformers embeddings)
3. WHEN config specifies a vector backend THEN the System SHALL use that backend for storage operations
4. WHEN config specifies an embedding provider THEN the System SHALL use that provider for generating embeddings
5. WHEN config contains invalid values THEN the System SHALL report validation errors and use defaults for invalid fields

### Requirement 12: Living Documentation Generator

**User Story:** As a developer, I want SpecMem to generate living documentation from my specifications, so that I have always up-to-date project documentation.

#### Acceptance Criteria

1. WHEN generating living docs THEN the System SHALL output Markdown summaries organized by specification type
2. WHEN generating docs THEN the System SHALL include links to source SpecIR blocks
3. WHEN specifications change THEN the System SHALL regenerate affected documentation sections
4. WHEN displaying docs THEN the System SHALL show specification relationships and dependencies

### Requirement 13: Query API (Future)

**User Story:** As an agent developer, I want to query SpecMem programmatically, so that I can integrate specification context into agent workflows.

#### Acceptance Criteria

1. WHEN `specmem serve` is running THEN the System SHALL expose a REST API for memory queries
2. WHEN an API query is received THEN the System SHALL return relevant SpecBlocks in JSON format
3. WHEN streaming is requested THEN the System SHALL provide streaming context responses for large result sets

### Requirement 14: Web UI (Future)

**User Story:** As a developer, I want a web interface to browse and manage my specification memory, so that I can visualize and interact with my project's knowledge.

#### Acceptance Criteria

1. WHEN the UI is launched THEN the System SHALL display structured memory organized by type and status
2. WHEN filtering memory THEN the UI SHALL support filtering by active vs legacy status
3. WHEN viewing history THEN the UI SHALL show diff view of specification changes over time
4. WHEN exporting THEN the UI SHALL allow exporting Agent Experience Packs
5. WHEN searching THEN the UI SHALL provide semantic search across all knowledge
