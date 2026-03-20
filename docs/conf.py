"""Sphinx configuration for design-research-experiments documentation."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from sphinx.application import Sphinx

autoclass_content = "both"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "design-research-experiments"
copyright = "2026, design-research-experiments contributors"
author = "design-research-experiments contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = True
napoleon_use_rtype = False
autodoc_typehints = "none"
autosummary_generate = True
autosummary_imported_members = True
nitpicky = True
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

try:
    import pydata_sphinx_theme  # noqa: F401
except ImportError:
    html_theme = "alabaster"
    html_theme_options: dict[str, object] = {}
else:
    html_theme = "pydata_sphinx_theme"
    html_theme_options = {
        "logo": {
            "text": project,
            "image_light": "_static/drc-light.png",
            "image_dark": "_static/drc-dark.png",
        },
        "icon_links": [
            {
                "name": "GitHub",
                "url": "https://github.com/cmudrc/design-research-experiments",
                "icon": "fa-brands fa-github",
            },
        ],
        "navbar_align": "content",
        "header_links_before_dropdown": 4,
        "show_nav_level": 2,
        "navigation_with_keys": True,
        "show_prev_next": False,
        "secondary_sidebar_items": ["page-toc"],
    }

html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_logo = "_static/drc-light.png"
html_favicon = "_static/favicon.ico"
html_title = project
html_sidebars = (
    {
        "index": [],
        "examples/index": [],
        "reference/index": [],
    }
    if html_theme == "pydata_sphinx_theme"
    else {}
)

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
