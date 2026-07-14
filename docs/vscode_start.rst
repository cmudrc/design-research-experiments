Run An Example In VS Code
=========================

Use this page when you want to try ``design-research-experiments`` in VS Code.
Choose the installed-package path for a first user workflow, or the source
checkout path when you want to run the repository's checked-in examples and
development checks.

The checked-in ``examples/`` directory lives in the repository source. Do not
assume those files are present inside the PyPI wheel.

Requirements
------------

- Python 3.12 or newer. Maintainer workflows target the version in
  ``.python-version``.
- VS Code with the Python extension.
- A VS Code integrated terminal.

Installed Package From PyPI
---------------------------

Open an empty folder in VS Code, then create and activate a virtual
environment from ``Terminal > New Terminal``.

On macOS or Linux:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install design-research-experiments

On Windows PowerShell:

.. code-block:: powershell

   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install design-research-experiments

Run ``Python: Select Interpreter`` from the command palette and choose the
interpreter inside ``.venv``. If VS Code does not list it, enter the interpreter
path manually:

- macOS/Linux: ``.venv/bin/python``
- Windows: ``.venv\Scripts\python.exe``

Create ``experiments_example.py`` in the workspace folder:

.. code-block:: python

   from design_research_experiments import (
       build_design,
       build_prompt_framing_study,
       validate_study,
   )

   study = build_prompt_framing_study()
   errors = validate_study(study)
   if errors:
       raise RuntimeError("\n".join(errors))

   conditions = build_design(study)
   print(study.study_id)
   print(f"conditions: {len(conditions)}")

Run the file with VS Code's ``Run Python File`` action, or run:

.. code-block:: bash

   python experiments_example.py

Source Checkout For Repository Examples
---------------------------------------

Use this path when you want the checked-in examples, docs, tests, and optional
development tooling.

.. code-block:: bash

   git clone https://github.com/cmudrc/design-research-experiments.git
   cd design-research-experiments
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip setuptools wheel
   python -m pip install -e ".[dev]"

Equivalent maintainer shortcut:

.. code-block:: bash

   make dev

Run the deterministic example path from the integrated terminal:

.. code-block:: bash

   make run-example
   make examples-test
   python examples/basic_usage.py

First Development Checks
------------------------

Run the checks from VS Code's integrated terminal:

.. code-block:: bash

   make test
   make qa
   make docs-check

``make qa`` runs linting, formatting checks, type checks, and tests. Run
``make coverage`` before merge when changing tested behavior.

Optional Backends
-----------------

Install optional design-of-experiments backends only when a workflow needs
them:

.. code-block:: bash

   python -m pip install -e ".[doe]"

Troubleshooting
---------------

- If VS Code imports fail but the terminal works, reselect the ``.venv``
  interpreter and reload the window.
- If ``make`` uses the wrong Python, activate ``.venv`` in the terminal or run
  ``PYTHON=.venv/bin/python make test``.
- If Windows activation is blocked, switch the terminal profile to Command
  Prompt and run ``.\.venv\Scripts\activate.bat``.
- If optional design-of-experiments backends are needed, install
  ``pip install -e ".[doe]"`` inside the active environment.
- Avoid committing generated runtime output under ``artifacts/``,
  ``docs/_build/``, or local virtual environment directories.
