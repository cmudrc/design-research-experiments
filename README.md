# design-research-experiments

`design-research-experiments` is the study-definition and experiment-orchestration
layer for the cmudrc ecosystem.

It composes:

- `design-research-agents` for agent execution and tracing
- `design-research-problems` for typed benchmark/problem definitions and evaluation
- `design-research-analysis` for downstream unified-table analysis

## Scope

This package focuses on:

- hypothesis-first study schemas
- design-of-experiments materialization
- reproducible run orchestration with checkpoint/resume
- canonical artifact exports (`study.yaml`, `manifest.json`, `conditions.csv`,
  `runs.csv`, `events.csv`, `evaluations.csv`, hypothesis/analysis-plan files)
- thin adapters for agent/problem/analysis package interoperability

It intentionally does not duplicate core agent internals, problem registries, or
general statistical engines.

## Quickstart

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
make dev
make test
```

Run the example:

```bash
make run-example
```

## CLI

The package installs a `drexp` CLI:

```bash
drexp validate-study path/to/study.yaml
drexp materialize-design path/to/study.yaml
drexp run-study path/to/study.yaml
drexp resume-study path/to/study.yaml
drexp export-analysis path/to/study.yaml
drexp bundle-results path/to/output_dir
```

## Public API

Top-level exports are intentionally small:

- `Study`, `Factor`, `Level`, `Constraint`, `Condition`, `Block`
- `Hypothesis`, `OutcomeSpec`, `AnalysisPlan`
- `RunSpec`, `RunResult`, `BenchmarkBundle`
- `build_design`, `materialize_conditions`
- `run_study`, `resume_study`
- `export_analysis_tables`, `validate_study`
