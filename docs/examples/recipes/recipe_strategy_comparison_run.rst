Recipe Strategy Comparison Run
==============================

Source: ``examples/recipe_strategy_comparison_run.py``

Introduction
------------

Execute a packaged-problem strategy comparison study with deterministic mocks.

Technical Implementation
------------------------

1. Build ``StrategyComparisonConfig`` overrides for bundle selection, run budget, and output path.
2. Create deterministic problem packets and one factory per compared agent strategy.
3. Run the study and write a markdown summary artifact.

.. literalinclude:: ../../../examples/recipe_strategy_comparison_run.py
   :language: python
   :lines: 16-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/recipe_strategy_comparison_run.py

The script prints completed run count and writes
``artifacts/example-strategy-comparison/artifacts/strategy_comparison_summary.md``.
