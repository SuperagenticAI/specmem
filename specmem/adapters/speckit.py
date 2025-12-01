"""GitHub SpecKit adapter for SpecMem.

GitHub SpecKit (https://github.com/github/spec-kit) is an open source toolkit
for Spec-Driven Development (SDD). This adapter handles:
- .specify/ directory structure
- specs/*/spec.md - Feature specifications with user stories
- specs/*/plan.md - Implementation plans with technical context
- specs/*/tasks.md - Task lists organized by user story
- memory/constitution.md - Project governing principles
"""

import logging
import re
from pathlib import Path

from specmem.adapters.base import SpecAdapter
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


logger = logging.getLogger(__name__)


class SpecKitAdapter(SpecAdapter):
    """Experimental adapter for GitHub SpecKit specifications.

    Detects and parses:
    - .specify/specs/*/spec.md - Feature specifications
    - .specify/specs/*/plan.md - Implementation plans
    - .specify/specs/*/tasks.md - Task breakdowns
    - .specify/memory/constitution.md - Project principles
    - .specify/templates/ - Specification templates
    """

    @property
    def name(self) -> str:
        return "SpecKit"

    def is_experimental(self) -> bool:
        """SpecKit adapter is experimental."""
        return True

    def detect(self, repo_path: str) -> bool:
        """Check if GitHub SpecKit structure exists in the repository."""
        path = Path(repo_path)
        if not path.exists():
            return False

        # Check for .specify directory structure
        specify_dir = path / ".specify"
        if specify_dir.exists() and specify_dir.is_dir():
            # Check for key subdirectories
            specs_dir = specify_dir / "specs"
            memory_dir = specify_dir / "memory"
            if specs_dir.exists() or memory_dir.exists():
                return True

        return False

    def load(self, repo_path: str) -> list[SpecBlock]:
        """Load and parse all GitHub SpecKit files."""
        self.warn_if_experimental()
        blocks: list[SpecBlock] = []
        path = Path(repo_path)

        if not path.exists():
            return blocks

        specify_dir = path / ".specify"
        if not specify_dir.exists():
            return blocks

        # Parse constitution (project principles)
        constitution_file = specify_dir / "memory" / "constitution.md"
        if constitution_file.exists():
            try:
                blocks.extend(self._parse_constitution(constitution_file))
            except Exception as e:
                logger.warning(f"Failed to parse constitution {constitution_file}: {e}")

        # Parse all feature specs
        specs_dir = specify_dir / "specs"
        if specs_dir.exists():
            for feature_dir in specs_dir.iterdir():
                if not feature_dir.is_dir():
                    continue

                # Parse spec.md
                spec_file = feature_dir / "spec.md"
                if spec_file.exists():
                    try:
                        blocks.extend(self._parse_spec(spec_file, feature_dir.name))
                    except Exception as e:
                        logger.warning(f"Failed to parse spec {spec_file}: {e}")

                # Parse plan.md
                plan_file = feature_dir / "plan.md"
                if plan_file.exists():
                    try:
                        blocks.extend(self._parse_plan(plan_file, feature_dir.name))
                    except Exception as e:
                        logger.warning(f"Failed to parse plan {plan_file}: {e}")

                # Parse tasks.md
                tasks_file = feature_dir / "tasks.md"
                if tasks_file.exists():
                    try:
                        blocks.extend(self._parse_tasks(tasks_file, feature_dir.name))
                    except Exception as e:
                        logger.warning(f"Failed to parse tasks {tasks_file}: {e}")

                # Parse research.md if exists
                research_file = feature_dir / "research.md"
                if research_file.exists():
                    try:
                        blocks.extend(self._parse_research(research_file, feature_dir.name))
                    except Exception as e:
                        logger.warning(f"Failed to parse research {research_file}: {e}")

        logger.info(f"Loaded {len(blocks)} SpecBlocks from GitHub SpecKit")
        return blocks

    def _parse_constitution(self, file_path: Path) -> list[SpecBlock]:
        """Parse constitution.md - project governing principles."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract articles/sections from constitution
        article_pattern = (
            r"(?:^|\n)##?\s+(Article\s+\w+[:\s]+.+?|Section\s+[\d.]+[:\s]+.+?)(?=\n##?\s+|\Z)"
        )
        matches = re.findall(article_pattern, content, re.DOTALL | re.IGNORECASE)

        if matches:
            for i, match in enumerate(matches):
                block_id = SpecBlock.generate_id(source, f"constitution_article_{i}")
                blocks.append(
                    SpecBlock(
                        id=block_id,
                        type=SpecType.DECISION,
                        text=match.strip()[:500],
                        source=source,
                        status=SpecStatus.ACTIVE,
                        tags=["speckit", "constitution", "principle"],
                        links=[],
                        pinned=True,  # Constitution is foundational
                    )
                )
        else:
            # No articles found, create single block
            block_id = SpecBlock.generate_id(source, "constitution")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.DECISION,
                    text=content[:1000] if len(content) > 1000 else content,
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["speckit", "constitution"],
                    links=[],
                    pinned=True,
                )
            )

        return blocks

    def _parse_spec(self, file_path: Path, feature_name: str) -> list[SpecBlock]:
        """Parse spec.md - feature specification with user stories."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract user stories
        user_story_pattern = r"###\s+User Story\s+(\d+)\s*-\s*(.+?)(?:\(Priority:\s*(\w+)\))?\n(.*?)(?=###\s+User Story|\Z|##\s+)"
        story_matches = re.findall(user_story_pattern, content, re.DOTALL | re.IGNORECASE)

        for story_num, title, priority, body in story_matches:
            block_id = SpecBlock.generate_id(source, f"user_story_{story_num}")
            tags = ["speckit", "user_story", feature_name]
            if priority:
                tags.append(f"priority_{priority.lower()}")

            # Extract acceptance scenarios
            acceptance_match = re.search(
                r"\*\*Acceptance Scenarios\*\*:(.*?)(?=\*\*|\Z|---)",
                body,
                re.DOTALL | re.IGNORECASE,
            )
            if acceptance_match:
                acceptance_match.group(1).strip()

            text = f"User Story {story_num}: {title.strip()}\n\n{body.strip()[:400]}"

            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.REQUIREMENT,
                    text=text,
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=tags,
                    links=[],
                    pinned=priority and priority.upper() == "P1",
                )
            )

        # Extract functional requirements
        fr_pattern = r"\*\*FR-(\d+)\*\*:\s*(.+?)(?=\*\*FR-|\Z|\n\n)"
        fr_matches = re.findall(fr_pattern, content, re.DOTALL)

        for fr_num, fr_text in fr_matches:
            block_id = SpecBlock.generate_id(source, f"fr_{fr_num}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.REQUIREMENT,
                    text=f"[FR-{fr_num}] {fr_text.strip()}",
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["speckit", "functional_requirement", feature_name],
                    links=[],
                    pinned="MUST" in fr_text.upper(),
                )
            )

        # Extract success criteria
        sc_pattern = r"\*\*SC-(\d+)\*\*:\s*(.+?)(?=\*\*SC-|\Z|\n\n)"
        sc_matches = re.findall(sc_pattern, content, re.DOTALL)

        for sc_num, sc_text in sc_matches:
            block_id = SpecBlock.generate_id(source, f"sc_{sc_num}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.REQUIREMENT,
                    text=f"[SC-{sc_num}] {sc_text.strip()}",
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["speckit", "success_criteria", feature_name],
                    links=[],
                    pinned=False,
                )
            )

        return blocks

    def _parse_plan(self, file_path: Path, feature_name: str) -> list[SpecBlock]:
        """Parse plan.md - implementation plan with technical context."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract technical context section
        tech_context_match = re.search(
            r"##\s+Technical Context\s*\n(.*?)(?=##\s+|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if tech_context_match:
            tech_text = tech_context_match.group(1).strip()
            block_id = SpecBlock.generate_id(source, "technical_context")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.DESIGN,
                    text=f"[Technical Context]\n{tech_text[:500]}",
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["speckit", "plan", "technical_context", feature_name],
                    links=[],
                    pinned=True,
                )
            )

        # Extract project structure
        structure_match = re.search(
            r"##\s+Project Structure\s*\n(.*?)(?=##\s+|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if structure_match:
            structure_text = structure_match.group(1).strip()
            block_id = SpecBlock.generate_id(source, "project_structure")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.DESIGN,
                    text=f"[Project Structure]\n{structure_text[:500]}",
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["speckit", "plan", "structure", feature_name],
                    links=[],
                    pinned=False,
                )
            )

        # Extract summary if no specific sections found
        if not blocks:
            summary_match = re.search(
                r"##\s+Summary\s*\n(.*?)(?=##\s+|\Z)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if summary_match:
                block_id = SpecBlock.generate_id(source, "plan_summary")
                blocks.append(
                    SpecBlock(
                        id=block_id,
                        type=SpecType.DESIGN,
                        text=f"[Plan Summary]\n{summary_match.group(1).strip()[:500]}",
                        source=source,
                        status=SpecStatus.ACTIVE,
                        tags=["speckit", "plan", feature_name],
                        links=[],
                        pinned=True,
                    )
                )

        return blocks

    def _parse_tasks(self, file_path: Path, feature_name: str) -> list[SpecBlock]:
        """Parse tasks.md - task breakdown by user story."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract phases/user story sections
        phase_pattern = r"##\s+Phase\s+(\d+):\s*(.+?)\n(.*?)(?=##\s+Phase|\Z)"
        phase_matches = re.findall(phase_pattern, content, re.DOTALL | re.IGNORECASE)

        for phase_num, _phase_title, phase_body in phase_matches:
            # Extract individual tasks
            task_pattern = r"-\s+\[([ xX])\]\s+(T\d+)\s*(?:\[P\])?\s*(?:\[US\d+\])?\s*(.+?)(?=\n-\s+\[|\n\n|\Z)"
            task_matches = re.findall(task_pattern, phase_body, re.DOTALL)

            for status_char, task_id, task_text in task_matches:
                block_id = SpecBlock.generate_id(source, f"task_{task_id}")
                status = SpecStatus.ACTIVE if status_char == " " else SpecStatus.LEGACY

                blocks.append(
                    SpecBlock(
                        id=block_id,
                        type=SpecType.TASK,
                        text=f"[{task_id}] {task_text.strip()}",
                        source=source,
                        status=status,
                        tags=["speckit", "task", feature_name, f"phase_{phase_num}"],
                        links=[],
                        pinned=False,
                    )
                )

        return blocks

    def _parse_research(self, file_path: Path, feature_name: str) -> list[SpecBlock]:
        """Parse research.md - technical research findings."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Create a single block for research content
        block_id = SpecBlock.generate_id(source, "research")
        blocks.append(
            SpecBlock(
                id=block_id,
                type=SpecType.KNOWLEDGE,
                text=content[:1000] if len(content) > 1000 else content,
                source=source,
                status=SpecStatus.ACTIVE,
                tags=["speckit", "research", feature_name],
                links=[],
                pinned=False,
            )
        )

        return blocks
