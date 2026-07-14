# Contributing

## Development Setup

For a step-by-step VS Code setup, including the PyPI install path, source
checkout path, interpreter selection, first checks, and troubleshooting, see
[VS Code Start](docs/vscode_start.rst).

```bash
python -m venv .venv
source .venv/bin/activate
make dev
```

The preferred maintainer interpreter is set in `.python-version` (`3.12`).

Before cutting a release, run:

```bash
make release-check
```

## Local Quality Checks

Run these before opening a pull request:

```bash
make fmt
make lint
make type
make docstrings-check
make test
make coverage
make docs-check
make docs
```

## Quality Gates

- `make coverage` enforces at least 95% total line coverage for the default deterministic suite.
- `make examples-test` executes the checked-in runnable examples.
- `make examples-coverage` requires every curated top-level `__all__` export to appear in at least one runnable example.

Optional but useful:

```bash
pre-commit install
pre-commit run --all-files
```

## Pull Request Guidelines

- Keep changes small enough to review quickly.
- Add or update tests for behavior changes.
- Update docs and examples when interfaces change.
- Describe what changed and how you validated it.

## Code Style

- Python 3.12+ target
- Ruff for linting and formatting
- Mypy for type checking
- Pytest for tests
- Google-style docstrings in `src/`, `examples/`, and `scripts/`
