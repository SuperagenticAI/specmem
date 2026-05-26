"""Guidelines scanner for detecting coding guideline files."""

from __future__ import annotations

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class GuidelinesScanner:
    """Scans workspace for coding guideline files.

    Detects files from multiple sources:
    - CLAUDE.md (Claude Code)
    - AGENTS.md (Generic agent instructions)
    - .cursorrules (Cursor)
    - .cursor/rules/*.mdc (Cursor project rules)
    - .codex/skills/*/SKILL.md (Codex skills)
    - .claude/skills/*/SKILL.md (Claude skills)
    - .github/copilot-instructions.md and .github/instructions/*.instructions.md
    - GEMINI.md, OPENCODE.md, QWEN.md
    - .kiro/steering/*.md (Kiro steering files)
    """

    FILE_PATTERNS: dict[str, list[str]] = {
        "claude": ["**/CLAUDE.md", "**/Claude.md", "**/claude.md"],
        "agents": ["**/AGENTS.md", "**/Agents.md", "**/AGENT.md", "**/Agent.md"],
        "cursor": ["**/.cursorrules", "**/cursor.rules", "**/.cursor/rules/*.mdc"],
        "steering": [".kiro/steering/*.md"],
        "codex_skill": ["**/.codex/skills/*/SKILL.md"],
        "claude_skill": ["**/.claude/skills/*/SKILL.md"],
        "copilot": [
            "**/.github/copilot-instructions.md",
            "**/.github/instructions/*.instructions.md",
        ],
        "gemini": ["**/GEMINI.md", "**/Gemini.md", "**/gemini.md"],
        "opencode": ["**/OPENCODE.md", "**/OpenCode.md", "**/opencode.md"],
        "qwen": ["**/QWEN.md", "**/Qwen.md", "**/qwen.md"],
    }

    def __init__(self, workspace_path: Path | None = None):
        """Initialize the scanner.

        Args:
            workspace_path: Path to the workspace root
        """
        self.workspace_path = workspace_path or Path.cwd()

    def scan(self) -> dict[str, list[Path]]:
        """Scan for all guideline files grouped by source type.

        Returns:
            Dictionary mapping source type to list of file paths
        """
        results: dict[str, list[Path]] = {}

        for source_type, patterns in self.FILE_PATTERNS.items():
            files: list[Path] = []
            for pattern in patterns:
                found = list(self.workspace_path.glob(pattern))
                files.extend(found)

            # Remove duplicates while preserving order
            seen: set[Path] = set()
            unique_files: list[Path] = []
            for f in files:
                if f not in seen:
                    seen.add(f)
                    unique_files.append(f)

            if unique_files:
                results[source_type] = unique_files
                logger.debug(f"Found {len(unique_files)} {source_type} files")

        return results

    def has_guidelines(self) -> bool:
        """Check if any guideline files exist.

        Returns:
            True if at least one guideline file exists
        """
        for patterns in self.FILE_PATTERNS.values():
            for pattern in patterns:
                if list(self.workspace_path.glob(pattern)):
                    return True
        return False

    def get_all_files(self) -> list[Path]:
        """Get all guideline files as a flat list.

        Returns:
            List of all guideline file paths
        """
        all_files: list[Path] = []
        scanned = self.scan()
        for files in scanned.values():
            all_files.extend(files)
        return all_files
