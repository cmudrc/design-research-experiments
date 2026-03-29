# design-research-experiments
[![CI](https://github.com/cmudrc/design-research-experiments/actions/workflows/ci.yml/badge.svg)](https://github.com/cmudrc/design-research-experiments/actions/workflows/ci.yml)
[![Coverage](https://raw.githubusercontent.com/cmudrc/design-research-experiments/main/.github/badges/coverage.svg)](https://github.com/cmudrc/design-research-experiments/actions/workflows/ci.yml)
[![Examples Passing](https://raw.githubusercontent.com/cmudrc/design-research-experiments/main/.github/badges/examples-passing.svg)](https://github.com/cmudrc/design-research-experiments/actions/workflows/examples.yml)
[![Public API In Examples](https://raw.githubusercontent.com/cmudrc/design-research-experiments/main/.github/badges/examples-api-coverage.svg)](https://github.com/cmudrc/design-research-experiments/actions/workflows/examples.yml)
[![Docs](https://github.com/cmudrc/design-research-experiments/actions/workflows/docs-pages.yml/badge.svg)](https://github.com/cmudrc/design-research-experiments/actions/workflows/docs-pages.yml)

<!-- release-callout:start -->
> [!IMPORTANT]
> Current monthly release: [Mariner Matrix - May 2026](https://github.com/cmudrc/design-research-experiments/milestone/2)  
> Due: May 1, 2026  
> Tracks: April 2026 work
<!-- release-callout:end -->

`design-research-experiments` is the hypothesis-first study-definition and
experiment-orchestration layer in the cmudrc design research ecosystem.

It composes sibling libraries rather than reimplementing them:

- `design-research-agents` for executable agent behavior, workflows, and traces
- `design-research-problems` for problem catalogs, registries, and evaluators
- `design-research-analysis` for downstream unified-table analysis and reporting

## Overview

This package centers on reproducible experiment structure and execution:

- typed schemas for studies, factors, blocks, hypotheses, outcomes, and analysis plans
- design-of-experiments materialization (full/constrained factorial, randomized block,
  repeated measures, latin square, custom matrices)
- run orchestration with deterministic seeding, checkpointing, resume support, and
  interactive `tqdm` progress on terminal runs
- canonical artifact exports (`study.yaml`, `manifest.json`, `conditions.csv`,
  `runs.csv`, `events.csv`, `evaluations.csv`, and machine-readable hypothesis/plan files)
- documented artifact contracts that downstream analysis can ingest directory-first
- thin adapters that connect to the public APIs of sibling agent/problem/analysis libraries

## Quickstart

Requires Python 3.12+.
Maintainer workflows target Python `3.12` (`.python-version`).

```bash
python -m venv .venv
source .venv/bin/activate
make dev
make test
```

Run a basic example:

```bash
make run-example
```

This repo maintains a hard 90% total line-coverage floor in CI via
`make coverage`. The repo-specific rule tracks the family-wide coverage policy
in [cmudrc/design-research#4](https://github.com/cmudrc/design-research/issues/4).

## CLI

The package installs a `drexp` CLI:

```bash
drexp validate-study path/to/study.yaml
drexp materialize-design path/to/study.yaml
drexp generate-doe --kind lhs --factors-json '{"x": [0, 1], "y": [10, 20]}' --n-samples 12 --out artifacts/doe.csv
drexp run-study path/to/study.yaml
drexp resume-study path/to/study.yaml
drexp export-analysis path/to/study.yaml
drexp bundle-results path/to/output_dir
```

## Examples

See [examples/README.md](https://github.com/cmudrc/design-research-experiments/blob/main/examples/README.md)
for runnable scripts, including end-to-end recipe executions.

## Docs

See the [published documentation](https://cmudrc.github.io/design-research-experiments/)
for guides, the [artifact contract](https://cmudrc.github.io/design-research-experiments/artifact_contract.html),
and API reference.

Build docs locally with:

```bash
make docs
```

## Public API

Top-level exports are intentionally small:

- `Study`, `Factor`, `Level`, `Constraint`, `Condition`, `Block`
- `RecipeStudyConfig`, `ComparisonStudyConfig`, and recipe-specific typed config classes
- `Hypothesis`, `OutcomeSpec`, `AnalysisPlan`
- `RunSpec`, `RunResult`, `BenchmarkBundle`
- `build_design`, `generate_doe`, `materialize_conditions`
- `build_univariate_comparison_study`, `build_bivariate_comparison_study`,
  `build_strategy_comparison_study`, and other recipe builders
- `run_study`, `resume_study`
- `export_analysis_tables`, `validate_study`

## Contributing

Contribution workflow and quality gates are documented in
[CONTRIBUTING.md](https://github.com/cmudrc/design-research-experiments/blob/main/CONTRIBUTING.md).
