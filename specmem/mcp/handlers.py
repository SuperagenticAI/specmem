"""MCP Tool handlers for SpecMem.

Each handler implements the logic for a specific MCP tool,
connecting to the SpecMemClient for actual functionality.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from specmem.client import SpecMemClient


logger = logging.getLogger(__name__)


class ToolHandlers:
    """Handlers for SpecMem MCP tools.

    Each method handles a specific tool call, validating inputs
    and returning structured responses.
    """

    def __init__(self, client: SpecMemClient | None = None):
        """Initialize handlers with optional client.

        Args:
            client: SpecMemClient instance (can be set later via set_client)
        """
        self._client = client

    def set_client(self, client: SpecMemClient) -> None:
        """Set the SpecMemClient instance.

        Args:
            client: SpecMemClient to use for operations
        """
        self._client = client

    @property
    def client(self) -> SpecMemClient:
        """Get the client, raising if not initialized."""
        if self._client is None:
            raise RuntimeError("SpecMem not initialized. Run 'specmem init' first.")
        return self._client

    def is_initialized(self) -> bool:
        """Check if the client is initialized."""
        return self._client is not None

    async def handle_query(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle specmem_query tool call.

        Args:
            arguments: Tool arguments with 'query', optional 'top_k', 'include_legacy'

        Returns:
            Dict with 'results' list of matching specs
        """
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 10)
        include_legacy = arguments.get("include_legacy", False)

        if not query:
            return {
                "results": [],
                "message": "Empty query provided",
            }

        try:
            results = self.client.query(
                text=query,
                top_k=top_k,
                include_legacy=include_legacy,
            )

            if not results:
                return {
                    "results": [],
                    "message": f"No specifications found matching: {query}",
                }

            return {
                "results": [
                    {
                        "id": block.id,
                        "type": block.type.value,
                        "text": block.text[:500] + "..." if len(block.text) > 500 else block.text,
                        "source": block.source,
                        "pinned": block.pinned,
                        "tags": block.tags,
                    }
                    for block in results
                ],
                "count": len(results),
            }
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                "error": "query_failed",
                "message": str(e),
            }

    async def handle_impact(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle specmem_impact tool call.

        Args:
            arguments: Tool arguments with 'files' list, optional 'depth'

        Returns:
            Dict with 'specs' and 'tests' affected by the files
        """
        files = arguments.get("files", [])
        depth = arguments.get("depth", 2)

        if not files:
            return {
                "error": "no_files",
                "message": "No files provided for impact analysis",
            }

        # Validate file paths
        invalid_paths = []
        workspace_path = self.client.path
        for file_path in files:
            full_path = workspace_path / file_path
            if not full_path.exists():
                invalid_paths.append(file_path)

        if invalid_paths:
            return {
                "error": "invalid_paths",
                "paths": invalid_paths,
                "message": f"Invalid file paths: {', '.join(invalid_paths)}",
            }

        try:
            impact_set = self.client.get_impact_set(
                changed_files=files,
                depth=depth,
            )

            return {
                "specs": [
                    {
                        "id": node.id,
                        "confidence": node.confidence,
                    }
                    for node in impact_set.specs
                ],
                "tests": [
                    {
                        "id": node.id,
                        "confidence": node.confidence,
                        "framework": node.data.get("framework", "unknown"),
                    }
                    for node in impact_set.tests
                ],
                "message": impact_set.message,
            }
        except Exception as e:
            logger.error(f"Impact analysis failed: {e}")
            return {
                "error": "impact_failed",
                "message": str(e),
            }

    async def handle_context(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle specmem_context tool call.

        Args:
            arguments: Tool arguments with 'files' list, optional 'token_budget'

        Returns:
            Dict with context bundle including specs, designs, tldr
        """
        files = arguments.get("files", [])
        token_budget = arguments.get("token_budget", 4000)

        if not files:
            return {
                "error": "no_files",
                "message": "No files provided for context",
            }

        try:
            bundle = self.client.get_context_for_change(
                changed_files=files,
                token_budget=token_budget,
            )

            return {
                "specs": [
                    {
                        "id": spec.id,
                        "type": spec.type,
                        "title": spec.title,
                        "summary": spec.summary,
                        "relevance": spec.relevance,
                        "pinned": spec.pinned,
                    }
                    for spec in bundle.specs
                ],
                "designs": [
                    {
                        "id": design.id,
                        "type": design.type,
                        "title": design.title,
                        "summary": design.summary,
                        "relevance": design.relevance,
                    }
                    for design in bundle.designs
                ],
                "tldr": bundle.tldr,
                "total_tokens": bundle.total_tokens,
                "token_budget": bundle.token_budget,
            }
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return {
                "error": "context_failed",
                "message": str(e),
            }

    async def handle_tldr(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle specmem_tldr tool call.

        Args:
            arguments: Tool arguments with optional 'token_budget'

        Returns:
            Dict with 'summary' string
        """
        token_budget = arguments.get("token_budget", 500)

        try:
            tldr = self.client.get_tldr(token_budget=token_budget)

            return {
                "summary": tldr,
            }
        except Exception as e:
            logger.error(f"TL;DR generation failed: {e}")
            return {
                "error": "tldr_failed",
                "message": str(e),
            }


    @staticmethod
    def _summarize_guideline(guideline: Any) -> dict[str, Any]:
        """Serialize a Guideline for cue delivery responses."""
        content = guideline.content or ""
        summary = content[:300] + ("..." if len(content) > 300 else "")
        return {
            "id": guideline.id,
            "title": guideline.title,
            "source": guideline.source_file,
            "source_type": (
                guideline.source_type.value
                if hasattr(guideline.source_type, "value")
                else str(guideline.source_type)
            ),
            "file_pattern": guideline.file_pattern,
            "summary": summary,
        }

    def _resolve_cue(self, cue: str | None, files: list[str]) -> str:
        """Map optional cue + files to a delivery mode."""
        if cue in (None, ""):
            return "path" if files else "session_start"
        if cue in ("session_start", "event"):
            return "session_start"
        if cue == "path":
            return "path"
        # semantic / symbol / temporal: align vocabulary; fall back by files
        if files:
            return "path"
        return "session_start"

    async def handle_cues(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle specmem_cues tool call.

        Deterministic cue-anchored delivery of pinned / path-matched context
        without requiring the agent to invent a natural-language query.

        Args:
            arguments: Optional 'cue', 'files', 'token_budget', 'tldr_budget'

        Returns:
            Dict with cue, layers, and optional context / TL;DR fields
        """
        from specmem.guidelines.aggregator import GuidelinesAggregator

        files = arguments.get("files") or []
        if not isinstance(files, list):
            return {
                "error": "invalid_files",
                "message": "'files' must be a list of path strings",
            }

        cue_raw = arguments.get("cue")
        mode = self._resolve_cue(cue_raw, files)
        token_budget = arguments.get("token_budget", 4000)
        tldr_budget = arguments.get("tldr_budget", 500)

        if mode == "path" and not files:
            return {
                "error": "no_files",
                "message": "Path cue requires at least one file in 'files'",
            }

        try:
            aggregator = GuidelinesAggregator(self.client.path)
            layers = aggregator.build_context(
                files=files if mode == "path" else [],
                task=None,
            )
            layer_payload = {
                name: [self._summarize_guideline(g) for g in guidelines]
                for name, guidelines in layers.items()
            }

            if mode == "session_start":
                tldr = self.client.get_tldr(token_budget=tldr_budget)
                return {
                    "cue": cue_raw or "session_start",
                    "delivery": "cue_anchored",
                    "mode": "session_start",
                    "tldr": tldr,
                    "layers": layer_payload,
                    "message": (
                        "Harness-friendly session_start delivery: always-on "
                        "guidance plus TL;DR (no query required)"
                    ),
                }

            bundle = self.client.get_context_for_change(
                changed_files=files,
                token_budget=token_budget,
            )
            return {
                "cue": cue_raw or "path",
                "delivery": "cue_anchored",
                "mode": "path",
                "files": files,
                "layers": layer_payload,
                "specs": [
                    {
                        "id": spec.id,
                        "type": spec.type,
                        "title": spec.title,
                        "summary": spec.summary,
                        "relevance": spec.relevance,
                        "pinned": spec.pinned,
                    }
                    for spec in bundle.specs
                ],
                "designs": [
                    {
                        "id": design.id,
                        "type": design.type,
                        "title": design.title,
                        "summary": design.summary,
                        "relevance": design.relevance,
                    }
                    for design in bundle.designs
                ],
                "tldr": bundle.tldr,
                "total_tokens": bundle.total_tokens,
                "token_budget": bundle.token_budget,
                "message": (
                    bundle.message
                    or "Path-cue delivery: file-scoped guidelines plus context bundle"
                ),
            }
        except Exception as e:
            logger.error(f"Cue delivery failed: {e}")
            return {
                "error": "cues_failed",
                "message": str(e),
            }

    async def handle_coverage(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle specmem_coverage tool call.

        Args:
            arguments: Tool arguments with optional 'feature'

        Returns:
            Dict with coverage analysis results
        """
        feature = arguments.get("feature")

        try:
            coverage = self.client.get_coverage(feature=feature)

            return {
                "features": [
                    {
                        "name": f.name,
                        "total_criteria": f.total_criteria,
                        "covered_criteria": f.covered_criteria,
                        "coverage_percentage": f.coverage_percentage,
                    }
                    for f in coverage.features
                ],
                "suggestions": [
                    {
                        "criterion": s.criterion,
                        "suggested_test": s.suggested_test,
                        "priority": s.priority,
                    }
                    for s in coverage.suggestions
                ],
                "overall_coverage": coverage.coverage_percentage
                if hasattr(coverage, "coverage_percentage")
                else None,
            }
        except Exception as e:
            logger.error(f"Coverage analysis failed: {e}")
            return {
                "error": "coverage_failed",
                "message": str(e),
            }

    async def handle_validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle specmem_validate tool call.

        Args:
            arguments: Tool arguments with optional 'spec_id'

        Returns:
            Dict with validation results including errors and warnings
        """
        spec_id = arguments.get("spec_id")

        try:
            result = self.client.validate(spec_id=spec_id)

            return {
                "is_valid": result.is_valid,
                "specs_validated": result.specs_validated,
                "rules_run": result.rules_run,
                "errors": [
                    {
                        "rule": issue.rule,
                        "spec_id": issue.spec_id,
                        "message": issue.message,
                        "severity": issue.severity.value,
                    }
                    for issue in result.get_errors()
                ],
                "warnings": [
                    {
                        "rule": issue.rule,
                        "spec_id": issue.spec_id,
                        "message": issue.message,
                        "severity": issue.severity.value,
                    }
                    for issue in result.get_warnings()
                ],
                "duration_ms": result.duration_ms,
            }
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "error": "validation_failed",
                "message": str(e),
            }
