# Examples

Runnable examples for `design-research-experiments`.

## Core API

- `basic_usage.py`: construct and serialize a minimal `Study`.
- `public_api_walkthrough.py`: validate a study and materialize conditions.
- `recipe_overview.py`: build recipe studies and render reporting scaffolds.

## Working Recipe Runs

- `recipe_prompt_framing_run.py`: execute a compact `PromptFramingRecipe` study with mock agents/problems.
- `recipe_grammar_scaffold_run.py`: execute a compact `GrammarScaffoldRecipe` study with mock agents/problems.

Run examples from repository root:

```bash
PYTHONPATH=src python examples/basic_usage.py
PYTHONPATH=src python examples/public_api_walkthrough.py
PYTHONPATH=src python examples/recipe_prompt_framing_run.py
PYTHONPATH=src python examples/recipe_grammar_scaffold_run.py
```
