Mechanical Design Recipe Portfolio
==================================

Source: ``examples/mechanical_design_recipe_portfolio.py``

Introduction
------------

Build and run a compact portfolio of study recipes around mechanical design
trade-offs such as bracket stiffness, truss weight, and manufacturability.

Technical Implementation
------------------------

1. Define a mechanical benchmark bundle plus recipe/config objects for
   bivariate and architecture-focused studies.
2. Materialize a compact bivariate study, execute it with deterministic mock
   agents, and export canonical analysis tables.
3. Print the generated study IDs and exported analysis artifacts for the
   mechanical-design portfolio.

.. literalinclude:: ../../../examples/mechanical_design_recipe_portfolio.py
   :language: python
   :lines: 20-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/mechanical_design_recipe_portfolio.py

The script prints the recipe study IDs, the number of completed runs, and the
artifact filenames exported for downstream analysis.
