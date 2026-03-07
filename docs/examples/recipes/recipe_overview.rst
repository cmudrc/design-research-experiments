Recipe Overview
===============

Source: ``examples/recipe_overview.py``

Introduction
------------

Survey the reusable recipe builders and reporting helpers without running a study.

Technical Implementation
------------------------

1. Instantiate each recipe factory once.
2. Load standard benchmark bundles.
3. Render markdown summary, methods scaffold, and codebook snippets.

.. literalinclude:: ../../../examples/recipe_overview.py
   :language: python
   :lines: 16-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/recipe_overview.py

The script prints bundle counts and markdown snippets that confirm recipe objects
and reporting helpers are wired correctly.
