# Examples

Runnable examples for `design-research-experiments`.

## Core API

- `basic_usage.py`: construct and serialize a minimal `Study`.
- `mechanical_design_recipe_portfolio.py`: inspect the recipe portfolio through a mechanical-design study scenario.
- `monty_hall_simulation.py`: simulate 100 random Monty Hall games per strategy condition.
- `public_api_walkthrough.py`: validate a study and materialize conditions.
- `real_stack_interoperability.py`: exercise the installed sibling-package handoff when the full stack is available.
- `doe_capabilities.py`: generate full/LHS/fractional DOE tables with diagnostics.
- `recipe_overview.py`: build recipe studies from function factories and render reporting scaffolds.

## Working Recipe Runs

- `recipe_prompt_framing_run.py`: execute a non-default `build_prompt_framing_study` configuration with mock agents/problems.
- `recipe_optimization_benchmark_run.py`: execute a non-default `build_optimization_benchmark_study` configuration with mock agents/problems.
- `recipe_strategy_comparison_run.py`: execute a packaged-problem `build_strategy_comparison_study` configuration with mock agents/problems.

Run the full deterministic example suite from the repository root:

```bash
make run-examples
```

Run individual examples with:

```bash
PYTHONPATH=src python examples/basic_usage.py
PYTHONPATH=src python examples/monty_hall_simulation.py
PYTHONPATH=src python examples/public_api_walkthrough.py
PYTHONPATH=src python examples/doe_capabilities.py
PYTHONPATH=src python examples/mechanical_design_recipe_portfolio.py
PYTHONPATH=src python examples/recipe_overview.py
PYTHONPATH=src python examples/recipe_prompt_framing_run.py
PYTHONPATH=src python examples/recipe_optimization_benchmark_run.py
PYTHONPATH=src python examples/recipe_strategy_comparison_run.py
PYTHONPATH=src python examples/real_stack_interoperability.py
```

The real-stack example exits successfully with a clear skip message when its
sibling packages are not installed.
