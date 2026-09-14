# Structured bivariate connectivity

Use `mne_compute_connectivity` when the connected server advertises it. It wraps
`spectral_connectivity_epochs`, not `spectral_connectivity_time`: estimates are
across retained trials, including when Morlet adds an epoch-relative time axis.
At least two trials are required; two is only a technical minimum, not evidence
of reliable estimation. Check trial counts, spectral support and stationarity.

## JSON examples

Two-band seed analysis, with signed imaginary coherence:

```json
{"params": {"method": "imcoh", "mode": "multitaper", "fmin": [8, 18], "fmax": [13, 24], "pairs": [["Cz", "Pz"], ["Cz", "Oz"]], "mt_bandwidth": 4, "con_name": "imcoh_bands"}}
```

Explicit phase-lag directions using Fourier spectra:

```json
{"params": {"method": "dpli", "mode": "fourier", "fmin": 8, "fmax": 13, "pairs": [["Cz", "Pz"], ["Pz", "Cz"]], "plot": false, "con_name": "dpli_edges"}}
```

Morlet across-trial connectivity retaining frequency and time axes:

```json
{"params": {"method": "wpli", "mode": "cwt_morlet", "fmin": 8, "fmax": 24, "cwt_freqs": [8, 10, 12, 20, 24], "cwt_n_cycles": [2, 2, 3, 4, 4], "faverage": false, "pairs": [["Cz", "Pz"]], "con_name": "wpli_time"}}
```

These are parameter examples, not universal scientific settings. Inspect channel
names, epoch length, sampling frequency and hypothesis before choosing them.

## Parameter rules

- `method`: coh, cohy, imcoh, plv, ciplv, ppc, pli, pli2_unbiased, dpli, wpli,
  wpli2_debiased. One measure per call/output, avoiding ambiguous list storage.
- `fmin`/`fmax`: positive scalar or matching arrays, below Nyquist. Ordered bands
  may overlap; a shared boundary bin can belong to both bands. `faverage=false`
  returns the selected frequency bins, not a separate axis per requested band.
- `picks`: channel type, list of names, or zero-based indices. Null selects data
  channels, excluding EOG/stim and bads. Bad channels are excluded even if requested.
  `pairs` contains ordered channel-name pairs after selection; no guessed indices.
- Without `pairs`, non-dPLI measures use lower-triangle ordered pairs. dPLI
  computes both directions explicitly. Inspect `con.indices` for the actual order.
- `tmin`/`tmax` are epoch-relative seconds and must be inside the epoch. Shorter
  windows reduce spectral support; they are not automatic sliding windows.
- `mt_bandwidth`, `mt_adaptive`, `mt_low_bias` apply only to multitaper.
  `cwt_freqs` and `cwt_n_cycles` apply only to Morlet. Incompatible options fail
  rather than being silently ignored. Default Morlet cycles: 7.
- `block_size` controls connection-block memory; execution uses one worker job.
  `plot=false` avoids figure generation. Reusing `con_name` replaces that output;
  input epochs are copied, not changed.

## Interpretation and storage

Results store native Connectivity objects with compact edge-first data:
`con.get_data()` is `(edges, frequencies_or_bands[, times])`.
`con.names`, `con.indices`, `con.freqs` and (for Morlet) `con.times` identify axes.
Do not assume the new tool's first dimension is `n_channels**2`. The legacy
`mne_connectivity` retains full `n_channels**2` storage for compatibility, while
also using the corrected ordered-edge plot. Uncomputed entries in dense exports
(NaNs, or lower-triangle storage placeholders from the legacy tool) are not measured zeroes.

The plot shows at most the first 30 ordered edges, not the strongest 30. Signed
values are preserved. Complex coherency uses magnitude only for the plot; stored
values and the numerical summary retain complex components. Morlet plots average
over time, so inspect stored time slices for transient hypotheses. The short
edge summary averages over returned bins/bands and time and is descriptive only.

Never force symmetry for imcoh, cohy or dPLI. Swapping the edge reverses imcoh's
sign, conjugates coherency, and changes the dPLI phase-lag statistic. dPLI is not
causal evidence. Debiased metrics can legitimately be negative. Non-finite values
and upstream warnings must be investigated, not converted to zero.

Granger, multivariate connectivity, PAC, multiple simultaneous estimators and
per-epoch connectivity remain `mne_run_code` workflows. Inspect the installed
library signature and use the appropriate multivariate/grouped index format;
do not force them through this bivariate schema.

Upstream reference: [spectral_connectivity_epochs](https://mne.tools/mne-connectivity/stable/generated/mne_connectivity.spectral_connectivity_epochs.html).
