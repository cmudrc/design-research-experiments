Recipe Prompt Framing Run
=========================

Source: ``examples/recipe_prompt_framing_run.py``

Introduction
------------

Execute a non-default prompt-framing recipe with deterministic mock components.

Technical Implementation
------------------------

1. Build ``PromptFramingConfig`` overrides for factors, design, budget, and IDs.
2. Create deterministic in-memory problem and agent adapters.
3. Run the study and write a markdown summary artifact.

.. literalinclude:: ../../../examples/recipe_prompt_framing_run.py
   :language: python
   :lines: 16-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/recipe_prompt_framing_run.py

The script prints completed run count and writes
``artifacts/example-prompt-framing/artifacts/prompt_framing_summary.md``.
