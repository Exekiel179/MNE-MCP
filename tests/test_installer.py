"""Verify environment reuse and fail-fast installation."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "installer", Path(__file__).resolve().parents[1] / "scripts/install.py"
)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def test_current_environment_only(monkeypatch):
    commands = []
    monkeypatch.setattr(installer, "preflight", lambda python: {"ready": True})
    monkeypatch.setattr(
        installer.subprocess, "run", lambda cmd, **kw: commands.append(cmd)
    )
    installer.install(clients="Codex,codex", skip_configure=False)
    assert all(c[0] == installer.sys.executable for c in commands)
    assert commands[0][1:4] == ["-m", "pip", "install"]
    assert commands[1][1:] == ["-m", "mne_mcp", "status"]
    assert commands[-1][1:4] == ["-m", "mne_mcp", "setup"]
    assert commands[-1][-2:] == ["--clients", "codex"]


def test_invalid_environment_stops_before_install(monkeypatch):
    commands = []
    monkeypatch.setattr(installer, "preflight", lambda python: {"ready": False})

    def fail(cmd, **kwargs):
        commands.append(cmd)
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(installer.subprocess, "run", fail)
    assert installer.main(["--skip-configure"]) == 1
    assert len(commands) == 0


@pytest.mark.parametrize("version", [[3, 12, 9], [3, 13, 0], [3, 14, 0]])
def test_missing_core_installed_then_verified(monkeypatch, version):
    commands = []
    report = {
        "ready": False,
        "version": version,
        "dependencies": {
            "pip": {"ok": True},
            "mne": {"ok": False, "missing": True},
            "pandas": {"ok": False, "missing": True},
        },
    }
    monkeypatch.setattr(
        installer.subprocess, "run", lambda cmd, **kw: commands.append(cmd)
    )
    monkeypatch.setattr(installer, "preflight", lambda python: {"ready": True})
    installer.prepare_environment("target-python", report)
    assert commands == [["target-python", "-m", "pip", "install", "mne>=1.6", "pandas"]]


@pytest.mark.parametrize("version", [[3, 12, 9], [3, 14, 0]])
def test_broken_import_does_not_trigger_pip(monkeypatch, version):
    monkeypatch.setattr(
        installer.subprocess, "run", lambda *a, **kw: pytest.fail("unexpected install")
    )
    report = {
        "ready": False,
        "version": version,
        "dependencies": {
            "pip": {"ok": True},
            "mne": {"ok": False, "missing": False, "error": "PermissionError"},
        },
    }
    with pytest.raises(ValueError, match="diagnosis"):
        installer.prepare_environment("python", report)


def test_failed_core_verification_stops(monkeypatch):
    report = {
        "ready": False,
        "version": [3, 12, 9],
        "dependencies": {"pip": {"ok": True}, "mne": {"ok": False, "missing": True}},
    }
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **kw: None)
    monkeypatch.setattr(installer, "preflight", lambda python: report)
    with pytest.raises(ValueError, match="did not pass"):
        installer.prepare_environment("python", report)


def test_explicit_interpreter_used_everywhere(monkeypatch):
    commands = []
    probes = []

    def probe(python):
        probes.append(python)
        return {"ready": True}

    monkeypatch.setattr(installer, "preflight", probe)
    monkeypatch.setattr(
        installer.subprocess, "run", lambda cmd, **kw: commands.append(cmd)
    )
    installer.install(
        clients="codex", skip_configure=False, python="/existing mne/bin/python"
    )
    assert probes == ["/existing mne/bin/python"]
    assert all(cmd[0] == probes[0] for cmd in commands)


def test_auto_client_requires_unique_match(monkeypatch):
    monkeypatch.setattr(installer, "detect_clients", lambda: ["codex", "claude"])
    with pytest.raises(ValueError, match="ambiguous"):
        installer.select_clients("auto")
    monkeypatch.setattr(installer, "detect_clients", lambda: ["claude"])
    assert installer.select_clients("auto") == ["claude"]


def test_json_check_does_not_install(monkeypatch, capsys):
    import json

    monkeypatch.setattr(
        installer, "preflight", lambda python: {"ready": False, "python": python}
    )
    monkeypatch.setattr(
        installer, "install", lambda **kw: pytest.fail("unexpected install")
    )
    assert installer.main(["--check", "--json", "--python", "existing-python"]) == 1
    assert json.loads(capsys.readouterr().out)["python"] == "existing-python"


@pytest.mark.parametrize(
    "version, ready",
    [
        ([3, 11, 9], False),
        ([3, 12, 9], True),
        ([3, 13, 0], True),
        ([3, 14, 0], True),
        ([3, 15, 0], True),
    ],
)
def test_preflight_has_no_upper_python_gate(monkeypatch, version, ready):
    import json
    from types import SimpleNamespace

    payload = {
        "python": "test-python",
        "version": version,
        "dependencies": {"mne": {"ok": True}},
    }
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(
            stdout="library notice\n__MNE_PROBE__" + json.dumps(payload)
        ),
    )
    monkeypatch.setattr(installer, "detect_clients", lambda: [])
    assert installer.preflight("test-python")["ready"] is ready


def test_package_metadata_has_no_upper_python_gate():
    import tomllib

    from packaging.specifiers import SpecifierSet

    metadata = tomllib.loads((installer.ROOT / "pyproject.toml").read_text())
    supported = SpecifierSet(metadata["project"]["requires-python"])
    assert "3.11" not in supported
    for version in ("3.12", "3.13", "3.14", "3.15"):
        assert version in supported


def test_package_has_console_script():
    import tomllib

    metadata = tomllib.loads((installer.ROOT / "pyproject.toml").read_text())
    assert metadata["project"]["scripts"]["mne-mcp"] == "mne_mcp.__main__:main"


def test_invalid_client_has_no_side_effects(monkeypatch):
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda *a, **k: pytest.fail("unexpected subprocess"),
    )
    assert installer.main(["--clients", "unknown"]) == 1


def test_default_install_targets_all_clients(monkeypatch):
    calls = []
    monkeypatch.setattr(installer, "install", lambda **kw: calls.append(kw))
    assert installer.main([]) == 0
    assert installer.select_clients(calls[0]["clients"]) == [
        "claude",
        "codex",
        "psyclaw",
        "opencode",
    ]
    assert installer.select_clients("psyclaw") == ["psyclaw"]
