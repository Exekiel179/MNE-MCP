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
    """The shim restores an alias whenever its modern target exists in this NumPy.

    (``np.trapezoid`` only exists on NumPy >= 2.0, so on the 1.x line ``trapz`` cannot be
    re-derived from it — we therefore only exercise aliases whose target is present.)
    """
    targets = {"in1d": "isin", "row_stack": "vstack"}  # present on NumPy 1.x and 2.x
    if hasattr(np, "trapezoid"):
        targets["trapz"] = "trapezoid"
    saved = {}
    for name in targets:
        if hasattr(np, name):
            saved[name] = getattr(np, name)
            delattr(np, name)
    try:
        apply_numpy_compat()
        for name in targets:
            assert hasattr(np, name), f"shim did not restore np.{name}"
        # a restored callable must actually work
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


# --- Packaging: skills/agents bundled in the wheel are found first (v0.2.2) ------


def test_skills_agents_source_prefers_bundled(tmp_path, monkeypatch):
    """get_*_source_dir must prefer the in-wheel `_bundled/` copy over the repo.

    A `pip`/`pipx`/`uvx` install has no source checkout, so `mne-mcp setup` can only
    install skills if they ship inside the wheel under `mne_mcp/_bundled/`.
    """
    from mne_mcp import claude_config

    fake_pkg = tmp_path / "mne_mcp"
    (fake_pkg / "_bundled" / "skills").mkdir(parents=True)
    (fake_pkg / "_bundled" / "agents").mkdir(parents=True)
    monkeypatch.setattr(claude_config, "__file__", str(fake_pkg / "claude_config.py"))

    skills = claude_config.get_skills_source_dir()
    agents = claude_config.get_agents_source_dir()
    assert skills is not None and skills.parts[-2:] == ("_bundled", "skills")
    assert agents is not None and agents.parts[-2:] == ("_bundled", "agents")
