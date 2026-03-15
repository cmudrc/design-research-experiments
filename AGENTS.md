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
- The reproducible interpreter target lives in `.python-version` (`3.12.12`).
- Install local tooling with `make dev`.
- For a frozen environment based on `uv.lock`, use `make repro`.

## Testing And Validation

Use the smallest useful check while iterating, then run the full gate before
merging.

- Fast local loop:
  - `make fmt`
  - `make lint`
  - `make type`
  - `make test`
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
- Update tests, docs, and examples alongside behavior changes.
- Avoid broad dependency growth in the base install.
- Keep recipe adapters thin and preserve canonical export files unless the
  release contract explicitly changes.

## Release Naming

- Theme: frontiers of exploration.
- Monthly release names are shared across milestone titles, release PR titles,
  and release branches.
  - Milestone title / PR title: `{base name} - {Month YYYY}`
  - Release branch: slugified full title, for example
    `mariner-matrix-may-2026`
- Milestone descriptions must use:
  - `Tracks {previous month YYYY} work.`
  - `Theme source: <url>`
- Release PR bodies must repeat the same `Theme source:` link used on the
  milestone.
- Never reuse an exact base name or the same primary subject across any month
  or any of the four design-research module repos unless all four `AGENTS.md`
  files are intentionally updated together.
- Before adding a new release name, check the `Release Naming` tables in all
  four repos to avoid repeats.

| Due date | Base name | Source subject |
| --- | --- | --- |
| April 1, 2026 | Apollo Ascent | Apollo program |
| May 1, 2026 | Mariner Matrix | Mariner program |
| June 1, 2026 | Juno Journey | Juno spacecraft |
| July 1, 2026 | Voyager Venture | Voyager program |
| August 1, 2026 | Artemis Advance | Artemis program |
| September 1, 2026 | Sputnik Sprint | Sputnik 1 |
| October 1, 2026 | Odyssey Orbit | 2001 Mars Odyssey |
| November 1, 2026 | New Horizons Nexus | New Horizons |
| December 1, 2026 | Dragon Drift | Crew Dragon |
| January 1, 2027 | Endeavour Expedition | Space Shuttle Endeavour |

## Keep This File Up To Date

Update this file whenever the contributor workflow changes, especially when
setup commands, validation commands, or the public API expectations change.
