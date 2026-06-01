"""Tests for the configuration wizard and persisted defaults."""

import pytest

from mne_mcp import config, wizard


def test_coerce_types():
    assert wizard.coerce("line_freq", "60") == 60
    assert wizard.coerce("filter_l_freq", "1.5") == 1.5
    assert wizard.coerce("reject_eeg_uv", "none") is None
    assert wizard.coerce("ica_n_components", "0.99") == 0.99
    assert wizard.coerce("ica_n_components", "15") == 15
    assert wizard.coerce("data_dir", "") is None
    assert wizard.coerce("default_montage", "biosemi64") == "biosemi64"


def test_validate_choices():
    with pytest.raises(ValueError):
        wizard.validate("line_freq", 55)
    with pytest.raises(ValueError):
        wizard.validate("ica_method", "badmethod")
    wizard.validate("line_freq", 60)  # valid, no raise
    wizard.validate("ica_method", "picard")  # valid


def test_save_load_roundtrip(tmp_path, monkeypatch):
    cfgfile = tmp_path / "config.json"
    monkeypatch.setenv("MNE_MCP_CONFIG", str(cfgfile))
    config.save_config({"line_freq": 60, "default_montage": "biosemi64"})
    loaded = config.load_config()
    assert loaded["line_freq"] == 60
    assert loaded["default_montage"] == "biosemi64"
    assert config.get_line_freq() == 60
    assert config.get_default_montage() == "biosemi64"
    # untouched keys keep built-in defaults
    assert loaded["ica_method"] == "fastica"


def test_reset(tmp_path, monkeypatch):
    cfgfile = tmp_path / "config.json"
    monkeypatch.setenv("MNE_MCP_CONFIG", str(cfgfile))
    config.save_config({"line_freq": 60})
    assert cfgfile.exists()
    config.reset_config()
    assert not cfgfile.exists()
    assert config.load_config()["line_freq"] == 50


def test_reject_uv_to_volts(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_CONFIG", str(tmp_path / "c.json"))
    assert config.get_reject_eeg() is None
    config.save_config({"reject_eeg_uv": 100})
    assert abs(config.get_reject_eeg() - 100e-6) < 1e-12


def test_timeout_config_when_no_env(tmp_path, monkeypatch):
    monkeypatch.delenv("MNE_MCP_TIMEOUT", raising=False)
    monkeypatch.setenv("MNE_MCP_CONFIG", str(tmp_path / "c.json"))
    config.save_config({"timeout": 600})
    assert config.get_timeout() == 600


def test_set_values_rejects_unknown_key(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_CONFIG", str(tmp_path / "c.json"))
    with pytest.raises(ValueError):
        wizard.set_values(["bogus_key=1"])


def test_set_values_applies(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_CONFIG", str(tmp_path / "c.json"))
    wizard.set_values(["line_freq=60", "ica_method=picard"])
    cfg = config.load_config()
    assert cfg["line_freq"] == 60 and cfg["ica_method"] == "picard"
