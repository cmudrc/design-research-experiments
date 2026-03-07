"""Validate pytest-cov JSON output against a minimum coverage threshold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the coverage checker.

    Returns:
        The parsed argument namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage-json",
        type=Path,
        required=True,
        help="Path to the pytest-cov JSON report.",
    )
    parser.add_argument(
        "--minimum",
        type=float,
        default=90.0,
        help="Minimum total coverage percentage.",
    )
    return parser.parse_args()


def load_total_coverage(path: Path) -> float:
    """Load the total coverage percentage from a pytest-cov JSON report.

    Args:
        path: Path to the JSON report.

    Returns:
        The total percentage covered.

    Raises:
        ValueError: Raised when the report does not include the totals block.
    """
    report = json.loads(path.read_text(encoding="utf-8"))
    totals = report.get("totals")
    if not isinstance(totals, dict):
        raise ValueError("Coverage report is missing the 'totals' section.")
    if "percent_covered" in totals:
        return float(totals["percent_covered"])
    if "percent_covered_display" in totals:
        return float(str(totals["percent_covered_display"]).rstrip("%"))
    raise ValueError("Coverage report is missing a total percentage field.")


def main() -> int:
    """Run the coverage threshold check.

    Returns:
        Process exit code: `0` on success and `1` on failure.
    """
    args = parse_args()
    total_coverage = load_total_coverage(args.coverage_json)
    if total_coverage < args.minimum:
        print(
            f"Coverage threshold failed: {total_coverage:.2f}% < {args.minimum:.2f}%.",
        )
        return 1
    print(f"Coverage check passed: {total_coverage:.2f}% >= {args.minimum:.2f}%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
