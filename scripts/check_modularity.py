"""Check CI-10 modularity limits: file <= 500 lines and function <= 50 lines."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

MAX_FILE_LINES = 500
MAX_FUNCTION_LINES = 50

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "graphify-out",
}


def iter_python_files(root: Path):
    """Yield project Python files, skipping virtualenvs and tool caches."""
    for path in sorted(root.rglob("*.py")):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def file_violations(path: Path) -> list[str]:
    """Return CI-10 violations found in a single Python file."""
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []
    file_lines = len(text.splitlines())
    if file_lines > MAX_FILE_LINES:
        violations.append(f"{path}: file has {file_lines} lines (max {MAX_FILE_LINES})")

    for node in ast.walk(ast.parse(text, filename=str(path))):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        length = node.end_lineno - node.lineno + 1
        if length > MAX_FUNCTION_LINES:
            violations.append(
                f"{path}:{node.lineno}: function '{node.name}' has {length} lines "
                f"(max {MAX_FUNCTION_LINES})"
            )
    return violations


def find_violations(root: Path) -> list[str]:
    """Return all CI-10 violations under the given project root."""
    violations: list[str] = []
    for path in iter_python_files(root):
        violations.extend(file_violations(path))
    return violations


def main(root: str = ".") -> int:
    """Run the modularity check; return a non-zero exit code on violations."""
    root_path = Path(root).resolve()
    violations = find_violations(root_path)
    if not violations:
        print(f"OK: all files <= {MAX_FILE_LINES} lines and functions <= {MAX_FUNCTION_LINES} lines")
        return 0
    for violation in violations:
        print(violation)
    print(f"FAILED: {len(violations)} modularity violation(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
