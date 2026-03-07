"""Public package exports for the template library."""

from .core import (
    ProjectBlueprint,
    build_default_blueprint,
    describe_project,
    normalize_package_name,
)

__all__ = [
    "ProjectBlueprint",
    "build_default_blueprint",
    "describe_project",
    "normalize_package_name",
]
