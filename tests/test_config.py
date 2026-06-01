"""Tests for configuration & capability detection."""

import importlib

from mne_mcp import config


def test_detect_capabilities_reports_mne():
    caps = config.detect_capabilities()
    # MNE is a hard dependency, so it must be detected in the test env.
    assert caps["mne"] is True
    assert caps["mne_version"]
    assert caps["numpy_version"]
    # sklearn is an optional extra used for ICA.
    assert "sklearn" in caps


def test_timeout_env(monkeypatch):
    monkeypatch.setenv("MNE_MCP_TIMEOUT", "42")
    assert config.get_timeout() == 42
    monkeypatch.setenv("MNE_MCP_TIMEOUT", "not-a-number")
    assert config.get_timeout() == 300  # falls back to default
    monkeypatch.setenv("MNE_MCP_TIMEOUT", "-5")
    assert config.get_timeout() == 300  # rejects non-positive


def test_results_dir_created(tmp_path, monkeypatch):
    target = tmp_path / "results"
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(target))
    out = config.get_results_dir()
    assert out == target
    assert out.exists()


def test_runtime_config_keys():
    cfg = config.get_runtime_config()
    assert {"timeout", "temp_dir", "results_dir", "data_dir"} <= set(cfg)
