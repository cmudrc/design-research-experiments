Installation
============

Package Install
---------------

.. code-block:: bash

   pip install design-research-experiments

Editable Install
----------------

.. code-block:: bash

   git clone https://github.com/cmudrc/design-research-experiments.git
   cd design-research-experiments
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -e ".[dev]"

Maintainer Shortcut
-------------------

.. code-block:: bash

   make dev

Notes
-----

The experiments package keeps runtime dependencies deliberately small and relies
on adapters for optional integration with sibling libraries. See
:doc:`dependencies_and_extras` for frozen install and release-check workflows.
