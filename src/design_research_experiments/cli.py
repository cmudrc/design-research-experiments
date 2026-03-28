"""Command-line interface for design-research-experiments."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .adapters.analysis import export_analysis_tables
from .artifacts import bundle_results, load_checkpointed_run_results
from .designs import build_design, generate_doe
from .io import csv_io
from .runners import resume_study, run_study
from .study import Study, load_study, validate_study


def main(argv: Sequence[str] | None = None) -> int:
    """Run the `drexp` CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    return int(handler(args))


def _build_parser() -> argparse.ArgumentParser:
    """Build the root CLI parser and command handlers."""
    parser = argparse.ArgumentParser(
        prog="drexp", description="Design research experiment orchestration"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-study", help="Validate a study file")
    validate_parser.add_argument("study", type=Path, help="Path to study YAML/JSON")
    validate_parser.set_defaults(handler=_handle_validate_study)

    materialize_parser = subparsers.add_parser(
        "materialize-design",
        help="Materialize study design into conditions",
    )
    materialize_parser.add_argument("study", type=Path, help="Path to study YAML/JSON")
    materialize_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path for conditions CSV output",
    )
    materialize_parser.set_defaults(handler=_handle_materialize_design)

    doe_parser = subparsers.add_parser(
        "generate-doe",
        help="Generate a DOE table (full, lhs, frac2) and write CSV output",
    )
    doe_parser.add_argument(
        "--kind",
        required=True,
        choices=["full", "lhs", "frac2"],
        help="Design type to generate.",
    )
    doe_parser.add_argument(
        "--factors-json",
        required=True,
        help="JSON object mapping factor names to DOE definitions.",
    )
    doe_parser.add_argument(
        "--n-samples",
        type=int,
        default=None,
        help="Number of LHS samples (required for --kind lhs).",
    )
    doe_parser.add_argument("--seed", type=int, default=0, help="Random seed.")
    doe_parser.add_argument(
        "--center-points",
        type=int,
        default=0,
        help="Number of center points to append.",
    )
    doe_parser.add_argument(
        "--replicates",
        type=int,
        default=1,
        help="Number of design-table replicates to append.",
    )
    doe_parser.add_argument(
        "--block-randomization-key",
        type=str,
        default=None,
        help="Optional column for within-block randomization.",
    )
    doe_parser.add_argument("--out", required=True, type=Path, help="Output CSV path.")
    randomize_group = doe_parser.add_mutually_exclusive_group()
    randomize_group.add_argument(
        "--randomize",
        dest="randomize",
        action="store_true",
        help="Randomize run order (default).",
    )
    randomize_group.add_argument(
        "--no-randomize",
        dest="randomize",
        action="store_false",
        help="Keep generated run order unchanged.",
    )
    doe_parser.set_defaults(randomize=True, handler=_handle_generate_doe)

    run_parser = subparsers.add_parser("run-study", help="Execute a study")
    run_parser.add_argument("study", type=Path, help="Path to study YAML/JSON")
    run_parser.add_argument("--parallelism", type=int, default=None, help="Local worker count")
    run_parser.add_argument("--dry-run", action="store_true", help="Validate only")
    run_parser.add_argument("--sqlite", action="store_true", help="Mirror outputs to SQLite")
    _add_progress_arguments(run_parser)
    run_parser.set_defaults(handler=_handle_run_study)

    resume_parser = subparsers.add_parser("resume-study", help="Resume a checkpointed study")
    resume_parser.add_argument("study", type=Path, help="Path to study YAML/JSON")
    resume_parser.add_argument("--parallelism", type=int, default=None, help="Local worker count")
    resume_parser.add_argument("--sqlite", action="store_true", help="Mirror outputs to SQLite")
    _add_progress_arguments(resume_parser)
    resume_parser.set_defaults(handler=_handle_resume_study)

    export_parser = subparsers.add_parser(
        "export-analysis",
        help="Export canonical analysis tables from checkpointed runs",
    )
    export_parser.add_argument("study", type=Path, help="Path to study YAML/JSON")
    export_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional explicit output directory",
    )
    export_parser.add_argument("--sqlite", action="store_true", help="Mirror outputs to SQLite")
    export_parser.set_defaults(handler=_handle_export_analysis)

    bundle_parser = subparsers.add_parser("bundle-results", help="Bundle a study output directory")
    bundle_parser.add_argument("output_dir", type=Path, help="Study output directory")
    bundle_parser.add_argument(
        "--bundle-path",
        type=Path,
        default=None,
        help="Optional target tar.gz path",
    )
    bundle_parser.set_defaults(handler=_handle_bundle_results)

    return parser


def _add_progress_arguments(parser: argparse.ArgumentParser) -> None:
    """Add tri-state progress-bar arguments to one parser."""
    progress_group = parser.add_mutually_exclusive_group()
    progress_group.add_argument(
        "--progress",
        dest="show_progress",
        action="store_true",
        help="Force a tqdm progress bar during run execution.",
    )
    progress_group.add_argument(
        "--no-progress",
        dest="show_progress",
        action="store_false",
        help="Disable the tqdm progress bar during run execution.",
    )
    parser.set_defaults(show_progress=None)


def _handle_validate_study(args: argparse.Namespace) -> int:
    """Handle the `validate-study` command."""
    study = _load_study(args.study)
    errors = validate_study(study)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"Study '{study.study_id}' is valid.")
    return 0


def _handle_materialize_design(args: argparse.Namespace) -> int:
    """Handle the `materialize-design` command."""
    study = _load_study(args.study)
    conditions = build_design(study)

    output_path = args.output or _study_output_dir(study) / "conditions.csv"
    rows = []
    for condition in conditions:
        row = {
            "study_id": study.study_id,
            "condition_id": condition.condition_id,
            "admissible": condition.admissible,
            "constraint_messages": condition.constraint_messages,
        }
        row.update(condition.factor_assignments)
        row.update({f"block_{key}": value for key, value in condition.block_assignments.items()})
        rows.append(row)

    csv_io.write_csv(output_path, rows)
    print(f"Materialized {len(conditions)} conditions to {output_path}")
    return 0


def _handle_generate_doe(args: argparse.Namespace) -> int:
    """Handle the `generate-doe` command."""
    try:
        factors = json.loads(str(args.factors_json))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--factors-json must be valid JSON: {exc.msg}") from exc
    if not isinstance(factors, dict):
        raise SystemExit("--factors-json must decode to a JSON object.")

    result = generate_doe(
        kind=str(args.kind),
        factors=factors,
        n_samples=args.n_samples,
        seed=int(args.seed),
        center_points=int(args.center_points),
        replicates=int(args.replicates),
        randomize=bool(args.randomize),
        block_randomization_key=args.block_randomization_key,
    )
    rows = result["design"]
    csv_io.write_csv(args.out, rows)
    print(result["interpretation"])
    for warning in result["warnings"]:
        print(f"Warning: {warning}")
    print(f"Wrote design to {args.out}")
    return 0


def _handle_run_study(args: argparse.Namespace) -> int:
    """Handle the `run-study` command."""
    study = _load_study(args.study)
    results = run_study(
        study,
        parallelism=args.parallelism,
        dry_run=args.dry_run,
        include_sqlite=args.sqlite,
        show_progress=args.show_progress,
    )
    if args.dry_run:
        print(f"Dry-run validation succeeded for study '{study.study_id}'.")
    else:
        print(f"Completed {len(results)} runs for study '{study.study_id}'.")
    return 0


def _handle_resume_study(args: argparse.Namespace) -> int:
    """Handle the `resume-study` command."""
    study = _load_study(args.study)
    results = resume_study(
        study,
        parallelism=args.parallelism,
        include_sqlite=args.sqlite,
        show_progress=args.show_progress,
    )
    print(f"Study '{study.study_id}' now has {len(results)} total runs after resume.")
    return 0


def _handle_export_analysis(args: argparse.Namespace) -> int:
    """Handle the `export-analysis` command."""
    study = _load_study(args.study)
    output_dir = args.output_dir or _study_output_dir(study)
    run_results = list(load_checkpointed_run_results(output_dir).values())
    conditions = build_design(study)

    paths = export_analysis_tables(
        study,
        conditions=conditions,
        run_results=run_results,
        output_dir=output_dir,
        include_sqlite=args.sqlite,
    )

    print(f"Exported canonical analysis tables to {output_dir}")
    for name, path in sorted(paths.items()):
        print(f"- {name}: {path}")
    return 0


def _handle_bundle_results(args: argparse.Namespace) -> int:
    """Handle the `bundle-results` command."""
    bundle_path = bundle_results(args.output_dir, args.bundle_path)
    print(f"Bundled study output to {bundle_path}")
    return 0


def _load_study(path: Path) -> Study:
    """Load and validate one study file from disk."""
    study = load_study(path)
    errors = validate_study(study)
    if errors:
        raise SystemExit("\n".join(errors))
    return study


def _study_output_dir(study: Study) -> Path:
    """Return the concrete output directory for a study."""
    return Path(study.output_dir or Path("artifacts") / study.study_id)


if __name__ == "__main__":
    raise SystemExit(main())
