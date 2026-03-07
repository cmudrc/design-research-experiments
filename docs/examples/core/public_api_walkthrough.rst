Public API Walkthrough
======================

Source: ``examples/public_api_walkthrough.py``

Introduction
------------

Walk through the core study lifecycle: build, validate, and materialize conditions.

Technical Implementation
------------------------

1. Build a compact ``Study`` object with one factor, hypothesis, and outcome.
2. Validate via ``drex.validate_study``.
3. Materialize conditions through both ``drex.build_design`` and
   ``drex.materialize_conditions`` for parity checks.

.. literalinclude:: ../../../examples/public_api_walkthrough.py
   :language: python
   :lines: 17-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/public_api_walkthrough.py

The script prints condition counts for both materialization paths and raises an
error only when validation fails.
