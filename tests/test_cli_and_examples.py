"""Tests for CLI commands and example scripts."""

from __future__ import annotations

import re
import runpy
from pathlib import Path

from design_research_experiments import cli
from design_research_experiments.io import csv_io

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


def test_cli_progress_flags_are_forwarded(tmp_path: Path, monkeypatch: object) -> None:
    """CLI run and resume commands should forward tri-state progress options."""
    study = make_study(tmp_path=tmp_path, study_id="cli-progress", agent_specs=("agent-a",))
    study_path = tmp_path / "study.yaml"
    study.to_yaml(study_path)

    run_calls: list[dict[str, object]] = []
    resume_calls: list[dict[str, object]] = []

    def _fake_run(_study: object, **kwargs: object) -> list[object]:
        run_calls.append(kwargs)
        return []

    def _fake_resume(_study: object, **kwargs: object) -> list[object]:
        resume_calls.append(kwargs)
        return []

    monkeypatch.setattr(cli, "run_study", _fake_run)
    monkeypatch.setattr(cli, "resume_study", _fake_resume)

    assert cli.main(["run-study", str(study_path)]) == 0
    assert cli.main(["run-study", str(study_path), "--progress"]) == 0
    assert cli.main(["run-study", str(study_path), "--no-progress"]) == 0
    assert cli.main(["resume-study", str(study_path)]) == 0
    assert cli.main(["resume-study", str(study_path), "--progress"]) == 0
    assert cli.main(["resume-study", str(study_path), "--no-progress"]) == 0

    assert [call["show_progress"] for call in run_calls] == [None, True, False]
    assert [call["show_progress"] for call in resume_calls] == [None, True, False]


def test_cli_generate_doe_writes_csv(tmp_path: Path) -> None:
    """CLI should generate a DOE table CSV from JSON factor specs."""
    out_path = tmp_path / "doe.csv"

    assert (
        cli.main(
            [
                "generate-doe",
                "--kind",
                "lhs",
                "--factors-json",
                '{"x": [0, 1], "y": [10, 20]}',
                "--n-samples",
                "6",
                "--seed",
                "0",
                "--out",
                str(out_path),
            ]
        )
        == 0
    )
    rows = csv_io.read_csv(out_path)
    assert len(rows) == 6


def test_example_scripts_execute(tmp_path: Path, monkeypatch: object) -> None:
    """Bundled examples should execute successfully from a clean working directory."""
    monkeypatch.chdir(tmp_path)

    for script_name in (
        "basic_usage.py",
        "monty_hall_simulation.py",
        "public_api_walkthrough.py",
        "doe_capabilities.py",
        "recipe_overview.py",
        "recipe_prompt_framing_run.py",
        "recipe_optimization_benchmark_run.py",
        "recipe_strategy_comparison_run.py",
    ):
        runpy.run_path(
            str(Path(__file__).resolve().parents[1] / "examples" / script_name),
            run_name="__main__",
        )


def test_examples_use_top_level_import_convention() -> None:
    """Examples should import only the top-level package as `drex`."""
    examples_dir = Path(__file__).resolve().parents[1] / "examples"
    from_pattern = re.compile(r"^from design_research_experiments\.", re.MULTILINE)
    import_pattern = re.compile(r"^import design_research_experiments as drex$", re.MULTILINE)

    for path in sorted(examples_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert from_pattern.search(text) is None, f"Submodule import found in {path.name}"
        assert import_pattern.search(text) is not None, (
            f"Top-level alias import missing in {path.name}"
        )


def test_monty_hall_example_reports_switching_advantage(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    """The Monty Hall example should report the expected switching advantage."""
    monkeypatch.chdir(tmp_path)

    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "examples" / "monty_hall_simulation.py"),
        run_name="__main__",
    )

    output = capsys.readouterr().out
    csv_path = tmp_path / "artifacts" / "monty-hall" / "simulation_summary.csv"

    assert "Materialized 2 conditions" in output
    assert "Simulated 100 games per condition with seed 5" in output
    assert "stay wins 35/100 = 0.35" in output
    assert "switch wins 65/100 = 0.65" in output
    assert csv_path.exists()
    assert len(csv_io.read_csv(csv_path)) == 2
