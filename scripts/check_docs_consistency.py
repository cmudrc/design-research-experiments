"""Run a few lightweight consistency checks for the docs tree."""

from __future__ import annotations

import ast
import re
from pathlib import Path

DOCS_DIR = Path("docs")
INDEX_PATH = DOCS_DIR / "index.rst"
API_PATH = DOCS_DIR / "api.rst"
README_PATH = Path("README.md")
PUBLIC_API_PATH = Path("src/design_research_experiments/__init__.py")
EXAMPLES_DIR = Path("examples")
EXAMPLES_README_PATH = EXAMPLES_DIR / "README.md"

_API_EXPORT_BULLET_PATTERN = re.compile(
    r"^- ``([A-Za-z_][A-Za-z0-9_]*)``\s*$",
    re.MULTILINE,
)
_EXAMPLE_INVENTORY_PATTERN = re.compile(r"^- `([^`\n]+\.py)`:", re.MULTILINE)


def _normalize_toctree_entry(entry: str) -> str | None:
    """Return one internal toctree target when the entry points at a docs page.

    Args:
        entry: Raw toctree entry line content.

    Returns:
        Internal document target without the ``.rst`` suffix, or ``None`` for
        external links.
    """
    normalized = entry.strip()
    if "<" in normalized and normalized.endswith(">"):
        _, _, remainder = normalized.rpartition("<")
        normalized = remainder[:-1].strip()
    if "://" in normalized or normalized.startswith("mailto:"):
        return None
    return normalized.removesuffix(".rst")


def extract_toctree_entries(index_path: Path) -> tuple[str, ...]:
    """Extract internal document entries from all toctrees in `index.rst`.

    Args:
        index_path: Path to the docs index file.

    Returns:
        Referenced internal document names without suffixes.
    """
    entries: list[str] = []
    in_toctree = False
    for line in index_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == ".. toctree::":
            in_toctree = True
            continue
        if not in_toctree:
            continue
        if not stripped:
            continue
        if stripped.startswith(":"):
            continue
        if line.startswith("   "):
            normalized = _normalize_toctree_entry(stripped)
            if normalized is not None:
                entries.append(normalized)
            continue
        in_toctree = False
    return tuple(entries)


def extract_public_exports(init_path: Path) -> tuple[str, ...]:
    """Read the literal top-level ``__all__`` declaration from a module.

    Args:
        init_path: Path to the package ``__init__.py`` file.

    Returns:
        Public export names in declaration order.

    Raises:
        ValueError: If the module has no literal string ``__all__`` sequence.
    """
    module = ast.parse(init_path.read_text(encoding="utf-8"))
    for node in module.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
            continue
        value = node.value
        if not isinstance(value, (ast.List, ast.Tuple)):
            break
        exports = tuple(
            item.value
            for item in value.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        )
        if len(exports) == len(value.elts):
            return exports
        break
    raise ValueError(f"{init_path} has no literal string __all__ sequence")


def extract_documented_api_names(api_path: Path) -> frozenset[str]:
    """Return names from the API page's exact one-export-per-bullet inventory."""
    return frozenset(_API_EXPORT_BULLET_PATTERN.findall(api_path.read_text(encoding="utf-8")))


def find_api_inventory_differences(
    init_path: Path,
    api_path: Path,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return public API exports missing from docs and stale documented exports."""
    expected = set(extract_public_exports(init_path))
    documented = set(extract_documented_api_names(api_path))
    return tuple(sorted(expected - documented)), tuple(sorted(documented - expected))


def extract_documented_example_paths(readme_path: Path) -> frozenset[str]:
    """Return paths from exact ``- `path.py`:`` example inventory bullets."""
    return frozenset(_EXAMPLE_INVENTORY_PATTERN.findall(readme_path.read_text(encoding="utf-8")))


def discover_example_paths(examples_dir: Path) -> frozenset[str]:
    """Return runnable Python example paths relative to ``examples/``."""
    return frozenset(
        path.relative_to(examples_dir).as_posix()
        for path in examples_dir.rglob("*.py")
        if not path.name.startswith("_") and "__pycache__" not in path.parts
    )


def find_example_inventory_differences(
    examples_dir: Path,
    readme_path: Path,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return runnable examples missing from README and stale documented paths."""
    expected = set(discover_example_paths(examples_dir))
    documented = set(extract_documented_example_paths(readme_path))
    return tuple(sorted(expected - documented)), tuple(sorted(documented - expected))


def validate_docs_tree() -> list[str]:
    """Collect any missing or inconsistent documentation references.

    Returns:
        A list of validation error messages.
    """
    errors: list[str] = []
    if not README_PATH.exists():
        errors.append("README.md is missing.")
    if not INDEX_PATH.exists():
        errors.append("docs/index.rst is missing.")
        return errors

    for entry in extract_toctree_entries(INDEX_PATH):
        if not (DOCS_DIR / f"{entry}.rst").exists():
            errors.append(f"docs/index.rst references missing document: {entry}.rst")

    if not API_PATH.exists():
        errors.append("docs/api.rst is missing.")
    else:
        api_text = API_PATH.read_text(encoding="utf-8")
        if "design_research_experiments" not in api_text:
            errors.append("docs/api.rst does not reference the package module.")
        if not PUBLIC_API_PATH.exists():
            errors.append(f"{PUBLIC_API_PATH} is missing.")
        else:
            try:
                missing_exports, stale_exports = find_api_inventory_differences(
                    PUBLIC_API_PATH,
                    API_PATH,
                )
            except (SyntaxError, ValueError) as exc:
                errors.append(str(exc))
            else:
                if missing_exports:
                    errors.append(f"docs/api.rst omits public exports: {list(missing_exports)}")
                if stale_exports:
                    errors.append(f"docs/api.rst lists non-public exports: {list(stale_exports)}")

    if not EXAMPLES_DIR.exists():
        errors.append(f"{EXAMPLES_DIR} is missing.")
    elif not EXAMPLES_README_PATH.exists():
        errors.append(f"{EXAMPLES_README_PATH} is missing.")
    else:
        missing_examples, stale_examples = find_example_inventory_differences(
            EXAMPLES_DIR,
            EXAMPLES_README_PATH,
        )
        if missing_examples:
            errors.append(f"examples/README.md omits checked-in examples: {list(missing_examples)}")
        if stale_examples:
            errors.append(f"examples/README.md lists missing examples: {list(stale_examples)}")
    return errors


def main() -> int:
    """Run the docs consistency check.

    Returns:
        Process exit code: `0` on success and `1` on failure.
    """
    errors = validate_docs_tree()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
