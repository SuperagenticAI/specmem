"""Kiro adapter for SpecMem.

Parses Kiro spec files (requirements.md, design.md, tasks.md) and converts
them to SpecBlock format.
"""

import logging
import re
from pathlib import Path

from specmem.adapters.base import SpecAdapter
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


logger = logging.getLogger(__name__)


class KiroAdapter(SpecAdapter):
    """Adapter for Kiro spec-driven development framework.

    Detects and parses:
    - .kiro/specs/*/requirements.md - Requirements and acceptance criteria
    - .kiro/specs/*/design.md - Design decisions and architecture
    - .kiro/specs/*/tasks.md - Implementation tasks
    """

    @property
    def name(self) -> str:
        return "Kiro"

    def detect(self, repo_path: str) -> bool:
        """Check if Kiro specs exist in the repository."""
        kiro_dir = Path(repo_path) / ".kiro"
        if not kiro_dir.exists():
            return False

        specs_dir = kiro_dir / "specs"
        if not specs_dir.exists():
            return False

        # Check for any spec files
        for spec_folder in specs_dir.iterdir():
            if spec_folder.is_dir():
                for filename in ("requirements.md", "design.md", "tasks.md"):
                    if (spec_folder / filename).exists():
                        return True

        return False

    def load(self, repo_path: str) -> list[SpecBlock]:
        """Load and parse all Kiro spec files."""
        blocks: list[SpecBlock] = []
        kiro_dir = Path(repo_path) / ".kiro"
        specs_dir = kiro_dir / "specs"

        if not specs_dir.exists():
            return blocks

        for spec_folder in specs_dir.iterdir():
            if not spec_folder.is_dir():
                continue

            # Parse each spec file type
            requirements_file = spec_folder / "requirements.md"
            if requirements_file.exists():
                blocks.extend(self._parse_requirements(requirements_file))

            design_file = spec_folder / "design.md"
            if design_file.exists():
                blocks.extend(self._parse_design(design_file))

            tasks_file = spec_folder / "tasks.md"
            if tasks_file.exists():
                blocks.extend(self._parse_tasks(tasks_file))

        logger.info(f"Loaded {len(blocks)} SpecBlocks from Kiro specs")
        return blocks

    def _parse_requirements(self, file_path: Path) -> list[SpecBlock]:
        """Parse requirements.md file."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text()
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract requirements sections
        # Pattern: ### Requirement N: Title or ### Requirement N
        req_pattern = r"###\s+Requirement\s+(\d+)(?::\s*(.+?))?\n(.*?)(?=###\s+Requirement|\Z)"
        matches = re.findall(req_pattern, content, re.DOTALL | re.IGNORECASE)

        for req_num, _title, body in matches:
            # Extract user story
            user_story_match = re.search(
                r"\*\*User Story:\*\*\s*(.+?)(?=####|\*\*|\Z)", body, re.DOTALL
            )
            if user_story_match:
                user_story = user_story_match.group(1).strip()
                if user_story:
                    block_id = SpecBlock.generate_id(source, f"req_{req_num}_story")
                    blocks.append(
                        SpecBlock(
                            id=block_id,
                            type=SpecType.REQUIREMENT,
                            text=f"Requirement {req_num}: {user_story}",
                            source=source,
                            tags=[f"req_{req_num}", "user_story"],
                        )
                    )

            # Extract acceptance criteria
            ac_pattern = r"(\d+)\.\s+(WHEN|WHILE|IF|WHERE|THE)\s+(.+?)(?=\n\d+\.|####|\Z)"
            ac_matches = re.findall(ac_pattern, body, re.DOTALL | re.IGNORECASE)

            for ac_num, keyword, ac_text in ac_matches:
                full_ac = f"{keyword} {ac_text}".strip()
                if full_ac:
                    block_id = SpecBlock.generate_id(source, f"req_{req_num}_ac_{ac_num}")
                    # Check if this should be pinned (contains MUST, SHALL, constraint)
                    pinned = any(kw in full_ac.upper() for kw in ["MUST", "SHALL", "CONSTRAINT"])
                    blocks.append(
                        SpecBlock(
                            id=block_id,
                            type=SpecType.REQUIREMENT,
                            text=f"[Req {req_num}.{ac_num}] {full_ac}",
                            source=source,
                            tags=[f"req_{req_num}", f"ac_{ac_num}", "acceptance_criteria"],
                            pinned=pinned,
                        )
                    )

        # If no structured requirements found, extract as general content
        if not blocks:
            blocks.extend(self._extract_markdown_sections(content, source, SpecType.REQUIREMENT))

        return blocks

    def _parse_design(self, file_path: Path) -> list[SpecBlock]:
        """Parse design.md file."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text()
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract major sections (## headers)
        section_pattern = r"##\s+(.+?)\n(.*?)(?=##\s|\Z)"
        matches = re.findall(section_pattern, content, re.DOTALL)

        for title, body in matches:
            title = title.strip()
            body = body.strip()

            if not body:
                continue

            # Determine if this is a decision or general design
            spec_type = SpecType.DECISION if "decision" in title.lower() else SpecType.DESIGN

            block_id = SpecBlock.generate_id(source, f"design_{title}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=spec_type,
                    text=f"[{title}] {body[:500]}..." if len(body) > 500 else f"[{title}] {body}",
                    source=source,
                    tags=["design", title.lower().replace(" ", "_")],
                )
            )

        return blocks

    def _parse_tasks(self, file_path: Path) -> list[SpecBlock]:
        """Parse tasks.md file."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text()
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract task items (- [ ] or - [x] patterns)
        # Pattern matches: - [ ] 1. Task text or - [x] 2.1 Task text
        task_pattern = r"-\s+\[([ xX])\]\s*(\d+(?:\.\d+)?)[.\s]+(.+?)(?=\n-\s+\[|\n\n|\Z)"
        matches = re.findall(task_pattern, content, re.DOTALL)

        for status_char, task_num, task_text in matches:
            task_text = task_text.strip()
            if not task_text:
                continue

            # Determine status from checkbox
            status = SpecStatus.ACTIVE if status_char == " " else SpecStatus.LEGACY

            block_id = SpecBlock.generate_id(source, f"task_{task_num}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.TASK,
                    text=f"[Task {task_num}] {task_text}",
                    source=source,
                    status=status,
                    tags=["task", f"task_{task_num.replace('.', '_')}"],
                )
            )

        return blocks

    def _extract_markdown_sections(
        self, content: str, source: str, spec_type: SpecType
    ) -> list[SpecBlock]:
        """Extract content from markdown sections as fallback."""
        blocks: list[SpecBlock] = []

        # Split by headers
        sections = re.split(r"\n(?=#+\s)", content)

        for section in sections:
            section = section.strip()
            if not section or len(section) < 20:
                continue

            # Get first line as title
            lines = section.split("\n", 1)
            title = lines[0].lstrip("#").strip()
            body = lines[1].strip() if len(lines) > 1 else ""

            if not body:
                continue

            block_id = SpecBlock.generate_id(source, f"{spec_type.value}_{title}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=spec_type,
                    text=f"[{title}] {body[:500]}..." if len(body) > 500 else f"[{title}] {body}",
                    source=source,
                    tags=[spec_type.value, title.lower().replace(" ", "_")[:30]],
                )
            )

        return blocks
