Examples
========

These runnable examples show how the package behaves in realistic experimental
workflows, from compact study definitions to recipe-backed runs that move
artifacts through the broader ecosystem.

.. note::

   **Start with** :doc:`core/basic_usage` if you want the shortest path from
   package import to a concrete study definition and materialized condition set.

Core API Patterns
-----------------

Small, readable examples that focus on study schemas, validation, and
lightweight orchestration.

- :doc:`core/index`
- :doc:`core/basic_usage`
- :doc:`core/monty_hall_simulation`

DOE Exploration
---------------

Compare design strategies and inspect how condition spaces change with
different methodological choices.

- :doc:`doe/index`
- :doc:`doe/doe_capabilities`

Recipe-Backed Runs
------------------

Follow end-to-end examples that compose benchmark studies, execution
plans, and canonical artifact exports.

- :doc:`recipes/index`
- :doc:`recipes/recipe_prompt_framing_run`
- :doc:`recipes/recipe_optimization_benchmark_run`

.. toctree::
   :maxdepth: 2
   :hidden:

   core/index
   doe/index
   recipes/index
