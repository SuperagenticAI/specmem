"""OpenSpec adapter for SpecMem.

Fission-AI OpenSpec (https://github.com/Fission-AI/OpenSpec) keeps
specifications and change proposals under an ``openspec/`` directory.
This adapter handles the official on-disk layout (verified against OpenSpec
docs around v1.12.x):

- ``openspec/specs/**`` — source-of-truth specs (often ``spec.md`` per domain)
- ``openspec/changes/**`` — change folders with proposal/design/tasks/delta specs
- ``openspec/config.yaml`` — optional project planning context (indexed lightly)

Marked stable: the directory layout and artifact filenames are documented and
stable enough for first-class support (same bar as Kiro / AGENTS.md).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from specmem.adapters.base import SpecAdapter
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


logger = logging.getLogger(__name__)


class OpenSpecAdapter(SpecAdapter):
    """Stable adapter for Fission-AI OpenSpec on-disk layout.

    Detects ``openspec/`` when it contains ``specs/``, ``changes/``, and/or
    ``config.yaml``. Parses markdown into SpecBlocks with heading splits,
    maps clear filenames to SpecTypes, and lightly indexes ``config.yaml``.
    """

    ROOT_DIR = "openspec"
    CONFIG_NAME = "config.yaml"
    MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})
    SKIP_DIRS = frozenset(
        {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".tox",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".specmem",
            "dist",
            "build",
            "schemas",  # custom workflow schemas; not spec content
        }
    )

    @property
    def name(self) -> str:
        return "OpenSpec"

    def is_experimental(self) -> bool:
        """OpenSpec layout is documented and stable; not experimental."""
        return False

    def detect(self, repo_path: str) -> bool:
        """Return True if openspec/ has specs, changes, and/or config.yaml."""
        root = Path(repo_path) / self.ROOT_DIR
        if not root.is_dir():
            return False

        if (root / self.CONFIG_NAME).is_file():
            return True

        specs = root / "specs"
        if specs.is_dir() and self._dir_has_markdown(specs):
            return True

        changes = root / "changes"
        if changes.is_dir() and self._dir_has_markdown(changes):
            return True

        # Empty specs/ or changes/ dirs still signal an OpenSpec project
        return specs.is_dir() or changes.is_dir()

    def load(self, repo_path: str) -> list[SpecBlock]:
        """Load OpenSpec markdown and optional config into SpecBlocks."""
        blocks: list[SpecBlock] = []
        path = Path(repo_path)
        root = path / self.ROOT_DIR

        if not root.is_dir():
            return blocks

        for md_file in self._find_markdown(root):
            try:
                blocks.extend(self._parse_markdown_file(md_file, root))
            except Exception as e:
                logger.warning(f"Failed to parse OpenSpec file {md_file}: {e}")

        config_file = root / self.CONFIG_NAME
        if config_file.is_file():
            try:
                blocks.extend(self._parse_config(config_file))
            except Exception as e:
                logger.warning(f"Failed to parse OpenSpec config {config_file}: {e}")

        logger.info(f"Loaded {len(blocks)} SpecBlocks from OpenSpec")
        return blocks

    def _dir_has_markdown(self, directory: Path) -> bool:
        """Return True if any markdown file exists under directory."""
        try:
            for entry in directory.rglob("*"):
                if not entry.is_file():
                    continue
                if entry.suffix.lower() not in self.MARKDOWN_SUFFIXES:
                    continue
                if self._is_under_skip_dir(directory, entry):
                    continue
                return True
        except OSError as e:
            logger.warning(f"Failed to scan {directory}: {e}")
        return False

    def _find_markdown(self, openspec_root: Path) -> list[Path]:
        """Find markdown under specs/ and changes/, skipping junk dirs."""
        found: list[Path] = []
        seen: set[Path] = set()

        for sub in ("specs", "changes"):
            base = openspec_root / sub
            if not base.is_dir():
                continue
            self._walk_markdown(openspec_root, base, seen, found)

        return found

    def _walk_markdown(
        self,
        openspec_root: Path,
        directory: Path,
        seen: set[Path],
        found: list[Path],
    ) -> None:
        try:
            entries = list(directory.iterdir())
        except OSError as e:
            logger.warning(f"Failed to read directory {directory}: {e}")
            return

        for entry in entries:
            try:
                if entry.is_dir():
                    if entry.name in self.SKIP_DIRS:
                        continue
                    self._walk_markdown(openspec_root, entry, seen, found)
                elif entry.is_file() and entry.suffix.lower() in self.MARKDOWN_SUFFIXES:
                    key = entry.resolve()
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append(entry)
            except OSError as e:
                logger.warning(f"Failed to inspect {entry}: {e}")

    def _is_under_skip_dir(self, root: Path, file_path: Path) -> bool:
        try:
            relative = file_path.relative_to(root)
        except ValueError:
            return False
        return any(part in self.SKIP_DIRS for part in relative.parts)

    def _parse_markdown_file(self, file_path: Path, openspec_root: Path) -> list[SpecBlock]:
        """Parse one markdown file into SpecBlocks."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        if not content.strip():
            return blocks

        spec_type = self._infer_type(file_path, openspec_root)
        status = self._infer_status(file_path, openspec_root)
        base_tags = self._path_tags(file_path, openspec_root)

        sections = self._extract_sections(content)

        if sections:
            for section in sections:
                tags = list(base_tags)
                if section["title"]:
                    tags.append(self._slug(section["title"]))

                blocks.append(
                    SpecBlock(
                        id=SpecBlock.generate_id(source, section["content"]),
                        type=spec_type,
                        text=section["content"],
                        source=source,
                        status=status,
                        tags=tags,
                        links=[],
                        pinned=False,
                    )
                )
        elif re.search(r"^#{1,3}\s+.+", content, re.MULTILINE):
            # Headings exist but no usable body text
            return blocks
        else:
            blocks.append(
                SpecBlock(
                    id=SpecBlock.generate_id(source, content),
                    type=spec_type,
                    text=content,
                    source=source,
                    status=status,
                    tags=list(base_tags),
                    links=[],
                    pinned=True,
                )
            )

        return blocks

    def _infer_type(self, file_path: Path, openspec_root: Path) -> SpecType:
        """Map filename / path to SpecType when the role is clear."""
        name = file_path.name.lower()

        if name == "tasks.md":
            return SpecType.TASK
        if name == "design.md":
            return SpecType.DESIGN
        if name in {"spec.md", "specs.md"}:
            return SpecType.REQUIREMENT
        if name == "proposal.md":
            return SpecType.KNOWLEDGE

        # Domain specs live under openspec/specs/<domain>/
        try:
            relative = file_path.relative_to(openspec_root)
        except ValueError:
            return SpecType.MD

        parts = [p.lower() for p in relative.parts]
        if parts and parts[0] == "specs":
            return SpecType.REQUIREMENT
        if "specs" in parts and name.endswith(".md"):
            # Delta specs under changes/<name>/specs/
            return SpecType.REQUIREMENT

        return SpecType.KNOWLEDGE

    def _infer_status(self, file_path: Path, openspec_root: Path) -> SpecStatus:
        """Archived changes are legacy; everything else is active."""
        try:
            relative = file_path.relative_to(openspec_root)
        except ValueError:
            return SpecStatus.ACTIVE

        parts = [p.lower() for p in relative.parts]
        if "archive" in parts:
            return SpecStatus.LEGACY
        return SpecStatus.ACTIVE

    def _path_tags(self, file_path: Path, openspec_root: Path) -> list[str]:
        """Build tags from openspec + path segments."""
        tags = ["openspec"]
        try:
            relative = file_path.relative_to(openspec_root)
        except ValueError:
            tags.append(self._slug(file_path.stem))
            return tags

        parts = list(relative.parts)
        # Drop the filename; keep directory context
        for part in parts[:-1]:
            slug = self._slug(part)
            if slug and slug not in tags:
                tags.append(slug)

        stem_slug = self._slug(file_path.stem)
        if stem_slug and stem_slug not in tags:
            tags.append(stem_slug)

        # Helpful role tags
        name = file_path.name.lower()
        if name == "proposal.md" and "proposal" not in tags:
            tags.append("proposal")
        if name == "tasks.md" and "tasks" not in tags:
            tags.append("tasks")
        if name == "design.md" and "design" not in tags:
            tags.append("design")
        if "archive" in (p.lower() for p in parts) and "archive" not in tags:
            tags.append("archive")

        return tags

    def _parse_config(self, config_path: Path) -> list[SpecBlock]:
        """Index light config.yaml content as knowledge blocks.

        Reads ``context`` and stringifies ``rules`` / ``operations`` when
        present. Does not deeply validate the OpenSpec config schema.
        """
        blocks: list[SpecBlock] = []
        source = str(config_path)

        try:
            raw = config_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {config_path}: {e}")
            return blocks

        if not raw.strip():
            return blocks

        try:
            parsed = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse OpenSpec config.yaml: {e}")
            # Fall back to raw text as a single knowledge block
            return [
                SpecBlock(
                    id=SpecBlock.generate_id(source, raw),
                    type=SpecType.KNOWLEDGE,
                    text=raw.strip(),
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["openspec", "config"],
                    links=[],
                    pinned=False,
                )
            ]

        if not isinstance(parsed, dict):
            return blocks

        context = parsed.get("context")
        if isinstance(context, str) and context.strip():
            text = context.strip()
            blocks.append(
                SpecBlock(
                    id=SpecBlock.generate_id(source, f"context:{text}"),
                    type=SpecType.KNOWLEDGE,
                    text=text,
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["openspec", "config", "context"],
                    links=[],
                    pinned=True,
                )
            )

        rules = parsed.get("rules")
        if isinstance(rules, dict) and rules:
            rules_text = self._format_mapping("Planning rules", rules)
            if rules_text:
                blocks.append(
                    SpecBlock(
                        id=SpecBlock.generate_id(source, f"rules:{rules_text}"),
                        type=SpecType.KNOWLEDGE,
                        text=rules_text,
                        source=source,
                        status=SpecStatus.ACTIVE,
                        tags=["openspec", "config", "rules"],
                        links=[],
                        pinned=False,
                    )
                )

        operations = parsed.get("operations")
        if isinstance(operations, dict) and operations:
            ops_text = self._format_mapping("Operations guidance", operations)
            if ops_text:
                blocks.append(
                    SpecBlock(
                        id=SpecBlock.generate_id(source, f"operations:{ops_text}"),
                        type=SpecType.KNOWLEDGE,
                        text=ops_text,
                        source=source,
                        status=SpecStatus.ACTIVE,
                        tags=["openspec", "config", "operations"],
                        links=[],
                        pinned=False,
                    )
                )

        # If nothing useful was extracted but schema is set, note it lightly
        if not blocks:
            schema = parsed.get("schema")
            if schema:
                text = f"OpenSpec schema: {schema}"
                blocks.append(
                    SpecBlock(
                        id=SpecBlock.generate_id(source, text),
                        type=SpecType.KNOWLEDGE,
                        text=text,
                        source=source,
                        status=SpecStatus.ACTIVE,
                        tags=["openspec", "config", "schema"],
                        links=[],
                        pinned=False,
                    )
                )

        return blocks

    @staticmethod
    def _format_mapping(title: str, mapping: dict[str, Any]) -> str:
        """Render a shallow dict of lists/strings into readable markdown."""
        lines = [title, ""]
        for key, value in mapping.items():
            lines.append(f"## {key}")
            if isinstance(value, list):
                for item in value:
                    lines.append(f"- {item}")
            elif isinstance(value, str):
                lines.append(value.strip())
            else:
                lines.append(str(value))
            lines.append("")
        text = "\n".join(lines).strip()
        return text if text != title else ""

    def _extract_sections(self, content: str) -> list[dict[str, str]]:
        """Split content on markdown # / ## / ### headings."""
        sections: list[dict[str, str]] = []
        header_pattern = r"^(#{1,3})\s+(.+)$"

        current_section: dict[str, str] | None = None
        current_content: list[str] = []

        for line in content.split("\n"):
            header_match = re.match(header_pattern, line)
            if header_match:
                if current_section is not None:
                    current_section["content"] = "\n".join(current_content).strip()
                    if current_section["content"]:
                        sections.append(current_section)

                current_section = {
                    "title": header_match.group(2).strip(),
                    "content": "",
                }
                current_content = []
            else:
                current_content.append(line)

        if current_section is not None:
            current_section["content"] = "\n".join(current_content).strip()
            if current_section["content"]:
                sections.append(current_section)

        return sections

    @staticmethod
    def _slug(title: str) -> str:
        """Turn a path segment or heading into a short tag slug."""
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        return slug[:40]
