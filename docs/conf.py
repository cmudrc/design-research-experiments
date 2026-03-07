"""Sphinx configuration for the template documentation."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from sphinx.application import Sphinx

autoclass_content = "both"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "python-template"
copyright = "2026, python-template contributors"
author = "python-template contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = True
napoleon_use_rtype = False
autodoc_typehints = "none"
autosummary_generate = True
autosummary_imported_members = True
nitpicky = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

if os.environ.get("READTHEDOCS") == "True":
    html_theme = "sphinx_rtd_theme"
else:
    try:
        import sphinx_rtd_theme  # noqa: F401

        html_theme = "sphinx_rtd_theme"
    except ImportError:
        html_theme = "alabaster"

html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_logo = "drc.png"
html_title = project
html_theme_options = {"logo_only": False} if html_theme == "sphinx_rtd_theme" else {}

_VIEWPORT_META_RE = re.compile(r'<meta name="viewport"[^>]*>', re.IGNORECASE)


def _dedupe_viewport_meta(
    app: object,
    pagename: str,
    templatename: str,
    context: dict[str, object],
    doctree: object,
) -> None:
    """Keep one viewport tag by removing extra entries from Sphinx metatags."""
    del app, pagename, templatename, doctree
    metatags = context.get("metatags")
    if isinstance(metatags, str):
        context["metatags"] = _VIEWPORT_META_RE.sub("", metatags)


def setup(app: Sphinx) -> None:
    """Register build-time hooks."""
    app.connect("html-page-context", _dedupe_viewport_meta)
