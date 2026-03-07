# python-template

`python-template` is a compact starter for typed Python
libraries. It borrows the shared project shape from
`design-research-agents` and `design-research-problems`, but keeps the initial
surface area small enough to customize quickly.

## Overview

This template includes:

- A `src/` layout package with a small public API and type marker
- `pyproject.toml` settings for packaging, Ruff, mypy, and pytest
- A `Makefile` with common development, docs, coverage, and release targets
- Basic Sphinx docs, a runnable example, and GitHub Actions workflows
- Contributor guidance in `AGENTS.md` and `CONTRIBUTING.md`

## Quickstart

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
make dev
make test
make run-example
```

For a frozen local environment, `make dev` installs `uv`, so you can generate
and use `uv.lock` immediately:

```bash
make lock
make repro
```

## Repository Shape

```text
.
├── .github
│   └── workflows
│       ├── ci.yml
│       └── docs-pages.yml
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── AGENTS.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── README.md
├── docs
│   ├── api.rst
│   ├── conf.py
│   ├── dependencies_and_extras.rst
│   ├── drc.png
│   ├── index.rst
│   └── quickstart.rst
├── examples
│   ├── README.md
│   └── basic_usage.py
├── pyproject.toml
├── scripts
│   ├── check_coverage_thresholds.py
│   ├── check_docs_consistency.py
│   └── check_google_docstrings.py
├── src
│   └── python_template
│       ├── __init__.py
│       ├── core.py
│       └── py.typed
├── tests
│   ├── test_core.py
│   └── test_public_api.py
└── uv.lock
```

The top-level tree above is the minimum working package scaffold. Each element
has a specific job:

- `.github/` stores GitHub-specific automation and repository metadata.
  - `.github/workflows/` contains the GitHub Actions pipelines for this repository.
    - `.github/workflows/ci.yml` runs the main validation pipeline, centered on `make ci`.
    - `.github/workflows/docs-pages.yml` builds the docs and publishes them to GitHub Pages.
- `.gitignore` keeps local caches, IDE files, build outputs, and virtualenvs out of version control.
- `.pre-commit-config.yaml` defines the optional local pre-commit hook configuration.
- `.python-version` pins the preferred reproducible interpreter version for local setup.
- `AGENTS.md` provides repository-specific instructions for coding agents and automation.
- `CONTRIBUTING.md` documents the contributor workflow, quality checks, and review expectations.
- `LICENSE` defines the repository's software license terms.
- `Makefile` is the main command surface for setup, linting, typing, testing, docs, and release checks.
- `README.md` is the onboarding document that explains the template and how to use it.
- `docs/` contains the Sphinx documentation source tree.
  - `docs/api.rst` builds the API reference from the package's Python docstrings.
  - `docs/conf.py` configures Sphinx extensions, theme settings, and the docs build behavior.
  - `docs/dependencies_and_extras.rst` explains the dependency model and optional extras.
  - `docs/drc.png` is the shared DRC logo used in the generated docs site.
  - `docs/index.rst` is the documentation landing page and toctree entry point.
  - `docs/quickstart.rst` provides the short setup path for local development.
- `examples/` contains small runnable examples intended to show the public API in use.
  - `examples/README.md` explains what examples exist and how to run them.
  - `examples/basic_usage.py` is the minimal working example for the template package.
- `pyproject.toml` defines package metadata, dependencies, build settings, and tool configuration.
- `scripts/` contains helper scripts used by the Make targets and local checks.
  - `scripts/check_coverage_thresholds.py` enforces the minimum coverage percentage from the coverage report.
  - `scripts/check_docs_consistency.py` verifies that the docs tree and package references stay in sync.
  - `scripts/check_google_docstrings.py` checks for required module, class, and function docstrings.
- `src/` is the source root for the `src`-layout package.
  - `src/python_template/` contains the installable Python package itself.
    - `src/python_template/__init__.py` defines the curated public import surface.
    - `src/python_template/core.py` contains the small example implementation shipped with the template.
    - `src/python_template/py.typed` marks the package as PEP 561 typed for downstream tooling.
- `tests/` contains the pytest suite that protects the public behavior.
  - `tests/test_core.py` tests the package's example core behavior.
  - `tests/test_public_api.py` keeps the top-level exports explicit and stable.
- `uv.lock` pins the reproducible dependency graph used by `make repro`.

## Customizing The Template

Before using this as a real package, update:

- Project metadata in `pyproject.toml`
- Package and import names under `src/`
- The README, docs, and example script
- CI workflow names, deploy settings, and repository URLs

## Docs

Build the docs locally with:

```bash
make docs
```

The generated HTML output is written to `docs/_build/html/`.

## Contributing

See `CONTRIBUTING.md` for the local development workflow and contribution
expectations.
