# Structured analysis parameters

Use these extensions when the connected server advertises `mne_compute_tfr`.
Older servers still support the legacy strings and `mne_tfr_morlet`.

## Epochs

Prefer native JSON to serialized Python expressions:

```json
{
  "event_id": {"target": 1, "standard": 2},
  "tmin": -1.5,
  "tmax": 1.5,
  "baseline": [null, 0],
  "reject": {"eeg": 0.0001, "eog": 0.0002},
  "flat": {"eeg": 0.0000000001},
  "picks": ["Cz", "Pz", "EOG"],
  "detrend": 1,
  "reject_by_annotation": true,
  "event_repeated": "error"
}
```

Thresholds are peak-to-peak in SI units, not universal recommendations. Inspect
channel types and signal scale first. Omitted/null `reject` uses configured EEG
rejection; `{}` explicitly disables it. Do not combine `reject` and `reject_eeg`.
`baseline=null` disables baseline subtraction; `"default"` means `[null, 0]`.
`event_repeated="drop"` or `"merge"` changes event semantics: choose deliberately.
Filtering also accepts JSON channel names/indices and legacy comma-separated picks.

## Time-frequency

Call `mne_compute_tfr` with one `params` object. Frequencies must increase strictly
and be below Nyquist. `n_cycles` is positive scalar or one value per frequency.

Morlet total power and ITC (wide epochs required):

```json
{"params": {"freqs": [8, 12, 20], "n_cycles": [3, 4, 5], "picks": ["Cz", "Pz"], "return_itc": true, "tfr_name": "power", "itc_name": "itc"}}
```

Multitaper power with explicit smoothing and baseline normalization:

```json
{"params": {"method": "multitaper", "freqs": [8, 12, 20], "n_cycles": 4, "time_bandwidth": 4, "baseline": [-0.8, -0.4], "baseline_mode": "logratio", "tfr_name": "mt_power"}}
```

Retain trials for downstream statistics without generating a figure:

```json
{"params": {"freqs": [8, 12, 20], "n_cycles": 3, "average": false, "return_itc": false, "plot": false, "tfr_name": "trial_power"}}
```

`average=true` averages single-trial power (total power), not power of the ERP and
not strictly induced-only power. ITC requires averaging and is never baseline
normalized by this tool. Power normalization is applied to the stored output;
do not apply it again when plotting. With `average=false`, normalization occurs
per trial; a requested plot averages those normalized trial powers for display.
`decim>1` only subsamples after transformation and can alias. Start at 1.
Output names may replace existing outputs; choose distinct names to retain results.

Use `mne_run_code` for Stockwell, complex coefficients, custom estimators and other
unexposed APIs. Inspect the installed MNE signature before using version-dependent
arguments; do not assume every online recipe matches the server environment.

## Timeout recovery

A timeout/cancelled request does not stop the computation. While status says
`busy`, session reads, writes, code and reset are rejected without being queued.
Wait for `mne_check_status` to report `idle`, then inspect session objects and saved
outputs. A completed or failed operation may already have changed data. Do not
blindly repeat filtering, ICA application, or baseline correction. A permanently
stuck worker requires an explicit restart decision, which loses in-memory data.
