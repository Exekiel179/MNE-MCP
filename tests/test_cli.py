"""Exercise the package entrypoint and each command's main() branch."""

import json
import subprocess
import sys

import pytest

from mne_mcp import __main__ as cli


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    for key, value in {
        "MNE_MCP_CONFIG": tmp_path / "defaults.json",
        "MNE_MCP_RESULTS_DIR": tmp_path / "results",
        "MNE_MCP_DATA_DIR": tmp_path,
        "MNE_MCP_PSYCLAW_CONFIG": tmp_path / ".psyclaw/mcp/mne.json",
        "MPLCONFIGDIR": tmp_path / "matplotlib",
        "_MNE_FAKE_HOME_DIR": tmp_path,
        "MNE_DONTWRITE_HOME": "true",
        "PYTHON_DOTENV_DISABLED": "1",
    }.items():
        monkeypatch.setenv(key, str(value))


def run_module(*args):
    return subprocess.run(
        [sys.executable, "-m", "mne_mcp", *args],
        capture_output=True,
        text=True,
        timeout=90,
    )


@pytest.mark.parametrize(
    "args, expected, code",
    [
        (("version",), "MNE MCP v", 0),
        (("setup", "--help"), "python -m mne_mcp setup", 0),
        (("setup", "--clients", "unknown"), "Setup failed", 2),
    ],
)
def test_package_entrypoint(args, expected, code):
    result = run_module(*args)
    assert result.returncode == code, result.stderr
    assert expected in result.stdout + result.stderr


def test_package_setup_registers_and_verifies(tmp_path):
    result = run_module("setup", "--clients", "psyclaw")
    assert result.returncode == 0, result.stderr
    entry = json.loads((tmp_path / ".psyclaw/mcp/mne.json").read_text())
    assert entry["args"] == ["-m", "mne_mcp", "serve", "--transport", "stdio"]
    assert len(list((tmp_path / ".psyclaw/skills").glob("*/SKILL.md"))) == 14
    verified = run_module("verify", "--client", "psyclaw")
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["connected"] is True


def run_cli(argv, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["python -m mne_mcp", *argv])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    return exc.value.code


def test_cli_version(monkeypatch, capsys):
    assert run_cli(["version"], monkeypatch) == 0
    assert "MNE MCP v" in capsys.readouterr().out


def test_cli_status(monkeypatch, capsys):
    assert run_cli(["status"], monkeypatch) == 0
    assert "Capability Status" in capsys.readouterr().out


def test_cli_setup_info(monkeypatch, capsys):
    assert run_cli(["setup-info"], monkeypatch) == 0
    assert "mcpServers" in capsys.readouterr().out


def test_cli_configure_show(monkeypatch, capsys):
    assert run_cli(["configure", "--show"], monkeypatch) == 0


def test_cli_configure_claude_writes_tmp(monkeypatch, capsys, tmp_path):
    settings = tmp_path / "claude.json"
    code = run_cli(["configure-claude", "--settings-file", str(settings)], monkeypatch)
    assert code == 0
    assert settings.exists()


def test_cli_setup_rejects_empty_clients(monkeypatch, capsys):
    assert run_cli(["setup", "--clients", ""], monkeypatch) == 2
    assert "Setup failed" in capsys.readouterr().err


def test_cli_setup_defaults_all(monkeypatch, capsys):
    from mne_mcp import claude_config, connection

    selected = []
    checks = []

    def verify(**kwargs):
        checks.append(kwargs)
        return {"tool_count": 42, "mne_available": True}

    def configure(clients, **kwargs):
        selected.extend(clients)
        return {"clients": [], "skills": None}

    monkeypatch.setattr(connection, "verify_connection", verify)
    monkeypatch.setattr(claude_config, "configure_clients", configure)
    assert run_cli(["setup"], monkeypatch) == 0
    assert selected == list(claude_config.DEFAULT_CLIENTS)
    assert checks == [{}, {"registered": True}]


def test_cli_failed_connection_does_not_register(monkeypatch, capsys):
    from mne_mcp import claude_config, connection

    def fail(**kwargs):
        raise ValueError("connection failed")

    monkeypatch.setattr(connection, "verify_connection", fail)
    monkeypatch.setattr(
        claude_config,
        "configure_clients",
        lambda *a, **k: pytest.fail("unexpected write"),
    )
    assert run_cli(["setup", "--clients", "psyclaw"], monkeypatch) == 2


def test_cli_verify_saved_psyclaw(monkeypatch, capsys):
    from mne_mcp import connection

    def verify(*, registered):
        assert registered
        return {"connected": True}

    monkeypatch.setattr(connection, "verify_connection", verify)
    assert run_cli(["verify", "--client", "psyclaw"], monkeypatch) == 0
