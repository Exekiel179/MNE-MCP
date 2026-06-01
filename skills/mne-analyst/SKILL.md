---
name: mne-analyst
description: >
  Analyze human neurophysiology data (EEG, MEG, sEEG, ECoG, fNIRS) with MNE-Python through the
  MNE MCP server: load recordings, preprocess (filter, notch, re-reference, montage, bad-channel
  interpolation), run ICA artifact removal, epoch around events, average ERP/ERF, compute
  time-frequency power, plot and interpret every step, and reach the rest of MNE via run_code.
  Use when the user asks to analyze or preprocess EEG/MEG/iEEG/fNIRS data, work with .fif/.edf/.bdf/
  .set/.vhdr/.cnt/.egi/.snirf files, do filtering, ICA, epoching, ERP/evoked, PSD, topomaps,
  time-frequency/Morlet, source localization, connectivity, decoding, or BIDS. Triggered by keywords
  like MNE, EEG, MEG, ERP, ICA, 脑电, 脑磁, 预处理, 滤波, 分段, 叠加平均, 时频, 源定位, epoch, evoked,
  topomap, raw.fif, montage, 伪迹去除.
---

# MNE Analyst

Drive MNE-Python neurophysiology analysis conversationally and reliably. The MNE MCP server keeps a
**persistent session**: once you load a recording it stays in memory across tool calls, so build the
pipeline step by step rather than re-loading.

## Workflow

1. **Check capabilities** — Call `mne_check_status` first. Confirm MNE-Python is present (and
   `scikit-learn` if ICA is needed).
2. **Load & inspect** — `mne_load_raw` the file, then `mne_describe` / `mne_get_info` to learn
   channel names, types, sampling rate, montage, and existing bad channels **before** processing.
   Never guess channel names or data shape.
3. **Look before deciding** — Plot the PSD (`mne_plot_psd`) and/or raw traces (`mne_plot_raw`) and
   **read the returned PNG** to choose filter cutoffs, spot line noise, and find bad channels.
4. **Preprocess in the standard order** (see [references/mne-pipelines.md](references/mne-pipelines.md)).
5. **Run each step, then interpret** — After every plotting tool returns `> Figure: <path>`, **read
   that PNG** and explain what it shows in plain language.
6. **Archive results** — After meaningful analysis steps, archive figures + the equivalent MNE code
   to `mne_result/`. See [Output Archiving](#output-archiving).
7. **Reach beyond the structured tools with `mne_run_code`** — Source localization, connectivity,
   decoding, statistics, BIDS, custom plots, and unusual file formats all run in the same live
   session via `mne_run_code` (pre-bound: `mne`, `np`, `pd`, `plt`, and your loaded objects).

## Reliability Rules

- Never guess channel names, montage, or event codes — inspect first with `mne_get_info` /
  `mne_session_info`.
- **Set a montage before** topographic plots (`plot_topomap`, ICA components) or `interpolate_bads` —
  these need channel positions.
- **ICA wants high-pass-filtered data** (~1 Hz). If you will ICA-clean ERP data, fit ICA on a 1 Hz
  high-passed copy, then apply to the 0.1 Hz version.
- **Units are SI**: EEG/MEG signals are in **volts / tesla**. Rejection thresholds are tiny numbers
  (100 µV = `100e-6`). Don't pass microvolt integers.
- Filter for the goal: ERP analysis ≈ 0.1–40 Hz; ICA training ≈ 1 Hz high-pass; remove line noise
  with `notch` at 50 Hz (CN/EU) or 60 Hz (US).
- TFR/Morlet needs epochs long enough for the lowest frequency's wavelet — use a wider epoch window
  for time-frequency than for a plain ERP (see failure-patterns).
- Read MNE warnings, not just success — annotations, dropped epochs, and rank deficiency matter.
- Several tools (montage, filter band, ICA method/components, epoch window, rejection) fall back to
  **user-configured defaults** when you omit a parameter. Call `mne_get_config` to see them; the user
  changes them with `mne-mcp configure`. Respect their configured line frequency (50 vs 60 Hz).

## Standard EEG Pipeline (typical order)

```
mne_load_raw            → mne_set_montage      → mne_plot_psd (inspect)
→ mne_filter (1–40 Hz, notch 50) → mne_mark_bad_channels → mne_interpolate_bads
→ mne_set_reference average
→ mne_fit_ica (on 1 Hz HP data) → mne_plot_ica_components → mne_apply_ica (exclude eye/heart comps)
→ mne_find_events / mne_events_from_annotations
→ mne_make_epochs (tmin/tmax, baseline, reject) → mne_average_evoked
→ mne_plot_evoked / mne_plot_topomap   (+ mne_tfr_morlet for time-frequency)
→ mne_save
```

See [references/mne-pipelines.md](references/mne-pipelines.md) for ERP, time-frequency, and source
pipelines with parameters, and [references/mne-mcp-tools.md](references/mne-mcp-tools.md) for every
tool's arguments.

## Interpreting figures

Every plotting tool saves a PNG and returns `> Figure: <path>`. **Always read the PNG** and describe:
- **PSD** — line-noise peaks (50/60 Hz), broadband noise, channels that stick out (candidates for bad).
- **ICA components** — frontal/eye-blink dipoles, cardiac (regular spikes), muscle (high-freq edge).
- **Evoked / topomap** — component latencies (e.g. N1/P2/P300), polarity, scalp distribution.

## Output Archiving

After a meaningful analysis or plotting step, archive to `mne_result/` in the working directory:

**1. Ensure directory** — create `mne_result/` if missing.

**2. Sequence number** — find existing `mne_result/[0-9][0-9]_*`, take max prefix + 1 (start `01`).

**3. Copy figures** — for each `> Figure: <path>` in the result, copy the PNG to
   `mne_result/NN_<label>.png` (e.g. `01_psd.png`, `02_ica_components.png`, `03_evoked.png`).

**4. Append code** — append the ` ```python ` block from the tool result to a running
   `mne_result/pipeline.py` with a header comment, so the whole analysis is reproducible as one
   script:

```python
# ── NN  <step label>  <YYYY-MM-DD> ─────────────────────────────
<equivalent MNE code from the tool result>
```

**Constraints:** read-only tools (`mne_check_status`, `mne_session_info`, `mne_describe`,
`mne_get_info`, `mne_list_files`) do **not** trigger archiving. Sequence numbers are global, not
per-type.

## Reference Files

- **[references/mne-pipelines.md](references/mne-pipelines.md)** — Full preprocessing/ERP/TFR/source
  pipelines, parameter conventions, and `run_code` recipes for source localization, connectivity,
  decoding, statistics, and BIDS. Load when planning or running a multi-step analysis.
- **[references/mne-mcp-tools.md](references/mne-mcp-tools.md)** — Every MNE MCP tool with parameters
  and when to use each. Load when choosing which tool to call.
- **[references/failure-patterns.md](references/failure-patterns.md)** — Read when diagnosing montage
  errors, ICA convergence, TFR wavelet-length errors, unit mistakes, empty epochs, or format issues.
