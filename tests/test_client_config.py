"""Tests for multi-client MCP registration (Claude Code / Codex / opencode)."""

import json
import tomllib

import pytest

from mne_mcp import claude_config as cc


def test_codex_creates_and_parses(tmp_path):
    p = tmp_path / "config.toml"
    res = cc.configure_codex(p)
    assert res["status"] == "created"
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    assert "mne" in data["mcp_servers"]
    srv = data["mcp_servers"]["mne"]
    assert isinstance(srv["args"], list)
    assert isinstance(srv["env"], dict)
    assert srv["enabled"] is True


def test_codex_preserves_other_and_is_idempotent(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('[mcp_servers.other]\ncommand = "x"\nargs = []\n', encoding="utf-8")
    cc.configure_codex(p)
    res2 = cc.configure_codex(p)  # run again
    assert res2["status"] == "updated"
    text = p.read_text(encoding="utf-8")
    # exactly one mne table, other preserved, still valid TOML
    assert text.count("[mcp_servers.mne]") == 1
    data = tomllib.loads(text)
    assert "other" in data["mcp_servers"] and "mne" in data["mcp_servers"]


def test_opencode_creates_and_preserves(tmp_path):
    p = tmp_path / "opencode.json"
    p.write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "mcp": {"other": {"type": "local", "command": ["y"]}},
            }
        ),
        encoding="utf-8",
    )
    res = cc.configure_opencode(p)
    assert res["status"] in ("added", "created")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["mcp"]["mne"]["type"] == "local"
    assert isinstance(data["mcp"]["mne"]["command"], list)
    assert data["mcp"]["mne"]["enabled"] is True
    assert "other" in data["mcp"]  # preserved


def test_install_skills_to_tmp(tmp_path):
    res = cc.install_skills(tmp_path)
    # source skills exist in this checkout
    assert res["error"] is None
    assert set(res["installed"]) >= {"mne-analyst", "mne-mcp-guard"}
    assert (tmp_path / "mne-analyst" / "SKILL.md").exists()


def test_configure_clients_orchestrator(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_CLAUDE_CONFIG", str(tmp_path / "claude.json"))
    monkeypatch.setenv("MNE_MCP_CODEX_CONFIG", str(tmp_path / "codex.toml"))
    monkeypatch.setenv("MNE_MCP_OPENCODE_CONFIG", str(tmp_path / "opencode.json"))
    out = cc.configure_clients(["claude", "codex", "opencode"], with_skills=False)
    clients = {r["client"] for r in out["clients"]}
    assert clients == {"claude", "codex", "opencode"}
    assert out["skills"] is None
    assert (tmp_path / "claude.json").exists()
    assert (tmp_path / "codex.toml").exists()
    assert (tmp_path / "opencode.json").exists()


def test_configure_clients_rejects_unknown():
    with pytest.raises(ValueError):
        cc.configure_clients(["notaclient"], with_skills=False)
