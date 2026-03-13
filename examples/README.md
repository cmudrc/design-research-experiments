# Examples

Runnable examples for `design-research-experiments`.

## Core API

- `basic_usage.py`: construct and serialize a minimal `Study`.
- `monty_hall_simulation.py`: simulate 100 random Monty Hall games per strategy condition.
- `public_api_walkthrough.py`: validate a study and materialize conditions.
- `doe_capabilities.py`: generate full/LHS/fractional DOE tables with diagnostics.
- `recipe_overview.py`: build recipe studies from function factories and render reporting scaffolds.

## Working Recipe Runs

- `recipe_prompt_framing_run.py`: execute a non-default `build_prompt_framing_study` configuration with mock agents/problems.
- `recipe_optimization_benchmark_run.py`: execute a non-default `build_optimization_benchmark_study` configuration with mock agents/problems.

Run examples from repository root:

```bash
PYTHONPATH=src python examples/basic_usage.py
PYTHONPATH=src python examples/monty_hall_simulation.py
PYTHONPATH=src python examples/public_api_walkthrough.py
PYTHONPATH=src python examples/doe_capabilities.py
PYTHONPATH=src python examples/recipe_prompt_framing_run.py
PYTHONPATH=src python examples/recipe_optimization_benchmark_run.py
```
