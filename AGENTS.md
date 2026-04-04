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

## Release Naming

- Theme: frontiers of exploration.
- Monthly work-cycle names are shared across milestone titles, release PR
  titles, and release branches.
- Name the cycle for the month the work is done, not the later drop month.
  - Milestone title / PR title: `{base name} - {Work month YYYY}`
  - Release branch: slugified full title, for example
    `mariner-matrix-april-2026`
- Milestone due dates should land in the first week of the following month.
- Milestone descriptions must use:
  - `Work month: {Month YYYY}.`
  - `Theme source: <url>`
- Release PR bodies must repeat the same `Theme source:` link used on the
  milestone and refer to the same work month named in the title.
- Never reuse an exact base name or the same primary subject across any work
  month or any of the four design-research module repos unless all four
  `AGENTS.md` files are intentionally updated together.
- Before adding a new release name, check the `Release Naming` tables in all
  four repos to avoid repeats.

| Work month | Target drop | Base name | Source subject |
| --- | --- | --- | --- |
| March 2026 | April 1, 2026 | Apollo Ascent | Apollo program |
| April 2026 | May 1, 2026 | Mariner Matrix | Mariner program |
| May 2026 | June 1, 2026 | Juno Journey | Juno spacecraft |
| June 2026 | July 1, 2026 | Voyager Venture | Voyager program |
| July 2026 | August 1, 2026 | Artemis Advance | Artemis program |
| August 2026 | September 1, 2026 | Sputnik Sprint | Sputnik 1 |
| September 2026 | October 1, 2026 | Odyssey Orbit | 2001 Mars Odyssey |
| October 2026 | November 1, 2026 | New Horizons Nexus | New Horizons |
| November 2026 | December 1, 2026 | Dragon Drift | Crew Dragon |
| December 2026 | January 1, 2027 | Endeavour Expedition | Space Shuttle Endeavour |

## Keep This File Up To Date

Update this file whenever the contributor workflow changes, especially when
setup commands, validation commands, or the public API expectations change.
