"""Broader operation-layer coverage on synthetic, montage-equipped EEG (no downloads)."""

import mne
import numpy as np
import pytest

from mne_mcp import operations as ops
from mne_mcp.kernel import get_session

mne.set_log_level("ERROR")

CH = [
    "Fp1",
    "Fp2",
    "F3",
    "F4",
    "C3",
    "C4",
    "P3",
    "P4",
    "O1",
    "O2",
    "F7",
    "F8",
    "T7",
    "T8",
    "Fz",
    "Cz",
    "Pz",
    "Oz",
]


@pytest.fixture
def raw_session(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(tmp_path))
    s = get_session()
    s.reset()
    info = mne.create_info(CH, 200.0, ch_types="eeg")
    data = np.random.RandomState(3).randn(len(CH), int(200 * 30)) * 1e-5
    s.set("raw", mne.io.RawArray(data, info))
    ops.set_montage("raw", "standard_1020")
    return s, tmp_path


def _evoked(s):
    s.set("events", np.array([[i * 200 + 100, 0, (i % 2) + 1] for i in range(40)]))
    ops.make_epochs("raw", "events", event_id="a:1,b:2", tmin=-0.2, tmax=0.5)
    ops.average_evoked("epochs", condition="a", evoked_name="evoked")


def test_resample_and_crop(raw_session):
    s, _ = raw_session
    ops.resample("raw", 100.0)
    assert s.get("raw").info["sfreq"] == 100.0
    ops.crop("raw", 0.0, 5.0)
    assert s.get("raw").times[-1] <= 5.01


def test_get_info_and_describe(raw_session):
    assert "Cz" in ops.get_info("raw")["markdown"]
    assert "Raw" in ops.describe_object("raw")["markdown"]


def test_reference_and_bad_channels(raw_session):
    s, _ = raw_session
    ops.set_reference("raw", "F3,F4")  # linked pair
    r = ops.mark_bad_channels("raw", "T7")
    assert "T7" in s.get("raw").info["bads"]
    ops.interpolate_bads("raw")  # needs montage (set in fixture)
    assert "T7" not in s.get("raw").info["bads"]


def test_raw_and_sensor_plots(raw_session):
    assert len(ops.plot_raw("raw")["figures"]) >= 1
    assert len(ops.plot_sensors("raw", kind="topomap")["figures"]) >= 1


def test_evoked_plots_and_topomap(raw_session):
    s, _ = raw_session
    _evoked(s)
    assert len(ops.plot_evoked("evoked", style="joint")["figures"]) >= 1
    assert len(ops.plot_evoked("evoked", style="butterfly")["figures"]) >= 1
    assert len(ops.plot_topomap("evoked", times="0.1,0.2")["figures"]) >= 1


def test_tfr_morlet(raw_session):
    s, _ = raw_session
    s.set("events", np.array([[i * 250 + 200, 0, 1] for i in range(20)]))
    ops.make_epochs(
        "raw", "events", event_id="c:1", tmin=-0.5, tmax=1.5, epochs_name="epo_tfr"
    )
    r = ops.tfr_morlet("epo_tfr", fmin=6, fmax=30, n_freqs=8, tfr_name="power")
    assert len(r["figures"]) >= 1 and s.has("power")


def test_save_objects(raw_session, tmp_path):
    s, _ = raw_session
    _evoked(s)
    for name, fname in [
        ("raw", "x_raw.fif"),
        ("epochs", "x-epo.fif"),
        ("evoked", "x-ave.fif"),
    ]:
        out = tmp_path / fname
        ops.save_object(name, str(out))
        assert out.exists()


def test_ica_roundtrip(raw_session):
    s, _ = raw_session
    pytest.importorskip("sklearn")
    ops.fit_ica("raw", n_components=5)
    assert s.has("ica")
    assert len(ops.plot_ica_components("ica")["figures"]) >= 1
    assert len(ops.plot_ica_sources("ica", "raw")["figures"]) >= 1
    ops.apply_ica("ica", "raw", exclude="0")


def test_events_from_annotations(raw_session):
    s, _ = raw_session
    raw = s.get("raw")
    raw.set_annotations(
        mne.Annotations(
            onset=[1.0, 3.0, 5.0],
            duration=[0.0, 0.0, 0.0],
            description=["stim", "stim", "stim"],
        )
    )
    ops.events_from_annotations("raw", events_name="ann_events")
    assert s.has("ann_events")
