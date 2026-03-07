Dependencies And Extras
=======================

The base install intentionally has no required runtime dependencies.

The `dev` extra installs the local contributor toolchain:

- `build`
- `mypy`
- `pre-commit`
- `pytest`
- `pytest-cov`
- `ruff`
- `sphinx`
- `sphinx-rtd-theme`
- `twine`
- `uv`

Install it with:

.. code-block:: bash

   pip install -e ".[dev]"
