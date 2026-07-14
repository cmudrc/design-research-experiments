# AGENTS.md

## Purpose

This repository is a Python 3.12+ framework for hypothesis-first experiment
definition and orchestration in the cmudrc design research ecosystem. Keep
changes focused, keep study schemas explicit, and preserve deterministic
materialization and run-artifact contracts.

## Setup

- Create and activate a virtual environment:
  - `python -m venv .venv`
  - `source .venv/bin/activate`
- The preferred interpreter target lives in `.python-version` (`3.12`).
- Install local tooling with `make dev`.

## Testing And Validation

Use the smallest useful check while iterating, then run the full gate before
merging.

- Fast local loop:
  - `make fmt`
  - `make lint`
  - `make type`
  - `make test`
  - `make coverage` when changing tested behavior
- If docs changed:
  - `make docs-check`
  - `make docs`
- If the example changed:
  - `make run-example`
- Pre-merge baseline:
  - `make ci`
- Pre-publish baseline:
  - `make release-check`

## Public Vs Private Boundaries

- The supported public surface is whatever is re-exported from
  `src/design_research_experiments/__init__.py`.
- Prefer adding new public behavior to stable top-level modules before creating
  deeper internal package trees.
- If you add internal helper modules later, prefix them with `_` and keep them
  out of the top-level exports unless there is a deliberate API decision.

## Behavioral Guardrails

- Keep tests deterministic and offline by default.
- Maintain the hard 90% total line-coverage floor enforced in CI via
  `make coverage`; this repo-specific baseline tracks
  [cmudrc/design-research#4](https://github.com/cmudrc/design-research/issues/4).
- Update tests, docs, and examples alongside behavior changes.
- Avoid broad dependency growth in the base install.
- Keep recipe adapters thin and preserve canonical export files unless the
  release contract explicitly changes.

## Release Planning

- Do not create monthly milestone naming tables, themed release PR names, or
  calendar release branches as default maintenance.
- Prefer small issue/PR-scoped planning and package version releases driven by
  user-facing changes.
- Use GitHub milestones only for explicit, short-lived initiatives with an
  active owner; they are optional scheduling aids, not release gates.
- Name release branches and release PRs for the version or concrete change set
  they contain.
- When publishing, update package metadata, docs, examples, and GitHub
  Releases/PyPI notes as needed. Do not add README callouts that point to
  monthly milestones.

## Keep This File Up To Date

Update this file whenever the contributor workflow changes, especially when
setup commands, validation commands, or the public API expectations change.
