# Spectral analysis — deeper recipes & decisions

Companion to `mne-spectral/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`raw`, `epochs`) and run inside `mne_run_code` (where `mne`, `np`, `plt`, and loaded objects are
pre-bound).

## Welch vs multitaper

- **Welch** — robust, intuitive; resolution set by segment length, variance reduced by averaging
  overlapping windows. Good default for resting-state band power.
  `epochs.compute_psd(method="welch", fmin=1, fmax=45, n_fft=int(sfreq*2), n_overlap=int(sfreq))`.
- **Multitaper** — better bias/variance tradeoff and controlled spectral smoothing via `bandwidth`
  (time-bandwidth product); preferred for short segments or when smoothing must be explicit.
  `epochs.compute_psd(method="multitaper", fmin=1, fmax=45, bandwidth=2)`.
- **Frequency resolution** ≈ 1 / segment_length. 2 s ⇒ 0.5 Hz (delta poorly resolved); 4 s ⇒ 0.25 Hz.

## Absolute vs relative power, and why relative needs care

Relative power `P_band / P_total` removes between-subject total-power scale — useful — **but** the
set of relative bands is **compositional**: if the bands partition the analyzed range they sum to 1,
so they live on a simplex, are linearly dependent, and exhibit a spurious negative correlation
structure. Consequences:

- Per-band t-tests treated as independent + FDR-BH (which assumes independence / positive
  dependence) → invalid error control.
- A change in one band mechanically pushes the others.

**Valid options**
1. **Analyze absolute power** (often the cleanest), and report total power separately.
2. **Centered log-ratio (CLR)** transform the composition, then run standard multivariate or
   per-component tests in CLR space:
   ```python
   comp = np.stack([rel[b] for b in bands])          # (n_bands, n_subj)
   clr  = np.log(comp) - np.log(comp).mean(0, keepdims=True)
   ```
3. **Logit** a single proportion of interest if only one band ratio matters:
   `logit = np.log(p/(1-p))`.

Do **not** `log()` a relative power and call it normal because "EEG power is log-normal" — that
property is about positive, unbounded *absolute* power across trials, not a bounded proportion
across subjects.

## Separating the aperiodic 1/f (specparam / FOOOF)

Raw band power = oscillatory peak + aperiodic background. Two groups can differ in the **aperiodic
exponent** (slope) or **offset** with identical oscillations — or vice versa — and raw band power
cannot tell them apart. Fit a spectral model per channel/subject:

```python
from specparam import SpectralModel            # FOOOF was renamed to specparam
sm = SpectralModel(peak_width_limits=(1,12), max_n_peaks=6, min_peak_height=0.1,
                   aperiodic_mode="fixed")      # "knee" if a bend is visible
sm.fit(freqs, psd_mean[ch], freq_range=[1, 45])
ap_exponent = sm.get_params("aperiodic", "exponent")
ap_offset   = sm.get_params("aperiodic", "offset")
peaks       = sm.get_params("peak")             # CF, PW, BW per oscillatory peak
```

Report aperiodic exponent/offset **and** periodic peak parameters; compare those across groups rather
than (or alongside) raw band power.

## Individual alpha frequency (IAF)

Fixed band edges (e.g., alpha = 8–13 Hz) can straddle a subject's true alpha peak. Estimate IAF
(peak in 7–14 Hz, or center-of-gravity) and define individualized bands relative to it when alpha is
central to the hypothesis.

## Statistical inference for spectra

- **Whole-spectrum, no pre-chosen band/ROI** → **cluster-based permutation** across the
  frequency (× channel) grid handles the correlation between neighbouring bins and gives
  family-wise control. Remember: inference is **cluster-level**, not per-bin.
- **A few pre-registered bands/ROIs** → per-band tests with correction over the *actual* family
  (bands × channels), assumptions checked; CLR space if relative.
- **Small n** → permutation / Wilcoxon; don't assert normality.
- Always report **effect sizes + CIs** and **per-group artifact rejection rates**.

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| Per-band relative-power t-tests + FDR | compositional dependence | absolute power or CLR |
| `log(relative_power)` "for normality" | wrong transform for a proportion | logit, or absolute/CLR |
| Band difference but no peak check | 1/f slope/offset confound | specparam; compare aperiodic params |
| "Occipital alpha differs" with no pre-reg | data-driven ROI / double-dipping | pre-register ROI or whole-head cluster test |
| n=10, "data are normal" | untestable assumption at small n | permutation / non-parametric |
| Groups differ, unequal trials kept | differential rejection | report rejection rates; autoreject |
| 2 s epochs for a delta claim | frequency resolution too coarse | longer epochs (≥4 s) |
