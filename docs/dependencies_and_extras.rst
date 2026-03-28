Dependencies and Extras
=======================

Core Install
------------

.. code-block:: bash

   pip install design-research-experiments

Editable contributor setup:

.. code-block:: bash

   git clone https://github.com/cmudrc/design-research-experiments.git
   cd design-research-experiments
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -e ".[dev]"

Or use:

.. code-block:: bash

   make dev

Maintainer workflows target Python ``3.12`` from ``.python-version``.

Extras Matrix
-------------

.. list-table::
   :header-rows: 1

   * - Extra
     - Purpose
   * - ``dev``
     - Contributor tooling and documentation/test gates

This package intentionally keeps runtime dependencies narrow because it sits at
methodological orchestration level and integrates sibling libraries through
adapters. In most projects, richer capability profiles are selected in
``design-research-agents``, ``design-research-problems``, and
``design-research-analysis`` rather than in this package itself.

Recommended install profiles:

- study design and orchestration only: base install
- local development and validation: ``pip install -e ".[dev]"``

Release packaging validation is exposed via ``make release-check``.
