Examples
========

The examples in this repository are runnable research-oriented scripts. They are
designed to show not only API usage, but how the library fits into realistic
experimental workflows. The featured examples below list dependencies,
expected scope, and the primary concept they demonstrate.

Featured Examples
-----------------

Basic Usage
~~~~~~~~~~~

Construct and serialize a compact study definition.

**Requires:** base install
**Runtime:** short
**Teaches:** study schema basics, hypotheses, outcomes, and serialization

Monty Hall Simulation
~~~~~~~~~~~~~~~~~~~~~

Run a tiny randomized probability simulation with the core study API.

**Requires:** base install
**Runtime:** short
**Teaches:** reproducible RNG, condition-level simulation, summary artifact generation

DOE Capabilities
~~~~~~~~~~~~~~~~

Generate and inspect multiple DOE strategies.

**Requires:** base install
**Runtime:** short
**Teaches:** design-type selection, condition-space control, DOE interpretation

Recipe Prompt Framing Run
~~~~~~~~~~~~~~~~~~~~~~~~~

Instantiate and execute a recipe-backed prompt-framing study.

**Requires:** base install; this script uses deterministic mock components
**Runtime:** medium
**Teaches:** recipe configuration, checkpointed run flow, canonical artifact outputs

Recipe Optimization Benchmark Run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run a recipe-configured optimization benchmarking study.

**Requires:** base install; this script uses deterministic mock components
**Runtime:** medium
**Teaches:** benchmark study composition, replication control, analysis export path

Recipe Strategy Comparison Run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run a packaged-problem strategy comparison study with factor-bound agent arms.

**Requires:** base install; this script uses deterministic mock components
**Runtime:** medium
**Teaches:** generalized comparison recipes, factor-bound agent execution, canonical summary export

Full Catalog
------------

.. toctree::
   :maxdepth: 2

   core/index
   doe/index
   recipes/index
