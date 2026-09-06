Paper-Draft Support
===================

``design-research-experiments`` can assemble factual, evidence-linked writing
support without asking a language model to invent prose or references. This is
an explicit halfway point between raw study artifacts and a manuscript.

Nothing in ``run_study`` writes paper-draft files. ``collect_paper_support`` is
side-effect free, and ``export_paper_support`` must be called explicitly before
the following directory exists:

.. code-block:: text

   artifacts/
     paper-draft/
       paper_support.json
       paper_outline.md
       references.json
       references.bib

The Markdown output begins with ``PAPER DRAFT SUPPORT — NOT A MANUSCRIPT``.
It labels every contribution as configured, observed, analyzed, or user
supplied, preserves its package/component provenance, and ends with unresolved
reporting TODOs. It does not assert a scientific narrative.

Component Contribution Contract
-------------------------------

Problems, Agents, Analysis, and user extensions contribute independently
versioned JSON-compatible packets. The initial reporting contract is ``0.1.0``:

.. code-block:: json

   {
     "schema_version": "0.1.0",
     "source": {
       "package": "design-research-problems",
       "package_version": "0.5.0",
       "component_type": "problem",
       "component_id": "example-problem"
     },
     "contributions": [
       {
         "contribution_id": "problems:example-problem:background",
         "section": "background",
         "kind": "bullet",
         "text": "Describe the curated problem foundation.",
         "evidence_basis": "configured",
         "citation_keys": ["foundation2024"],
         "evidence_refs": ["study.yaml#/problem_ids/0"],
         "metadata": {}
       }
     ],
     "references": [
       {
         "key": "foundation2024",
         "title": "A curated foundation",
         "raw_text": "@article{foundation2024, title={A curated foundation}}"
       }
     ],
     "reporting_gaps": []
   }

The packet deliberately uses the Problems library's existing ``Citation``
field shape. Experiments accepts those dataclass instances or their JSON form;
it does not define a competing bibliography model.

Stable citation keys are deduplicated across packets. Compatible partial
records are merged and retain every contributing source. Conflicting titles or
other populated fields fail loudly. A contribution cannot cite an absent key.
Only curated ``raw_text`` beginning with a BibTeX entry marker is written to
``references.bib``; missing BibTeX becomes a TODO instead of a fabricated
entry.

Evidence Boundaries
-------------------

``evidence_basis`` accepts four values:

- ``configured``: present in the study or component configuration;
- ``observed``: directly established by retained run evidence;
- ``analyzed``: established by an executed analysis record; and
- ``user``: supplied explicitly by the caller.

Observed and analyzed contributions require at least one ``evidence_ref``.
Merely configuring a tool, evaluator, model, or analysis does not satisfy that
requirement.

The aggregator itself contributes hypotheses, design details, factor levels,
seed policy, planned analyses, and observed run accounting. Missing sibling
metadata, incomplete or failed runs, configured-but-unobserved analysis, and
incomplete BibTeX are emitted as explicit gaps.

Explicit Export
---------------

.. code-block:: python

   import design_research_experiments as drex

   support = drex.collect_paper_support(
       "artifacts/my-study",
       component_packets=(problem_packet, agent_packet, analysis_packet),
   )
   paths = drex.export_paper_support(
       support,
       output_dir="artifacts/my-study",
   )

Collection can begin from a live ``Study``, ``study.yaml``, ``study.json``, or a
portable completed study directory. Export refuses to overwrite an existing
paper-draft directory unless ``overwrite=True`` is stated explicitly.

This layer does not yet create ``main.tex`` or claim that a planned analysis
ran. Those belong to later slices built on executed analysis records and this
validated contribution set.
