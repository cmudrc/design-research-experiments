Basic Usage
===========

Source: ``examples/basic_usage.py``

Introduction
------------

Construct the smallest useful ``Study`` using only top-level ``drex`` exports.

Technical Implementation
------------------------

1. Define one manipulated factor with two levels.
2. Register one primary outcome plus one hypothesis and analysis plan.
3. Print ``study.to_dict()`` so the serialized schema is visible in one place.
4. Show that a study with no execution yet has no durable run-evidence records.

.. literalinclude:: ../../../examples/basic_usage.py
   :language: python
   :lines: 17-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/basic_usage.py

The script prints the study dictionary followed by an empty evidence-record
mapping. Executed studies populate that mapping under ``artifacts/runs/``.
