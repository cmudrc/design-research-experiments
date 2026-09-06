"""Build an explicit, deterministic paper-support scaffold.

## Introduction
Run a tiny offline study, aggregate one component-owned citation and background
blurb with the durable run evidence, then explicitly export paper-draft support.
No paper files are written by ``run_study`` or ``collect_paper_support``.

## Technical Implementation
The example passes a versioned JSON-compatible component packet to
``collect_paper_support``. The packet carries one curated BibTeX record and
evidence-linked contributions. ``export_paper_support`` is called separately
with explicit overwrite permission.

## Expected Results
The script records two successful run-evidence directories and writes
``paper_support.json``, ``paper_outline.md``, ``references.json``, and
``references.bib`` beneath ``artifacts/example-paper-support/artifacts/paper-draft``.
"""

from __future__ import annotations

from pathlib import Path

import design_research_experiments as drex


def main() -> None:
    """Run the offline example and explicitly export its paper support."""
    output_dir = Path("artifacts/example-paper-support")
    study = drex.Study(
        study_id="example-paper-support",
        title="Example Paper Support Study",
        description="A deterministic demonstration of evidence-grounded paper support.",
        factors=(
            drex.Factor(
                name="prompt_frame",
                description="Prompt framing condition",
                kind=drex.FactorKind.MANIPULATED,
                levels=(
                    drex.Level(name="neutral", value="neutral"),
                    drex.Level(name="challenge", value="challenge"),
                ),
            ),
        ),
        hypotheses=(
            drex.Hypothesis(
                hypothesis_id="h1",
                label="Prompt framing effect",
                statement="Prompt framing changes the primary outcome.",
                independent_vars=("prompt_frame",),
                dependent_vars=("primary_outcome",),
            ),
        ),
        outcomes=(
            drex.OutcomeSpec(
                name="primary_outcome",
                source_table="runs",
                column="primary_outcome",
                aggregation="mean",
                primary=True,
            ),
        ),
        analysis_plans=(
            drex.AnalysisPlan(
                analysis_plan_id="ap1",
                hypothesis_ids=("h1",),
                tests=("difference_in_means",),
                outcomes=("primary_outcome",),
            ),
        ),
        output_dir=output_dir,
    )

    def run_condition(_run_spec: drex.RunSpec, condition: drex.Condition) -> drex.RunOutput:
        """Return one deterministic raw response and outcome."""
        frame = str(condition.factor_assignments["prompt_frame"])
        return drex.RunOutput(
            outputs={"response": f"retained response for {frame}"},
            metrics={"primary_outcome": float(frame == "challenge")},
        )

    drex.run_study(
        study,
        condition_runner=run_condition,
        checkpoint=False,
        show_progress=False,
    )
    component_packet = {
        "schema_version": "0.1.0",
        "source": {
            "package": "example-method-library",
            "package_version": "1.0.0",
            "component_type": "prompt-method",
            "component_id": "prompt-framing",
        },
        "contributions": [
            {
                "contribution_id": "example:prompt-framing:background",
                "section": "background",
                "kind": "bullet",
                "text": "Prompt framing was treated as an experimental manipulation.",
                "evidence_basis": "configured",
                "citation_keys": ["example2026"],
                "evidence_refs": ["study.yaml#/factors/0"],
            },
        ],
        "references": [
            {
                "key": "example2026",
                "title": "Example curated source",
                "raw_text": "@misc{example2026, title={Example curated source}}",
            }
        ],
        "reporting_gaps": [],
    }
    support = drex.collect_paper_support(study, component_packets=(component_packet,))
    paths = drex.export_paper_support(support, output_dir=output_dir, overwrite=True)
    print(f"Draft status: {support.draft_status}")
    print(f"Run accounting: {dict(support.run_accounting)}")
    print(f"Paper outline: {paths['paper_outline.md']}")


if __name__ == "__main__":
    main()
