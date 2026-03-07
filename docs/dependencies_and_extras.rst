Dependencies and Extras
=======================

The project keeps runtime dependencies minimal and pushes contributor tooling
into the development profile.

Core Install
------------

.. code-block:: bash

   pip install -e .

Runtime dependency:

- ``PyYAML`` for study YAML serialization/deserialization.

Development Install
-------------------

.. code-block:: bash

   make dev

This installs linting, typing, testing, docs, and release-check tooling.

Reproducible Install
--------------------

.. code-block:: bash

   make repro REPRO_EXTRAS="dev"

The frozen install uses ``uv.lock`` and pinned interpreter ``3.12.12``.

Maintainer Release Baseline
---------------------------

Use this flow before tagging a release:

1. Use Python ``3.12.12`` (from ``.python-version``).
2. Regenerate lock data: ``make lock``.
3. Verify frozen install and checks: ``make repro REPRO_EXTRAS=\"dev\"`` and ``make ci``.
4. Build artifacts and validate metadata: ``make release-check``.
5. Commit lock/dependency updates before tagging.

Notes
-----

- The package currently exposes one optional dependency profile: ``dev``.
- SQLite export support uses the Python standard library ``sqlite3`` module
  and does not require an extra package.
