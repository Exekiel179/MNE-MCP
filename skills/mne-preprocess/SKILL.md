---
name: mne-preprocess
description: >
  Preprocessing & data-quality cleanup of EEG/MEG/iEEG via MNE — filtering (high-pass/low-pass/
  bandpass, FIR vs IIR, transition bandwidth), notch/line-noise removal, resampling, re-referencing
  (average/REST/linked-mastoid/bipolar), montage setting, bad-channel detection + spline
  interpolation, cropping and segment rejection — run SKEPTICALLY: grill the design and the
  downstream analysis before touching the data, execute with best-practice defaults, then submit the
  pipeline to methodology critique. Use for cleaning raw recordings, choosing a high-pass for ERP vs
  ICA, removing 50/60 Hz line noise, downsampling, picking a reference, and fixing bad channels.
  Triggers: preprocess, preprocessing, 预处理, filter, 滤波, high-pass, low-pass, bandpass, 带通,
  notch, 陷波, line noise, 工频, 50Hz, 60Hz, resample, 重采样, downsample, 降采样, reference, 重参考,
  average reference, 平均参考, REST, linked mastoid, 乳突, bipolar, montage, 电极位置, bad channels,
  坏导, 坏道, interpolate, 插值, crop, 裁剪, data quality, 数据质量.
---

# MNE Preprocessing (grill → analyze → critic)

Preprocessing & data-quality cleanup of neurophysiology data via the MNE MCP server. This skill is
**skeptical by design**: nearly every preprocessing mistake (a too-aggressive high-pass that eats
your slow ERP, a reference that fabricates connectivity, filtering before epoching, differential
bad-channel handling between groups) runs *without any error* and silently biases everything
downstream — so the discipline is to **grill the downstream analysis before cleaning, and critique
the pipeline before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety; `mne-methodology-critic` for
> Phase 3. Loaded objects persist in one MNE session, and preprocessing edits are **in place**.

---

## PHASE 1 — GRILL (before processing anything)

Do **not** filter, reference, or resample until these are answered. If the user can't answer one,
propose a sensible default **and explicitly flag the open risk** — never silently choose.

**The question that decides every parameter**
- **What is the DOWNSTREAM analysis?** Filter choices follow from it, and there is no neutral
  default: **0.1 Hz** high-pass for **ERP** (slow components survive), **~1 Hz** high-pass for **ICA**
  (drift hurts decomposition), **broadband / no/low high-pass** for **TFR / low-frequency power**.
  Set the pipeline to the analysis, not the other way round.

**Filtering**
- High-pass edge — and ⚠️ **will the filter edge distort the effect of interest?** A 0.5–1 Hz HP can
  attenuate/shift slow ERP components (CNV, P300, readiness potential). Justify the edge.
- Low-pass edge (anti-alias / smoothing) and **transition bandwidth**; FIR (linear-phase, default)
  vs IIR (causal, ringing tradeoffs)?
- **Line frequency: 50 or 60 Hz?** (region-dependent) — notch it (+ harmonics) or rely on a low-pass
  below it?

**Resampling**
- Needed at all? If so, **before or after epoching?** Downsample **after** epoching where possible —
  resampling continuous data jitters event sample positions. New sfreq must stay **> 2× the low-pass**
  (anti-aliasing) — MNE low-passes on resample, but verify.

**Reference & montage**
- Montage system (`standard_1020`, `biosemi64`, `GSN-HydroCel-128`, …)? Needed for interpolation,
  topomaps, and source work.
- Reference rationale: average / REST / linked-mastoid / bipolar — and **does it suit the later
  analysis?** Average/common references inflate apparent **connectivity** and matter for **source**
  modeling; pin the reference to those needs now, not after.

**Bad channels & quality**
- Bad-channel criteria: **objective** (variance/flatness/correlation thresholds, e.g. PyPREP/RANSAC)
  or **eyeballed**? Will the **two groups be treated differently** (differential handling fabricates
  group effects)?
- Will interpolation be used, and how many channels — interpolation **reduces data rank**, which
  caps later ICA / source `n_components`.
- Segments to crop or annotate-and-reject (and the same objective vs eyeballed concern)?

---

## PHASE 2 — ANALYZE

1. **Capability + look first.** `mne_check_status`; then **look before cleaning**: `mne_plot_psd`
   (read the PNG — find the **line-noise** spike at 50/60 Hz + harmonics, drift, dead/noisy channels)
   and `mne_plot_raw` (drifts, flat lines, jumps). `mne_plot_sensors` to confirm the montage.

2. **Montage** (if positions aren't already set) — needed for interpolation/topomaps:
   `mne_set_montage(name="raw", montage="standard_1020")`.

3. **Filter + notch**, with the edge chosen for the *downstream* analysis:

   ```python
   # ERP pipeline: gentle high-pass preserves slow components; low-pass + line notch
   raw.filter(l_freq=0.1, h_freq=40.0, fir_design="firwin")   # FIR, linear phase
   raw.notch_filter(freqs=[50, 100, 150])                       # 50 Hz region + harmonics
   ```
   (Structured form: `mne_filter(name="raw", l_freq=0.1, h_freq=40, notch=50)`. For **ICA** use
   `l_freq=1.0`; for **TFR/low-freq power** keep the high-pass minimal/off.)

4. **Reference**, chosen for the downstream need:

   ```python
   raw.set_eeg_reference("average", projection=False)          # whole-head, common for source/ERP
   # linked mastoid:  raw.set_eeg_reference(["TP9", "TP10"])
   # REST (infinity): raw.set_eeg_reference("REST")            # needs a forward / sphere model
   ```
   (Structured form: `mne_set_reference(name="raw", ref_channels="average")` /
   `"REST"` / `"TP9,TP10"`.)

5. **Bad channels + interpolate** — prefer an objective criterion, then spline-interpolate:

   ```python
   # objective flag: flat or extreme-variance channels (illustrative thresholds)
   data = raw.get_data(picks="eeg"); v = data.var(axis=1)
   names = [raw.ch_names[i] for i in range(len(v))]
   flat = [names[i] for i in np.where(v < 1e-14)[0]]
   noisy = [names[i] for i in np.where(v > np.median(v) + 5 * np.std(v))[0]]
   raw.info["bads"] = sorted(set(flat + noisy))
   raw.interpolate_bads(reset_bads=True)                        # spline; needs montage
   ```
   (Structured form: `mne_mark_bad_channels(name="raw", bads="Fp1,T7")` then
   `mne_interpolate_bads(name="raw")`. **Record how many channels were interpolated — it lowers
   data rank** for any later ICA/source step.)

6. **Resample** — *after* epoching when you can; if on continuous data, keep events safe:
   `mne_resample(name="raw", sfreq=250)` (verify new sfreq > 2× the low-pass).

7. **Crop / annotate** bad segments: `mne_crop(name="raw", tmin=0, tmax=300)`, or mark
   `BAD_*` annotations so epoching drops them.

8. **Re-inspect.** `mne_plot_psd` again — confirm the line-noise spike is gone, the high-pass
   removed drift, and no channel still looks dead/noisy. Then **archive** the equivalent code +
   figures (the `mne-analyst` archiving convention).

Best-practice reminders: filter **before** epoching to avoid edge artifacts at every epoch boundary;
pick the high-pass for the analysis; report **per-group** bad-channel/rejection counts; track how
many channels were interpolated (rank).

---

## PHASE 3 — CRITIC (before believing the result)

Hand the pipeline (filter band, reference, bad channels, resampling, order of operations) to
**`mne-methodology-critic`** (invoke the skill, or dispatch it as a subagent with
`references/methodology-checklist.md`). For preprocessing it will specifically check:

- **high-pass distortion** of slow ERP components (≳0.1–0.3 Hz can attenuate/shift CNV/P300);
- **filter applied before vs after epoching** (post-epoch filtering injects **edge artifacts** at
  every boundary);
- **reference choice biasing** later **connectivity / source** (average/common references inflate
  apparent connectivity and shift source estimates);
- **differential bad-channel handling** between groups (unequal interpolation fabricates group
  effects);
- **interpolation reducing data rank** (caps later ICA / source `n_components`);
- **resampling-induced event jitter** (downsampling continuous data before epoching shifts event
  timing).

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating that the data
are "clean."

See `references/preprocess-methods.md` for deeper recipes (FIR vs IIR & transition bandwidth, notch
strategies, reference math, objective bad-channel detection, rank bookkeeping, and pipeline order).
