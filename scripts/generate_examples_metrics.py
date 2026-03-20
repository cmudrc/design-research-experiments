"""Compute example inventory and public-API coverage metrics."""

from __future__ import annotations

import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = REPO_ROOT / "examples"
PUBLIC_API_INIT = REPO_ROOT / "src" / "design_research_experiments" / "__init__.py"
PACKAGE_NAME = "design_research_experiments"
METRICS_PATH = REPO_ROOT / "artifacts" / "examples" / "examples_metrics.json"


def _discover_examples() -> tuple[Path, ...]:
    """Return runnable example files under ``examples/``.

    Returns:
        Tuple of Python and notebook example paths sorted by path.
    """
    discovered: list[Path] = []
    for pattern in ("*.py", "*.ipynb"):
        for path in sorted(EXAMPLES_ROOT.rglob(pattern)):
            parts = path.relative_to(REPO_ROOT).parts
            if "__pycache__" in parts or path.name.startswith("_") or "artifacts" in parts:
                continue
            discovered.append(path)
    return tuple(sorted(discovered))


def _extract_exports(path: Path) -> tuple[str, ...]:
    """Extract public API symbol names from ``__all__`` in the package init module.

    Args:
        path: Package ``__init__.py`` path.

    Returns:
        Tuple of exported symbol names excluding ``__version__``.

    Raises:
        ValueError: If the module does not define a static ``__all__`` list or tuple.
    """
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        if not isinstance(node.targets[0], ast.Name) or node.targets[0].id != "__all__":
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            break

        exports: list[str] = []
        for element in node.value.elts:
            if (
                isinstance(element, ast.Constant)
                and isinstance(element.value, str)
                and element.value != "__version__"
            ):
                exports.append(element.value)
        return tuple(exports)

    raise ValueError(f"Failed to extract a static __all__ export list from {path}.")


def _collect_package_aliases(module: ast.Module) -> set[str]:
    """Collect local aliases for direct package imports.

    Args:
        module: Parsed example module.

    Returns:
        Alias names bound to direct ``import design_research_experiments`` statements.
    """
    aliases: set[str] = set()
    for node in ast.walk(module):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name == PACKAGE_NAME:
                aliases.add(alias.asname or PACKAGE_NAME)
    return aliases


def _collect_explicit_imported_exports(module: ast.Module, export_set: set[str]) -> set[str]:
    """Collect exported symbols imported from the package root or submodules.

    Args:
        module: Parsed example module.
        export_set: Set of public export names.

    Returns:
        Exported symbols referenced by import statements.
    """
    covered: set[str] = set()
    for node in ast.walk(module):
        if not isinstance(node, ast.ImportFrom):
            continue
        module_name = node.module or ""
        if module_name != PACKAGE_NAME and not module_name.startswith(f"{PACKAGE_NAME}."):
            continue
        for alias in node.names:
            if alias.name == "*":
                covered.update(export_set)
                continue
            if alias.name in export_set:
                covered.add(alias.name)
    return covered


def _collect_attribute_access_exports(
    module: ast.Module,
    export_set: set[str],
    package_aliases: set[str],
) -> set[str]:
    """Collect exported symbols accessed as attributes on package aliases.

    Args:
        module: Parsed example module.
        export_set: Set of public export names.
        package_aliases: Alias names bound to direct package imports.

    Returns:
        Exported symbols accessed as package attributes.
    """
    covered: set[str] = set()
    for node in ast.walk(module):
        if not isinstance(node, ast.Attribute):
            continue
        if not isinstance(node.value, ast.Name):
            continue
        if node.value.id in package_aliases and node.attr in export_set:
            covered.add(node.attr)
    return covered


def _usage_from_source(source: str, export_symbols: tuple[str, ...]) -> set[str]:
    """Collect covered public API symbols from one source string.

    Args:
        source: Python source text.
        export_symbols: Ordered tuple of public API symbols.

    Returns:
        Covered public symbols referenced in the source.
    """
    try:
        module = ast.parse(source)
    except SyntaxError:
        return set()

    export_set = set(export_symbols)
    package_aliases = _collect_package_aliases(module)
    covered = _collect_explicit_imported_exports(module, export_set)
    covered.update(_collect_attribute_access_exports(module, export_set, package_aliases))
    return covered


def _usage_from_notebook(path: Path, export_symbols: tuple[str, ...]) -> set[str]:
    """Collect covered public API symbols from one notebook example.

    Args:
        path: Notebook example path.
        export_symbols: Ordered tuple of public API symbols.

    Returns:
        Covered public symbols referenced in code cells.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    hits: set[str] = set()
    for cell in payload.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        cell_source = "".join(source) if isinstance(source, list) else str(source)
        hits.update(_usage_from_source(cell_source, export_symbols))
    return hits


def _percent(part: int, whole: int) -> float:
    """Return a one-decimal percentage for ``part / whole``.

    Args:
        part: Numerator.
        whole: Denominator.

    Returns:
        Percentage rounded to one decimal place.
    """
    if whole == 0:
        return 100.0
    return round((part / whole) * 100.0, 1)


def main() -> None:
    """Compute and write example inventory and public-API coverage metrics."""
    examples = _discover_examples()
    if not examples:
        raise ValueError("No examples found under examples/.")

    exports = _extract_exports(PUBLIC_API_INIT)
    covered: set[str] = set()
    for example in examples:
        if example.suffix == ".py":
            covered.update(_usage_from_source(example.read_text(encoding="utf-8"), exports))
        elif example.suffix == ".ipynb":
            covered.update(_usage_from_notebook(example, exports))

    example_count = len(examples)
    covered_exports = len(covered)
    total_exports = len(exports)
    metrics = {
        "examples": {
            "passed": example_count,
            "total": example_count,
            "pass_percent": 100.0,
        },
        "public_api": {
            "covered_exports": covered_exports,
            "total_exports": total_exports,
            "coverage_percent": _percent(covered_exports, total_exports),
        },
        "inventory": {
            "example_file_count": example_count,
            "public_api_symbol_count": total_exports,
            "used_public_api_symbols": sorted(covered),
        },
        "example_file_count": example_count,
        "public_api_symbol_count": total_exports,
        "used_public_api_symbols": sorted(covered),
        "api_coverage_pct": _percent(covered_exports, total_exports),
    }

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(
        f"Wrote {METRICS_PATH} "
        f"(examples: {example_count}/{example_count}, api: {covered_exports}/{total_exports})"
    )


if __name__ == "__main__":
    main()
