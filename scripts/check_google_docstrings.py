"""Check that Python modules, classes, and functions include docstrings."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TARGETS = ("src", "examples", "scripts")
SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}


@dataclass(frozen=True, slots=True)
class MissingDocstring:
    """Represent a missing docstring found during validation.

    Args:
        path: The Python file containing the missing docstring.
        target: The module, class, or function name.
        kind: The AST node type.
    """

    path: Path
    target: str
    kind: str


def iter_python_files(targets: tuple[str, ...]) -> tuple[Path, ...]:
    """Collect Python files from the configured target directories.

    Args:
        targets: Directory names to scan.

    Returns:
        All discovered Python files in sorted order.
    """
    files: list[Path] = []
    for target in targets:
        root = Path(target)
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
    return tuple(sorted(files))


def _collect_from_body(
    path: Path,
    body: list[ast.stmt],
    parents: tuple[str, ...],
) -> list[MissingDocstring]:
    """Collect missing docstrings from a list of AST statements.

    Args:
        path: The source file path.
        body: Statements to inspect.
        parents: Parent names used to build qualified names.

    Returns:
        Any missing docstring records discovered in the body.
    """
    missing: list[MissingDocstring] = []
    for node in body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            qualified_name = ".".join((*parents, node.name))
            if ast.get_docstring(node) is None:
                missing.append(
                    MissingDocstring(
                        path=path,
                        target=qualified_name,
                        kind=type(node).__name__,
                    )
                )
            missing.extend(_collect_from_body(path, node.body, (*parents, node.name)))
    return missing


def collect_missing_docstrings(path: Path) -> list[MissingDocstring]:
    """Inspect one Python file for missing docstrings.

    Args:
        path: The file to inspect.

    Returns:
        Any missing docstring records.

    Raises:
        SyntaxError: Raised if the file cannot be parsed.
    """
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    missing: list[MissingDocstring] = []
    if ast.get_docstring(module) is None:
        missing.append(MissingDocstring(path=path, target="<module>", kind="Module"))
    missing.extend(_collect_from_body(path, module.body, ()))
    return missing


def main() -> int:
    """Run the docstring validation script.

    Returns:
        Process exit code: `0` on success and `1` on failure.
    """
    missing: list[MissingDocstring] = []
    for path in iter_python_files(DEFAULT_TARGETS):
        missing.extend(collect_missing_docstrings(path))

    if missing:
        for item in missing:
            print(f"{item.path}: missing docstring for {item.kind} {item.target}")
        return 1
    print("Docstring checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
