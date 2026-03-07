Examples and Recipes
====================

The repository ships runnable examples under ``examples/``.

Core API examples
-----------------

- ``examples/basic_usage.py``: construct and serialize a minimal ``Study``.
- ``examples/public_api_walkthrough.py``: validate a study and materialize conditions.
- ``examples/recipe_overview.py``: build recipe studies and render reporting scaffolds.

Working recipe execution examples
---------------------------------

- ``examples/recipe_prompt_framing_run.py``:
  builds ``PromptFramingRecipe`` and executes a compact run with mock
  agents/problems, exporting canonical artifacts.
- ``examples/recipe_grammar_scaffold_run.py``:
  builds ``GrammarScaffoldRecipe`` and executes a compact run with mock
  agents/problems, then writes methods/significance/codebook markdown outputs.

Run examples
------------

From repository root:

.. code-block:: bash

   PYTHONPATH=src python examples/basic_usage.py
   PYTHONPATH=src python examples/public_api_walkthrough.py
   PYTHONPATH=src python examples/recipe_prompt_framing_run.py
   PYTHONPATH=src python examples/recipe_grammar_scaffold_run.py
