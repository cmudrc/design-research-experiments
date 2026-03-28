# Contributing

## Development Setup

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

This repo maintains a hard 90% total line-coverage floor in CI. Run
`make coverage` before merge when touching tested behavior. This repo-level
baseline tracks the family-wide policy in
[cmudrc/design-research#4](https://github.com/cmudrc/design-research/issues/4).

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
