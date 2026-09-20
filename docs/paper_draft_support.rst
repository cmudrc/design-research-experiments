Paper-Draft Support
===================

``design-research-experiments`` can assemble factual, evidence-linked writing
support and a compilable paper draft without asking a language model to invent
prose or references. Both operations are explicit and require author review.

Nothing in ``run_study`` writes paper-draft files. ``collect_paper_support`` is
side-effect free. ``export_paper_support`` retains the lower-level scaffold:

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
The aggregate reference's ``provenance`` is a deduplicated list of packet
sources, not a bibliographic field to merge with component-local provenance.
Prompt and problem lineage remains available in contribution metadata.
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

The complete paper-draft assembler is a separate explicit call:

.. code-block:: python

   paths = drex.export_paper_draft(
       "artifacts/my-study/manifest.json",
       component_packets=(problem_packet, agent_packet, analysis_packet),
       require_complete=True,
   )

It creates:

.. code-block:: text

   paper-draft/
     main.tex
     paper_draft.md
     references.bib
     paper_draft_manifest.json
     README.md
     sections/
       introduction.tex
       background.tex
       methods.tex
       results.tex
       discussion.tex
     tables/
     figures/

The first page is marked exactly ``Generated paper draft. Author review
required.`` The manifest declares ``document_status`` as ``paper-draft`` and
records completeness, run accounting, contribution provenance, evidence
references, citations, figures, tables, and unresolved reporting gaps.

The Introduction carries the study title, description, rationale, hypotheses,
and explicit author TODOs rather than inventing novelty or a literature gap.
Background preserves sibling contributions as modular blocks. Methods phrases
configured and observed facts differently. Results includes only executed
analysis contributions and retained assets. Discussion provides factual recaps
and author TODOs for interpretation, implications, prior work, and future work.

Only curated BibTeX ``raw_text`` is written or cited. Missing BibTeX remains a
visible TODO, so a partial draft still compiles. Figure and table paths must be
relative to the study artifact root; absolute paths, traversal, and symlinks are
rejected. Missing safe paths become evidence-critical TODOs.

Collection can begin from a live ``Study``, ``study.yaml``, ``study.json``, a
portable completed study directory, or its ``manifest.json``. Fresh processes
also load an optional ``component_metadata.json`` containing one packet, a
packet array, or ``{"packets": [...]}``. Export refuses to overwrite an
existing paper-draft directory unless ``overwrite=True`` is stated explicitly.

``require_complete=True`` writes the draft and then raises
``PaperDraftIncompleteError`` if evidence-critical reporting gaps remain. The
CLI mirrors this behavior with a nonzero exit status:

.. code-block:: bash

   drexp draft-paper artifacts/my-study --require-complete
