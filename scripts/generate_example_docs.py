#!/usr/bin/env python3
"""Generate per-example Sphinx pages from canonical top-of-file docstrings."""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path

REQUIRED_SECTIONS = (
    "Introduction",
    "Technical Implementation",
    "Expected Results",
)

SUPPORTED_SECTIONS = (*REQUIRED_SECTIONS, "References")

CATEGORY_ORDER = ("core", "doe", "recipes")

CATEGORY_TITLES = {
    "core": "Core Examples",
    "doe": "DOE Examples",
    "recipes": "Recipe Run Examples",
}

TITLE_TOKEN_OVERRIDES = {
    "api": "API",
    "doe": "DOE",
}


@dataclass(slots=True, frozen=True)
class ExampleDocSpec:
    """One parsed example docs specification."""

    rel_path: str
    category: str
    slug: str
    title: str
    source_start_line: int
    sections: dict[str, str]


def _repo_root() -> Path:
    """Return repository root path."""
    return Path(__file__).resolve().parents[1]


def _discover_examples(repo_root: Path) -> list[Path]:
    """Discover runnable Python examples under ``examples/``."""
    examples_root = repo_root / "examples"
    discovered: list[Path] = []
    for path in sorted(examples_root.rglob("*.py")):
        rel_parts = path.relative_to(examples_root).parts
        if "__pycache__" in rel_parts:
            continue
        if path.name.startswith("_"):
            continue
        discovered.append(path)
    return discovered


def _parse_python_doc_text(path: Path) -> tuple[str, int]:
    """Parse module docstring text and first source line after docstring."""
    source = path.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(path))
    docstring = ast.get_docstring(module, clean=False)
    if not isinstance(docstring, str) or not docstring.strip():
        raise ValueError(f"{path}: missing module docstring.")

    source_start_line = 1
    if module.body:
        first = module.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            and isinstance(first.end_lineno, int)
        ):
            source_start_line = first.end_lineno + 1

    lines = source.splitlines()
    while source_start_line <= len(lines) and not lines[source_start_line - 1].strip():
        source_start_line += 1

    return docstring, source_start_line


def _parse_canonical_sections(*, doc_text: str, source_path: Path) -> dict[str, str]:
    """Parse canonical docs sections from one example docstring."""
    heading_pattern = re.compile(r"^##\s+(.+?)\s*$")
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for raw_line in doc_text.splitlines():
        line = raw_line.rstrip()
        match = heading_pattern.match(line.strip())
        if match is not None:
            heading = match.group(1).strip()
            if heading in SUPPORTED_SECTIONS:
                current = heading
                sections[current] = []
            else:
                current = None
            continue
        if current is not None:
            sections[current].append(line)

    missing = [section for section in REQUIRED_SECTIONS if section not in sections]
    if missing:
        raise ValueError(f"{source_path}: missing canonical section(s): {missing}")

    return {name: "\n".join(sections[name]).strip() for name in sections}


def _category_for_example(path: Path) -> str:
    """Classify one example into a docs category."""
    stem = path.stem
    if stem.startswith("recipe_"):
        return "recipes"
    if "doe" in stem:
        return "doe"
    return "core"


def _slug_for_example(path: Path) -> str:
    """Build deterministic docs slug for one example path."""
    return path.stem


def _title_for_example(path: Path) -> str:
    """Build human-readable page title for one example path."""
    title_parts: list[str] = []
    for token in path.stem.replace("-", "_").split("_"):
        normalized = token.strip().lower()
        if not normalized:
            continue
        title_parts.append(TITLE_TOKEN_OVERRIDES.get(normalized, normalized.capitalize()))
    return " ".join(title_parts)


def _render_optional_section(heading: str, body: str | None) -> list[str]:
    """Render one optional RST section block."""
    normalized = (body or "").strip()
    if not normalized:
        return []
    return [
        heading,
        "-" * len(heading),
        "",
        normalized,
        "",
    ]


def _render_example_page(spec: ExampleDocSpec) -> str:
    """Render one example page as RST."""
    include_path = f"../../../{spec.rel_path}"
    run_command = f"PYTHONPATH=src python {spec.rel_path}"

    introduction = spec.sections["Introduction"]
    technical_implementation = spec.sections["Technical Implementation"]
    expected_results = spec.sections["Expected Results"]
    references = spec.sections.get("References")

    lines = [
        spec.title,
        "=" * len(spec.title),
        "",
        f"Source: ``{spec.rel_path}``",
        "",
        "Introduction",
        "------------",
        "",
        introduction,
        "",
        "Technical Implementation",
        "------------------------",
        "",
        technical_implementation,
        "",
        f".. literalinclude:: {include_path}",
        "   :language: python",
        f"   :lines: {spec.source_start_line}-",
        "   :linenos:",
        "",
        "Expected Results",
        "----------------",
        "",
        ".. rubric:: Run Command",
        "",
        ".. code-block:: bash",
        "",
        f"   {run_command}",
        "",
        expected_results,
        "",
    ]

    lines.extend(_render_optional_section("References", references))
    return "\n".join(lines)


def _render_category_index(category: str, entries: list[ExampleDocSpec]) -> str:
    """Render one category index page as RST."""
    title = CATEGORY_TITLES[category]
    lines = [
        title,
        "=" * len(title),
        "",
        f"Generated from canonical top-of-file docstrings in ``examples`` ({category}).",
        "",
        ".. toctree::",
        "   :maxdepth: 1",
        "",
    ]
    for entry in entries:
        lines.append(f"   {entry.slug}")
    lines.append("")
    return "\n".join(lines)


def _render_examples_index() -> str:
    """Render top-level examples index page as RST."""
    title = "Examples"
    return "\n".join(
        [
            title,
            "=" * len(title),
            "",
            "These runnable examples show how the package behaves in realistic experimental",
            "workflows, from compact study definitions to recipe-backed runs that move",
            "artifacts through the broader ecosystem.",
            "",
            ".. note::",
            "",
            "   **Start with** :doc:`core/basic_usage` if you want the shortest path from",
            "   package import to a concrete study definition and materialized condition set.",
            "",
            "Core API Patterns",
            "-----------------",
            "",
            "Small, readable examples that focus on study schemas, validation, and",
            "lightweight orchestration.",
            "",
            "- :doc:`core/index`",
            "- :doc:`core/basic_usage`",
            "- :doc:`core/monty_hall_simulation`",
            "",
            "DOE Exploration",
            "---------------",
            "",
            "Compare design strategies and inspect how condition spaces change with",
            "different methodological choices.",
            "",
            "- :doc:`doe/index`",
            "- :doc:`doe/doe_capabilities`",
            "",
            "Recipe-Backed Runs",
            "------------------",
            "",
            "Follow end-to-end examples that compose benchmark studies, execution",
            "plans, and canonical artifact exports.",
            "",
            "- :doc:`recipes/index`",
            "- :doc:`recipes/recipe_prompt_framing_run`",
            "- :doc:`recipes/recipe_optimization_benchmark_run`",
            "",
            ".. toctree::",
            "   :maxdepth: 2",
            "   :hidden:",
            "",
            "   core/index",
            "   doe/index",
            "   recipes/index",
            "",
        ]
    )


def _build_specs(repo_root: Path) -> list[ExampleDocSpec]:
    """Build parsed docs specs for runnable examples."""
    specs: list[ExampleDocSpec] = []
    for path in _discover_examples(repo_root):
        rel_path = path.relative_to(repo_root).as_posix()
        doc_text, source_start_line = _parse_python_doc_text(path)
        sections = _parse_canonical_sections(doc_text=doc_text, source_path=path)
        specs.append(
            ExampleDocSpec(
                rel_path=rel_path,
                category=_category_for_example(path),
                slug=_slug_for_example(path),
                title=_title_for_example(path),
                source_start_line=source_start_line,
                sections=sections,
            )
        )
    return sorted(specs, key=lambda item: (CATEGORY_ORDER.index(item.category), item.rel_path))


def _sync_file(*, path: Path, content: str, check: bool, stale: list[str]) -> None:
    """Write one generated file or record drift in check mode."""
    desired = content.rstrip() + "\n"
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == desired:
            return
    if check:
        stale.append(path.as_posix())
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desired, encoding="utf-8")


def _sync_stale_pages(
    *,
    generated_pages: set[Path],
    docs_examples_root: Path,
    check: bool,
    stale: list[str],
) -> None:
    """Remove stale generated pages or report drift in check mode."""
    for category in CATEGORY_ORDER:
        category_dir = docs_examples_root / category
        if not category_dir.exists():
            continue
        for existing in sorted(category_dir.glob("*.rst")):
            if existing in generated_pages:
                continue
            if check:
                stale.append(existing.as_posix())
            else:
                existing.unlink()


def generate(*, repo_root: Path, check: bool) -> int:
    """Generate docs pages or validate generated pages are up to date."""
    specs = _build_specs(repo_root)
    docs_examples_root = repo_root / "docs" / "examples"

    stale: list[str] = []
    generated_pages: set[Path] = set()

    _sync_file(
        path=docs_examples_root / "index.rst",
        content=_render_examples_index(),
        check=check,
        stale=stale,
    )

    for category in CATEGORY_ORDER:
        entries = [item for item in specs if item.category == category]
        if not entries:
            continue

        category_index_path = docs_examples_root / category / "index.rst"
        generated_pages.add(category_index_path)
        _sync_file(
            path=category_index_path,
            content=_render_category_index(category, entries),
            check=check,
            stale=stale,
        )

        for entry in entries:
            page_path = docs_examples_root / category / f"{entry.slug}.rst"
            generated_pages.add(page_path)
            _sync_file(
                path=page_path,
                content=_render_example_page(entry),
                check=check,
                stale=stale,
            )

    _sync_stale_pages(
        generated_pages=generated_pages,
        docs_examples_root=docs_examples_root,
        check=check,
        stale=stale,
    )

    if stale:
        print("Example docs are out of date:")
        for path in sorted(stale):
            print(f"- {path}")
        return 1

    if check:
        print("Example docs are up to date.")
    else:
        print("Generated example docs.")
    return 0


def main() -> int:
    """CLI entrypoint for example docs generation/check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate generated docs are up to date.",
    )
    args = parser.parse_args()
    return generate(repo_root=_repo_root(), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
