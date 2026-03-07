DOE Capabilities
================

Source: ``examples/doe_capabilities.py``

Introduction
------------

Demonstrate one-shot DOE generation for full-factorial, LHS, and frac2 designs.

Technical Implementation
------------------------

1. Generate three DOE tables with ``drex.generate_doe``.
2. Write the LHS table to ``artifacts/doe-capabilities/lhs_design.csv``.
3. Print run counts for quick sanity checks.

.. literalinclude:: ../../../examples/doe_capabilities.py
   :language: python
   :lines: 16-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/doe_capabilities.py

The script reports run counts for each design type and confirms the CSV artifact
path for the generated LHS table.
