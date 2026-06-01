"""Tests for Claude Code MCP auto-configuration."""

import json

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
    assert "mne" in data["mcpServers"]   # added
