"""Core helpers that demonstrate the template package shape."""

from __future__ import annotations

import re
from dataclasses import dataclass

_DEFAULT_TOOLCHAIN = ("ruff", "mypy", "pytest", "sphinx")
_PACKAGE_TOKEN_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class ProjectBlueprint:
    """Describe the baseline choices captured by the template.

    Args:
        name: The distribution name used for packaging.
        package_name: The Python import package name.
        python_version: The minimum supported Python version line.
        include_docs: Whether the repository ships with docs scaffolding.
        include_examples: Whether the repository ships with example scripts.
        toolchain: The default local quality and documentation tools.
    """

    name: str
    package_name: str
    python_version: str = "3.12"
    include_docs: bool = True
    include_examples: bool = True
    toolchain: tuple[str, ...] = _DEFAULT_TOOLCHAIN

    def summary_lines(self) -> tuple[str, ...]:
        """Return a compact, human-readable project summary.

        Returns:
            A tuple of display lines that can be printed directly.
        """
        return (
            f"Project: {self.name}",
            f"Import package: {self.package_name}",
            f"Python: {self.python_version}+",
            f"Docs included: {'yes' if self.include_docs else 'no'}",
            f"Examples included: {'yes' if self.include_examples else 'no'}",
            f"Toolchain: {', '.join(self.toolchain)}",
        )


def normalize_package_name(name: str) -> str:
    """Convert a project name into a valid import package token.

    Args:
        name: An arbitrary project or distribution name.

    Returns:
        A normalized, underscore-separated package token.

    Raises:
        ValueError: Raised when the normalized name would be empty.
    """
    normalized = _PACKAGE_TOKEN_RE.sub("_", name.strip().lower()).strip("_")
    if not normalized:
        raise ValueError("Package name cannot be empty after normalization.")
    return normalized


def build_default_blueprint(
    project_name: str,
    package_name: str | None = None,
) -> ProjectBlueprint:
    """Build a default project blueprint for the template repository.

    Args:
        project_name: The distribution or repository name.
        package_name: An optional explicit import package name.

    Returns:
        A populated project blueprint.
    """
    resolved_package_name = (
        normalize_package_name(project_name)
        if package_name is None
        else normalize_package_name(package_name)
    )
    return ProjectBlueprint(name=project_name, package_name=resolved_package_name)


def describe_project(blueprint: ProjectBlueprint) -> str:
    """Render a blueprint into a printable multi-line description.

    Args:
        blueprint: The project blueprint to describe.

    Returns:
        A newline-delimited description string.
    """
    return "\n".join(blueprint.summary_lines())
