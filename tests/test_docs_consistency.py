"""Tests for lightweight docs consistency helpers."""

from __future__ import annotations

from pathlib import Path

from scripts.check_docs_consistency import extract_toctree_entries


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
