"""Tests for the core template helpers."""

from __future__ import annotations

from python_template import (
    ProjectBlueprint,
    build_default_blueprint,
    describe_project,
    normalize_package_name,
)


def test_normalize_package_name_rewrites_non_identifier_tokens() -> None:
    """Normalize a repository name into an import-safe package token."""

    assert normalize_package_name("Design Research Template") == "design_research_template"


def test_build_default_blueprint_uses_normalized_package_name() -> None:
    """Default blueprints should derive the import package name."""

    blueprint = build_default_blueprint("python-template")

    assert blueprint == ProjectBlueprint(
        name="python-template",
        package_name="python_template",
    )


def test_describe_project_includes_expected_summary_fields() -> None:
    """The rendered project summary should include the major template defaults."""

    blueprint = build_default_blueprint("python-template")
    description = describe_project(blueprint)

    assert "Project: python-template" in description
    assert "Import package: python_template" in description
    assert "Toolchain: ruff, mypy, pytest, sphinx" in description
