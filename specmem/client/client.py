"""SpecMemClient - Main client class for agent integration."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specmem.adapters import detect_adapters
from specmem.client.exceptions import ConfigurationError, MemoryStoreError
from specmem.client.models import (
    ContextBundle,
    HookSummary,
    Proposal,
    SpecSummary,
    SteeringSummary,
)
from specmem.client.proposals import ProposalStore
from specmem.context import TokenEstimator
from specmem.core.config import SpecMemConfig
from specmem.core.memory_bank import MemoryBank
from specmem.core.specir import SpecBlock, SpecStatus, SpecType
from specmem.diff import SpecDiff
from specmem.diff.models import (
    Contradiction,
    Deprecation,
    DriftReport,
    SpecChange,
    SpecVersion,
    StalenessWarning,
)
from specmem.impact import GraphBuilder, ImpactSet, SpecImpactGraph


# Optional: local embeddings (requires specmem[local])
try:
    from specmem.vectordb import LanceDBStore, get_embedding_provider

    _HAS_LOCAL = True
except ImportError:
    _HAS_LOCAL = False
    LanceDBStore = None  # type: ignore
    get_embedding_provider = None  # type: ignore


if TYPE_CHECKING:
    from specmem.validator import ValidationIssue, ValidationResult


logger = logging.getLogger(__name__)


class SpecMemClient:
    """Python client for SpecMem agent integration.

    Provides a simple API for coding agents to:
    - Get context bundles for code changes
    - Query impacted specifications
    - Propose and manage spec edits
    - Access TL;DR summaries

    Example:
        from specmem import SpecMemClient

        sm = SpecMemClient()
        bundle = sm.get_context_for_change(["auth/service.py"])
        print(bundle.tldr)
    """

    DEFAULT_TOKEN_BUDGET = 4000
    DEFAULT_TLDR_BUDGET = 500

    def __init__(
        self,
        path: str | Path = ".",
        config_path: str | Path | None = None,
    ) -> None:
        """Initialize the SpecMem client.

        Args:
            path: Repository path (default: current directory)
            config_path: Optional path to config file

        Raises:
            ConfigurationError: If configuration is invalid
            MemoryStoreError: If memory store cannot be initialized
        """
        self.path = Path(path).resolve()
        self._config: SpecMemConfig | None = None
        self._memory_bank: MemoryBank | None = None
        self._proposal_store: ProposalStore | None = None
        self._token_estimator = TokenEstimator()
        self._blocks: list[SpecBlock] = []
        self._graph: SpecImpactGraph | None = None
        self._specdiff: SpecDiff | None = None

        # Load configuration
        self._load_config(config_path)

        # Initialize memory store
        self._initialize_store()

        logger.debug(f"SpecMemClient initialized for {self.path}")

    def _load_config(self, config_path: str | Path | None) -> None:
        """Load configuration from file."""
        try:
            if config_path:
                self._config = SpecMemConfig.load(Path(config_path))
            else:
                # Try to load from default locations
                default_path = self.path / ".specmem.toml"
                if default_path.exists():
                    self._config = SpecMemConfig.load(default_path)
                else:
                    self._config = SpecMemConfig()
            logger.debug(f"Loaded config: {self._config}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e

    def _initialize_store(self) -> None:
        """Initialize the memory store."""
        if not _HAS_LOCAL:
            raise MemoryStoreError(
                "Local embeddings not available. Install with: pip install specmem[local]"
            )

        try:
            # Create .specmem directory if needed
            specmem_dir = self.path / ".specmem"
            specmem_dir.mkdir(parents=True, exist_ok=True)

            # Initialize vector store
            db_path = specmem_dir / "vectordb"
            vector_store = LanceDBStore(db_path=str(db_path))
            vector_store.initialize()

            # Initialize embedding provider
            embedding_provider = get_embedding_provider(
                provider=self._config.embedding.provider,
                model=self._config.embedding.model,
                api_key=self._config.embedding.get_api_key(),
            )

            # Create memory bank
            self._memory_bank = MemoryBank(vector_store, embedding_provider)
            self._memory_bank.initialize()

            # Initialize proposal store
            self._proposal_store = ProposalStore(specmem_dir)

            # Load existing specs
            self._load_specs()

            logger.debug("Memory store initialized")
        except Exception as e:
            raise MemoryStoreError(f"Failed to initialize memory store: {e}") from e

    def _load_specs(self) -> None:
        """Load specs from adapters."""
        detected = detect_adapters(str(self.path))

        for adapter in detected:
            try:
                blocks = adapter.load(str(self.path))
                self._blocks.extend(blocks)
                logger.debug(f"Loaded {len(blocks)} blocks from {adapter.name}")
            except Exception as e:
                logger.warning(f"Failed to load from {adapter.name}: {e}")

        # Add to memory bank if we have blocks
        if self._blocks and self._memory_bank:
            self._memory_bank.add_blocks(self._blocks)

    def get_context_for_change(
        self,
        changed_files: list[str],
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        format: str = "json",
    ) -> ContextBundle:
        """Get optimized context bundle for changed files.

        Args:
            changed_files: List of changed file paths
            token_budget: Maximum tokens for the bundle
            format: Output format (json, markdown)

        Returns:
            ContextBundle with specs, designs, tests, steering, hooks, and TL;DR
        """
        if not changed_files:
            return ContextBundle(
                token_budget=token_budget,
                message="No changed files provided",
            )

        # Find relevant specs
        relevant_blocks = self._find_relevant_blocks(changed_files)

        # Categorize blocks
        specs = []
        designs = []

        for block, score in relevant_blocks:
            summary = SpecSummary(
                id=block.id,
                type=block.type.value,
                title=self._extract_title(block.text),
                summary=self._truncate_text(block.text, 200),
                source=block.source,
                relevance=score,
                pinned=block.pinned,
            )

            if block.type in (SpecType.REQUIREMENT, SpecType.TASK, SpecType.KNOWLEDGE):
                specs.append(summary)
            elif block.type in (SpecType.DESIGN, SpecType.DECISION):
                designs.append(summary)
            else:
                specs.append(summary)

        # Get applicable steering files
        steering = self._get_steering_for_files(changed_files)

        # Get triggered hooks
        triggered_hooks = self._get_hooks_for_files(changed_files)

        # Generate TL;DR
        tldr = self._generate_tldr(specs + designs, self.DEFAULT_TLDR_BUDGET)

        # Calculate tokens
        total_tokens = self._estimate_bundle_tokens(specs, designs, tldr)

        # Add steering tokens
        for s in steering:
            total_tokens += self._token_estimator.count_tokens(s.content)

        # Truncate if over budget
        while total_tokens > token_budget and (specs or designs):
            if designs and (not specs or designs[-1].relevance < specs[-1].relevance):
                designs.pop()
            elif specs:
                specs.pop()
            total_tokens = self._estimate_bundle_tokens(specs, designs, tldr)
            for s in steering:
                total_tokens += self._token_estimator.count_tokens(s.content)

        # Build message if no specs found
        message = ""
        if not relevant_blocks and not steering:
            message = "No related specifications or steering found for the changed files"

        return ContextBundle(
            specs=specs,
            designs=designs,
            tests=[],  # TODO: Add test mappings
            steering=steering,
            triggered_hooks=triggered_hooks,
            tldr=tldr,
            total_tokens=total_tokens,
            token_budget=token_budget,
            changed_files=changed_files,
            message=message,
        )

    def get_impacted_specs(
        self,
        changed_files: list[str] | None = None,
        git_diff: str | None = None,
    ) -> list[SpecBlock]:
        """Get specs impacted by code changes.

        Uses the SpecImpact graph for traversal-based impact analysis.

        Args:
            changed_files: List of changed file paths
            git_diff: Git diff string to parse

        Returns:
            List of impacted SpecBlock objects, ranked by relevance
        """
        files = changed_files or []

        # Parse git diff if provided
        if git_diff:
            files.extend(self._parse_git_diff(git_diff))

        if not files:
            return []

        # Use SpecImpact graph for traversal
        try:
            impact_set = self.get_impact_set(files)

            # Map graph nodes back to SpecBlocks
            impacted = []
            spec_ids = {node.id.replace("spec:", "") for node in impact_set.specs}

            for block in self._blocks:
                if block.id in spec_ids:
                    impacted.append(block)

            return impacted
        except Exception as e:
            logger.warning(f"SpecImpact graph analysis failed: {e}")

            # Fallback to semantic search
            relevant = self._find_relevant_blocks(files)
            return [block for block, _ in relevant]

    def query(
        self,
        text: str,
        top_k: int = 10,
        include_legacy: bool = False,
    ) -> list[SpecBlock]:
        """Query specs by natural language.

        Args:
            text: Natural language query
            top_k: Maximum number of results
            include_legacy: Whether to include legacy specs

        Returns:
            List of matching SpecBlock objects
        """
        if not self._memory_bank:
            return []

        results = self._memory_bank.query(
            query_text=text,
            top_k=top_k,
            include_legacy=include_legacy,
            include_pinned=True,
        )

        # Sort: pinned first, then by score
        blocks = [(r.block, r.score) for r in results]
        blocks.sort(key=lambda x: (not x[0].pinned, -x[1]))

        return [block for block, _ in blocks[:top_k]]

    def propose_edit(
        self,
        spec_id: str,
        edits: dict[str, Any],
        rationale: str,
    ) -> Proposal:
        """Propose an edit to a specification.

        Args:
            spec_id: ID of the spec to edit
            edits: Dictionary of proposed changes
            rationale: Explanation for the changes

        Returns:
            Created Proposal object
        """
        return self._proposal_store.create(spec_id, edits, rationale)

    def accept_proposal(self, proposal_id: str) -> bool:
        """Accept a pending proposal.

        Args:
            proposal_id: Proposal ID

        Returns:
            True if accepted
        """
        return self._proposal_store.accept(proposal_id)

    def reject_proposal(self, proposal_id: str) -> bool:
        """Reject a pending proposal.

        Args:
            proposal_id: Proposal ID

        Returns:
            True if rejected
        """
        return self._proposal_store.reject(proposal_id)

    def list_proposals(
        self,
        status: str | None = None,
    ) -> list[Proposal]:
        """List proposals.

        Args:
            status: Filter by status (pending, accepted, rejected)

        Returns:
            List of proposals
        """
        from specmem.client.models import ProposalStatus

        status_enum = ProposalStatus(status) if status else None
        return self._proposal_store.list(status=status_enum)

    def get_tldr(self, token_budget: int = DEFAULT_TLDR_BUDGET) -> str:
        """Get TL;DR summary of key specs.

        Args:
            token_budget: Maximum tokens for summary

        Returns:
            Concise summary string
        """
        if not self._blocks:
            return "No specifications found in memory."

        # Get pinned and high-relevance specs
        pinned = [b for b in self._blocks if b.pinned and b.status == SpecStatus.ACTIVE]
        active = [b for b in self._blocks if not b.pinned and b.status == SpecStatus.ACTIVE]

        summaries = []
        for block in pinned[:5]:
            summaries.append(
                SpecSummary(
                    id=block.id,
                    type=block.type.value,
                    title=self._extract_title(block.text),
                    summary=self._truncate_text(block.text, 100),
                    source=block.source,
                    pinned=True,
                )
            )

        for block in active[:10]:
            summaries.append(
                SpecSummary(
                    id=block.id,
                    type=block.type.value,
                    title=self._extract_title(block.text),
                    summary=self._truncate_text(block.text, 100),
                    source=block.source,
                    pinned=False,
                )
            )

        return self._generate_tldr(summaries, token_budget)

    def list_specs(
        self,
        status: str | None = None,
        type: str | None = None,
    ) -> list[SpecBlock]:
        """List all specs with optional filters.

        Args:
            status: Filter by status (active, deprecated, legacy, obsolete)
            type: Filter by type (requirement, design, task, etc.)

        Returns:
            List of SpecBlock objects
        """
        blocks = self._blocks

        if status:
            try:
                status_enum = SpecStatus(status.lower())
                blocks = [b for b in blocks if b.status == status_enum]
            except ValueError:
                pass

        if type:
            try:
                type_enum = SpecType(type.lower())
                blocks = [b for b in blocks if b.type == type_enum]
            except ValueError:
                pass

        return blocks

    # Helper methods

    def _find_relevant_blocks(
        self,
        files: list[str],
    ) -> list[tuple[SpecBlock, float]]:
        """Find blocks relevant to given files."""
        if not self._memory_bank:
            return []

        # Create query from file paths
        query = " ".join(files)

        results = self._memory_bank.query(
            query_text=query,
            top_k=20,
            include_legacy=False,
            include_pinned=True,
        )

        return [(r.block, r.score) for r in results]

    def _get_steering_for_files(
        self,
        files: list[str],
    ) -> list[SteeringSummary]:
        """Get steering files applicable to the given files.

        Args:
            files: List of file paths

        Returns:
            List of SteeringSummary objects
        """
        try:
            from specmem.kiro import KiroConfigIndexer

            indexer = KiroConfigIndexer(self.path)
            indexer.index_steering()

            # Collect unique steering files
            seen_paths: set[str] = set()
            steering_summaries: list[SteeringSummary] = []

            for file_path in files:
                applicable = indexer.get_steering_for_file(file_path)
                for steering in applicable:
                    path_str = str(steering.path)
                    if path_str not in seen_paths:
                        seen_paths.add(path_str)
                        steering_summaries.append(
                            SteeringSummary(
                                title=steering.title,
                                content=self._truncate_text(steering.body, 500),
                                inclusion=steering.inclusion,
                                pattern=steering.file_match_pattern,
                                source=path_str,
                            )
                        )

            return steering_summaries
        except Exception as e:
            logger.warning(f"Failed to get steering for files: {e}")
            return []

    def _get_hooks_for_files(
        self,
        files: list[str],
    ) -> list[HookSummary]:
        """Get hooks that would trigger for the given files.

        Args:
            files: List of file paths

        Returns:
            List of HookSummary objects for file_save triggers
        """
        try:
            from specmem.kiro import KiroConfigIndexer

            indexer = KiroConfigIndexer(self.path)
            indexer.index_hooks()

            # Collect unique hooks
            seen_names: set[str] = set()
            hook_summaries: list[HookSummary] = []

            for file_path in files:
                hooks = indexer.get_hooks_for_trigger("file_save", file_path)
                for hook in hooks:
                    if hook.name not in seen_names:
                        seen_names.add(hook.name)
                        hook_summaries.append(
                            HookSummary(
                                name=hook.name,
                                description=hook.description,
                                trigger=hook.trigger,
                                action=hook.action,
                                pattern=hook.file_pattern,
                            )
                        )

            return hook_summaries
        except Exception as e:
            logger.warning(f"Failed to get hooks for files: {e}")
            return []

    def _extract_title(self, text: str) -> str:
        """Extract title from spec text."""
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                return line.lstrip("#").strip()
            if line and not line.startswith("-"):
                return line[:50] + ("..." if len(line) > 50 else "")
        return "Untitled"

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(" ", 1)[0] + "..."

    def _generate_tldr(
        self,
        summaries: list[SpecSummary],
        token_budget: int,
    ) -> str:
        """Generate TL;DR from summaries."""
        if not summaries:
            return "No specifications available."

        lines = ["Key specifications:"]

        for summary in summaries[:5]:
            pinned = "📌 " if summary.pinned else ""
            lines.append(f"- {pinned}[{summary.type}] {summary.title}")

        if len(summaries) > 5:
            lines.append(f"- ...and {len(summaries) - 5} more")

        tldr = "\n".join(lines)

        # Truncate if over budget
        tokens = self._token_estimator.count_tokens(tldr)
        while tokens > token_budget and len(lines) > 2:
            lines.pop(-2)  # Remove second-to-last item
            tldr = "\n".join(lines)
            tokens = self._token_estimator.count_tokens(tldr)

        return tldr

    def _estimate_bundle_tokens(
        self,
        specs: list[SpecSummary],
        designs: list[SpecSummary],
        tldr: str,
    ) -> int:
        """Estimate total tokens for a bundle."""
        total = self._token_estimator.count_tokens(tldr)

        for spec in specs:
            total += self._token_estimator.count_tokens(spec.summary)
            total += 20  # Overhead for metadata

        for design in designs:
            total += self._token_estimator.count_tokens(design.summary)
            total += 20

        return total

    def _parse_git_diff(self, diff: str) -> list[str]:
        """Parse git diff to extract changed files."""
        files = []

        # Match diff --git a/path b/path
        pattern = r"diff --git a/(.+?) b/"
        matches = re.findall(pattern, diff)
        files.extend(matches)

        # Match +++ b/path
        pattern = r"\+\+\+ b/(.+)"
        matches = re.findall(pattern, diff)
        files.extend(matches)

        return list(set(files))

    # ==========================================================================
    # SpecImpact Graph Integration
    # ==========================================================================

    @property
    def graph(self) -> SpecImpactGraph:
        """Get the SpecImpact graph (lazy-loaded).

        Returns:
            SpecImpactGraph instance
        """
        if self._graph is None:
            self._graph = self._load_or_build_graph()
        return self._graph

    def _load_or_build_graph(self) -> SpecImpactGraph:
        """Load existing graph or build a new one."""
        graph_path = self.path / ".specmem" / "impact_graph.json"

        if graph_path.exists():
            logger.debug(f"Loading existing graph from {graph_path}")
            return SpecImpactGraph(graph_path)

        # Build new graph
        logger.info("Building new SpecImpact graph...")
        builder = GraphBuilder(self.path)
        graph = builder.build(self._blocks, storage_path=graph_path)
        return graph

    def get_impact_set(
        self,
        changed_files: list[str],
        depth: int = 2,
        include_suggested: bool = False,
    ) -> ImpactSet:
        """Get full impact set for changed files using the graph.

        Args:
            changed_files: List of changed file paths
            depth: Maximum traversal depth for transitive relationships
            include_suggested: Include suggested (low-confidence) links

        Returns:
            ImpactSet containing affected specs, code, and tests
        """
        return self.graph.query_impact(
            changed_files=changed_files,
            depth=depth,
            include_suggested=include_suggested,
        )

    def rebuild_graph(self) -> SpecImpactGraph:
        """Rebuild the SpecImpact graph from scratch.

        Returns:
            Newly built SpecImpactGraph
        """
        graph_path = self.path / ".specmem" / "impact_graph.json"

        logger.info("Rebuilding SpecImpact graph...")
        builder = GraphBuilder(self.path)
        self._graph = builder.build(self._blocks, storage_path=graph_path)
        return self._graph

    # ==========================================================================
    # SpecDiff Integration - Temporal Spec Intelligence
    # ==========================================================================

    @property
    def specdiff(self) -> SpecDiff:
        """Get the SpecDiff instance (lazy-loaded).

        Returns:
            SpecDiff instance for temporal spec intelligence
        """
        if self._specdiff is None:
            self._specdiff = self._load_or_build_specdiff()
        return self._specdiff

    def _load_or_build_specdiff(self) -> SpecDiff:
        """Load existing SpecDiff or create a new one."""
        db_path = self.path / ".specmem" / "specdiff.db"

        # Create SpecDiff with impact graph for drift detection
        specdiff = SpecDiff(db_path, impact_graph=self._graph)

        # Build version history if not exists
        if not db_path.exists() or db_path.stat().st_size == 0:
            logger.info("Building initial version history...")
            for block in self._blocks:
                specdiff.track_version(block)

        return specdiff

    def get_spec_history(
        self,
        spec_id: str,
        limit: int | None = None,
    ) -> list[SpecVersion]:
        """Get version history for a specification.

        Args:
            spec_id: Specification identifier
            limit: Maximum number of versions to return

        Returns:
            List of SpecVersion objects ordered by timestamp (oldest first)
        """
        return self.specdiff.get_history(spec_id, limit)

    def get_spec_diff(
        self,
        spec_id: str,
        from_version: str | None = None,
        to_version: str | None = None,
    ) -> SpecChange | None:
        """Get diff between two spec versions.

        Args:
            spec_id: Specification identifier
            from_version: Starting version (default: second-to-last)
            to_version: Ending version (default: latest)

        Returns:
            SpecChange describing the differences, or None if not enough versions
        """
        return self.specdiff.get_diff(spec_id, from_version, to_version)

    def check_staleness(
        self,
        spec_ids: list[str] | None = None,
        cached_versions: dict[str, str] | None = None,
    ) -> list[StalenessWarning]:
        """Check if specs are stale.

        Args:
            spec_ids: List of spec identifiers to check (default: all)
            cached_versions: Map of spec_id to cached version_id

        Returns:
            List of staleness warnings for stale specs
        """
        if spec_ids is None:
            spec_ids = [block.id for block in self._blocks]

        return self.specdiff.check_staleness(spec_ids, cached_versions)

    def get_drift_report(self) -> DriftReport:
        """Get report on code drift from specifications.

        Returns:
            DriftReport with drifted code items
        """
        return self.specdiff.get_drift_report()

    def get_contradictions(self, spec_id: str) -> list[Contradiction]:
        """Find contradictions in spec history.

        Args:
            spec_id: Specification identifier

        Returns:
            List of contradictions found
        """
        return self.specdiff.get_contradictions(spec_id)

    def get_deprecations(
        self,
        include_expired: bool = False,
    ) -> list[Deprecation]:
        """Get deprecated specs sorted by urgency.

        Args:
            include_expired: Include deprecations past deadline

        Returns:
            List of deprecations ordered by urgency descending
        """
        return self.specdiff.get_deprecations(include_expired)

    def track_spec_version(self, spec: SpecBlock) -> SpecVersion:
        """Track a new version of a specification.

        Args:
            spec: The spec block to track

        Returns:
            Created SpecVersion
        """
        return self.specdiff.track_version(spec)

    def acknowledge_staleness(
        self,
        spec_id: str,
        version: str,
    ) -> bool:
        """Acknowledge a staleness warning.

        Args:
            spec_id: Specification identifier
            version: Version being acknowledged

        Returns:
            True if acknowledged successfully
        """
        return self.specdiff.acknowledge_staleness(spec_id, version)

    # ==========================================================================
    # SpecValidator Integration - Specification Quality Assurance
    # ==========================================================================

    def validate(
        self,
        spec_id: str | None = None,
    ) -> ValidationResult:
        """Validate specifications for quality issues.

        Checks for:
        - Contradictory requirements
        - Missing acceptance criteria
        - Invalid constraints
        - Duplicate specifications
        - Timeline issues
        - Structure problems

        Args:
            spec_id: Optional spec ID to validate (validates all if None)

        Returns:
            ValidationResult with all issues found
        """
        from specmem.validator import (
            AcceptanceCriteriaRule,
            ConstraintRule,
            ContradictionRule,
            DuplicateRule,
            StructureRule,
            TimelineRule,
            ValidationConfig,
            ValidationEngine,
            ValidationResult,
        )

        # Get specs to validate
        specs = self._blocks
        if spec_id:
            specs = [b for b in specs if spec_id in b.id]

        if not specs:
            return ValidationResult(
                issues=[],
                specs_validated=0,
                rules_run=0,
                duration_ms=0.0,
            )

        # Load config
        try:
            validation_config = ValidationConfig.from_toml(self._config.to_dict())
        except Exception:
            validation_config = ValidationConfig()

        # Create engine and register rules
        engine = ValidationEngine(validation_config)
        engine.register_rules(
            [
                ContradictionRule(),
                AcceptanceCriteriaRule(),
                ConstraintRule(),
                DuplicateRule(),
                TimelineRule(),
                StructureRule(),
            ]
        )

        # Run validation
        return engine.validate(specs)

    def get_validation_errors(
        self,
        spec_id: str | None = None,
    ) -> list[ValidationIssue]:
        """Get error-level validation issues.

        Args:
            spec_id: Optional spec ID to filter

        Returns:
            List of error-level ValidationIssue objects
        """
        result = self.validate(spec_id)
        return result.get_errors()

    def get_validation_warnings(
        self,
        spec_id: str | None = None,
    ) -> list[ValidationIssue]:
        """Get warning-level validation issues.

        Args:
            spec_id: Optional spec ID to filter

        Returns:
            List of warning-level ValidationIssue objects
        """
        result = self.validate(spec_id)
        return result.get_warnings()

    def is_valid(self, spec_id: str | None = None) -> bool:
        """Check if specs pass validation (no errors).

        Args:
            spec_id: Optional spec ID to check

        Returns:
            True if no error-level issues found
        """
        result = self.validate(spec_id)
        return result.is_valid

    # ==========================================================================
    # Spec Coverage Integration - Test Gap Analysis
    # ==========================================================================

    def get_coverage(
        self,
        feature: str | None = None,
    ) -> Any:
        """Get spec coverage analysis.

        Analyzes the gap between specification acceptance criteria
        and existing tests.

        Args:
            feature: Optional feature name to analyze (analyzes all if None)

        Returns:
            CoverageResult with coverage data and suggestions
        """
        from specmem.coverage import CoverageEngine, CoverageResult

        engine = CoverageEngine(self.path)

        if feature:
            feature_coverage = engine.analyze_feature(feature)
            return CoverageResult(
                features=[feature_coverage],
                suggestions=engine.get_suggestions(feature),
            )
        else:
            return engine.analyze_coverage()

    def get_coverage_suggestions(
        self,
        feature: str | None = None,
    ) -> list[Any]:
        """Get test suggestions for uncovered criteria.

        Args:
            feature: Optional feature name to get suggestions for

        Returns:
            List of TestSuggestion objects
        """
        from specmem.coverage import CoverageEngine

        engine = CoverageEngine(self.path)
        return engine.get_suggestions(feature)

    def get_coverage_badge(self) -> str:
        """Generate coverage badge markdown.

        Returns:
            Badge markdown string for README
        """
        from specmem.coverage import CoverageEngine

        engine = CoverageEngine(self.path)
        return engine.generate_badge()

    # ==========================================================================
    # Spec Lifecycle Management - Pragmatic SDD
    # ==========================================================================

    def prune_specs(
        self,
        spec_names: list[str] | None = None,
        mode: str = "archive",
        dry_run: bool = True,
        force: bool = False,
        orphaned: bool = False,
        stale: bool = False,
        stale_days: int = 90,
    ) -> list[Any]:
        """Prune orphaned or stale specifications.

        Supports both targeted pruning (by name) and automatic pruning
        (orphaned/stale specs).

        Args:
            spec_names: Specific spec names to prune (optional)
            mode: Prune mode - "archive" (default) or "delete"
            dry_run: If True, preview changes without applying (default: True)
            force: If True, skip confirmation for delete mode
            orphaned: If True, prune all orphaned specs
            stale: If True, prune all stale specs
            stale_days: Days threshold for stale detection (default: 90)

        Returns:
            List of PruneResult objects describing actions taken

        Raises:
            ValueError: If mode is invalid
            SpecNotFoundError: If specified spec names don't exist

        Example:
            # Preview orphaned specs
            results = sm.prune_specs(orphaned=True)

            # Actually archive orphaned specs
            results = sm.prune_specs(orphaned=True, dry_run=False)

            # Delete specific specs
            results = sm.prune_specs(
                spec_names=["old-feature"],
                mode="delete",
                dry_run=False,
                force=True
            )
        """
        from specmem.lifecycle import HealthAnalyzer, PrunerEngine

        spec_base = self.path / ".kiro" / "specs"
        archive_dir = self.path / ".specmem" / "archive"

        if not spec_base.exists():
            return []

        if mode not in ("archive", "delete"):
            raise ValueError(f"Invalid mode: {mode}. Use 'archive' or 'delete'.")

        analyzer = HealthAnalyzer(
            spec_base_path=spec_base,
            stale_threshold_days=stale_days,
        )
        pruner = PrunerEngine(
            health_analyzer=analyzer,
            archive_dir=archive_dir,
        )

        if spec_names:
            return pruner.prune_by_name(
                spec_names=spec_names,
                mode=mode,  # type: ignore
                dry_run=dry_run,
                force=force,
            )
        elif orphaned:
            return pruner.prune_orphaned(
                mode=mode,  # type: ignore
                dry_run=dry_run,
                force=force,
            )
        elif stale:
            return pruner.prune_stale(
                threshold_days=stale_days,
                mode=mode,  # type: ignore
                dry_run=dry_run,
            )
        else:
            # Return analysis results
            return pruner.analyze()

    def generate_specs(
        self,
        files: list[str],
        format: str = "kiro",
        group_by: str = "directory",
        write: bool = False,
    ) -> list[Any]:
        """Generate specifications from code files.

        Analyzes code files and generates spec documents based on
        function signatures, docstrings, and comments.

        Args:
            files: List of file or directory paths to analyze
            format: Output format - "kiro" (default) or "speckit"
            group_by: Grouping strategy - "file", "directory", or "module"
            write: If True, write specs to disk (default: False)

        Returns:
            List of GeneratedSpec objects

        Example:
            # Generate specs from a directory
            specs = sm.generate_specs(["src/auth/"])

            # Generate and write to disk
            specs = sm.generate_specs(
                ["src/auth.py"],
                format="kiro",
                write=True
            )
        """
        from specmem.lifecycle import GeneratorEngine

        output_dir = self.path / ".kiro" / "specs"

        generator = GeneratorEngine(
            default_format=format,
            output_dir=output_dir,
        )

        all_specs = []

        for file_arg in files:
            file_path = Path(file_arg)
            if not file_path.is_absolute():
                file_path = self.path / file_path

            if not file_path.exists():
                logger.warning(f"File not found: {file_arg}")
                continue

            if file_path.is_file():
                spec = generator.generate_from_file(file_path)
                all_specs.append(spec)
            else:
                specs = generator.generate_from_directory(
                    file_path,
                    group_by=group_by,  # type: ignore
                    output_format=format,
                )
                all_specs.extend(specs)

        if write:
            for spec in all_specs:
                generator.write_spec(spec)

        return all_specs

    def compress_specs(
        self,
        spec_names: list[str] | None = None,
        threshold: int = 5000,
        all_verbose: bool = False,
        save: bool = False,
    ) -> list[Any]:
        """Compress verbose specifications.

        Condenses verbose specs while preserving acceptance criteria.

        Args:
            spec_names: Specific spec names to compress (optional)
            threshold: Character threshold for verbose detection (default: 5000)
            all_verbose: If True, compress all verbose specs
            save: If True, save compressed versions to disk

        Returns:
            List of CompressedSpec objects

        Example:
            # Find verbose specs
            verbose = sm.compress_specs()

            # Compress specific spec
            results = sm.compress_specs(spec_names=["auth-feature"])

            # Compress all verbose specs and save
            results = sm.compress_specs(all_verbose=True, save=True)
        """
        from specmem.lifecycle import CompressorEngine

        spec_base = self.path / ".kiro" / "specs"
        compressed_dir = self.path / ".specmem" / "compressed"

        if not spec_base.exists():
            return []

        compressor = CompressorEngine(
            verbose_threshold_chars=threshold,
            compression_storage_dir=compressed_dir,
        )

        # Discover specs
        specs: list[tuple[str, Path]] = []
        for item in spec_base.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                specs.append((item.name, item))

        if not specs:
            return []

        results = []

        if spec_names:
            for name in spec_names:
                spec_path = spec_base / name
                if spec_path.exists():
                    compressed = compressor.compress_spec(name, spec_path)
                    results.append(compressed)
        elif all_verbose:
            results = compressor.compress_all(specs)
        else:
            # Return list of verbose spec names
            return compressor.get_verbose_specs(specs, threshold)

        if save:
            for result in results:
                compressor.save_compressed(result)

        return results

    def get_spec_health(
        self,
        spec_name: str | None = None,
        stale_days: int = 90,
    ) -> Any:
        """Get health scores for specifications.

        Calculates health scores based on code references, modification
        date, and query frequency.

        Args:
            spec_name: Specific spec to analyze (optional, analyzes all if None)
            stale_days: Days threshold for stale detection (default: 90)

        Returns:
            SpecHealthScore for single spec, or dict with summary and scores for all

        Example:
            # Get health for all specs
            health = sm.get_spec_health()
            print(f"Average score: {health['average_score']}")

            # Get health for specific spec
            score = sm.get_spec_health("auth-feature")
            print(f"Score: {score.score}, Orphaned: {score.is_orphaned}")
        """
        from specmem.lifecycle import HealthAnalyzer

        spec_base = self.path / ".kiro" / "specs"

        if not spec_base.exists():
            return {"total_specs": 0, "scores": []}

        analyzer = HealthAnalyzer(
            spec_base_path=spec_base,
            stale_threshold_days=stale_days,
        )

        if spec_name:
            spec_path = spec_base / spec_name
            if not spec_path.exists():
                raise FileNotFoundError(f"Spec not found: {spec_name}")
            return analyzer.analyze_spec(spec_name, spec_path)

        scores = analyzer.analyze_all()
        summary = analyzer.get_summary()

        return {
            "total_specs": summary["total_specs"],
            "orphaned_count": summary["orphaned_count"],
            "stale_count": summary["stale_count"],
            "average_score": summary["average_score"],
            "scores": scores,
        }
