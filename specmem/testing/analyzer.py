"""Code Analyzer for spec inference.

Analyzes code files to extract symbols and infer potential specifications.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specmem.core import CodeRef, SpecBlock, SpecType


logger = logging.getLogger(__name__)


@dataclass
class Symbol:
    """Extracted code symbol (function, class, etc.)."""

    name: str
    kind: str  # function, class, method
    docstring: str | None = None
    line_start: int = 0
    line_end: int = 0
    signature: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "kind": self.kind,
            "docstring": self.docstring,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "signature": self.signature,
        }


@dataclass
class CodeAnalysis:
    """Result of analyzing a code file."""

    file_path: str
    language: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "file_path": self.file_path,
            "language": self.language,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": self.imports,
            "dependencies": self.dependencies,
        }


@dataclass
class SpecCandidate:
    """Candidate spec inferred from code.

    Represents a potential specification that could be created
    based on code analysis.
    """

    suggested_id: str
    title: str
    spec_type: SpecType
    confidence: float
    rationale: str
    code_refs: list[CodeRef] = field(default_factory=list)
    suggested_content: str = ""
    matched_spec_id: str | None = None

    def __post_init__(self) -> None:
        """Validate fields."""
        if not self.suggested_id:
            raise ValueError("suggested_id cannot be empty")
        if not self.title:
            raise ValueError("title cannot be empty")
        if not self.rationale:
            raise ValueError("rationale cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "suggested_id": self.suggested_id,
            "title": self.title,
            "spec_type": self.spec_type.value,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "code_refs": [r.to_dict() for r in self.code_refs],
            "suggested_content": self.suggested_content,
            "matched_spec_id": self.matched_spec_id,
        }


class CodeAnalyzer:
    """Analyzes code to infer specifications.

    Supports Python, JavaScript, and TypeScript.
    """

    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
    }

    def __init__(self, workspace_path: Path | str) -> None:
        """Initialize the code analyzer.

        Args:
            workspace_path: Path to the workspace root
        """
        self.workspace_path = Path(workspace_path).resolve()

    def analyze_file(self, path: Path | str) -> CodeAnalysis:
        """Analyze a code file.

        Args:
            path: Path to the code file

        Returns:
            CodeAnalysis with extracted information
        """
        path = Path(path)
        if not path.is_absolute():
            path = self.workspace_path / path

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        language = self._detect_language(path)
        content = path.read_text()
        rel_path = str(path.relative_to(self.workspace_path))

        if language == "python":
            return self._analyze_python(content, rel_path)
        elif language in ("javascript", "typescript"):
            return self._analyze_javascript(content, rel_path, language)
        else:
            return CodeAnalysis(file_path=rel_path, language=language)

    def extract_symbols(self, content: str, language: str) -> list[Symbol]:
        """Extract function/class definitions from code.

        Args:
            content: Code content
            language: Programming language

        Returns:
            List of extracted Symbol objects
        """
        if language == "python":
            return self._extract_python_symbols(content)
        elif language in ("javascript", "typescript"):
            return self._extract_js_symbols(content)
        else:
            return []

    def infer_specs(
        self,
        path: Path | str,
        existing_specs: list[SpecBlock] | None = None,
    ) -> list[SpecCandidate]:
        """Infer potential specs from a code file.

        Args:
            path: Path to the code file
            existing_specs: Optional list of existing specs to match against

        Returns:
            List of SpecCandidate objects
        """
        analysis = self.analyze_file(path)
        candidates: list[SpecCandidate] = []

        for symbol in analysis.symbols:
            candidate = self._create_candidate_from_symbol(
                symbol,
                analysis.file_path,
                analysis.language,
            )

            if candidate:
                # Try to match against existing specs
                if existing_specs:
                    matched = self._match_to_existing_spec(candidate, existing_specs)
                    if matched:
                        candidate.matched_spec_id = matched.id
                        candidate.confidence = min(candidate.confidence + 0.2, 1.0)

                candidates.append(candidate)

        # Sort by confidence
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates

    def _detect_language(self, path: Path) -> str:
        """Detect programming language from file extension."""
        return self.LANGUAGE_EXTENSIONS.get(path.suffix.lower(), "unknown")

    def _analyze_python(self, content: str, file_path: str) -> CodeAnalysis:
        """Analyze Python code."""
        symbols = self._extract_python_symbols(content)
        imports = self._extract_python_imports(content)

        return CodeAnalysis(
            file_path=file_path,
            language="python",
            symbols=symbols,
            imports=imports,
        )

    def _extract_python_symbols(self, content: str) -> list[Symbol]:
        """Extract symbols from Python code using AST."""
        symbols: list[Symbol] = []

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Failed to parse Python code: {e}")
            return symbols

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node)
                signature = self._get_python_signature(node)
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="function",
                        docstring=docstring,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        signature=signature,
                    )
                )
            elif isinstance(node, ast.AsyncFunctionDef):
                docstring = ast.get_docstring(node)
                signature = self._get_python_signature(node)
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="async_function",
                        docstring=docstring,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        signature=signature,
                    )
                )
            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node)
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="class",
                        docstring=docstring,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                    )
                )

        return symbols

    def _get_python_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Get function signature from AST node."""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        return f"{node.name}({', '.join(args)})"

    def _extract_python_imports(self, content: str) -> list[str]:
        """Extract imports from Python code."""
        imports: list[str] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        return imports

    def _analyze_javascript(
        self,
        content: str,
        file_path: str,
        language: str,
    ) -> CodeAnalysis:
        """Analyze JavaScript/TypeScript code."""
        symbols = self._extract_js_symbols(content)
        imports = self._extract_js_imports(content)

        return CodeAnalysis(
            file_path=file_path,
            language=language,
            symbols=symbols,
            imports=imports,
        )

    def _extract_js_symbols(self, content: str) -> list[Symbol]:
        """Extract symbols from JavaScript/TypeScript code using regex."""
        symbols: list[Symbol] = []

        # Function declarations
        func_pattern = r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)"
        for match in re.finditer(func_pattern, content):
            name = match.group(1)
            params = match.group(2)
            line = content[: match.start()].count("\n") + 1

            # Look for JSDoc comment before function
            docstring = self._extract_jsdoc(content, match.start())

            symbols.append(
                Symbol(
                    name=name,
                    kind="function",
                    docstring=docstring,
                    line_start=line,
                    signature=f"{name}({params})",
                )
            )

        # Arrow functions assigned to const/let
        arrow_pattern = r"(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>"
        for match in re.finditer(arrow_pattern, content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            docstring = self._extract_jsdoc(content, match.start())

            symbols.append(
                Symbol(
                    name=name,
                    kind="function",
                    docstring=docstring,
                    line_start=line,
                )
            )

        # Class declarations
        class_pattern = r"(?:export\s+)?class\s+(\w+)"
        for match in re.finditer(class_pattern, content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            docstring = self._extract_jsdoc(content, match.start())

            symbols.append(
                Symbol(
                    name=name,
                    kind="class",
                    docstring=docstring,
                    line_start=line,
                )
            )

        return symbols

    def _extract_jsdoc(self, content: str, position: int) -> str | None:
        """Extract JSDoc comment before a position."""
        # Look backwards for /** ... */
        before = content[:position].rstrip()
        if before.endswith("*/"):
            start = before.rfind("/**")
            if start != -1:
                comment = before[start:].strip()
                # Clean up the comment
                lines = comment.split("\n")
                cleaned = []
                for line in lines:
                    line = line.strip()
                    line = line.removeprefix("/**")
                    line = line.removesuffix("*/")
                    line = line.removeprefix("*")
                    line = line.strip()
                    if line:
                        cleaned.append(line)
                return " ".join(cleaned) if cleaned else None
        return None

    def _extract_js_imports(self, content: str) -> list[str]:
        """Extract imports from JavaScript/TypeScript code."""
        imports: list[str] = []

        # ES6 imports
        import_pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1))

        # require statements
        require_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
        for match in re.finditer(require_pattern, content):
            imports.append(match.group(1))

        return imports

    def _create_candidate_from_symbol(
        self,
        symbol: Symbol,
        file_path: str,
        language: str,
    ) -> SpecCandidate | None:
        """Create a SpecCandidate from a Symbol."""
        # Skip private/internal symbols
        if symbol.name.startswith("_"):
            return None

        # Determine spec type based on symbol kind
        if symbol.kind == "class":
            spec_type = SpecType.DESIGN
            title = f"Class: {symbol.name}"
        else:
            spec_type = SpecType.REQUIREMENT
            title = f"Function: {symbol.name}"

        # Generate suggested ID
        suggested_id = f"{file_path.replace('/', '.').replace('.py', '').replace('.ts', '').replace('.js', '')}.{symbol.name}"

        # Calculate confidence based on available information
        confidence = 0.5
        if symbol.docstring:
            confidence += 0.3
        if symbol.signature:
            confidence += 0.1

        # Generate rationale
        rationale_parts = [f"Found {symbol.kind} '{symbol.name}' in {file_path}"]
        if symbol.docstring:
            rationale_parts.append(f"Has documentation: {symbol.docstring[:100]}...")
        else:
            rationale_parts.append("No documentation found")

        # Generate suggested content
        content_parts = [f"# {title}", ""]
        if symbol.docstring:
            content_parts.append(f"## Description\n\n{symbol.docstring}")
        if symbol.signature:
            content_parts.append(f"## Signature\n\n```{language}\n{symbol.signature}\n```")

        code_ref = CodeRef(
            language=language,
            file_path=file_path,
            symbols=[symbol.name],
            line_range=(symbol.line_start, symbol.line_end) if symbol.line_end else None,
            confidence=confidence,
        )

        return SpecCandidate(
            suggested_id=suggested_id,
            title=title,
            spec_type=spec_type,
            confidence=confidence,
            rationale=" ".join(rationale_parts),
            code_refs=[code_ref],
            suggested_content="\n".join(content_parts),
        )

    def _match_to_existing_spec(
        self,
        candidate: SpecCandidate,
        existing_specs: list[SpecBlock],
    ) -> SpecBlock | None:
        """Try to match a candidate to an existing spec."""
        # Simple matching based on name similarity
        candidate.title.lower()

        for spec in existing_specs:
            spec_text = spec.text.lower()

            # Check if candidate name appears in spec
            if candidate.suggested_id.split(".")[-1].lower() in spec_text:
                return spec

            # Check if spec mentions the function/class
            for ref in candidate.code_refs:
                for symbol in ref.symbols:
                    if symbol.lower() in spec_text:
                        return spec

        return None
