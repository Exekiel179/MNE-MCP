"""Fast operation-layer tests on synthetic EEG (no downloads, no ICA)."""

import mne
import numpy as np
import pytest

from mne_mcp import operations as ops
from mne_mcp.kernel import get_session

mne.set_log_level("ERROR")


@pytest.fixture
def fresh_session(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(tmp_path))
    s = get_session()
    s.reset()
    sfreq = 200.0
    ch_names = ["Fz", "Cz", "Pz", "Oz", "C3", "C4", "F3", "F4"]
    info = mne.create_info(ch_names, sfreq, ch_types="eeg")
    data = np.random.RandomState(1).randn(len(ch_names), int(sfreq * 20)) * 1e-5
    raw = mne.io.RawArray(data, info)
    s.set("raw", raw)
    return s


def test_set_montage_and_describe(fresh_session):
    ops.set_montage("raw", "standard_1020")
    out = ops.describe_object("raw")["markdown"]
    assert "Raw" in out


def test_filter_changes_info(fresh_session):
    res = ops.filter_data("raw", l_freq=1.0, h_freq=40.0)
    assert "filter" in res["code"]


def test_plot_psd_produces_figure(fresh_session):
    res = ops.plot_psd("raw", fmin=1, fmax=45)
    assert len(res["figures"]) == 1


def test_make_epochs_and_average(fresh_session):
    s = fresh_session
    events = np.array([[i * 300 + 100, 0, 1] for i in range(10)])
    s.set("events", events)
    ops.make_epochs("raw", "events", event_id="cond:1", tmin=-0.1, tmax=0.4)
    assert s.has("epochs")
    ops.average_evoked("epochs", condition="cond", evoked_name="evoked")
    assert s.has("evoked")


def test_unknown_object_raises_keyerror(fresh_session):
    with pytest.raises(KeyError):
        ops.describe_object("nonexistent")


def test_wrong_kind_rejected(fresh_session):
    # plot_raw requires a Raw; feed it an ndarray
    fresh_session.set("arr", np.zeros((3, 3)))
    with pytest.raises(ValueError):
        ops.plot_raw("arr")


def test_list_files_prunes_noise_dirs(tmp_path):
    (tmp_path / "good_raw.fif").write_bytes(b"x")
    venv = tmp_path / ".venv" / "lib" / "site-packages"
    venv.mkdir(parents=True)
    (venv / "bundled_raw.fif").write_bytes(b"y")
    out = ops.list_files(str(tmp_path))["markdown"]
    assert "good_raw.fif" in out
    assert "bundled_raw.fif" not in out  # .venv is pruned


def test_make_epochs_baseline_none(fresh_session):
    s = fresh_session
    s.set("events", np.array([[i * 300 + 100, 0, 1] for i in range(8)]))
    ops.make_epochs(
        "raw", "events", event_id="c:1", tmin=-0.1, tmax=0.3, baseline="none"
    )
    assert s.has("epochs")


def test_advanced_decode_connectivity_cov(fresh_session):
    s = fresh_session
    s.set("events", np.array([[i * 250 + 100, 0, (i % 2) + 1] for i in range(16)]))
    ops.make_epochs(
        "raw", "events", event_id="a:1,b:2", tmin=-0.1, tmax=0.4, epochs_name="epochs"
    )

    r = ops.decode_time("epochs", "a", "b", cv=3)
    assert len(r["figures"]) == 1 and s.has("decoding")

    r = ops.compute_noise_cov("epochs")
    assert s.has("noise_cov")

    # connectivity needs the optional mne-connectivity package (the [full] extra)
    pytest.importorskip("mne_connectivity")
    r = ops.connectivity("epochs", method="coh", fmin=8, fmax=20)
    assert len(r["figures"]) == 1 and s.has("con")


def test_decode_requires_two_classes(fresh_session):
    s = fresh_session
    s.set("events", np.array([[i * 300 + 100, 0, 1] for i in range(8)]))
    ops.make_epochs("raw", "events", event_id="c:1", tmin=-0.1, tmax=0.3)
    with pytest.raises(ValueError):
        ops.decode_time("epochs")  # only one class present
