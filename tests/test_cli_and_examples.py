"""Tests for CLI commands and example scripts."""

from __future__ import annotations

import runpy
from pathlib import Path

from design_research_experiments import cli

from .helpers import make_study


def _mock_agent(*, problem_packet: object, seed: int) -> dict[str, object]:
    """Return deterministic mock output for CLI execution tests."""
    del problem_packet
    return {
        "output": {"text": f"seed={seed}"},
        "metrics": {"input_tokens": 3, "output_tokens": 4, "cost_usd": 0.005},
        "events": [{"event_type": "assistant_output", "text": "ok", "actor_id": "agent"}],
    }


def test_cli_roundtrip_commands(tmp_path: Path, monkeypatch: object) -> None:
    """CLI should validate, materialize, run, resume, export, and bundle a study."""
    study = make_study(tmp_path=tmp_path, study_id="cli-study", agent_specs=("agent-a",))
    study_path = tmp_path / "study.yaml"
    study.to_yaml(study_path)

    import design_research_experiments.adapters.agents as adapter_agents

    monkeypatch.setattr(
        adapter_agents,
        "_resolve_from_design_research_agents",
        lambda agent_id: _mock_agent if agent_id == "agent-a" else None,
    )

    assert cli.main(["validate-study", str(study_path)]) == 0

    conditions_path = tmp_path / "conditions.csv"
    assert cli.main(["materialize-design", str(study_path), "--output", str(conditions_path)]) == 0
    assert conditions_path.exists()

    assert cli.main(["run-study", str(study_path), "--parallelism", "1", "--sqlite"]) == 0

    output_dir = Path(study.output_dir or tmp_path / "cli-study")
    assert (output_dir / "runs.csv").exists()

    assert cli.main(["resume-study", str(study_path)]) == 0
    assert cli.main(["export-analysis", str(study_path), "--sqlite"]) == 0

    bundle_path = tmp_path / "bundle.tar.gz"
    assert cli.main(["bundle-results", str(output_dir), "--bundle-path", str(bundle_path)]) == 0
    assert bundle_path.exists()


def test_cli_run_study_dry_run(tmp_path: Path, monkeypatch: object) -> None:
    """CLI dry-run path should return success without execution."""
    study = make_study(tmp_path=tmp_path, study_id="cli-dry-run")
    study_path = tmp_path / "study.json"
    study.to_json(study_path)

    import design_research_experiments.adapters.agents as adapter_agents

    monkeypatch.setattr(
        adapter_agents, "_resolve_from_design_research_agents", lambda _id: _mock_agent
    )

    assert cli.main(["run-study", str(study_path), "--dry-run"]) == 0


def test_example_scripts_execute(tmp_path: Path, monkeypatch: object) -> None:
    """Bundled examples should execute successfully from a clean working directory."""
    monkeypatch.chdir(tmp_path)

    for script_name in (
        "basic_usage.py",
        "public_api_walkthrough.py",
        "recipe_overview.py",
    ):
        runpy.run_path(
            str(Path(__file__).resolve().parents[1] / "examples" / script_name),
            run_name="__main__",
        )
