# MNE MCP Failure Patterns

Read this when an MNE MCP step errors or behaves unexpectedly.

## "no session object named '...'"
The object isn't loaded (or you used the wrong name). Call `mne_session_info` to list what exists.
Objects persist across calls, but `mne_reset_session` clears everything.

## Montage / channel-position errors
Symptoms: `DigMontage is only a subset...`, `No digitization points found`, errors from
`plot_topomap`, `plot_components`, or `interpolate_bads`.
- Call `mne_set_montage` first. Pick a montage matching the cap; list built-ins via
  `mne_run_code code="mne.channels.get_builtin_montages()"`.
- If channel names don't match the montage (e.g. `EEG 001`), rename first via `mne_run_code`
  (`raw.rename_channels({...})`) or use `on_missing`.

## Unit mistakes (the #1 silent error)
Signals are in **volts/tesla**. A rejection threshold of `100` means 100 *volts* and rejects nothing
(or everything). Use `100e-6` for 100 µV. Evoked amplitudes near `1e-5`, not `10`.

## ICA
- `n_components` too high vs data rank (after average reference rank drops by 1) → reduce, or pass a
  float like `0.99` (variance fraction).
- ICA unstable / components look like drift → you forgot to high-pass (~1 Hz) before fitting.
- "requires scikit-learn" → `pip install scikit-learn` into the server env.
- FastICA didn't converge → try `method=picard` or `method=infomax`.

## TFR: "wavelet is longer than the signal"
With `n_cycles = freqs/2` the wavelet has roughly constant time support, so short epochs fail at low
frequencies. Fixes: epoch wider (`tmin=-0.5 tmax=1.5`), raise `fmin`, or via `mne_run_code` pass a
smaller `n_cycles` (e.g. fixed `n_cycles=3`).

## Empty / all-dropped epochs
- `reject_eeg` too strict → loosen it, or inspect with `mne_plot_epochs_image`.
- `event_id` names/codes don't exist → check `mne_find_events` / `events_from_annotations` output for
  the real codes before naming conditions.
- Epoch window runs past recording end → check `mne_describe` duration.

## File won't load
- `mne_load_raw` auto-detects by extension but some formats need a sidecar (BrainVision `.vhdr`
  needs `.eeg`+`.vmrk`; EEGLAB `.set` may need `.fdt`). Point at the header file.
- Unknown/again format → load via `mne_run_code` with the specific reader
  (`mne.io.read_raw_nihon`, `read_raw_curry`, `read_raw_snirf`, …).

## Timeouts
Big files, ICA, and TFR are slow. Raise `MNE_MCP_TIMEOUT` (seconds) in the MCP env config and restart
Claude Code. For very large raw, `mne_load_raw preload=false` and crop before heavy steps.

## Figures
Every plot tool returns `> Figure: <path>`. If you don't *read* the PNG you're flying blind — read it
and interpret before deciding the next step.
