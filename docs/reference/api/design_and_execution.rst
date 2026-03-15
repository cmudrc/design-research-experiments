Design and Execution
====================

These helpers sit between the static study definition and the outputs that land
on disk. They cover three related jobs: generating admissible designs,
validating the study contract, and orchestrating actual execution.

In a typical workflow, you validate early, materialize conditions next, and run
only once the study contract looks stable.

.. currentmodule:: design_research_experiments

Design Materialization
----------------------

Use these helpers to turn factors, blocks, and design specifications into the
condition sets that will actually be executed.

.. autosummary::
   :nosignatures:

   build_design
   generate_doe
   materialize_conditions

.. autofunction:: build_design

.. autofunction:: generate_doe

.. autofunction:: materialize_conditions

Validation and Orchestration
----------------------------

Use these helpers once a study definition exists and you want to check it,
execute it, or resume execution from checkpointed artifacts.

.. autosummary::
   :nosignatures:

   validate_study
   run_study
   resume_study

.. autofunction:: validate_study

.. autofunction:: run_study

.. autofunction:: resume_study
