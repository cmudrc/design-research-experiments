PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,$(shell if command -v python3.12 >/dev/null 2>&1; then echo python3.12; else echo python3; fi))
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
MYPY ?= $(PYTHON) -m mypy
SPHINX ?= $(PYTHON) -m sphinx
BUILD ?= $(PYTHON) -m build
TWINE ?= $(PYTHON) -m twine
UV ?= $(if $(wildcard .venv/bin/uv),.venv/bin/uv,uv)
REPRO_PYTHON ?= $(shell cat .python-version 2>/dev/null || echo 3.12.12)
REPRO_EXTRAS ?= dev

.PHONY: help check-python check-uv dev install-dev repro lock \
	lint fmt fmt-check type test qa coverage docstrings-check \
	run-example docs docs-build docs-check docs-linkcheck \
	release-check ci clean

help:
	@echo "Common targets:"
	@echo "  dev              Install the project in editable mode with dev dependencies."
	@echo "  repro            Frozen reproducible install using uv.lock."
	@echo "  lock             Regenerate uv.lock."
	@echo "  test             Run the pytest suite."
	@echo "  qa               Run lint, fmt-check, type, and test."
	@echo "  run-example      Execute the bundled example script."
	@echo "  docs             Build the HTML docs."
	@echo "  ci               Run the main local CI checks."

check-python:
	@$(PYTHON) -c "import pathlib, sys; print(f'Using Python {sys.version.split()[0]} at {pathlib.Path(sys.executable)}'); raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" || (echo "Python >= 3.12 is required by pyproject.toml"; exit 1)

check-uv:
	@command -v $(UV) >/dev/null 2>&1 || (echo "uv is required for lock/repro targets. Install it from https://docs.astral.sh/uv/getting-started/installation/"; exit 1)

dev:
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"

install-dev: dev

repro: check-uv
	$(UV) sync --frozen --python $(REPRO_PYTHON) $(foreach extra,$(REPRO_EXTRAS),--extra $(extra))

lock: check-uv
	$(UV) lock --python $(REPRO_PYTHON)

lint: check-python
	$(RUFF) check .

fmt: check-python
	$(RUFF) format .

fmt-check: check-python
	$(RUFF) format --check .

type: check-python
	$(MYPY) src

test: check-python
	PYTHONPATH=src $(PYTEST) -q

qa: lint fmt-check type test

coverage: check-python
	mkdir -p artifacts/coverage
	PYTHONPATH=src $(PYTEST) --cov=src/python_template --cov-report=term --cov-report=json:artifacts/coverage/coverage.json -q
	$(PYTHON) scripts/check_coverage_thresholds.py --coverage-json artifacts/coverage/coverage.json

docstrings-check: check-python
	$(PYTHON) scripts/check_google_docstrings.py

run-example: check-python
	PYTHONPATH=src $(PYTHON) examples/basic_usage.py

docs-build: check-python
	PYTHONPATH=src $(SPHINX) -b html docs docs/_build/html -n -W --keep-going -E

docs-check: check-python
	$(PYTHON) scripts/check_docs_consistency.py

docs-linkcheck: check-python
	PYTHONPATH=src $(SPHINX) -b linkcheck docs docs/_build/linkcheck -W --keep-going -E

docs: docs-build

release-check: check-python
	rm -rf build dist
	$(BUILD)
	$(TWINE) check dist/*

ci: qa coverage docstrings-check docs-check run-example release-check

clean:
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache artifacts build dist docs/_build
	find src -maxdepth 2 -type d -name "*.egg-info" -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type f \( -name "*.pyc" -o -name ".coverage.*" \) -exec rm -f {} + 2>/dev/null || true
