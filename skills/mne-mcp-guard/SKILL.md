---
name: mne-mcp-guard
description: >
  Make MNE-Python MCP analysis robust by preventing common neurophysiology-pipeline failures before
  they happen and diagnosing them when they do. Use when an EEG/MEG/iEEG analysis should run
  defensively: avoiding unit mistakes (volts vs microvolts), montage/position errors, ICA
  non-convergence, time-frequency wavelet-length errors, empty/over-rejected epochs, wrong event
  codes, slow-step timeouts, or unsupported file formats; or when Claude should inspect data and run
  a minimal smoke step before a heavy MNE operation.
---

# MNE MCP Guard

Use this skill to make MNE MCP execution reliable, especially before expensive steps (ICA,
time-frequency, source localization) and on unfamiliar data.

## Workflow

1. **Check capability first** — `mne_check_status`. If MNE is missing, stop and say so; if
   scikit-learn is missing, ICA is unavailable.
2. **Inspect before processing** — `mne_get_info` / `mne_describe`. Never guess channel names,
   sampling rate, montage, or event codes.
3. **Look before parameterizing** — `mne_plot_psd` (read the PNG) before choosing filter cutoffs;
   `mne_plot_raw` before choosing rejection thresholds.
4. **Smoke-test heavy steps**
   - Before ICA: confirm data is high-pass filtered (~1 Hz) and montage is set.
   - Before epoching: verify real event codes exist (`mne_find_events` /
     `mne_events_from_annotations`) and that the epoch window fits the recording.
   - Before TFR: confirm the epoch window is long enough for the lowest frequency.
5. **Escalate gradually** — get a minimal version working (one condition, default params), then add
   options. Don't jump to a 60-component ICA or full source pipeline on the first try.
6. **Read warnings, not just success** — dropped epochs, rank deficiency, montage subset warnings,
   and annotation notes change the validity of results.

## Guardrails

- **Units are SI (volts/tesla).** A `reject` of `100` is 100 volts. 100 µV is `100e-6`. This is the
  most common silent error — verify any threshold's order of magnitude.
- **Set a montage** before topomaps, ICA component plots, or interpolation.
- **High-pass before ICA** (~1 Hz) or components will be unstable.
- Don't assume a file loads in one call — BrainVision/EEGLAB need sidecar files; point at the header.
- Don't conclude "timeout = broken." ICA/TFR/large files are genuinely slow; raise
  `MNE_MCP_TIMEOUT` and retry, or crop/decimate first.

## Decision tree

1. **"no session object named ..."?** → `mne_session_info`; load the data or fix the name.
2. **Plot/interpolation error mentioning positions/montage?** → `mne_set_montage`; check channel
   names match the montage.
3. **ICA error or weird components?** → confirm sklearn present, high-pass applied, and
   `n_components` ≤ data rank (lower it or use a `0.99` variance fraction).
4. **TFR "wavelet longer than signal"?** → wider epochs, higher `fmin`, or smaller `n_cycles` via
   `mne_run_code`.
5. **All epochs dropped / empty evoked?** → loosen `reject_eeg`, verify event codes, check the epoch
   window against recording length.
6. **Step times out?** → increase `MNE_MCP_TIMEOUT`; for large raw use `preload=false` + `mne_crop`.

## References

- Read `references/failure-patterns.md` for concrete error→fix mappings.
- Use `mne-analyst` for the full workflow and pipeline conventions; this skill is specifically for
  failure prevention and recovery.
