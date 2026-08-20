Dependencies and Extras
=======================

Core Install
------------

.. code-block:: bash

   python -m pip install design-research-experiments

Editable contributor setup:

.. code-block:: bash

   git clone https://github.com/cmudrc/design-research-experiments.git
   cd design-research-experiments
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"

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
   * - ``doe``
     - Optional SciPy/QMC and pyDOE3 design-of-experiments backends

This package intentionally keeps runtime dependencies narrow because it sits at
methodological orchestration level and integrates sibling libraries through
adapters. In most projects, richer capability profiles are selected in
``design-research-agents``, ``design-research-problems``, and
``design-research-analysis`` rather than in this package itself.

The base install includes deterministic stdlib implementations for the DOE
paths used by the bundled examples. Install ``doe`` only when selecting the
SciPy/QMC Latin-hypercube backend or the pyDOE3 fractional-factorial backend:

.. code-block:: bash

   python -m pip install "design-research-experiments[doe]"

Recommended install profiles:

- study design and orchestration only: base install
- optional SciPy/QMC or pyDOE3 backends: ``python -m pip install "design-research-experiments[doe]"``
- local development and validation: ``python -m pip install -e ".[dev]"``

Release packaging validation is exposed via ``make release-check``.
