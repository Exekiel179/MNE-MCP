"""End-to-end REAL-DATA smoke test on the PhysioNet eegbci dataset.

Downloads subject S001 eyes-open (run 1) and eyes-closed (run 2) resting baselines and
runs a real spectral pipeline through the MNE-MCP operation layer, asserting the classic
**Berger effect** (occipital alpha power higher with eyes closed). This complements the
synthetic ``smoke_pipeline.py`` by exercising the real EDF-reading path — which is exactly
where the NumPy-2.x alias bug (see ``test_regressions.py``) surfaced.

Run with the project environment:
    python tests/smoke_eegbci.py
Network access to physionet.org is required (the dataset is cached after first download).
"""

import os
import sys
import tempfile

import numpy as np

os.environ.setdefault(
    "MNE_MCP_RESULTS_DIR", os.path.join(tempfile.gettempdir(), "mne-mcp-eegbci")
)

import mne  # noqa: E402
from mne.datasets import eegbci  # noqa: E402

from mne_mcp import operations as ops  # noqa: E402
from mne_mcp.kernel import get_session  # noqa: E402

mne.set_log_level("ERROR")
ok = 0
fail = 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label} {extra}")
    else:
        fail += 1
        print(f"  FAIL  {label} {extra}")


# 1. Fetch eyes-open (run 1) + eyes-closed (run 2) baselines for S001.
#    A network outage on the CI runner must not be a hard failure: skip cleanly so this
#    test guards the *pipeline* (when data is reachable), not physionet's uptime.
try:
    paths = eegbci.load_data(subjects=1, runs=[1, 2], update_path=True)
except Exception as e:  # noqa: BLE001 - catch any download/network error
    msg = f"{type(e).__name__}: {e}".lower()
    net = (
        "timed out",
        "timeout",
        "connection",
        "max retries",
        "temporarily",
        "resolve",
        "network",
        "ssl",
        "url",
        "http",
    )
    if any(k in msg for k in net):
        print(
            f"SKIP: could not reach physionet.org ({type(e).__name__}); "
            "skipping real-data smoke (network unavailable)."
        )
        sys.exit(0)
    raise
check(
    "download eegbci S001 runs 1,2",
    len(paths) == 2 and all(os.path.exists(p) for p in paths),
)

s = get_session()
s.reset()
occ = ["O1", "Oz", "O2"]


def alpha_power(raw_name, edf_path):
    # load through the operation layer -> exercises the real EDF reader (Bug-1 path)
    r = ops.load_raw(edf_path, name=raw_name)
    check(f"load_raw {raw_name}", s.has(raw_name) and "Raw" in r["markdown"])
    raw = s.get(raw_name)
    eegbci.standardize(raw)
    raw.set_montage("standard_1005")
    ops.filter_data(raw_name, 1.0, 40.0, notch=60.0)
    ops.set_reference(raw_name, "average")
    ep = mne.make_fixed_length_epochs(raw, duration=2.0, overlap=0.0, preload=True)
    check(f"{raw_name} has epochs", len(ep) > 0)
    spec = ep.compute_psd(
        method="welch", fmin=1, fmax=40, n_fft=int(raw.info["sfreq"] * 2), picks=occ
    )
    psd, freqs = spec.get_data(return_freqs=True)
    band = (freqs >= 8) & (freqs <= 13)
    # absolute occipital alpha power per epoch (uV^2); np.trapz exercises the shim too
    return np.trapz(psd.mean(1)[:, band], freqs[band], axis=1) * 1e12


a_eo = alpha_power("raw_eo", paths[0])
a_ec = alpha_power("raw_ec", paths[1])

check("alpha power finite", np.all(np.isfinite(a_eo)) and np.all(np.isfinite(a_ec)))
ratio = float(np.median(a_ec) / np.median(a_eo))
# Berger effect: occipital alpha is markedly higher eyes-closed. Real S001 ratio ~33x;
# assert a generous margin so the test is a robust regression, not brittle.
check(
    "Berger effect (EC occipital alpha > EO)",
    ratio > 1.5,
    extra=f"EC/EO median alpha ratio = {ratio:.1f}x",
)

print(f"\nRESULT: {ok} passed, {fail} failed  (EC/EO occipital alpha = {ratio:.1f}x)")
sys.exit(1 if fail else 0)
