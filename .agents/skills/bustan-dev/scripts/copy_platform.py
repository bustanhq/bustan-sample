# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Copy the platform modules and the test support of the reference project to a bustan project.

The reference is https://github.com/bustanhq/bustan-sample. The script clones it into a temporary
folder (or reads --reference), copies these folders, and changes the import
package of the reference to the package of the target:

- src/<pkg>/platform/            the shared modules of providers
- tests/<pkg>/platform/          their tests
- tests/support/                 open_sqlite(), the fakes and wait_until()

It never replaces a file. After it, do the steps that it prints: the
dependencies, the settings keys, the root module and tests/conftest.py.

Contract: standard library only. Exit codes: 0 when it copied the files, 1
when a file exists, 2 for a usage error.

    uv run copy_platform.py ~/code/my-api
    uv run copy_platform.py ~/code/my-api --only clock,database --dry-run
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REFERENCE_URL = "https://github.com/bustanhq/bustan-sample.git"
REFERENCE_PACKAGE = "bustan_sample"
DEPENDENCIES = {
    "database": ["aiosqlite"],
    "http": ["httpx2"],
    "jobs": ["croniter"],
}
DEV_DEPENDENCIES = {"jobs": ["types-croniter"]}
# Each module and the modules it imports. A copy includes the modules it needs.
NEEDS = {
    "clock": [],
    "database": [],
    "events": ["database", "jobs"],
    "jobs": ["clock", "database"],
    "mail": ["http"],
    "http": [],
    "health": ["database"],
    "idempotency": ["clock", "database"],
    "request_logging": [],
    "throttling": ["database"],
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="copy_platform.py", description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path, help="the target folder with pyproject.toml")
    parser.add_argument("--package", help="the import package (default: the only one in src/)")
    parser.add_argument(
        "--reference", type=Path, help=f"a local clone (default: a new clone of {REFERENCE_URL})"
    )
    parser.add_argument("--only", help="a comma-separated list of platform modules")
    parser.add_argument("--dry-run", action="store_true", help="list the files, write nothing")
    args = parser.parse_args(argv)
    project = args.project.expanduser().resolve()
    package = args.package or _only_package(project / "src")
    if package is None:
        print("give --package: src/ has no package, or more than one", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as folder:
        if args.reference is not None:
            reference = args.reference.expanduser().resolve()
        else:
            reference = Path(folder) / "reference"
            clone = ["git", "clone", "-q", "--depth", "1", REFERENCE_URL, str(reference)]
            if subprocess.run(clone, check=False).returncode != 0:
                print(f"git clone {REFERENCE_URL} failed", file=sys.stderr)
                return 2
        return _copy(args, project, package, reference)


def _copy(args: argparse.Namespace, project: Path, package: str, reference: Path) -> int:
    if not (reference / "src" / REFERENCE_PACKAGE / "platform").is_dir():
        print(f"{reference} is not the reference project", file=sys.stderr)
        return 2
    selected = _with_needs(args.only.split(",") if args.only else list(NEEDS))
    if selected is None:
        print(f"--only takes names from: {', '.join(NEEDS)}", file=sys.stderr)
        return 2
    pairs = _pairs(reference, project, package, selected)
    existing = [target for _, target in pairs if target.exists()]
    if existing:
        for target in existing:
            print(f"exists: {target.relative_to(project)}", file=sys.stderr)
        return 1
    pattern = re.compile(rf"\b{REFERENCE_PACKAGE}\b")
    for source, target in pairs:
        print(f"{'would copy' if args.dry_run else 'copied'} {target.relative_to(project)}")
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(pattern.sub(package, source.read_text()))
    _print_next_steps(package, selected)
    return 0


def _only_package(src: Path) -> str | None:
    if not src.is_dir():
        return None
    packages = [p.name for p in src.iterdir() if (p / "__init__.py").exists()]
    return packages[0] if len(packages) == 1 else None


def _with_needs(names: list[str]) -> list[str] | None:
    selected: list[str] = []
    pending = [name.strip() for name in names if name.strip()]
    while pending:
        name = pending.pop()
        if name not in NEEDS:
            return None
        if name not in selected:
            selected.append(name)
            pending.extend(NEEDS[name])
    return sorted(selected)


def _pairs(reference: Path, project: Path, package: str, selected: list[str]):
    pairs: list[tuple[Path, Path]] = []
    roots = [
        (
            reference / "src" / REFERENCE_PACKAGE / "platform",
            project / "src" / package / "platform",
        ),
        (
            reference / "tests" / REFERENCE_PACKAGE / "platform",
            project / "tests" / package / "platform",
        ),
    ]
    for source_root, target_root in roots:
        init = source_root / "__init__.py"
        if init.exists():
            pairs.append((init, target_root / "__init__.py"))
        for name in selected:
            folder = source_root / name
            for source in sorted(folder.rglob("*.py")) if folder.is_dir() else []:
                pairs.append((source, target_root / source.relative_to(source_root)))
    support = reference / "tests" / "support"
    for source in sorted(support.glob("*.py")):
        pairs.append((source, project / "tests" / "support" / source.name))
    return pairs


def _print_next_steps(package: str, selected: list[str]) -> None:
    runtime = sorted({dep for name in selected for dep in DEPENDENCIES.get(name, [])})
    dev = sorted({dep for name in selected for dep in DEV_DEPENDENCIES.get(name, [])})
    print("\nNext steps:")
    if runtime:
        print(f"- uv add {' '.join(runtime)}")
    if dev:
        print(f"- uv add --dev {' '.join(dev)}")
    print(f"- Copy the DATABASE_ and JOBS_ keys of src/{REFERENCE_PACKAGE}/app_settings.py of")
    print(f"  {REFERENCE_URL.removesuffix('.git')}")
    print("  into the settings model of the project, and into .env.example.")
    print("- Import the platform modules in the root module, as the reference does:")
    print("  HealthModule.for_root(), ThrottlerModule.for_root(storage=THROTTLER_STORAGE),")
    print("  ThrottlingModule, HealthChecksModule, RequestLoggingModule.")
    print("- Copy the client fixture and the environment lines of tests/conftest.py.")
    print("- Add [tool.pytest] with pythonpath = ['tests'] and --import-mode=importlib.")
    print(f"- Run ruff, ty, pytest and audit.py. Package: {package}")


if __name__ == "__main__":
    raise SystemExit(main())
