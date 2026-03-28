"""Check public API usage coverage across example files."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = REPO_ROOT / "examples"
PUBLIC_API_INIT = REPO_ROOT / "src" / "design_research_experiments" / "__init__.py"


def _discover_examples() -> list[Path]:
    """Return Python scripts and notebooks under ``examples``."""
    python_examples = sorted(EXAMPLES_ROOT.rglob("*.py"))
    notebook_examples = sorted(EXAMPLES_ROOT.rglob("*.ipynb"))
    return python_examples + notebook_examples


def _extract_exports(path: Path) -> list[str]:
    """Extract public ``__all__`` exports from the package module."""
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
            and isinstance(node.value, (ast.List, ast.Tuple))
        ):
            names: list[str] = []
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    names.append(elt.value)
            return names
    return []


def _usage_from_source(source: str, exports: set[str]) -> set[str]:
    """Return exported symbols referenced by one Python source string."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    hits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in exports:
            hits.add(node.id)
        if isinstance(node, ast.Attribute) and node.attr in exports:
            hits.add(node.attr)
    return hits


def _usage_from_notebook(path: Path, exports: set[str]) -> set[str]:
    """Return exported symbols referenced in code cells of one notebook."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    cells = payload.get("cells", [])
    hits: set[str] = set()
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        cell_source = "".join(source) if isinstance(source, list) else str(source)
        hits.update(_usage_from_source(cell_source, exports))
    return hits


def main() -> int:
    """Compute example API-usage coverage and enforce a threshold."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimum", type=float, default=90.0)
    args = parser.parse_args()

    exports = _extract_exports(PUBLIC_API_INIT)
    if not exports:
        raise ValueError("Failed to extract __all__ exports from package __init__.py")
    export_set = set(exports)

    examples = _discover_examples()
    if not examples:
        raise ValueError("No examples found under examples/.")

    covered: set[str] = set()
    for example in examples:
        if example.suffix == ".py":
            covered.update(_usage_from_source(example.read_text(encoding="utf-8"), export_set))
        elif example.suffix == ".ipynb":
            covered.update(_usage_from_notebook(example, export_set))

    coverage_percent = (len(covered) / len(exports)) * 100.0 if exports else 100.0
    missing = sorted(export_set - covered)

    print(f"Example API coverage: {coverage_percent:.1f}% ({len(covered)}/{len(exports)})")
    if missing:
        print("Missing exports in examples:")
        for symbol in missing:
            print(f"- {symbol}")

    if coverage_percent < args.minimum:
        print(f"Coverage threshold failed: {coverage_percent:.1f}% < {args.minimum:.1f}%")
        return 1

    print("Example API coverage threshold passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
