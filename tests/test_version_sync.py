"""Tests for the version sync tool (openseed version show/bump)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

import openseed.cli.version as v_module
from openseed.cli.version import (
    _bump_version,
    _read_init_version,
    _read_pyproject_version,
    _write_init_version,
    _write_pyproject_version,
    bump,
    show,
)

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def pyproject(tmp_path: Path) -> Path:
    p = tmp_path / "pyproject.toml"
    p.write_text('[project]\nname = "openseed"\nversion = "0.9.0"\n')
    return p


@pytest.fixture()
def init_py(tmp_path: Path) -> Path:
    p = tmp_path / "__init__.py"
    p.write_text('"""OpenSeed."""\n\n__version__ = "0.9.0"\n')
    return p


@pytest.fixture()
def patched(pyproject: Path, init_py: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    monkeypatch.setattr(v_module, "_PYPROJECT", pyproject)
    monkeypatch.setattr(v_module, "_INIT_PY", init_py)
    return pyproject, init_py


# ── unit: pure helpers ────────────────────────────────────────────────────────


def test_read_pyproject_version(pyproject: Path) -> None:
    assert _read_pyproject_version(pyproject) == "0.9.0"


def test_read_init_version_string_literal(init_py: Path) -> None:
    assert _read_init_version(init_py) == "0.9.0"


def test_read_init_version_dynamic(tmp_path: Path) -> None:
    p = tmp_path / "__init__.py"
    p.write_text('from importlib.metadata import version\n__version__ = version("openseed")\n')
    assert _read_init_version(p) is None


def test_bump_patch() -> None:
    assert _bump_version("0.9.0", "patch") == "0.9.1"


def test_bump_minor() -> None:
    assert _bump_version("0.9.0", "minor") == "0.10.0"


def test_bump_major() -> None:
    assert _bump_version("0.9.0", "major") == "1.0.0"


def test_bump_patch_resets_nothing() -> None:
    assert _bump_version("1.2.3", "patch") == "1.2.4"


# ── unit: file writers ────────────────────────────────────────────────────────


def test_write_pyproject_version(pyproject: Path) -> None:
    _write_pyproject_version(pyproject, "0.9.1")
    assert _read_pyproject_version(pyproject) == "0.9.1"


def test_write_init_version_replaces_string_literal(init_py: Path) -> None:
    _write_init_version(init_py, "0.9.1")
    assert _read_init_version(init_py) == "0.9.1"


def test_write_init_version_replaces_dynamic(tmp_path: Path) -> None:
    p = tmp_path / "__init__.py"
    p.write_text('from importlib.metadata import version\n__version__ = version("openseed")\n')
    _write_init_version(p, "0.9.1")
    assert _read_init_version(p) == "0.9.1"


def test_write_init_version_creates_if_absent(tmp_path: Path) -> None:
    p = tmp_path / "__init__.py"
    p.write_text('"""No version here."""\n')
    _write_init_version(p, "0.9.1")
    assert _read_init_version(p) == "0.9.1"


# ── CLI: show ─────────────────────────────────────────────────────────────────


def test_show_prints_version(patched: tuple[Path, Path]) -> None:
    result = CliRunner().invoke(show)
    assert result.exit_code == 0
    assert "0.9.0" in result.output


def test_show_warns_when_versions_differ(
    pyproject: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_py = tmp_path / "__init__.py"
    init_py.write_text('__version__ = "0.8.0"\n')
    monkeypatch.setattr(v_module, "_PYPROJECT", pyproject)
    monkeypatch.setattr(v_module, "_INIT_PY", init_py)
    result = CliRunner().invoke(show)
    assert result.exit_code == 0
    assert "differ" in result.output


# ── CLI: bump ─────────────────────────────────────────────────────────────────


def test_bump_patch_cli(patched: tuple[Path, Path]) -> None:
    pyproject, init_py = patched
    result = CliRunner().invoke(bump, ["patch"])
    assert result.exit_code == 0
    assert _read_pyproject_version(pyproject) == "0.9.1"
    assert _read_init_version(init_py) == "0.9.1"


def test_bump_keeps_files_in_sync(patched: tuple[Path, Path]) -> None:
    pyproject, init_py = patched
    CliRunner().invoke(bump, ["minor"])
    assert _read_pyproject_version(pyproject) == _read_init_version(init_py)


def test_bump_default_is_patch(patched: tuple[Path, Path]) -> None:
    pyproject, _ = patched
    CliRunner().invoke(bump, [])
    assert _read_pyproject_version(pyproject) == "0.9.1"
