"""Tests for lightweight docs consistency helpers."""

from __future__ import annotations

from pathlib import Path

from scripts.check_docs_consistency import (
    discover_example_paths,
    extract_documented_api_names,
    extract_documented_example_paths,
    extract_public_exports,
    extract_toctree_entries,
    find_api_inventory_differences,
    find_example_inventory_differences,
)


def test_extract_toctree_entries_skips_external_links(tmp_path: Path) -> None:
    """External toctree targets should not be treated as local docs pages."""
    index_path = tmp_path / "index.rst"
    index_path.write_text(
        "\n".join(
            [
                ".. toctree::",
                "   quickstart",
                "   Contributing <https://example.com/CONTRIBUTING.md>",
                "",
                ".. toctree::",
                "   API Reference <reference/index>",
            ]
        ),
        encoding="utf-8",
    )

    assert extract_toctree_entries(index_path) == ("quickstart", "reference/index")


def test_extract_toctree_entries_normalizes_rst_suffix(tmp_path: Path) -> None:
    """Internal entries with explicit ``.rst`` suffixes should normalize cleanly."""
    index_path = tmp_path / "index.rst"
    index_path.write_text(
        "\n".join(
            [
                ".. toctree::",
                "   installation.rst",
                "   Concepts <concepts.rst>",
            ]
        ),
        encoding="utf-8",
    )

    assert extract_toctree_entries(index_path) == ("installation", "concepts")


def test_extract_public_exports_reads_literal_all(tmp_path: Path) -> None:
    """The API checker should read a literal export inventory without importing it."""
    init_path = tmp_path / "__init__.py"
    init_path.write_text('__all__ = ["Study", "run_study"]\n', encoding="utf-8")

    assert extract_public_exports(init_path) == ("Study", "run_study")


def test_extract_documented_api_names_reads_only_exact_inventory_bullets(
    tmp_path: Path,
) -> None:
    """Incidental prose literals should not satisfy the API inventory."""
    api_path = tmp_path / "api.rst"
    api_path.write_text(
        "Study helpers include ``Study`` in prose.\n"
        "- ``run_study``\n"
        "- Related helper: ``validate_study``\n",
        encoding="utf-8",
    )

    assert extract_documented_api_names(api_path) == {"run_study"}


def test_find_api_inventory_differences_reports_missing_and_stale_names(
    tmp_path: Path,
) -> None:
    """API comparison should reject both omitted exports and stale inventory rows."""
    init_path = tmp_path / "__init__.py"
    init_path.write_text('__all__ = ["Study", "run_study"]\n', encoding="utf-8")
    api_path = tmp_path / "api.rst"
    api_path.write_text("- ``Study``\n- ``removed_export``\n", encoding="utf-8")

    assert find_api_inventory_differences(init_path, api_path) == (
        ("run_study",),
        ("removed_export",),
    )


def test_example_inventory_is_exact_recursive_and_symmetric(tmp_path: Path) -> None:
    """Example comparison should use exact relative paths in both directions."""
    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    (examples_dir / "listed.py").write_text("", encoding="utf-8")
    nested_dir = examples_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "missing.py").write_text("", encoding="utf-8")
    (nested_dir / "_helper.py").write_text("", encoding="utf-8")
    readme_path = examples_dir / "README.md"
    readme_path.write_text(
        "- `listed.py`: listed example\n"
        "The string `nested/missing.py.old` is not an inventory entry.\n"
        "- `stale.py`: removed example\n",
        encoding="utf-8",
    )

    assert discover_example_paths(examples_dir) == {"listed.py", "nested/missing.py"}
    assert extract_documented_example_paths(readme_path) == {"listed.py", "stale.py"}
    assert find_example_inventory_differences(examples_dir, readme_path) == (
        ("nested/missing.py",),
        ("stale.py",),
    )
