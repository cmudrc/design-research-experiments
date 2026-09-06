"""Tests for explicit full paper-draft assembly."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from design_research_experiments import (
    PaperDraftIncompleteError,
    cli,
    export_paper_draft,
)
from design_research_experiments.conditions import Condition
from design_research_experiments.paper import PAPER_DRAFT_CONTRACT_VERSION
from design_research_experiments.runners import RunOutput, run_study
from design_research_experiments.schemas import ValidationError
from design_research_experiments.study import RunSpec

from .helpers import make_study


def _packet(
    *,
    package: str = "design-research-problems",
    component_id: str = "component-a",
    contributions: list[dict[str, Any]] | None = None,
    references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": PAPER_DRAFT_CONTRACT_VERSION,
        "source": {
            "package": package,
            "package_version": "1.0.0",
            "component_type": "test-component",
            "component_id": component_id,
        },
        "contributions": contributions or [],
        "references": references or [],
        "reporting_gaps": [],
    }


def _contribution(
    contribution_id: str,
    *,
    section: str,
    kind: str = "paragraph",
    evidence_basis: str = "configured",
    citation_keys: list[str] | None = None,
    path: str | None = None,
    hypothesis_ids: list[str] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if path is not None:
        metadata["path"] = path
    if hypothesis_ids is not None:
        metadata["hypothesis_ids"] = hypothesis_ids
    return {
        "contribution_id": contribution_id,
        "section": section,
        "kind": kind,
        "text": (
            "A retained result uses 50% of A&B under x_y and \N{GREEK SMALL LETTER ALPHA} < 0.05."
        ),
        "evidence_basis": evidence_basis,
        "citation_keys": citation_keys or [],
        "evidence_refs": ["retained/evidence.json"],
        "metadata": metadata,
    }


def _run_complete_study(tmp_path: Path, *, study_id: str = "complete-draft") -> Any:
    study = make_study(
        tmp_path=tmp_path,
        study_id=study_id,
        problem_ids=(),
        agent_specs=(),
    )
    study.title = "Paper #1: A&B_Study"
    study.description = "Configured scope is 50% & reproducible."
    study.rationale = (
        "The rationale retains \N{GREEK SMALL LETTER ALPHA} and x_y without inventing a "
        "literature gap."
    )
    study.analysis_plans = ()

    def run_condition(_run_spec: RunSpec, _condition: Condition) -> RunOutput:
        return RunOutput(outputs={"raw": "retained"}, metrics={"primary_outcome": 1.0})

    run_study(study, condition_runner=run_condition, checkpoint=False, show_progress=False)
    return study


def _compile_with_tectonic(draft_dir: Path) -> None:
    tectonic = shutil.which("tectonic")
    if tectonic is None:
        pytest.skip("tectonic is not installed")
    completed = subprocess.run(
        [tectonic, "main.tex"],
        cwd=draft_dir,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_full_draft_has_required_tree_manifest_boundaries_and_compiles(tmp_path: Path) -> None:
    study = _run_complete_study(tmp_path)
    packet = _packet(
        contributions=[
            _contribution(
                "problems:background",
                section="background",
                citation_keys=["curated2026"],
            )
        ],
        references=[
            {
                "key": "curated2026",
                "title": "Curated paper",
                "raw_text": "@misc{publisher-key, title={Curated paper}}",
            }
        ],
    )

    paths = export_paper_draft(study, component_packets=(packet,), require_complete=True)
    draft_dir = Path(study.output_dir or "") / "paper-draft"

    required = {
        "main.tex",
        "paper_draft.md",
        "references.bib",
        "paper_draft_manifest.json",
        "README.md",
        "sections/introduction.tex",
        "sections/background.tex",
        "sections/methods.tex",
        "sections/results.tex",
        "sections/discussion.tex",
    }
    assert required <= set(paths)
    assert (draft_dir / "tables").is_dir()
    assert (draft_dir / "figures").is_dir()
    assert "Generated paper draft. Author review required." in paths["main.tex"].read_text()
    assert "\\maketitle\n\\noindent\\fbox" in paths["main.tex"].read_text()
    assert "The study configuration specifies" in paths["sections/methods.tex"].read_text()
    assert "Retained execution evidence shows" in paths["sections/methods.tex"].read_text()
    assert "50\\%" in paths["sections/background.tex"].read_text()
    assert "A\\&B" in paths["sections/background.tex"].read_text()
    assert "x\\_y" in paths["sections/background.tex"].read_text()
    manifest = json.loads(paths["paper_draft_manifest.json"].read_text())
    assert manifest["document_status"] == "paper-draft"
    assert manifest["author_review_required"] is True
    assert manifest["completeness"] == "full"
    assert manifest["partial_blocks"] == 0
    assert manifest["run_accounting"]["successful"] == 2
    assert manifest["evidence_backed_blocks"] >= 5
    assert manifest["citation_count"] == 1
    assert manifest["todo_blocks"] >= 1
    assert paths["references.bib"].read_text().startswith("@misc{curated2026,")
    _compile_with_tectonic(draft_dir)


def test_partial_draft_is_written_before_strict_failure_and_overwrite_is_explicit(
    tmp_path: Path,
) -> None:
    study = make_study(tmp_path=tmp_path, study_id="partial-draft")
    with pytest.raises(PaperDraftIncompleteError) as captured:
        export_paper_draft(study, require_complete=True)

    paths = captured.value.paths
    assert paths["main.tex"].exists()
    assert "TODO (evidence)" in paths["paper_draft.md"].read_text()
    manifest = json.loads(paths["paper_draft_manifest.json"].read_text())
    assert manifest["completeness"] == "partial"
    assert manifest["partial_blocks"] >= 4
    _compile_with_tectonic(paths["main.tex"].parent)

    with pytest.raises(ValidationError, match="already contains files"):
        export_paper_draft(study)
    rewritten = export_paper_draft(study, overwrite=True)
    assert rewritten["main.tex"].exists()


def test_assets_are_copied_and_unsafe_or_missing_paths_are_not_silenced(tmp_path: Path) -> None:
    study = _run_complete_study(tmp_path, study_id="draft-assets")
    artifact_root = Path(study.output_dir or "")
    table_source = artifact_root / "analysis" / "effect_table.tex"
    table_source.parent.mkdir(parents=True)
    table_source.write_text("\\begin{tabular}{lr}A & 1\\\\\\end{tabular}\n", encoding="utf-8")
    table_packet = _packet(
        package="design-research-analysis",
        contributions=[
            _contribution(
                "analysis:effect-table",
                section="results",
                kind="table",
                evidence_basis="analyzed",
                path="analysis/effect_table.tex",
                hypothesis_ids=["h1"],
            )
        ],
    )
    paths = export_paper_draft(study, component_packets=(table_packet,), require_complete=True)
    manifest = json.loads(paths["paper_draft_manifest.json"].read_text())
    assert manifest["tables"] == ["tables/analysis-effect-table.tex"]
    assert paths["asset:analysis:effect-table"].read_text() == table_source.read_text()
    assert "\\input{tables/analysis-effect-table}" in paths["sections/results.tex"].read_text()

    missing_packet = _packet(
        package="design-research-analysis",
        contributions=[
            _contribution(
                "analysis:missing-figure",
                section="results",
                kind="figure",
                evidence_basis="analyzed",
                path="analysis/missing.png",
            )
        ],
    )
    missing = export_paper_draft(study, component_packets=(missing_packet,), overwrite=True)
    missing_manifest = json.loads(missing["paper_draft_manifest.json"].read_text())
    assert missing_manifest["completeness"] == "partial"
    assert any("missing artifact" in gap["message"] for gap in missing_manifest["reporting_gaps"])

    for unsafe_path in ("../outside.png", str(tmp_path / "absolute.png")):
        unsafe_packet = _packet(
            package="design-research-analysis",
            contributions=[
                _contribution(
                    "analysis:unsafe",
                    section="results",
                    kind="figure",
                    evidence_basis="analyzed",
                    path=unsafe_path,
                )
            ],
        )
        with pytest.raises(ValidationError, match="relative and safe"):
            export_paper_draft(study, component_packets=(unsafe_packet,), overwrite=True)


def test_manifest_source_persisted_packets_and_cli_strict_status(tmp_path: Path) -> None:
    study = _run_complete_study(tmp_path, study_id="portable-full-draft")
    artifact_root = Path(study.output_dir or "")
    packet = _packet(contributions=[_contribution("problems:portable", section="background")])
    (artifact_root / "component_metadata.json").write_text(
        json.dumps({"packets": [packet]}),
        encoding="utf-8",
    )
    paths = export_paper_draft(artifact_root / "manifest.json", require_complete=True)
    assert paths["main.tex"].exists()

    strict_study = make_study(tmp_path=tmp_path, study_id="cli-partial")
    strict_study.to_yaml(Path(strict_study.output_dir or "") / "study.yaml")
    assert (
        cli.main(
            [
                "draft-paper",
                str(strict_study.output_dir),
                "--require-complete",
            ]
        )
        == 2
    )
    assert (Path(strict_study.output_dir or "") / "paper-draft" / "main.tex").exists()


def test_target_cannot_replace_artifact_root_and_symlink_assets_are_rejected(
    tmp_path: Path,
) -> None:
    study = _run_complete_study(tmp_path, study_id="safe-target")
    artifact_root = Path(study.output_dir or "")
    with pytest.raises(ValidationError, match="cannot replace"):
        export_paper_draft(study, output_dir=artifact_root, overwrite=True)

    outside = tmp_path / "outside.tex"
    outside.write_text("unsafe", encoding="utf-8")
    link = artifact_root / "linked.tex"
    link.symlink_to(outside)
    packet = _packet(
        package="design-research-analysis",
        contributions=[
            _contribution(
                "analysis:linked",
                section="results",
                kind="table",
                evidence_basis="analyzed",
                path="linked.tex",
            )
        ],
    )
    with pytest.raises(ValidationError, match="symlink"):
        export_paper_draft(study, component_packets=(packet,))
