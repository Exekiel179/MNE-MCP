# MNE MCP Guard — Failure → Fix

Concise error-to-fix table for defensive MNE MCP execution. (The `mne-analyst` skill has a longer
version; this one is tuned for fast recovery.)

| Symptom | Likely cause | Fix |
|---|---|---|
| `no session object named '...'` | not loaded / wrong name / session reset | `mne_session_info`; reload or correct name |
| Rejects everything or nothing | unit mistake (volts vs µV) | use `100e-6` for 100 µV, not `100` |
| `plot_topomap` / ICA components error | no montage / channel positions | `mne_set_montage`; ensure names match |
| ICA "requires scikit-learn" | sklearn not in server env | `pip install scikit-learn`, restart |
| ICA components look like drift | no high-pass before fitting | fit ICA on `raw.copy().filter(1.0, None)` |
| FastICA not converging | algorithm/data | `method=picard` or `infomax`; lower `n_components` |
| `n_components` error | exceeds data rank (avg ref drops rank) | reduce, or pass float `0.99` |
| TFR "wavelet longer than signal" | epochs too short for low freq | wider epochs / higher `fmin` / smaller `n_cycles` |
| All epochs dropped | `reject` too strict / bad window | loosen threshold; verify window vs duration |
| Empty event_id / KeyError on condition | wrong event codes | inspect `find_events` output before naming |
| File won't load | missing sidecar / niche format | point at header; use specific `read_raw_*` via `mne_run_code` |
| Operation times out | ICA/TFR/large file | raise `MNE_MCP_TIMEOUT`; `preload=false` + crop |
| `success` but odd results | ignored warnings (rank, drops, annotations) | read warnings; re-examine the figure |

## Smoke steps before heavy operations

```
# Before ICA
mne_describe name=raw            # confirm filtered, montage set, sfreq sane
# Before epoching
mne_find_events raw_name=raw     # confirm real event codes exist
# Before TFR
mne_describe name=epochs_tfr     # confirm window length is adequate
```
