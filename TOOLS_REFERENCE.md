# MNE-MCP Tools Reference

**English** | [简体中文](TOOLS_REFERENCE.zh-CN.md)

40 tools over a **persistent session**: loaded objects (`raw`, `epochs`, `evoked`, `ica`, …) live in
memory across calls. Plotting tools save a PNG and return its path; read the PNG to interpret it.
Tool results also include the equivalent MNE code in a ```python``` block.

Decoding and decoding group tests now include evidence-bound interpretation, limitations,
missing information and review-only Results drafts. These do not certify study design or
generate missing CIs/citations. See the [interpretation contract](skills/mne-writeup/references/evidence-to-claims.md).
Filter calls validate all cutoffs/notch frequencies before processing; crop and resample
reject invalid bounds/rates. REST reference requires `mne_run_code` with an explicit forward model.

Many tools fall back to **user-configurable defaults** (line frequency, montage, filter band,
rejection threshold, ICA settings, epoch window) when a parameter is omitted — set them with
`python -m mne_mcp configure` and inspect them with `mne_get_config`.

---

## Status & Session

### `mne_check_status`
Versions of MNE / scikit-learn / numpy / scipy / matplotlib / pandas, and runtime dirs. **Call first.**
Also reports execution `busy`/`idle`. A timeout does not stop its worker; session access
is rejected while busy. Inspect objects after idle before retrying in-place operations.

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
Show the configured default parameters the tools fall back to. Change them with `python -m mne_mcp configure`.

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
Prefer JSON `event_id={"target":1,"standard":2}` and `baseline=[null,0]` (or null to disable).
Additional parameters: `reject`/`flat` channel-type-to-SI-threshold mappings, `picks`
(type/name list/index list), `detrend=null|0|1`, `reject_by_annotation=true`, and
`event_repeated="error"|"drop"|"merge"`. `reject={}` disables configured rejection;
omit it to use defaults. Do not combine `reject` with `reject_eeg`.

### `mne_plot_epochs_image(name="epochs", picks=None)` · epochs × time heatmap.
### `mne_average_evoked(epochs_name="epochs", condition=None, evoked_name="evoked")` · ERP/ERF.
### `mne_plot_evoked(name="evoked", style="joint")` · `joint` / `topo` / `butterfly`.
### `mne_plot_topomap(name="evoked", times="auto")` · `auto` / `peaks` / `"0.1,0.2,0.3"`.

---

## Time-frequency & Export

### `mne_compute_tfr(params)`
Configurable Morlet/multitaper power with optional ITC. `params` requires `freqs` (ascending Hz).
Optional: `epochs_name="epochs"`, `method="morlet"`, `n_cycles=7` (scalar or one per frequency),
`time_bandwidth=null` (multitaper only), `picks=null`, `average=true`, `return_itc=false`,
`decim=1`, `baseline=null`, `baseline_mode="mean"`, `tfr_name="power"`, `itc_name="itc"`, `plot=true`.
ITC requires averaging. Baseline normalization changes stored power, not ITC.
`average=false` retains trials; plotting averages trial powers for display only.
Decimation is post-transform subsampling and can alias. Input epochs are unchanged;
output names can replace existing results. See [JSON examples](skills/mne-analyst/references/structured-analysis.md).

### `mne_tfr_morlet(epochs_name="epochs", fmin=4, fmax=40, n_freqs=20, tfr_name="power")`
Morlet wavelet power (`n_cycles=freqs/2`) + plot. Needs epochs long enough for the lowest frequency.

### `mne_save(name, path, overwrite=True)`
Naming: Raw → `*_raw.fif`, Epochs → `*-epo.fif`, Evoked → `*-ave.fif`.

---

## Advanced analysis (user-managed optional dependencies)

### `mne_decode(epochs_name="epochs", cond_a, cond_b, scoring="roc_auc", cv=5, name="decoding")`
Binary decoding with fold-local StandardScaler + logistic regression. `method="sliding"` (default)
returns `(time,)`; `method="generalizing"` returns `(train_time, test_time)`, with an optional plot.
Supports `cv_strategy="stratified"|"stratified_group"|"leave_one_group_out"`, `groups` aligned
with ALL retained input epochs, `picks`, `shuffle=false`, `random_state=97`, `plot=true`.
Optional `tmin/tmax` crop a copy; classifier parameters: `C=1.0`, `class_weight=null|"balanced"`,
`max_iter=1000`. Stores mean scores, `name_folds` and `name_details` with split/class diagnostics.
Reference lines are not significance tests; folds are not independent subjects. Needs scikit-learn.
See [examples and result semantics](skills/mne-decoding/references/structured-decoding.md).

### `mne_decoding_group_test(params)`
Group sign-flip inference on one `mne_decode` mean curve/matrix per independent subject.
Required: `score_names`, unique `subject_ids`, `independent_subjects=true`, explicit `null_value`.
Supports ROC AUC/balanced accuracy with matching grids and methods, never CV folds as subjects.
`correction="max_t"` (two-sided, pointwise FWER) or `"cluster"` (cluster-mass FWER with lattice
adjacency across time or both train/test axes); `tail=0`, `n_permutations=1024`, `seed=97`,
`alpha=0.05`, `threshold=null` (cluster-forming t threshold), `name="decoding_stats"`, `plot=true`.
Stores corrected p values or cluster p values, statistic, mask, mean effect, H0 and diagnostics.
Assumes symmetric independent-subject effects. Not single-subject label permutation or prevalence.
See [design limits, examples and result semantics](skills/mne-decoding/references/group-inference.md).

### `mne_connectivity(epochs_name="epochs", method="coh", fmin=8, fmax=13, con_name="con")`
Single-band connectivity (`coh`/`plv`/`wpli`/`pli`/`imcoh`...). Keeps legacy full storage,
but plots ordered edges without forcing symmetry. Default channel selection excludes bads
and non-data channels. Needs mne-connectivity and at least two retained epochs.

### `mne_compute_connectivity(params)`
Bivariate multi-band connectivity. Parameters: `epochs_name="epochs"`, `con_name="con"`,
`method="coh"`, `mode="multitaper"|"fourier"|"cwt_morlet"`, `fmin=8`, `fmax=13`
(scalars or matching lists), `faverage=true`, `picks=null`, `pairs=null` (ordered channel-name pairs),
`tmin=null`, `tmax=null`, `mt_bandwidth=null`, `mt_adaptive=false`, `mt_low_bias=true`,
`cwt_freqs=null`, `cwt_n_cycles=null` (Morlet default 7), `block_size=1000`, `plot=true`.
Rejects incompatible estimator options. Stores compact `(edges, frequencies_or_bands[, times])`
values, preserving signs and complex components. Plot: first 30 edges, complex magnitude,
time mean for Morlet; no inferred symmetry. Granger/multivariate/PAC use `mne_run_code`.
See [examples and output semantics](skills/mne-connectivity/references/structured-connectivity.md).

### `mne_compute_noise_cov(name="epochs", tmax=0.0, cov_name="noise_cov")`
Noise covariance from the epochs baseline — prerequisite for the inverse operator.

### `mne_make_forward(name="evoked", fwd_name="fwd")`
Template-head (fsaverage) EEG forward model for the object's montage. Downloads fsaverage once. Needs nibabel.

### `mne_apply_inverse(evoked_name="evoked", fwd_name="fwd", cov_name="noise_cov", method="dSPM", snr=3.0, stc_name="stc")`
Estimate cortical sources (`dSPM`/`MNE`/`sLORETA`/`eLORETA`); stores the stc, reports peak time.

### `mne_plot_source_estimate(stc_name="stc", hemi="both", time=None)`
Render the source estimate as a cortical map PNG (needs PyVista off-screen rendering).

---

## Not covered here?
BIDS, custom statistics, beamformers (LCMV/DICS), autoreject, condition contrasts, niche formats →
**`mne_run_code`**. See `skills/mne-analyst/references/mne-pipelines.md` for recipes.
