"""Regression tests for two bugs found 2026-06-05 during the first real-data (eegbci) run.

Bug 1 — NumPy 2.x alias removal blocked all data loading.
    NumPy >= 2.0 removed legacy aliases (``np.trapz`` -> ``np.trapezoid``,
    ``np.in1d`` -> ``np.isin``, ``np.row_stack`` -> ``np.vstack``, ...). A transitive
    dependency still calls the old names while reading an EDF, so *every* recording load
    raised ``AttributeError: module 'numpy' has no attribute 'trapz'/'in1d'``. Fixed by the
    ``mne_mcp._compat`` shim, applied at package import.

Bug 2 — ``picks`` comma-list not split.
    ``plot_psd`` / ``plot_epochs_image`` passed the ``picks`` string straight to MNE, so a
    comma-separated channel list (``"O1,Oz,O2"``) was treated as one bogus channel name and
    raised ``ValueError``. Fixed by ``operations._parse_picks``.
"""

import mne
import numpy as np
import pytest

from mne_mcp import operations as ops
from mne_mcp._compat import apply_numpy_compat
from mne_mcp.kernel import get_session

mne.set_log_level("ERROR")


# --- Bug 1: NumPy 2.x alias shim -------------------------------------------------


def test_numpy_aliases_present_after_import():
    """Importing the package must have restored the removed aliases."""
    import mne_mcp  # noqa: F401  (import triggers apply_numpy_compat)

    for name in ("trapz", "in1d", "row_stack"):
        assert hasattr(
            np, name
        ), f"np.{name} missing — compat shim not applied at import"


def test_apply_numpy_compat_restores_removed_aliases():
    """Even if the aliases are absent (NumPy 2.x), the shim restores working callables."""
    saved = {}
    for name in ("trapz", "in1d", "row_stack"):
        if hasattr(np, name):
            saved[name] = getattr(np, name)
            delattr(np, name)
    try:
        apply_numpy_compat()
        for name in ("trapz", "in1d", "row_stack"):
            assert hasattr(np, name)
        # the restored callables must actually work
        assert float(np.trapz([1.0, 1.0, 1.0], [0.0, 1.0, 2.0])) == 2.0
        assert list(np.in1d([1, 2, 3], [2, 3])) == [False, True, True]
    finally:
        for name, fn in saved.items():
            setattr(np, name, fn)


# --- Bug 2: picks comma-splitting ------------------------------------------------


def test_parse_picks_splits_comma_list():
    assert ops._parse_picks("O1,Oz,O2") == ["O1", "Oz", "O2"]
    assert ops._parse_picks(" O1 , Oz ") == ["O1", "Oz"]  # whitespace-tolerant
    assert ops._parse_picks("eeg") == "eeg"  # bare type passes through
    assert ops._parse_picks(None) is None


@pytest.fixture
def occ_session(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(tmp_path))
    s = get_session()
    s.reset()
    ch = ["O1", "Oz", "O2", "Pz", "Cz"]
    info = mne.create_info(ch, 200.0, ch_types="eeg")
    data = np.random.RandomState(2).randn(len(ch), 4000) * 1e-5
    s.set("raw", mne.io.RawArray(data, info))
    return s


def test_plot_psd_accepts_comma_picks(occ_session):
    """The exact call that failed on real data must now succeed."""
    res = ops.plot_psd("raw", fmin=1, fmax=40, picks="O1,Oz,O2")
    assert len(res["figures"]) == 1
