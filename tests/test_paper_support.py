"""Tests for evidence-grounded paper-support aggregation and export."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest

from design_research_experiments import collect_paper_support, export_paper_support
from design_research_experiments.conditions import Condition
from design_research_experiments.evidence import initialize_run_evidence, write_run_evidence
from design_research_experiments.paper import (
    PAPER_DRAFT_CONTRACT_VERSION,
    ContributionKind,
    ContributionSource,
    EvidenceBasis,
    PaperContribution,
    PaperContributionPacket,
    PaperSection,
    ReportingGap,
    render_paper_support_markdown,
)
from design_research_experiments.runners import RunOutput, run_study
from design_research_experiments.schemas import RunStatus, ValidationError
from design_research_experiments.study import RunResult, RunSpec

from .helpers import make_study


def component_packet(
    *,
    package: str,
    component_type: str,
    component_id: str,
    contributions: list[dict[str, Any]] | None = None,
    references: list[dict[str, Any]] | None = None,
    reporting_gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one valid JSON-compatible component packet."""
    return {
        "schema_version": PAPER_DRAFT_CONTRACT_VERSION,
        "source": {
            "package": package,
            "package_version": "1.2.3",
            "component_type": component_type,
            "component_id": component_id,
        },
        "contributions": contributions or [],
        "references": references or [],
        "reporting_gaps": reporting_gaps or [],
    }


def contribution(
    contribution_id: str,
    *,
    section: str = "methods",
    text: str = "Report the configured method.",
    evidence_basis: str = "configured",
    citation_keys: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one valid contribution payload."""
    return {
        "contribution_id": contribution_id,
        "section": section,
        "kind": "bullet",
        "text": text,
        "evidence_basis": evidence_basis,
        "citation_keys": citation_keys or [],
        "evidence_refs": ["component.json#/method"],
        "metadata": {"curated": True, **(metadata or {})},
    }


def test_collect_support_aggregates_evidence_components_and_citations(tmp_path: Path) -> None:
    """The aggregate should stay factual, deduplicated, and provenance-linked."""
    study = make_study(tmp_path=tmp_path, study_id="paper-support-study")

    def mixed_run(_run_spec: RunSpec, condition: Condition) -> RunOutput:
        if condition.factor_assignments["variant"] == "b":
            raise RuntimeError("expected evidence failure")
        return RunOutput(
            outputs={"response": "retained raw response"},
            metrics={"primary_outcome": 0.75},
        )

    run_study(study, condition_runner=mixed_run, checkpoint=False, show_progress=False)
    assert not (Path(study.output_dir or "") / "artifacts" / "paper-draft").exists()

    citation = {
        "key": "foundation2024",
        "kind": "bibtex",
        "authors": ["A. Author", "B. Author"],
        "title": "Foundation method",
        "year": 2024,
        "raw_text": "@article{foundation2024,\n  title={Foundation method}\n}",
    }
    problem_packet = component_packet(
        package="design-research-problems",
        component_type="problem",
        component_id="problem-1",
        contributions=[
            contribution(
                "problems:problem-1:background",
                section="background",
                text="The study used the curated problem foundation.",
                citation_keys=["foundation2024"],
            )
        ],
        references=[citation],
    )
    agent_packet = component_packet(
        package="design-research-agents",
        component_type="agent",
        component_id="agent-a",
        contributions=[contribution("agents:agent-a:methods", citation_keys=["foundation2024"])],
        references=[
            {
                "key": "foundation2024",
                "title": "Foundation method",
                "url": "https://example.test/foundation",
            }
        ],
    )
    analysis_packet = component_packet(
        package="design-research-analysis",
        component_type="analysis",
        component_id="ttest",
        contributions=[
            contribution(
                "analysis:ttest:result",
                section="results",
                text="The configured t-test completed against the retained observations.",
                evidence_basis="analyzed",
                metadata={
                    "included_run_ids": ["run-included"],
                    "exclusions": [{"run_id": "run-excluded", "reason": "Missing score."}],
                },
            )
        ],
    )

    support = collect_paper_support(
        study,
        component_packets=(problem_packet, agent_packet, analysis_packet),
    )
    payload = support.to_dict()

    assert payload["schema_version"] == PAPER_DRAFT_CONTRACT_VERSION
    assert payload["draft_status"] == "deterministic-scaffold-not-a-manuscript"
    assert payload["run_accounting"] == {
        "planned": 2,
        "attempted": 2,
        "terminal": 2,
        "successful": 1,
        "failed": 1,
        "skipped": 0,
        "incomplete": 0,
        "analyzed": 1,
        "excluded": 1,
    }
    assert {item["evidence_basis"] for item in payload["contributions"]} >= {
        "configured",
        "observed",
        "analyzed",
    }
    observed = next(
        item
        for item in payload["contributions"]
        if item["contribution_id"] == "experiments:observed-run-accounting"
    )
    assert "1 successful, 1 failed" in observed["text"]
    assert "1 analyzed run and 1 documented excluded run" in observed["text"]
    assert len(observed["evidence_refs"]) == 2
    assert len(payload["references"]) == 1
    assert payload["references"][0]["url"] == "https://example.test/foundation"
    assert {row["package"] for row in payload["references"][0]["provenance"]} == {
        "design-research-agents",
        "design-research-problems",
    }
    gap_ids = {gap["gap_id"] for gap in payload["reporting_gaps"]}
    assert "experiments:failed-runs" in gap_ids
    assert "experiments:analysis-not-observed" not in gap_ids
    assert "experiments:missing-problem-contributions" not in gap_ids
    assert "experiments:missing-agent-contributions" not in gap_ids


def test_shared_citations_keep_aggregate_provenance_separate_from_packet_metadata(
    tmp_path: Path,
) -> None:
    """Problem-local provenance must not overwrite the deduplicated source list."""
    study = make_study(tmp_path=tmp_path, study_id="shared-problem-citations")
    packets = [
        component_packet(
            package="design-research-problems",
            component_type="problem",
            component_id=problem_id,
            references=[
                {
                    "key": "shared-source",
                    "title": "Shared problem source",
                    "provenance": {"problem_id": problem_id, "prompt_ids": [prompt_id]},
                }
            ],
            contributions=[
                contribution(
                    f"problems:{problem_id}:background",
                    citation_keys=["shared-source"],
                    metadata={"prompt_ids": [prompt_id]},
                )
            ],
        )
        for problem_id, prompt_id in (("problem-1", "prompt-1"), ("problem-2", "prompt-2"))
    ]
    original = deepcopy(packets)

    support = collect_paper_support(study, component_packets=(*packets, packets[0]))

    assert len(support.references) == 1
    assert support.references[0]["provenance"] == [packet["source"] for packet in packets]
    assert collect_paper_support(study, component_packets=tuple(reversed(packets))) == support
    assert packets == original
    for packet in packets:
        retained = next(
            item
            for item in support.contributions
            if item.source.component_id == packet["source"]["component_id"]
        )
        assert (
            retained.metadata["prompt_ids"] == packet["contributions"][0]["metadata"]["prompt_ids"]
        )

    packets[1]["references"][0]["title"] = "Conflicting source title"
    with pytest.raises(ValidationError, match="Conflicting citation key"):
        collect_paper_support(study, component_packets=packets)


def test_export_is_explicit_strongly_marked_and_refuses_implicit_overwrite(
    tmp_path: Path,
) -> None:
    """Collection should be side-effect free; export should be visibly draft-only."""
    study = make_study(tmp_path=tmp_path, study_id="explicit-paper-export")
    citation = {
        "key": "source2025",
        "title": "Curated source",
        "raw_text": "@misc{source2025,\n  title={Curated source}\n}",
    }
    packet = component_packet(
        package="design-research-problems",
        component_type="problem",
        component_id="problem-1",
        references=[citation],
        contributions=[
            contribution(
                "problems:source",
                section="background",
                citation_keys=["source2025"],
            )
        ],
    )
    support = collect_paper_support(study, component_packets=(packet,))
    draft_dir = Path(study.output_dir or "") / "artifacts" / "paper-draft"
    assert not draft_dir.exists()

    paths = export_paper_support(support, output_dir=study.output_dir or tmp_path)

    assert set(paths) == {
        "paper_support.json",
        "paper_outline.md",
        "references.json",
        "references.bib",
    }
    assert all(path.parent == draft_dir for path in paths.values())
    assert (
        paths["paper_outline.md"]
        .read_text(encoding="utf-8")
        .startswith("# PAPER DRAFT SUPPORT — NOT A MANUSCRIPT")
    )
    assert "[@source2025]" in paths["paper_outline.md"].read_text(encoding="utf-8")
    assert paths["references.bib"].read_text(encoding="utf-8") == (
        "@misc{source2025,\n  title={Curated source}\n}\n"
    )
    assert not (draft_dir / "main.tex").exists()

    with pytest.raises(ValidationError, match="already contains files"):
        export_paper_support(support, output_dir=study.output_dir or tmp_path)
    assert export_paper_support(
        support,
        output_dir=study.output_dir or tmp_path,
        overwrite=True,
    )["paper_support.json"].exists()


def test_portable_directory_can_be_aggregated_in_a_fresh_process(tmp_path: Path) -> None:
    """Paper support should reconstruct from study.yaml and evidence after execution exits."""
    study = make_study(tmp_path=tmp_path, study_id="portable-paper-support")

    def run_condition(run_spec: RunSpec, _condition: Condition) -> RunOutput:
        return RunOutput(outputs={"raw": run_spec.run_id}, metrics={"primary_outcome": 1.0})

    run_study(study, condition_runner=run_condition, checkpoint=False, show_progress=False)
    output_dir = Path(study.output_dir or "")
    project_root = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(project_root / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from design_research_experiments import collect_paper_support; "
                f"support = collect_paper_support({json.dumps(str(output_dir))}); "
                "print(json.dumps(support.to_dict()['run_accounting'], sort_keys=True))"
            ),
        ],
        cwd=project_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "attempted": 2,
        "failed": 0,
        "incomplete": 0,
        "planned": 2,
        "skipped": 0,
        "successful": 2,
        "terminal": 2,
        "analyzed": 0,
        "excluded": 0,
    }

    assert collect_paper_support(output_dir).run_accounting["successful"] == 2
    json_path = study.to_json(output_dir / "portable-study.json")
    yaml_path = study.to_yaml(output_dir / "portable-study.yaml")
    assert collect_paper_support(json_path).study_id == study.study_id
    assert collect_paper_support(yaml_path).study_id == study.study_id


@dataclass(frozen=True)
class CitationLike:
    """Problems-compatible citation shape used without importing the sibling package."""

    key: str
    kind: str
    authors: tuple[str, ...]
    title: str
    year: int
    raw_text: str


def test_reference_inputs_reuse_dataclass_shape_and_expose_missing_bibtex(tmp_path: Path) -> None:
    """Citation-like dataclasses should normalize without a second bibliography model."""
    study = make_study(tmp_path=tmp_path, study_id="citation-shape")
    support = collect_paper_support(
        study,
        user_references=(
            CitationLike(
                key="complete",
                kind="bibtex",
                authors=("One Author",),
                title="Complete citation",
                year=2024,
                raw_text="@article{source_key, title={Complete citation}}",
            ),
            {"key": "incomplete", "title": "Needs curated BibTeX"},
        ),
    )

    assert support.references[0]["authors"] == ["One Author"]
    assert any(
        gap.gap_id == "experiments:missing-bibtex:incomplete" for gap in support.reporting_gaps
    )
    paths = export_paper_support(support, output_dir=study.output_dir or tmp_path)
    bib_text = paths["references.bib"].read_text(encoding="utf-8")
    assert "@article{complete" in bib_text
    assert "incomplete" not in bib_text


def test_missing_evidence_and_component_metadata_become_explicit_gaps(tmp_path: Path) -> None:
    """An unexecuted study must produce TODOs rather than plausible execution prose."""
    study = make_study(tmp_path=tmp_path, study_id="paper-gaps")

    support = collect_paper_support(study)

    assert support.run_accounting["planned"] == 0
    assert not any(
        contribution.evidence_basis.value == "observed" for contribution in support.contributions
    )
    gap_ids = {gap.gap_id for gap in support.reporting_gaps}
    assert gap_ids >= {
        "experiments:missing-run-evidence",
        "experiments:missing-problem-contributions",
        "experiments:missing-agent-contributions",
        "experiments:analysis-not-observed",
    }


def test_example_local_agent_packet_satisfies_the_component_contract(tmp_path: Path) -> None:
    """Custom agents may own honest metadata without impersonating the Agents package."""
    study = make_study(tmp_path=tmp_path, study_id="local-agent-metadata")
    packet = component_packet(
        package="design-research",
        component_type="agent",
        component_id="example.scripted-agent",
        contributions=[contribution("example:scripted-agent:methods")],
    )

    support = collect_paper_support(study, component_packets=(packet,))

    assert not any(
        gap.gap_id == "experiments:missing-agent-contributions" for gap in support.reporting_gaps
    )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda packet: packet.update(schema_version="9.9.9"), "schema_version"),
        (lambda packet: packet.update(source=[]), "source must be a JSON object"),
        (
            lambda packet: packet["source"].update(package=""),
            "source package must be a non-empty string",
        ),
        (lambda packet: packet.update(contributions="bad"), "contributions must be a JSON array"),
        (
            lambda packet: packet.update(contributions=["bad"]),
            "contributions entries must be objects",
        ),
        (lambda packet: packet.update(references="bad"), "references must be a JSON array"),
        (
            lambda packet: packet.update(references=[{"key": "missing-title"}]),
            "citation title must be a non-empty string",
        ),
        (
            lambda packet: packet.update(
                contributions=[contribution("bad-section", section="appendix")]
            ),
            "paper contribution section must be one of",
        ),
        (
            lambda packet: packet.update(
                contributions=[
                    {
                        **contribution("bad-kind"),
                        "kind": "sentence",
                    }
                ]
            ),
            "paper contribution kind must be one of",
        ),
        (
            lambda packet: packet.update(
                contributions=[
                    {
                        **contribution("bad-basis"),
                        "evidence_basis": "assumed",
                    }
                ]
            ),
            "evidence_basis must be one of",
        ),
    ],
)
def test_component_packet_validation_is_strict(
    mutate: Any,
    message: str,
) -> None:
    """Malformed sibling packets should fail at the integration boundary."""
    packet = component_packet(
        package="design-research-problems",
        component_type="problem",
        component_id="problem-1",
    )
    mutate(packet)

    with pytest.raises(ValidationError, match=message):
        PaperContributionPacket.from_mapping(packet)


def test_conflicts_and_unknown_citations_fail_loudly(tmp_path: Path) -> None:
    """Stable ids and citation keys must never silently resolve contradictory inputs."""
    study = make_study(tmp_path=tmp_path, study_id="paper-conflicts")
    first = component_packet(
        package="design-research-problems",
        component_type="problem",
        component_id="problem-1",
        contributions=[contribution("shared", citation_keys=["same-key"])],
        references=[{"key": "same-key", "title": "First title"}],
    )
    conflicting_reference = component_packet(
        package="design-research-agents",
        component_type="agent",
        component_id="agent-a",
        references=[{"key": "same-key", "title": "Different title"}],
    )
    with pytest.raises(ValidationError, match="Conflicting citation key"):
        collect_paper_support(study, component_packets=(first, conflicting_reference))

    conflicting_contribution = component_packet(
        package="design-research-agents",
        component_type="agent",
        component_id="agent-a",
        contributions=[contribution("shared", text="Contradictory blurb")],
    )
    with pytest.raises(ValidationError, match="Conflicting paper contribution id"):
        collect_paper_support(study, component_packets=(first, conflicting_contribution))

    unknown_citation = component_packet(
        package="design-research-problems",
        component_type="problem",
        component_id="problem-1",
        contributions=[contribution("unknown", citation_keys=["absent-key"])],
    )
    with pytest.raises(ValidationError, match="unknown citations: absent-key"):
        collect_paper_support(study, component_packets=(unknown_citation,))

    first_gap = component_packet(
        package="design-research-problems",
        component_type="problem",
        component_id="problem-1",
        reporting_gaps=[{"gap_id": "shared-gap", "section": "methods", "message": "First gap"}],
    )
    conflicting_gap = component_packet(
        package="design-research-agents",
        component_type="agent",
        component_id="agent-a",
        reporting_gaps=[{"gap_id": "shared-gap", "section": "methods", "message": "Different gap"}],
    )
    with pytest.raises(ValidationError, match="Conflicting reporting gap id"):
        collect_paper_support(study, component_packets=(first_gap, conflicting_gap))


def test_typed_packets_and_evidence_identity_are_validated(tmp_path: Path) -> None:
    """Typed packet versions and cross-study evidence should be checked explicitly."""
    study = make_study(tmp_path=tmp_path, study_id="typed-paper-packet")
    with pytest.raises(ValidationError, match="unsupported schema version"):
        PaperContributionPacket(
            source=ContributionSource(
                package="test-package",
                package_version="1.0.0",
                component_type="method",
                component_id="method-a",
            ),
            schema_version="9.9.9",
        )

    def run_condition(_run_spec: RunSpec, _condition: Condition) -> RunOutput:
        return RunOutput(outputs={"raw": "retained"})

    run_study(study, condition_runner=run_condition, checkpoint=False, show_progress=False)
    first_run_path = next((Path(study.output_dir or "") / "artifacts" / "runs").glob("*/run.json"))
    run_record = json.loads(first_run_path.read_text(encoding="utf-8"))
    run_record["study_id"] = "different-study"
    first_run_path.write_text(json.dumps(run_record), encoding="utf-8")

    with pytest.raises(ValidationError, match="does not belong to study"):
        collect_paper_support(study)


def test_typed_contract_rejects_invalid_direct_construction(tmp_path: Path) -> None:
    """The typed layer should enforce the same invariants as JSON packet parsing."""
    source = ContributionSource(
        package="test-package",
        package_version="1.0.0",
        component_type="method",
        component_id="method-a",
    )
    other_source = ContributionSource(
        package="other-package",
        package_version="1.0.0",
        component_type="method",
        component_id="method-b",
    )
    with pytest.raises(ValidationError, match="source package must be non-empty"):
        ContributionSource("", "1.0.0", "method", "method-a")

    valid = PaperContribution(
        contribution_id="typed:valid",
        section=PaperSection.METHODS,
        kind=ContributionKind.FIGURE,
        text="Include the retained comparison figure.",
        evidence_basis=EvidenceBasis.OBSERVED,
        source=source,
        evidence_refs=("artifacts/figure.png",),
    )
    invalid_cases = (
        {"section": cast(Any, "methods")},
        {"kind": cast(Any, "bullet")},
        {"evidence_basis": cast(Any, "configured")},
        {"contribution_id": ""},
        {"text": ""},
        {"evidence_refs": ()},
    )
    defaults: dict[str, Any] = {
        "contribution_id": "typed:invalid",
        "section": PaperSection.METHODS,
        "kind": ContributionKind.BULLET,
        "text": "Valid text",
        "evidence_basis": EvidenceBasis.OBSERVED,
        "source": source,
        "evidence_refs": ("run.json",),
    }
    for changes in invalid_cases:
        with pytest.raises(ValidationError):
            PaperContribution(**{**defaults, **changes})

    with pytest.raises(ValidationError, match="gap_id must be non-empty"):
        ReportingGap("", PaperSection.METHODS, "Message", source)
    with pytest.raises(ValidationError, match="message must be non-empty"):
        ReportingGap("gap", PaperSection.METHODS, "", source)
    with pytest.raises(ValidationError, match="contributions must share packet source"):
        PaperContributionPacket(
            source=other_source,
            contributions=(valid,),
        )
    with pytest.raises(ValidationError, match="gaps must share packet source"):
        PaperContributionPacket(
            source=other_source,
            reporting_gaps=(ReportingGap("gap", PaperSection.METHODS, "Message", source),),
        )

    typed_packet = PaperContributionPacket(source=source, contributions=(valid,))
    assert typed_packet.to_dict()["contributions"][0]["kind"] == "figure"
    study = make_study(
        tmp_path=tmp_path,
        study_id="typed-valid-paper",
        problem_ids=(),
        agent_specs=(),
    )
    support = collect_paper_support(study, component_packets=(typed_packet,))
    assert "**Figure:** Include the retained comparison figure." in (
        render_paper_support_markdown(support)
    )
    with pytest.raises(ValidationError, match="must be objects or JSON mappings"):
        collect_paper_support(study, component_packets=(cast(Any, object()),))


def test_pending_and_skipped_evidence_produce_grammatical_todos(tmp_path: Path) -> None:
    """Non-success lifecycle states should remain explicit and readable."""
    study = make_study(tmp_path=tmp_path, study_id="lifecycle-paper-gaps")
    run_spec = RunSpec(
        run_id="run-lifecycle",
        study_id=study.study_id,
        condition_id="condition-a",
        problem_id="problem-1",
        replicate=1,
        seed=1,
        agent_spec_ref="agent-a",
        problem_spec_ref="problem-1",
    )
    initialize_run_evidence(run_spec, output_dir=study.output_dir or tmp_path)
    pending = collect_paper_support(study)
    assert any(
        gap.message == "Resolve or explain 1 planned run without a terminal outcome."
        for gap in pending.reporting_gaps
    )

    write_run_evidence(
        RunResult(
            run_id=run_spec.run_id,
            status=RunStatus.SKIPPED,
            status_reason="test_skip",
            run_spec=run_spec,
        ),
        output_dir=study.output_dir or tmp_path,
    )
    skipped = collect_paper_support(study)
    assert any(
        gap.message == "Explain why 1 planned run was skipped." for gap in skipped.reporting_gaps
    )


def test_clean_complete_study_can_report_no_remaining_gaps(tmp_path: Path) -> None:
    """The renderer should visibly confirm when the supplied contract is complete."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="complete-paper-support",
        problem_ids=(),
        agent_specs=(),
    )
    study.analysis_plans = ()

    def run_condition(_run_spec: RunSpec, _condition: Condition) -> RunOutput:
        return RunOutput(outputs={"raw": "retained"})

    run_study(study, condition_runner=run_condition, checkpoint=False, show_progress=False)
    support = collect_paper_support(study)
    assert support.reporting_gaps == ()
    assert "- [x] No unresolved reporting gaps recorded." in render_paper_support_markdown(support)


def test_additional_malformed_reference_and_contribution_shapes_fail(tmp_path: Path) -> None:
    """Loose packet fields should not be silently coerced into plausible metadata."""
    study = make_study(tmp_path=tmp_path, study_id="malformed-paper-fields")
    with pytest.raises(ValidationError, match="Citation records must be JSON objects"):
        collect_paper_support(study, user_references=("not-a-citation",))

    for field_name, value, message in (
        ("citation_keys", "not-an-array", "citation_keys must be a JSON array"),
        ("citation_keys", [""], "citation_keys cannot contain empty values"),
        ("metadata", [], "metadata must be a JSON object"),
    ):
        raw_contribution = contribution("malformed")
        raw_contribution[field_name] = value
        packet = component_packet(
            package="design-research-problems",
            component_type="problem",
            component_id="problem-1",
            contributions=[raw_contribution],
        )
        with pytest.raises(ValidationError, match=message):
            collect_paper_support(study, component_packets=(packet,))
