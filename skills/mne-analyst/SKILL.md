---
name: mne-analyst
description: >
  Analyze human neurophysiology data (EEG, MEG, sEEG, ECoG, fNIRS) with MNE-Python through the MNE MCP
  server: load recordings, preprocess (filter, notch, re-reference, montage, bad channels), run ICA
  artifact removal, epoch around events, average ERP/ERF, compute time-frequency, plot and interpret
  every step, and reach the rest of MNE (source localization, connectivity, decoding, BIDS, stats) via
  mne_run_code. Use when the user asks to analyze or preprocess EEG/MEG/iEEG/fNIRS data, work with
  .fif/.edf/.bdf/.set/.vhdr/.cnt/.egi/.snirf files, or do filtering, ICA, epoching, ERP/evoked, PSD,
  topomaps, Morlet time-frequency, source estimation, connectivity, or decoding. Triggers: MNE, EEG,
  MEG, ERP, ICA, evoked, epoch, topomap, montage, raw.fif, 脑电, 脑磁, 预处理, 滤波, 分段, 叠加平均,
  时频, 源定位, 连接性, 解码, 伪迹去除.
---

# MNE Analyst

Drive MNE-Python analysis conversationally through the MNE MCP server. The server keeps **one
persistent session**, so load a recording once and build the pipeline step by step. Every plotting
tool returns `> Figure: <path>` — **read that PNG and interpret it before deciding the next step.**

## Quick start

```
mne_check_status                 # 1. confirm MNE (+ sklearn for ICA) is available
mne_load_raw path=... name=raw   # 2. load
mne_set_montage name=raw         # 3. positions (needed for topomaps/ICA/interpolation)
mne_plot_psd name=raw            # 4. LOOK (read the PNG) → pick filter cutoffs / spot bad channels
```

## Request → tools (routing)

| User wants | Call (in order) |
|---|---|
| Look at the data | `mne_describe` / `mne_get_info`, `mne_plot_psd`, `mne_plot_raw` |
| Clean / preprocess | `mne_filter` (+`notch`), `mne_mark_bad_channels` → `mne_interpolate_bads`, `mne_set_reference` |
| Remove eye/heart artifacts | `mne_fit_ica` (on ~1 Hz HP data) → `mne_plot_ica_components` → `mne_apply_ica exclude=...` |
| ERP / evoked | get events (`mne_find_events` or `mne_events_from_annotations`) → `mne_make_epochs` → `mne_average_evoked` → `mne_plot_evoked` / `mne_plot_topomap` |
| Time-frequency | `mne_make_epochs` (wide window) → `mne_tfr_morlet` |
| Decoding (MVPA) | `mne_decode cond_a=… cond_b=…` |
| Connectivity | `mne_connectivity method=coh fmin=8 fmax=13` |
| Source localization (EEG) | `mne_compute_noise_cov` → `mne_make_forward` → `mne_apply_inverse` → `mne_plot_source_estimate` |
| Save | `mne_save` |
| BIDS / stats / anything else | `mne_run_code` (see [references/mne-pipelines.md](references/mne-pipelines.md)) |

## Golden rules (prevent the common failures)

- ✅ **Inspect first** (`mne_get_info`) — never guess channel names, montage, or event codes.
- ✅ **Set a montage** before topomaps, ICA components, or interpolation.
- ✅ **High-pass ~1 Hz before ICA**; apply the resulting ICA to your ERP-filtered data.
- ✅ **SI units**: 100 µV = `reject_eeg=100e-6`, *not* `100`. (The #1 silent error.)
- ✅ **Read the figure** each plot returns; interpret it in plain language.
- ❌ Don't jump to a heavy step (ICA, TFR, source) before a quick sanity check.
- ❌ Don't use a short ERP window for TFR — Morlet needs a wider epoch (e.g. `tmin=-0.5 tmax=1.5`).

## Worked example

> User: "加载 sub01_raw.fif，1–40Hz 带通去 50Hz 工频，跑 ICA 去眼电，按 target 事件做 ERP 并画地形图"

1. `mne_load_raw path=sub01_raw.fif` → `mne_set_montage name=raw`
2. `mne_plot_psd name=raw` → **read PNG**: confirm 50 Hz peak, note any flat/noisy channels
3. `mne_filter name=raw l_freq=1 h_freq=40 notch=50`
4. `mne_fit_ica name=raw` → `mne_plot_ica_components` → **read PNG**: ICs 0,2 look frontal/blink
5. `mne_apply_ica ica_name=ica inst_name=raw exclude=0,2`
6. `mne_find_events` (or `mne_events_from_annotations`) → `mne_make_epochs event_id=target:1 tmin=-0.2 tmax=0.8`
7. `mne_average_evoked condition=target` → `mne_plot_evoked` + `mne_plot_topomap times=0.1,0.2,0.3`
8. Interpret: report the N1/P2/P300 latencies and scalp distribution from the figures.

## Defaults & config

Many tools fall back to **user-configured defaults** (montage, line freq, filter band, ICA method,
epoch window, rejection) when a parameter is omitted. Check them with `mne_get_config`; the user sets
them via `mne-mcp configure`. Respect their configured line frequency (50 vs 60 Hz).

## Output archiving

After a meaningful analysis/plot step, archive to `mne_result/` in the working directory:
1. Create `mne_result/` if missing; next sequence number = max `NN_` prefix + 1 (start `01`).
2. Copy each `> Figure:` PNG to `mne_result/NN_<label>.png` (e.g. `02_ica_components.png`).
3. Append the result's ` ```python ` block to `mne_result/pipeline.py` under a `# NN <step>` header,
   so the whole analysis re-runs as one script. Read-only tools (status/describe/get_info/session_info/
   list_files/get_config) don't trigger archiving.

## References

- **[references/mne-pipelines.md](references/mne-pipelines.md)** — full preprocessing/ERP/TFR pipelines
  + `mne_run_code` recipes for source localization, connectivity, decoding, statistics, BIDS, Report.
- **[references/mne-mcp-tools.md](references/mne-mcp-tools.md)** — every tool with parameters.
- **[references/failure-patterns.md](references/failure-patterns.md)** — error → fix for montage, ICA,
  TFR wavelet length, units, empty epochs, file formats, timeouts.
