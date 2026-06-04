# Methodology review checklist — general + per-method

Use the general checklist (in `SKILL.md`) on every analysis, then the matching section below.
Each item is phrased as the question to ask and the **failure mode** to watch for.

---

## Spectral / PSD / band power

- **Absolute vs relative power.** Relative power (band / total) is **compositional**: bands that
  partition the spectrum sum to 1, so they are linearly dependent and carry induced negative
  correlations. Per-band parametric tests + FDR assume independence → invalid. Use absolute power,
  or a log-ratio transform (CLR/ALR) and test in that space. *FAIL if per-band tests are run on raw
  relative power as if independent.*
- **Transform for proportions.** Relative power ∈ (0,1); "log-normal" applies to positive unbounded
  *absolute* power across trials, not proportions across subjects. Prefer **logit** for proportions.
- **Aperiodic 1/f.** Band power conflates oscillatory peaks with the 1/f aperiodic background. A
  group difference in aperiodic offset/exponent (or total power) can masquerade as a band effect.
  Separate with **specparam/FOOOF**; report aperiodic params and periodic peaks. *WARN if not done.*
- **Epoch length ↔ frequency resolution.** Resolution ≈ 1 / epoch_length (2 s ⇒ 0.5 Hz). Too short
  for delta; check the lowest band is resolvable.
- **PSD method specified.** Welch (window, overlap, n_fft) vs multitaper (bandwidth)? Detrending?
- **Differential rejection.** Fixed-µV thresholds reject unequally across groups/conditions →
  unequal retained data and SNR can create spurious power differences. Report per-group rejection.
- **Individual alpha.** Fixed band edges can misalign with individual alpha frequency (IAF);
  consider IAF-anchored bands.

## ERP / ERF (evoked)

- **Measurement window pre-specified?** Mean/peak amplitude in a window chosen *after* seeing the
  grand average is circular. Pre-register, or use orthogonal selection. *FAIL if peak-picked on the
  same data and then tested.*
- **Filter distortion.** Aggressive high-pass (>0.1–0.3 Hz) distorts slow components and can shift
  apparent latency/polarity; low-pass smooths peaks. Report filter and check artefacts.
- **Baseline.** Window length and placement; baseline noise propagates into the component.
- **Peak latency.** Single-subject peak latency is noisy; prefer **jackknife** + appropriate t.
- **Component identity.** Latency/polarity/topography must be consistent with the named component
  *and the stimulus modality* (e.g., auditory N1 is fronto-central, visual N1 is occipito-temporal
  ~150–200 ms — a 100 ms occipital deflection in vision is more likely P1).
- **Trial counts** balanced across conditions (affects ERP SNR).

## Time-frequency (TFR)

- **Baseline normalization** type stated (logratio / zscore / percent) and baseline window valid.
- **Edge / wavelet length.** Low frequencies need long epochs; estimates near epoch edges are
  unreliable (wavelet half-length). Don't interpret effects in the edge zone. *WARN if a low-freq
  effect is read off a too-short window.*
- **Evoked vs induced.** Power on the average (evoked) vs per-trial then average (total/induced) are
  different claims — state which.
- **n_cycles tradeoff.** Few cycles = better time, worse frequency resolution; justify.

## Connectivity

- **Volume conduction / field spread.** Coherence and PLV are inflated by a shared source / common
  reference. Prefer **imaginary coherence, wPLI, or PLI** for sensor-space EEG/MEG. *FAIL if
  zero-lag-sensitive measures are used to claim genuine sensor connectivity without caveat.*
- **Common reference** inflates apparent connectivity; consider source space or Laplacian.
- **SNR / trial-count bias.** Most connectivity metrics are biased by trial count and SNR; match
  across conditions or correct.
- **Directionality.** Granger/DTF require stationarity and are sensitive to SNR and pre-whitening.

## Source localization

- **Head model.** Template head (fsaverage) vs individual MRI; assumed BEM conductivities; nominal
  vs digitized electrode positions. Template-head EEG source estimates are exploratory; quantitative
  claims need individual MRI + co-registration. *WARN if quantitative source claims rest on a
  template head.*
- **Depth bias & regularization.** MNE/dSPM have depth bias; SNR/λ regularization affects spread.
- **Inference.** No claim about a single vertex/time without correction (cluster permutation in
  source space). Source maps are smooth → neighbouring vertices are dependent.

## Decoding / MVPA

- **Leakage.** All fitting (scaling, feature selection, ICA) must happen **inside** the CV fold on
  train data only. *FAIL on any preprocessing fit on the full dataset before CV.*
- **Chance level.** Establish chance via **label permutation**, not the nominal 1/n_classes,
  especially with class imbalance / small n.
- **Class imbalance.** Use balanced accuracy / ROC-AUC; report class sizes.
- **CV structure.** Subject-level (leave-one-subject-out) vs trial-level; trial-level CV inflates if
  trials from one subject leak across folds.
- **Temporal generalization** off-diagonal claims (maintenance/reactivation) need explicit care.

## Statistics (cross-cutting)

- **Cluster-based permutation** gives **cluster-level** inference, not point/peak inference — you may
  not claim a specific channel/time/frequency is significant, only the cluster. State this.
- **TFCE** avoids arbitrary cluster-forming thresholds; consider it.
- **Non-parametric for small n** — permutation/sign tests don't need normality.
- **Correction matches the family** of tests actually run (count exploratory tests too).
- **One- vs two-tailed**, paired vs independent, stated and justified.
- **Mixed models (LMM)** for nested/repeated data instead of averaging away trial-level variance.
