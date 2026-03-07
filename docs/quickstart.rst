Quickstart
==========

Requires Python 3.12+ and assumes you are working from the repository root.

Create and activate a virtual environment:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip

Path A: Python API (Notebook/Script)
------------------------------------

Use this when you want study setup and execution in pure Python.

1. Install development tooling and package dependencies:

.. code-block:: bash

   make dev

2. Build and run a compact recipe-backed study:

.. code-block:: bash

   PYTHONPATH=src python examples/recipe_prompt_framing_run.py
   PYTHONPATH=src python examples/recipe_optimization_benchmark_run.py

3. Inspect exported artifacts under ``artifacts/example-prompt-framing/``.

Path B: CLI
-----------

Use this when you want file-based study workflows.

1. Validate a study definition:

.. code-block:: bash

   drexp validate-study path/to/study.yaml

2. Materialize conditions and run:

.. code-block:: bash

   drexp materialize-design path/to/study.yaml
   drexp run-study path/to/study.yaml

3. Export analysis-ready tables and bundle outputs:

.. code-block:: bash

   drexp export-analysis path/to/study.yaml
   drexp bundle-results path/to/output_dir

4. Generate standalone DOE tables (full/LHS/fractional):

.. code-block:: bash

   drexp generate-doe --kind lhs --factors-json '{"x": [0, 1], "y": [10, 20]}' --n-samples 12 --out artifacts/doe.csv

Checks and Docs
---------------

.. code-block:: bash

   make test
   make docs-check
   make docs-build

Next Steps
----------

- Install profiles and maintainer release checks: :doc:`dependencies_and_extras`
- Runnable examples and recipe scripts: :doc:`examples/index`
- Curated top-level API surface: :doc:`api`
