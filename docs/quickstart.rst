Quickstart
==========

This example shows the shortest meaningful path through
``design-research-experiments``.

1. Install
----------

.. code-block:: bash

   pip install design-research-experiments

Or install from source:

.. code-block:: bash

   git clone https://github.com/cmudrc/design-research-experiments.git
   cd design-research-experiments
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -e .

2. Minimal Runnable Example
---------------------------

.. code-block:: python

   from design_research_experiments import build_design, build_prompt_framing_study, validate_study

   study = build_prompt_framing_study()
   errors = validate_study(study)
   if errors:
       raise RuntimeError("\n".join(errors))

   conditions = build_design(study)
   print(study.study_id)
   print(f"conditions: {len(conditions)}")

3. What Happened
----------------

You defined a full study object, validated methodological consistency, and
materialized admissible experimental conditions. This is the orchestration
starting point before binding concrete runs.

4. Where To Go Next
-------------------

- :doc:`concepts`
- :doc:`typical_workflow`
- :doc:`study_structure_example`
- :doc:`examples/index`

Ecosystem Note
--------------

In a typical study, ``design-research-agents`` provides executable
participants, ``design-research-problems`` supplies the task,
``design-research-experiments`` defines the study structure, and
``design-research-analysis`` interprets the resulting records.
