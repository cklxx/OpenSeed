"""Version management subcommands for OpenSeed."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import click
from rich.console import Console

console = Console()

_PACKAGE_DIR = Path(__file__).parent.parent
_ROOT = _PACKAGE_DIR.parent.parent
_PYPROJECT = _ROOT / "pyproject.toml"
_INIT_PY = _PACKAGE_DIR / "__init__.py"

# Matches: version = "0.9.0"  (pyproject.toml [project] table)
_PYPROJECT_VER_RE = re.compile(r'^(version\s*=\s*)"([^"]+)"', re.MULTILINE)
# Matches only string-literal __version__, not dynamic calls like version("pkg")
_DUNDER_VER_RE = re.compile(r'^(__version__\s*=\s*)"([^"]+)"', re.MULTILINE)
# Matches any __version__ assignment (for replacement including dynamic form)
_DUNDER_ASSIGN_RE = re.compile(r"^__version__\s*=\s*.+$", re.MULTILINE)
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _read_pyproject_version(path: Path) -> str:
    with path.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"].lstrip("v")


def _read_init_version(path: Path) -> str | None:
    """Return hardcoded __version__ string, or None if dynamic/absent."""
    m = _DUNDER_VER_RE.search(path.read_text())
    return m.group(2).lstrip("v") if m else None


def _write_pyproject_version(path: Path, new_ver: str) -> None:
    text = path.read_text()
    updated = _PYPROJECT_VER_RE.sub(rf'\g<1>"{new_ver}"', text)
    if updated == text:
        raise click.ClickException("Could not locate version field in pyproject.toml")
    path.write_text(updated)


def _write_init_version(path: Path, new_ver: str) -> None:
    text = path.read_text()
    replacement = f'__version__ = "{new_ver}"'
    if _DUNDER_ASSIGN_RE.search(text):
        updated = _DUNDER_ASSIGN_RE.sub(replacement, text)
    else:
        updated = text.rstrip("\n") + f"\n\n{replacement}\n"
    path.write_text(updated)


def _bump_version(ver: str, part: str) -> str:
    m = _SEMVER_RE.match(ver)
    if not m:
        raise click.ClickException(f"Invalid semver: {ver!r}")
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


@click.group("version")
def version_group() -> None:
    """Manage the openseed package version."""


@version_group.command("show")
def show() -> None:
    """Show current version from pyproject.toml and __init__.py."""
    pyproject_ver = _read_pyproject_version(_PYPROJECT)
    init_ver = _read_init_version(_INIT_PY)

    console.print(f"pyproject.toml : [bold]{pyproject_ver}[/bold]")
    if init_ver is None:
        console.print("__init__.py    : [dim]dynamic (importlib.metadata)[/dim]")
    else:
        console.print(f"__init__.py    : [bold]{init_ver}[/bold]")
        if pyproject_ver != init_ver:
            console.print(
                "[yellow]⚠  Versions differ — run `openseed version bump` to sync.[/yellow]"
            )


@version_group.command("bump")
@click.argument("part", type=click.Choice(["patch", "minor", "major"]), default="patch")
def bump(part: str) -> None:
    """Bump the version (patch|minor|major) in pyproject.toml and __init__.py."""
    current = _read_pyproject_version(_PYPROJECT)
    new_ver = _bump_version(current, part)
    _write_pyproject_version(_PYPROJECT, new_ver)
    _write_init_version(_INIT_PY, new_ver)
    console.print(f"[green]✓[/green] Bumped {current} → {new_ver} ({part})")
