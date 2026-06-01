# MNE-MCP Tools Reference

32 tools over a **persistent session**: loaded objects (`raw`, `epochs`, `evoked`, `ica`, …) live in
memory across calls. Plotting tools save a PNG and return its path; read the PNG to interpret it.
Tool results also include the equivalent MNE code in a ```python``` block.

Many tools fall back to **user-configurable defaults** (line frequency, montage, filter band,
rejection threshold, ICA settings, epoch window) when a parameter is omitted — set them with
`mne-mcp configure` and inspect them with `mne_get_config`.

---

## Status & Session

### `mne_check_status`
Versions of MNE / scikit-learn / numpy / scipy / matplotlib / pandas, and runtime dirs. **Call first.**

### `mne_session_info`
Table of every loaded object with a one-line summary (kind, channels, sfreq, etc.).

### `mne_describe(name)`
Detailed summary of one object: channels, ch-types, sfreq, filter band, bads, montage, duration.

### `mne_get_info(name)`
Full per-channel listing (name, type, bad flag) plus measurement info.

### `mne_reset_session`
Clear all objects and figures. Irreversible.

### `mne_run_code(code)`
Execute Python/MNE in the session. Pre-bound: `mne`, `np`, `pd`, `plt`, and all loaded objects.
Notebook-like: a final expression's value is returned; stdout captured; matplotlib figures saved as
PNG. The universal escape hatch for anything below + everything not listed.

### `mne_get_config`
Show the configured default parameters the tools fall back to. Change them with `mne-mcp configure`.

---

## Data IO

### `mne_list_files(directory=None, pattern=None)`
List neuro files (`.fif .edf .bdf .gdf .vhdr .set .cnt .egi .mff .ds .snirf …`). Defaults to
`MNE_MCP_DATA_DIR` or cwd. `pattern` is a glob.

### `mne_load_raw(path, name="raw", preload=True)`
Load a recording, auto-detecting format by extension (with reader fallback). `preload=False` for very
large files (load lazily, then `mne_crop`).

---

## Preprocessing — in place on `name`

### `mne_filter(name="raw", l_freq=None, h_freq=None, notch=None, picks=None)`
`l_freq`=high-pass edge, `h_freq`=low-pass edge, `notch`=line freq (50/60). e.g. ERP: `0.1, 40, 50`.

### `mne_resample(name, sfreq)` · downsample (epoch *after* if possible to preserve events).
### `mne_crop(name, tmin=0, tmax=None)` · keep a time window.
### `mne_set_montage(name, montage="standard_1020")` · set positions (`standard_1005`, `biosemi64`, `GSN-HydroCel-128`, …).
### `mne_set_reference(name, ref_channels="average")` · `average`, `REST`, or `"TP9,TP10"`.
### `mne_mark_bad_channels(name, bads, replace=False)` · `bads="Fp1,T7"`.
### `mne_interpolate_bads(name, reset_bads=True)` · spline interpolation (needs montage).

---

## Visualization — returns PNG path(s)

### `mne_plot_psd(name, fmin=0, fmax=None, picks=None)` · power spectrum (find line noise / bad chans).
### `mne_plot_raw(name, start=0, duration=20, n_channels=20)` · signal traces.
### `mne_plot_sensors(name, kind="topomap", show_names=True)` · electrode layout (`topomap`/`3d`).

---

## ICA — artifact removal

### `mne_fit_ica(name="raw", n_components=None, method="fastica", ica_name="ica", random_state=97)`
Fit ICA (needs scikit-learn). `n_components`: int, float (variance frac, e.g. `0.99`), or null.
`method`: `fastica` / `infomax` / `picard`. **Fit on ~1 Hz high-passed data.**

### `mne_plot_ica_components(ica_name="ica")` · component scalp maps.
### `mne_plot_ica_sources(ica_name="ica", inst_name="raw")` · component time courses.
### `mne_apply_ica(ica_name, inst_name, exclude=None)` · remove comps; `exclude="0,3"`.

---

## Events / Epochs / ERP

### `mne_find_events(raw_name="raw", stim_channel=None, events_name="events")` · from a trigger channel.
### `mne_events_from_annotations(raw_name="raw", events_name="events")` · from annotations (EDF/BV/EEGLAB).
### `mne_make_epochs(raw_name, events_name, event_id=None, tmin=-0.2, tmax=0.5, baseline="default", reject_eeg=None, epochs_name="epochs")`
`event_id="target:1,standard:2"` names/selects conditions; `baseline="default"` = `(None,0)`;
`reject_eeg=100e-6` = 100 µV peak-to-peak rejection.

### `mne_plot_epochs_image(name="epochs", picks=None)` · epochs × time heatmap.
### `mne_average_evoked(epochs_name="epochs", condition=None, evoked_name="evoked")` · ERP/ERF.
### `mne_plot_evoked(name="evoked", style="joint")` · `joint` / `topo` / `butterfly`.
### `mne_plot_topomap(name="evoked", times="auto")` · `auto` / `peaks` / `"0.1,0.2,0.3"`.

---

## Time-frequency & Export

### `mne_tfr_morlet(epochs_name="epochs", fmin=4, fmax=40, n_freqs=20, tfr_name="power")`
Morlet wavelet power (`n_cycles=freqs/2`) + plot. Needs epochs long enough for the lowest frequency.

### `mne_save(name, path, overwrite=True)`
Naming: Raw → `*_raw.fif`, Epochs → `*-epo.fif`, Evoked → `*-ave.fif`.

---

## Not covered here?
Source localization, connectivity, decoding, statistics, BIDS, Report, condition contrasts, niche
formats → **`mne_run_code`**. See `skills/mne-analyst/references/mne-pipelines.md` for recipes.
