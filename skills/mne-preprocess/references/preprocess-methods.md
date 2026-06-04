# Preprocessing — deeper recipes & decisions

Companion to `mne-preprocess/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`raw`, `epochs`) and run inside `mne_run_code` (where `mne`, `np`, `plt`, and loaded objects are
pre-bound). Preprocessing edits are **in place** on the named object.

## Filtering: FIR vs IIR, edges, and transition bandwidth

- **FIR** (MNE default, `fir_design="firwin"`) — **linear phase**, so the same delay at every
  frequency and (when compensated) no phase distortion of waveform shape. Preferred for ERP. Cost:
  long filters → longer edge transients.
- **IIR** (e.g. Butterworth, `method="iir"`) — short, efficient, but **non-linear phase** (causal
  filtering shifts/distorts latencies; zero-phase `filtfilt` fixes phase but can ring). Use when you
  need a steep rolloff cheaply and understand the phase consequences.
- **Transition bandwidth.** A narrower transition = steeper filter = longer impulse response = more
  ringing and longer edge artifacts. MNE's `l_trans_bandwidth` / `h_trans_bandwidth` default to
  `"auto"`; widening them trades passband sharpness for shorter, gentler transients.
- **High-pass edge is analysis-specific.** 0.1 Hz preserves slow ERP components; 0.5–1 Hz removes
  sweat/drift but **attenuates and can shift** CNV/P300/readiness potential; ~1 Hz is the ICA
  convention (drift wrecks the decomposition); minimal/no HP for low-frequency power/TFR.

```python
raw.filter(l_freq=0.1, h_freq=40.0, fir_design="firwin",
           l_trans_bandwidth="auto", h_trans_bandwidth="auto")
```

## Notch / line-noise removal

Mains noise sits at **50 Hz (most of the world) or 60 Hz (Americas)** plus harmonics. Either notch it
out or low-pass below it:

```python
raw.notch_filter(freqs=[50, 100, 150])              # narrow notch at line freq + harmonics
# spectrum-fit (cleaner, removes the line without a deep notch):
raw.notch_filter(freqs=[50, 100], method="spectrum_fit")
```

If your low-pass is already below the line frequency (e.g. 40 Hz LP with 50 Hz mains), an explicit
notch may be unnecessary — but verify on the post-filter PSD. Always re-check `mne_plot_psd`.

## Resampling: aliasing & event preservation

- New sfreq must be **> 2× the highest frequency of interest** (Nyquist). MNE low-passes before
  decimating, so it guards against aliasing — but don't downsample below twice your low-pass.
- **Downsample after epoching** when possible. Resampling **continuous** data moves event sample
  indices to the nearest new sample → **event jitter**. If you must resample continuous data, pass
  the events so MNE adjusts them, or resample the `Raw` and `events` together:
  `raw, events = raw.resample(250, events=events)`.

## Re-referencing: math and downstream consequences

- **Average reference** — subtract the mean over channels; assumes reasonable head coverage. Common
  for source modeling, but a **common/average reference inflates apparent connectivity** (shared
  reference signal) and changes the spatial pattern.
- **REST (reference electrode standardization technique)** — re-references to an estimated point at
  infinity using a head model; reduces reference bias for connectivity/source. Needs a forward/sphere.
- **Linked mastoid** — average of TP9/TP10 (or A1/A2); traditional for sleep/ERP, but mastoids are
  near active tissue and can bias temporal sites.
- **Bipolar** — difference of channel pairs; good for EOG/EMG/iEEG, removes common-mode but mixes
  two sites' activity.

```python
raw.set_eeg_reference("average", projection=False)       # or projection=True to add as a projector
raw.set_eeg_reference(["TP9", "TP10"])                    # linked mastoid
raw.set_eeg_reference("REST", forward=fwd)                # infinity reference (needs forward)
mne.set_bipolar_reference(raw, anode=["F3"], cathode=["F4"], ch_name=["F3-F4"])
```

Pick the reference for the **later** analysis: connectivity and source work are reference-sensitive,
so choosing average "by default" can silently bias them.

## Montage

Setting a montage attaches sensor positions — required for interpolation, topomaps, forward/source,
and many plots. Match the system to the cap:

```python
raw.set_montage("standard_1020", on_missing="warn")       # or "biosemi64", "GSN-HydroCel-128", ...
```

Nominal/template positions are fine for visualization but are a source of error for quantitative
source localization (digitized positions are better there).

## Bad-channel detection & interpolation (rank!)

Prefer an **objective, documented** criterion over eyeballing — and apply the **same** criterion to
every subject/group:

```python
# illustrative objective flags; PyPREP / RANSAC / autoreject do this more rigorously
data = raw.get_data(picks="eeg"); names = raw.copy().pick("eeg").ch_names
v = data.var(axis=1)
flat  = [names[i] for i in np.where(v < 1e-14)[0]]                       # dead channels
noisy = [names[i] for i in np.where(v > np.median(v) + 5*np.std(v))[0]]  # extreme variance
raw.info["bads"] = sorted(set(flat + noisy))
n_bad = len(raw.info["bads"])
raw.interpolate_bads(reset_bads=True)                                   # spherical spline; needs montage
```

**Interpolation reduces rank**: each interpolated channel is a linear combination of the others, so
the data rank drops by the number interpolated (plus 1 for an average reference). This **caps later
ICA / source `n_components`** — pass `n_components <= rank` to ICA, and account for it in covariance
rank for source work. Track and report `n_bad` per subject and **per group**.

## Cropping & segment rejection

Drop unusable spans by cropping or by annotating `BAD_*` segments (epoching then skips them):

```python
raw.crop(tmin=0, tmax=300)                                # keep first 5 min
raw.set_annotations(mne.Annotations(onset=[120.0], duration=[3.0], description=["BAD_movement"]))
```

Use the same objective-vs-eyeballed discipline here: hand-rejecting more from one group than another
fabricates differences.

## Pipeline order (a sane default)

1. Set montage → 2. Filter (HP/LP) + notch on **continuous** data (before epoching, to avoid
per-epoch edge artifacts) → 3. Re-reference → 4. Mark/interpolate bad channels → 5. (ICA/artifact
correction — see `mne-artifacts`) → 6. Epoch → 7. **Resample epochs** (not continuous) → 8.
Re-inspect PSD.

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| Flat/shifted P300 or CNV | high-pass too aggressive (≳0.3 Hz) | 0.1 Hz HP (or offline detrend) for ERP |
| Filtered each epoch after cutting | edge artifacts at every boundary | filter continuous data before epoching |
| "Connectivity differs between groups" | common/average reference inflation | imaginary coh / wPLI; consider REST or source |
| One group has 8 interpolated chans, other has 1 | differential bad-channel handling | same objective criterion across groups; report counts |
| ICA `n_components` errors / rank-deficient cov | interpolation/average ref dropped rank | set `n_components <= rank`; track interpolated count |
| Event latencies off by a sample | resampled continuous data | downsample epochs, or `resample(..., events=events)` |
| Line spike still in post-PSD | notch missed harmonics / wrong mains freq | notch 50/60 + harmonics; confirm region |
| 200 Hz data downsampled to 60 Hz | below 2× low-pass → aliasing | keep sfreq > 2× low-pass edge |
