"""Run a few lightweight consistency checks for the docs tree."""

from __future__ import annotations

from pathlib import Path

DOCS_DIR = Path("docs")
INDEX_PATH = DOCS_DIR / "index.rst"
API_PATH = DOCS_DIR / "api.rst"
README_PATH = Path("README.md")


def extract_toctree_entries(index_path: Path) -> tuple[str, ...]:
    """Extract document entries from the first toctree in `index.rst`.

    Args:
        index_path: Path to the docs index file.

    Returns:
        The referenced document names without suffixes.
    """
    entries: list[str] = []
    in_toctree = False
    for line in index_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == ".. toctree::":
            in_toctree = True
            continue
        if not in_toctree:
            continue
        if not stripped:
            continue
        if stripped.startswith(":"):
            continue
        if line.startswith("   "):
            entries.append(stripped)
            continue
        break
    return tuple(entries)


def validate_docs_tree() -> list[str]:
    """Collect any missing or inconsistent documentation references.

    Returns:
        A list of validation error messages.
    """
    errors: list[str] = []
    if not README_PATH.exists():
        errors.append("README.md is missing.")
    if not INDEX_PATH.exists():
        errors.append("docs/index.rst is missing.")
        return errors

    for entry in extract_toctree_entries(INDEX_PATH):
        if not (DOCS_DIR / f"{entry}.rst").exists():
            errors.append(f"docs/index.rst references missing document: {entry}.rst")

    if not API_PATH.exists():
        errors.append("docs/api.rst is missing.")
    elif "python_template" not in API_PATH.read_text(encoding="utf-8"):
        errors.append("docs/api.rst does not reference the package module.")
    return errors


def main() -> int:
    """Run the docs consistency check.

    Returns:
        Process exit code: `0` on success and `1` on failure.
    """
    errors = validate_docs_tree()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
