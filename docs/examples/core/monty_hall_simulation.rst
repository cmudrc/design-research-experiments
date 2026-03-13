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
3. Simulate 100 seeded random Monty Hall games for each condition, write a
   summary CSV artifact, and print the resulting win counts.

.. literalinclude:: ../../../examples/monty_hall_simulation.py
   :language: python
   :lines: 22-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/monty_hall_simulation.py

The script prints 2 materialized conditions, simulates 100 games per condition
with a fixed seed, reports ``stay`` winning ``35/100`` and ``switch`` winning
``65/100``, and writes a summary CSV artifact under ``artifacts/monty-hall``.
