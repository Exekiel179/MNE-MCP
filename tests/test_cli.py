"""CLI command tests — exercise each `mne-mcp` subcommand's main() branch."""

import sys

import pytest

from mne_mcp import cli


def run_cli(argv, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mne-mcp", *argv])
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
