# Changelog

All notable changes to SpecMem will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- First-class AGENTS.md SpecAdapter (AAIF / Linux Foundation standard). Detects
  `AGENTS.md` / `AGENT.md` at the repo root or nested, splits on markdown
  headings into knowledge SpecBlocks, and is marked stable (not experimental).

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.2.2] - 2026-06-04

### Changed
- Relicensed from AGPL-3.0-or-later to Apache-2.0.

### Fixed
- `specmem version` and `specmem.__version__` reported `0.2.0` regardless of the
  installed release. `__version__` is now derived from the installed package
  metadata, so it always matches the released version and cannot drift from
  `pyproject.toml`.

## [0.2.1] - 2026-06-04

### Fixed
- `specmem build` and `specmem query` raised a `TypeError` when using a cloud
  embedding provider or an alternative vector store (Qdrant, Chroma) without the
  `local` extra installed. The embedding provider factory is now always exported,
  so these commands work without `specmem[local]`.
- `specmem graph impact` crashed with `AttributeError: 'SpecBlock' object has no
  attribute 'title'`. Impact analysis now derives a title from the spec text and
  works again.
- `specmem query` ranking: pinned spec blocks were injected with an artificial
  perfect score and pushed the most relevant results out of the list. Query
  results are now ranked purely by semantic similarity.
- `specmem validate` ignored the validation settings in `.specmem.toml` because it
  read a non-existent attribute. Validation rules from the config file are now
  applied.

## [0.2.0] - 2026-05-26

### Added
- Optimized skill artifacts for `.codex/skills/*/SKILL.md` and `.claude/skills/*/SKILL.md`.
- `specmem guidelines optimize` for promoting a candidate skill or generating one from an instruction.
- `specmem guidelines score-skill` for static skill quality checks.
- `specmem guidelines optimized-status` for raw, optimized, stale, rejected, and invalid artifact states.
- `specmem build --optimize-skills` to index accepted optimized skill artifacts.
- Optimized skill provenance tags in indexed memory blocks.
- Public `specmem.guidelines` optimized-skill APIs.
- User, CLI, API, and memory-pattern documentation for optimized skills.

### Changed
- Agent guidance indexing can now opt into accepted optimized skill content while keeping default builds unchanged.

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- Fixed package version mismatch between `pyproject.toml`, lockfile metadata, and `specmem.__version__`.
- Prevented generated candidates from being copied over themselves during promotion.

### Security
- N/A

## [0.1.0] - 2025-12-01

### Added
- Initial public release
- Developed as part of the Kiroween Hackathon, December 2025
- IP of Superagentic AI

[Unreleased]: https://github.com/Shashikant86/specmem/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Shashikant86/specmem/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Shashikant86/specmem/releases/tag/v0.1.0
