# -*- coding: utf-8 -*-
"""Figure 4: REAL-DATA Berger effect (PhysioNet eegbci S001), occipital alpha
eyes-open vs eyes-closed. Mirrors tests/smoke_eegbci.py so the figure backs the
exact validated pipeline. Skips cleanly (no file written) if physionet is unreachable.
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

for fam in ["Microsoft YaHei", "SimHei", "Source Han Sans SC", "DejaVu Sans"]:
    try:
        matplotlib.rcParams["font.sans-serif"] = [fam]
        break
    except Exception:
        continue
matplotlib.rcParams["axes.unicode_minus"] = False

import mne
from mne.datasets import eegbci

mne.set_log_level("ERROR")
OCC = ["O1", "Oz", "O2"]

try:
    paths = eegbci.load_data(subjects=1, runs=[1, 2], update_path=True)
except Exception as e:  # noqa: BLE001
    print(f"SKIP: could not reach physionet ({type(e).__name__}); figure 4 not generated.")
    sys.exit(0)


def occ_psd(edf_path):
    raw = mne.io.read_raw_edf(edf_path, preload=True)
    eegbci.standardize(raw)
    raw.set_montage("standard_1005")
    raw.filter(1.0, 40.0, verbose="ERROR")
    raw.notch_filter(60.0, verbose="ERROR")
    raw.set_eeg_reference("average", verbose="ERROR")
    ep = mne.make_fixed_length_epochs(raw, duration=2.0, overlap=0.0, preload=True)
    spec = ep.compute_psd(method="welch", fmin=1, fmax=40,
                          n_fft=int(raw.info["sfreq"] * 2), picks=OCC)
    psd, freqs = spec.get_data(return_freqs=True)  # (n_epochs, n_ch, n_freq)
    psd_uv2 = psd * 1e12  # V^2/Hz -> uV^2/Hz
    mean_psd = psd_uv2.mean(axis=(0, 1))  # over epochs & occipital channels
    band = (freqs >= 8) & (freqs <= 13)
    # np.trapezoid is the NumPy 2.x name (np.trapz was removed; see mne_mcp._compat)
    per_epoch_alpha = np.trapezoid(psd_uv2.mean(1)[:, band], freqs[band], axis=1)
    return freqs, mean_psd, per_epoch_alpha


freqs, psd_eo, alpha_eo = occ_psd(paths[0])
_, psd_ec, alpha_ec = occ_psd(paths[1])
ratio = float(np.median(alpha_ec) / np.median(alpha_eo))

fig, (axA, axB) = plt.subplots(1, 2, figsize=(9.4, 3.9), dpi=200,
                               gridspec_kw={"width_ratios": [1.7, 1]})

# Panel A: occipital PSD, EO vs EC, alpha band shaded
axA.axvspan(8, 13, color="#ffe39e", alpha=0.55, label="α 频段 8–13 Hz")
axA.plot(freqs, psd_eo, color="#2b6cb0", lw=2.0, label="睁眼 (EO)")
axA.plot(freqs, psd_ec, color="#b03a3a", lw=2.0, label="闭眼 (EC)")
axA.set_yscale("log")
axA.set_xlim(1, 40)
axA.set_xlabel("频率 Frequency (Hz)")
axA.set_ylabel("功率谱密度 PSD (µV²/Hz, log)")
axA.set_title("(a) 枕区 O1/Oz/O2 平均功率谱", fontsize=11)
axA.legend(fontsize=8.5, loc="upper right", framealpha=0.9)
axA.grid(True, which="both", ls=":", lw=0.5, alpha=0.5)

# Panel B: per-epoch occipital alpha power, EO vs EC (log), with ratio
bp = axB.boxplot([alpha_eo, alpha_ec], tick_labels=["睁眼\nEO", "闭眼\nEC"],
                 widths=0.55, patch_artist=True, showfliers=False)
for patch, c in zip(bp["boxes"], ["#2b6cb0", "#b03a3a"]):
    patch.set_facecolor(c); patch.set_alpha(0.35); patch.set_edgecolor(c)
for med in bp["medians"]:
    med.set_color("#222"); med.set_linewidth(1.6)
axB.set_yscale("log")
axB.set_ylabel("枕区 α 绝对功率 (µV²)")
axB.set_title(f"(b) 闭眼/睁眼 中位数 ≈ {ratio:.0f}×", fontsize=11)
axB.grid(True, axis="y", ls=":", lw=0.5, alpha=0.5)

fig.tight_layout()
out = os.path.join(os.path.dirname(__file__), "media", "figure4_berger.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, bbox_inches="tight", facecolor="white")
print(f"WROTE {out}  (EC/EO occipital alpha median ratio = {ratio:.1f}x)")
