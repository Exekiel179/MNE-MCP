"""Tests for on-demand backend provisioning (mne_mcp.backend)."""

import tomllib
from pathlib import Path

import pytest

from mne_mcp import backend

ROOT = Path(__file__).resolve().parents[1]


def _pyproject_extras() -> dict:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["optional-dependencies"]


def _strip_selfref(specs):
    """Drop self-referential `mne-mcp[...]` entries from an extras list."""
    return [s for s in specs if not s.replace("_", "-").lower().startswith("mne-mcp")]


def test_profiles_are_nested():
    assert set(backend.PROFILES["analysis"]) <= set(backend.PROFILES["ica"])
    assert set(backend.PROFILES["ica"]) <= set(backend.PROFILES["full"])


def test_profiles_match_pyproject_extras():
    """backend.PROFILES must not drift from pyproject's optional-dependencies."""
    extras = _pyproject_extras()
    assert set(backend._ANALYSIS) == set(extras["analysis"])
    assert set(backend._ICA) == set(_strip_selfref(extras["ica"]))
    assert set(backend._FULL) == set(_strip_selfref(extras["full"]))


def test_pip_command_in_venv_has_no_user_flag(monkeypatch):
    monkeypatch.setattr(backend, "_in_virtualenv", lambda: True)
    cmd = backend.pip_command("ica")
    assert cmd[1:4] == ["-m", "pip", "install"]
    assert "--user" not in cmd
    assert "scikit-learn>=1.1.0" in cmd
    assert "mne>=1.6.0" in cmd


def test_pip_command_global_adds_user(monkeypatch):
    monkeypatch.setattr(backend, "_in_virtualenv", lambda: False)
    cmd = backend.pip_command("analysis")
    assert "--user" in cmd
    # scikit-learn is NOT part of the 'analysis' profile
    assert not any("scikit-learn" in c for c in cmd)


def test_pip_command_rejects_unknown_profile():
    with pytest.raises(ValueError):
        backend.pip_command("nope")


def test_install_backend_invalidates_caches_and_reports(monkeypatch):
    seen = {}

    class _Proc:
        returncode = 0
        stdout = "Successfully installed mne-1.6.0"
        stderr = ""

    monkeypatch.setattr(backend, "_in_virtualenv", lambda: True)
    monkeypatch.setattr(backend.subprocess, "run", lambda *a, **k: _Proc())
    monkeypatch.setattr(
        backend.importlib, "invalidate_caches", lambda: seen.setdefault("inv", True)
    )
    monkeypatch.setattr(backend, "backend_available", lambda: True)

    result = backend.install_backend("ica")
    assert seen.get("inv") is True  # caches invalidated so a live process sees it
    assert result["ok"] is True
    assert result["profile"] == "ica"
    assert result["available"] is True


def test_install_backend_reports_failure(monkeypatch):
    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "ERROR: could not find a version"

    monkeypatch.setattr(backend, "_in_virtualenv", lambda: True)
    monkeypatch.setattr(backend.subprocess, "run", lambda *a, **k: _Proc())
    monkeypatch.setattr(backend.importlib, "invalidate_caches", lambda: None)
    monkeypatch.setattr(backend, "backend_available", lambda: False)

    result = backend.install_backend("analysis")
    assert result["ok"] is False
    assert "could not find a version" in result["stderr_tail"]
