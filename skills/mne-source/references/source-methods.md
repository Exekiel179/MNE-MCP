# Source localization — deeper recipes & decisions

Companion to `mne-source/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`epochs`, `evoked`, and after the steps below `noise_cov`, `fwd`, `stc`) and run inside
`mne_run_code` (where `mne`, `np`, `plt`, and loaded objects are pre-bound). Source tools need the
**`[full]`** extra (`nibabel` for the forward model, `pyvista` for off-screen rendering).

## The inverse problem is ill-posed

Infinitely many cortical current distributions produce the same sensor data, so a unique solution
exists only after imposing a **prior** (minimum-norm energy, sparsity, maximal-SNR filter, …). The
"source map" is therefore the data *seen through that prior plus a head model plus a covariance*.
None of those choices errors out — they just move the estimate. Hence: report which prior, which head
model, which covariance, and treat template-head EEG estimates as **exploratory**.

## Noise covariance & rank (whitening)

The inverse whitens the data with the noise covariance; a wrong covariance bends the whole map.

- **Evoked** → covariance from the **pre-stimulus baseline**; **MEG** → often **empty-room**.
- Estimate with shrinkage and respect **rank**: `method="auto"`, `rank="info"`. Average reference
  (-1), interpolated channels, and ICA component removal each **drop rank**; an over-stated rank
  injects noise directions into the whitening.
- Enough samples: covariance needs ≫ n_channels samples to be stable; too few → unstable inverse.

```python
noise_cov = mne.compute_covariance(epochs, tmax=0.0, method="auto", rank="info")
mne.viz.plot_cov(noise_cov, evoked.info)        # eyeball whitening; check the whitened GFP ~ 1
```

## Forward model: template (fsaverage) vs individual MRI

- **Template (fsaverage)** — the MCP default. One generic head + generic BEM conductivities +
  (often) nominal electrode positions. Cheap, reproducible, **exploratory** — fine for "roughly
  occipital vs frontal," **not** for gyral/Brodmann claims.
- **Individual MRI** — FreeSurfer reconstruction → BEM surfaces → **co-registration** of digitized
  electrodes/HPI to the MRI. Required for quantitative anatomical localization. Co-registration error
  and skull-conductivity uncertainty remain the dominant EEG error sources.
- **Co-registration**: digitized + co-registered positions beat nominal montages; report which.

```python
fs_dir = mne.datasets.fetch_fsaverage()         # template head, downloaded once
fwd = mne.make_forward_solution(evoked.info, trans="fsaverage", src=src, bem=bem)
```

## Distributed inverses & depth bias

| Method | Prior | Depth bias | Note |
|---|---|---|---|
| **MNE** | min L2 energy | strong (superficial) | amplitudes interpretable; depth-weight to mitigate |
| **dSPM** | MNE noise-normalized | moderate | good default; t-like maps |
| **sLORETA** | noise-normalized, zero location bias (point-spread) | low | standardized, not amplitude |
| **eLORETA** | exact zero-error weighting | low | smooth, robust to noise |

```python
inv = mne.minimum_norm.make_inverse_operator(evoked.info, fwd, noise_cov, depth=0.8)
stc = mne.minimum_norm.apply_inverse(evoked, inv, lambda2=1.0/snr**2, method="dSPM")
```

⚠️ **Regularization** `lambda2 = 1/SNR²` is a hidden free parameter: too small → spiky/noisy, too
large → blurred. Justify the SNR or **sweep it** and show stability.

## Beamformers (LCMV / DICS)

Spatial filters that maximize source SNR; **assume sources are uncorrelated** — correlated bilateral
sources can cancel.

```python
from mne.beamformer import make_lcmv, apply_lcmv
data_cov = mne.compute_covariance(epochs, tmin=0.0, tmax=0.3)        # active window
filters  = make_lcmv(evoked.info, fwd, data_cov, reg=0.05,
                     noise_cov=noise_cov, pick_ori="max-power")
stc = apply_lcmv(evoked, filters)
```

**DICS** is the frequency-domain beamformer for **induced/oscillatory** power — build a cross-spectral
density (`mne.time_frequency.csd_morlet`) then `make_dics` / `apply_dics_csd`.

## Sparse / mixed-norm

When the generator is assumed **focal**, mixed-norm (MxNE / irMxNE / TF-MxNE) gives sparse estimates
instead of the smooth MNE blur: `mne.inverse_sparse.mixed_norm(evoked, fwd, noise_cov, alpha=...)`.
The sparsity is itself a strong prior — justify the focal assumption.

## Statistical inference for source estimates

- **Source maps are spatially smooth** → neighbouring vertices are **dependent**. A per-vertex
  threshold massively inflates false positives and the inference is **not** about any single vertex.
- **Whole-cortex** → **cluster-based permutation** over the source × time grid
  (`mne.stats.spatio_temporal_cluster_1samp_test` with the source-space adjacency); inference is
  **cluster-level**, not per-vertex/per-time.
- **A pre-registered label/ROI** → extract the time course (`stc.extract_label_time_course`) and test
  that, correcting over the actual family of ROIs.
- **Morph to fsaverage** before group stats so vertices correspond across subjects.
- Report effect sizes + CIs; never read a peak coordinate off a template-head EEG map as anatomy.

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| "Generator in left BA44" from fsaverage EEG | quantitative claim on a template head | downgrade to exploratory; or individual MRI + coreg |
| dSPM peak read as deep-vs-superficial | depth bias of MNE/dSPM | sLORETA/eLORETA; depth weighting; compare methods |
| One λ²/SNR, no justification | hidden free regularization parameter | justify SNR or sweep and show stability |
| "Vertex X significant at t" | per-vertex inference on a smooth map | cluster-based permutation; cluster-level claim |
| Unstable / noisy inverse | covariance from too few samples / wrong rank | more baseline; `rank="info"`; shrinkage |
| Bilateral source vanishes (LCMV) | beamformer correlated-source cancellation | MNE/dSPM, or model correlated sources |
| EEG source map over-read | volume conduction + skull-conductivity uncertainty | caveat; prefer MEG / individual MRI for strong claims |
