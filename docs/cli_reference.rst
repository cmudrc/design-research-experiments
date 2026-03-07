CLI Reference
=============

Entry point:

.. code-block:: bash

   drexp <subcommand> [options]

The CLI mirrors the study lifecycle from validation through execution and
artifact export.

Subcommands
-----------

``validate-study``
~~~~~~~~~~~~~~~~~~

Validate study structure and cross-reference integrity.

.. code-block:: bash

   drexp validate-study path/to/study.yaml

``materialize-design``
~~~~~~~~~~~~~~~~~~~~~~

Materialize admissible conditions and optionally write a conditions CSV.

.. code-block:: bash

   drexp materialize-design path/to/study.yaml --output artifacts/conditions.csv

``generate-doe``
~~~~~~~~~~~~~~~~

Generate DOE tables directly (full, lhs, frac2).

.. code-block:: bash

   drexp generate-doe --kind lhs --factors-json '{"x": [0, 1], "y": [10, 20]}' --n-samples 12 --out artifacts/doe.csv

``run-study``
~~~~~~~~~~~~~

Execute one study definition.

.. code-block:: bash

   drexp run-study path/to/study.yaml --parallelism 4

``resume-study``
~~~~~~~~~~~~~~~~

Resume from checkpointed outputs.

.. code-block:: bash

   drexp resume-study path/to/study.yaml --parallelism 4

``export-analysis``
~~~~~~~~~~~~~~~~~~~

Export canonical analysis tables from checkpointed runs.

.. code-block:: bash

   drexp export-analysis path/to/study.yaml --output-dir artifacts/study-output

``bundle-results``
~~~~~~~~~~~~~~~~~~

Create a bundled archive of study outputs.

.. code-block:: bash

   drexp bundle-results artifacts/study-output --bundle-path artifacts/study-output.tar.gz
