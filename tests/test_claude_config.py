"""Tests for Claude Code MCP auto-configuration."""

import json
import os
import sys

from mne_mcp import claude_config


def test_build_server_config_shape():
    entry = claude_config.build_mcp_server_config()
    assert entry["type"] == "stdio"
    assert isinstance(entry["args"], list)
    assert "serve" in entry["args"]
    assert "MNE_MCP_TIMEOUT" in entry["env"]


def test_configure_creates_then_unchanged(tmp_path):
    settings = tmp_path / ".claude.json"

    res1 = claude_config.configure_claude_settings(settings)
    assert res1["status"] == "created"
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert "mne" in data["mcpServers"]

    # Re-running with identical config should report unchanged.
    res2 = claude_config.configure_claude_settings(settings)
    assert res2["status"] == "unchanged"
    assert res2["backup_path"]  # a backup is taken when the file already exists


def test_configure_preserves_other_servers(tmp_path):
    settings = tmp_path / ".claude.json"
    settings.write_text(
        json.dumps({"mcpServers": {"spss": {"command": "spss-mcp"}}}),
        encoding="utf-8",
    )
    claude_config.configure_claude_settings(settings)
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert "spss" in data["mcpServers"]  # untouched
    assert "mne" in data["mcpServers"]  # added


def test_entrypoint_resolves_absolute_path(monkeypatch):
    """Regression: when `mne-mcp` is on PATH, the registered command must be its
    ABSOLUTE path, not the bare name. A bare command breaks on client restart
    because the setup-time virtualenv is no longer on PATH (server shows up as
    disconnected)."""
    fake = os.path.join(os.sep, "opt", "venv", "bin", "mne-mcp")
    monkeypatch.setattr(claude_config.shutil, "which", lambda name: fake)
    command, args = claude_config.get_entrypoint_config()
    assert command == fake
    assert command != "mne-mcp"
    assert os.path.isabs(command)
    assert args[0] == "serve"


def test_entrypoint_falls_back_to_python_module(monkeypatch):
    """With no `mne-mcp` on PATH, fall back to the running interpreter + module."""
    monkeypatch.setattr(claude_config.shutil, "which", lambda name: None)
    command, args = claude_config.get_entrypoint_config()
    assert command == sys.executable
    assert args[:2] == ["-m", "mne_mcp.cli"]


def test_built_config_command_is_absolute_when_on_path(monkeypatch):
    """The written Claude config must carry the absolute command too."""
    fake = os.path.join(os.sep, "opt", "venv", "bin", "mne-mcp")
    monkeypatch.setattr(claude_config.shutil, "which", lambda name: fake)
    entry = claude_config.build_mcp_server_config()
    assert entry["command"] == fake
    assert os.path.isabs(entry["command"])
