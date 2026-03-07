"""Tests for the curated public API."""

from __future__ import annotations

import python_template as package


def test_public_exports_match_the_curated_api() -> None:
    """Keep the top-level exports explicit and stable."""

    assert package.__all__ == [
        "ProjectBlueprint",
        "build_default_blueprint",
        "describe_project",
        "normalize_package_name",
    ]
