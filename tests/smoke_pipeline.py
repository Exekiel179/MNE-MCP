"""End-to-end smoke test of the MNE-MCP operation layer on synthetic EEG.

Run with the project venv:
    .venv/Scripts/python.exe tests/smoke_pipeline.py
Exercises the real operations + persistent kernel + figure capture, no downloads.
"""

import os
import sys
import tempfile

import numpy as np

RESULTS = os.path.join(tempfile.gettempdir(), "mne-mcp-smoke")
os.environ["MNE_MCP_RESULTS_DIR"] = RESULTS

import mne  # noqa: E402

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


# 1. Build synthetic raw and save to a *_raw.fif so load_raw exercises real IO.
sfreq = 200.0
ch_names = ["Fz", "Cz", "Pz", "Oz", "C3", "C4", "F3", "F4"]
info = mne.create_info(ch_names, sfreq, ch_types="eeg")
rng = np.random.RandomState(0)
data = rng.randn(len(ch_names), int(sfreq * 60)) * 1e-5
raw0 = mne.io.RawArray(data, info)
tmp_fif = os.path.join(tempfile.gettempdir(), "smoke_raw.fif")
raw0.save(tmp_fif, overwrite=True)

s = get_session()
s.reset()

r = ops.load_raw(tmp_fif, name="raw")
check("load_raw", s.has("raw") and "Raw" in r["markdown"])

r = ops.set_montage("raw", "standard_1020")
check("set_montage", "standard_1020" in r["code"])

r = ops.filter_data("raw", 1.0, 40.0, notch=50.0)
check("filter (bandpass+notch)", "filter" in r["code"])

r = ops.set_reference("raw", "average")
check("set_reference average", "set_eeg_reference" in r["code"])

r = ops.plot_psd("raw", fmin=1, fmax=45)
check("plot_psd -> figure", len(r["figures"]) == 1 and os.path.exists(r["figures"][0]))

r = ops.plot_sensors("raw")
check("plot_sensors -> figure", len(r["figures"]) == 1)

# ICA
r = ops.fit_ica("raw", n_components=5, ica_name="ica")
check("fit_ica", s.has("ica") and "ICA" in r["markdown"])

r = ops.plot_ica_components("ica")
check("plot_ica_components -> figure", len(r["figures"]) >= 1)

r = ops.apply_ica("ica", "raw", exclude="0")
check("apply_ica exclude=0", "exclude = [0]" in r["code"])

# Events + epochs (inject synthetic events via the kernel)
res = s.run_code(
    "events = np.array([[int(i*400+100), 0, 1] for i in range(25)])\nevents.shape"
)
check(
    "run_code creates events",
    s.has("events") and res["error"] is None,
    extra=str(res.get("error")),
)

r = ops.make_epochs("raw", "events", event_id="cond:1", tmin=-0.2, tmax=0.5)
check("make_epochs", s.has("epochs") and "Epochs" in r["markdown"])

r = ops.plot_epochs_image("epochs", picks="Cz")
check("plot_epochs_image -> figure", len(r["figures"]) >= 1)

r = ops.average_evoked("epochs", condition="cond", evoked_name="evoked")
check("average_evoked", s.has("evoked"))

r = ops.plot_evoked("evoked", style="joint")
check("plot_evoked joint -> figure", len(r["figures"]) >= 1)

r = ops.plot_topomap("evoked", times="0.1,0.2,0.3")
check("plot_topomap -> figure", len(r["figures"]) >= 1)

# TFR needs longer epochs than a typical ERP window — build a wider one.
ops.make_epochs(
    "raw", "events", event_id="cond:1", tmin=-0.5, tmax=1.5, epochs_name="epochs_tfr"
)
r = ops.tfr_morlet("epochs_tfr", fmin=8, fmax=40, n_freqs=8, tfr_name="power")
check("tfr_morlet -> figure", len(r["figures"]) >= 1 and s.has("power"))

# run_code: stdout + result + figure capture together
res = s.run_code(
    "print('hello from kernel')\nx = 2 + 2\nplt.figure(); plt.plot([1,2,3]); x"
)
check("run_code stdout", "hello from kernel" in res["stdout"])
check("run_code result value", res["result_repr"] == "4")
check("run_code figure capture", len(res["figures"]) == 1)

# session summary + describe
summ = s.summary()
check(
    "session summary lists raw/epochs/evoked",
    all(n in summ for n in ["raw", "epochs", "evoked", "ica"]),
)

# save round-trip
out = os.path.join(tempfile.gettempdir(), "smoke_out-ave.fif")
r = ops.save_object("evoked", out)
check("save evoked", os.path.exists(out))

print(f"\nRESULT: {ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
