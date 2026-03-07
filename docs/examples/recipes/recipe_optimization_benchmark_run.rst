Recipe Optimization Benchmark Run
=================================

Source: ``examples/recipe_optimization_benchmark_run.py``

Introduction
------------

Execute a non-default optimization benchmark recipe with deterministic mocks.

Technical Implementation
------------------------

1. Build ``OptimizationBenchmarkConfig`` overrides for factors and design.
2. Create deterministic problem packets and per-agent factories.
3. Run the study and write methods/significance/codebook markdown output.

.. literalinclude:: ../../../examples/recipe_optimization_benchmark_run.py
   :language: python
   :lines: 16-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/recipe_optimization_benchmark_run.py

The script prints completed run count and writes
``artifacts/example-optimization-benchmark/artifacts/optimization_benchmark_report.md``.
