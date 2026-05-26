# 📋 Changelog

All notable changes to SpecMem are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- N/A

### Changed
- N/A

### Fixed
- N/A

---

## [0.2.0] - 2026-05-26

### Added

- **Optimized Skills** - Validate and index improved agent skill artifacts
  - `specmem guidelines optimize` - Generate or promote optimized skill candidates
  - `specmem guidelines score-skill` - Run static quality checks for skills
  - `specmem guidelines optimized-status` - Show raw, optimized, stale, rejected, and invalid artifact states
  - `specmem build --optimize-skills` - Use accepted optimized skill artifacts during memory indexing
- Optimized skill artifact storage under `.specmem/skillopt/`
- Provenance tags for optimized skill memory blocks
- Public Python APIs for optimized skill artifact management
- User, CLI, API, and advanced memory-pattern documentation for optimized skills

### Changed

- Agent guidance indexing can opt into accepted optimized skill content while default builds keep indexing source skills.

### Fixed

- Aligned package version metadata across `pyproject.toml`, `uv.lock`, and `specmem.__version__`.
- Avoided same-file candidate copy failures during generated skill promotion.

---

## [0.1.1] - 2026-05-26

### Added

- Spec Coverage Analysis commands and docs.
- Documentation site, API reference, and advanced configuration guide.

### Changed

- Improved CLI error messages.

### Fixed

- Memory handling improvements for large spec collections.

---

## [0.1.0] - 2025-12-01

### 🎉 Initial Release

First public release of SpecMem - Cognitive Memory Layer for AI Coding Agents.

### Added

#### Core Features
- **SpecIR Format** - Canonical specification representation
- **Memory Bank** - Vector-based specification storage
- **Impact Graph** - Bidirectional relationship tracking
- **SpecDiff Timeline** - Temporal spec intelligence
- **SpecValidator** - Specification quality assurance

#### Adapters
- Kiro adapter (`.kiro/specs/`)
- Cursor adapter (`cursor.json`, `.cursorrules`)
- Claude Code adapter (`Claude.md`, `CLAUDE.md`)
- SpecKit adapter (`.speckit/`)
- Tessl adapter (`.tessl/`)

#### Vector Stores
- LanceDB (default, embedded)
- ChromaDB support
- Qdrant support

#### Embedding Providers
- Local embeddings (sentence-transformers)
- OpenAI embeddings
- Google embeddings
- Together AI embeddings

#### CLI Commands
- `specmem init` - Initialize project
- `specmem scan` - Scan specifications
- `specmem build` - Build agent pack
- `specmem query` - Search specifications
- `specmem impact` - Analyze change impact
- `specmem validate` - Validate specifications
- `specmem serve` - Start web UI

#### Python API
- `SpecMemClient` - Main client class
- `MemoryBank` - Specification storage
- `ImpactGraph` - Relationship graph
- Full type hints and documentation

#### Web UI
- Dashboard with spec overview
- Semantic search interface
- Interactive impact graph
- Timeline visualization
- Validation results viewer

### Technical Details
- Python 3.11+ support
- Apache 2.0 license
- Property-based testing with Hypothesis
- 70%+ code coverage
- Full type annotations

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.2.0 | 2026-05-26 | Optimized Skills |
| 0.1.1 | 2026-05-26 | Spec Coverage and documentation |
| 0.1.0 | 2025-12-01 | Initial release |

## Upgrade Guide

### From Pre-release to 0.1.0

If you were using a pre-release version:

1. Update your installation:
   ```bash
   pip install --upgrade specmem
   ```

2. Re-initialize your project:
   ```bash
   specmem init --force
   ```

3. Re-scan specifications:
   ```bash
   specmem scan --force
   ```

4. Rebuild the agent pack:
   ```bash
   specmem build
   ```

## Deprecation Policy

- Features are deprecated for at least one minor version before removal
- Deprecated features emit warnings
- Migration guides are provided for breaking changes

## Reporting Issues

Found a bug? Please [open an issue](https://github.com/Shashikant86/specmem/issues/new).

Include:
- SpecMem version (`specmem --version`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
