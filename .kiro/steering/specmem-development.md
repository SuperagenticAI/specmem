---
inclusion: always
---

# SpecMem Development Guidelines

## Project Overview

SpecMem is a cognitive memory layer for AI coding agents. It indexes specifications from `.kiro/specs/` and makes them searchable via semantic search and MCP tools.

## Key Commands

- `specmem demo` - Launch the web dashboard
- `specmem query "search term"` - Search specifications
- `specmem cov` - Check spec coverage
- `specmem health` - Check spec health scores
- `specmem build` - Build the memory index

## Architecture

- **Adapters**: Load specs from different formats (Kiro, Claude, Cursor)
- **VectorDB**: Store embeddings (LanceDB, Chroma, Qdrant)
- **Coverage**: Map acceptance criteria to tests
- **Graph**: Track spec-code-test relationships

## Testing

- Property-based tests in `tests/property/`
- Unit tests in `tests/unit/`
- Run with `pytest tests/`

## MCP Tools Available

When using SpecMem MCP server:
- `specmem_query` - Search specs by natural language
- `specmem_impact` - Find affected specs for file changes
- `specmem_context` - Get optimized context bundle
- `specmem_tldr` - Get summary of key specs
- `specmem_coverage` - Analyze spec coverage
- `specmem_validate` - Validate spec quality
