Monty Hall Simulation
=====================

Source: ``examples/monty_hall_simulation.py``

Introduction
------------

Model the Monty Hall game as a tiny two-condition ``drex.Study`` and simulate
100 random games for each strategy to show why switching usually wins more
often than staying.

Technical Implementation
------------------------

1. Define a study with one manipulated factor (``strategy``) and two levels:
   ``stay`` and ``switch``.
2. Validate the study and materialize the two conditions with
   ``drex.build_design``.
3. Pass a typed condition callback to ``drex.run_study`` so the standard runner
   owns deterministic seeds, result normalization, and canonical artifacts.

.. literalinclude:: ../../../examples/monty_hall_simulation.py
   :language: python
   :lines: 22-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/monty_hall_simulation.py

The script completes 2 conditions, simulates 100 games per condition, reports
``stay`` winning ``32/100`` and ``switch`` winning ``70/100``, and writes the
canonical artifact set under ``artifacts/monty-hall``.
