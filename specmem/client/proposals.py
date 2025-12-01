"""Proposal store for agent-suggested spec edits."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from specmem.client.exceptions import ProposalError
from specmem.client.models import Proposal, ProposalStatus


logger = logging.getLogger(__name__)


class ProposalStore:
    """Manages agent-proposed spec edits.

    Stores proposals in .specmem/proposals.json for persistence.
    """

    PROPOSALS_FILE = "proposals.json"

    def __init__(self, storage_path: Path | str = ".specmem") -> None:
        """Initialize the proposal store.

        Args:
            storage_path: Directory for storing proposals
        """
        self.storage_path = Path(storage_path)
        self._proposals: dict[str, Proposal] = {}
        self._loaded = False

    @property
    def proposals_file(self) -> Path:
        """Path to proposals JSON file."""
        return self.storage_path / self.PROPOSALS_FILE

    def _ensure_loaded(self) -> None:
        """Ensure proposals are loaded from disk."""
        if self._loaded:
            return

        if self.proposals_file.exists():
            try:
                data = json.loads(self.proposals_file.read_text())
                for proposal_data in data.get("proposals", []):
                    proposal = Proposal.from_dict(proposal_data)
                    self._proposals[proposal.id] = proposal
                logger.debug(f"Loaded {len(self._proposals)} proposals")
            except Exception as e:
                logger.warning(f"Failed to load proposals: {e}")

        self._loaded = True

    def _save(self) -> None:
        """Save proposals to disk."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

        data = {"proposals": [p.to_dict() for p in self._proposals.values()]}

        self.proposals_file.write_text(json.dumps(data, indent=2))
        logger.debug(f"Saved {len(self._proposals)} proposals")

    def create(
        self,
        spec_id: str,
        edits: dict[str, Any],
        rationale: str,
    ) -> Proposal:
        """Create a new proposal.

        Args:
            spec_id: ID of the spec to edit
            edits: Dictionary of proposed changes
            rationale: Explanation for the changes

        Returns:
            Created Proposal with unique ID
        """
        self._ensure_loaded()

        proposal_id = str(uuid.uuid4())[:8]

        proposal = Proposal(
            id=proposal_id,
            spec_id=spec_id,
            edits=edits,
            rationale=rationale,
            status=ProposalStatus.PENDING,
            created_at=datetime.now(),
        )

        self._proposals[proposal_id] = proposal
        self._save()

        logger.info(f"Created proposal {proposal_id} for spec {spec_id}")
        return proposal

    def get(self, proposal_id: str) -> Proposal | None:
        """Get a proposal by ID.

        Args:
            proposal_id: Proposal ID

        Returns:
            Proposal or None if not found
        """
        self._ensure_loaded()
        return self._proposals.get(proposal_id)

    def list(
        self,
        status: ProposalStatus | None = None,
        spec_id: str | None = None,
    ) -> list[Proposal]:
        """List proposals with optional filters.

        Args:
            status: Filter by status
            spec_id: Filter by spec ID

        Returns:
            List of matching proposals
        """
        self._ensure_loaded()

        proposals = list(self._proposals.values())

        if status is not None:
            proposals = [p for p in proposals if p.status == status]

        if spec_id is not None:
            proposals = [p for p in proposals if p.spec_id == spec_id]

        # Sort by created_at descending
        proposals.sort(key=lambda p: p.created_at, reverse=True)

        return proposals

    def accept(self, proposal_id: str) -> bool:
        """Accept a pending proposal.

        Args:
            proposal_id: Proposal ID

        Returns:
            True if accepted, False if not found or not pending

        Raises:
            ProposalError: If proposal is not in pending status
        """
        self._ensure_loaded()

        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return False

        if proposal.status != ProposalStatus.PENDING:
            raise ProposalError(
                f"Cannot accept proposal {proposal_id}: status is {proposal.status.value}"
            )

        proposal.status = ProposalStatus.ACCEPTED
        proposal.resolved_at = datetime.now()
        self._save()

        logger.info(f"Accepted proposal {proposal_id}")
        return True

    def reject(self, proposal_id: str, reason: str = "") -> bool:
        """Reject a pending proposal.

        Args:
            proposal_id: Proposal ID
            reason: Optional rejection reason

        Returns:
            True if rejected, False if not found

        Raises:
            ProposalError: If proposal is not in pending status
        """
        self._ensure_loaded()

        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return False

        if proposal.status != ProposalStatus.PENDING:
            raise ProposalError(
                f"Cannot reject proposal {proposal_id}: status is {proposal.status.value}"
            )

        proposal.status = ProposalStatus.REJECTED
        proposal.resolved_at = datetime.now()
        self._save()

        logger.info(f"Rejected proposal {proposal_id}")
        return True
