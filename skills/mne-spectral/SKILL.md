---
name: mne-spectral
description: >
  Spectral / power-spectral-density analysis of EEG/MEG/iEEG via MNE — Welch and multitaper PSD,
  absolute and relative band power (delta/theta/alpha/beta/gamma), spectral slope, and 1/f aperiodic
  separation (specparam / FOOOF) — run SKEPTICALLY: grill the design and assumptions before
  computing, execute with best-practice defaults, then submit the result to methodology critique.
  Use for resting-state or task power, band power, alpha/theta power, relative power, individual
  alpha frequency, aperiodic exponent/offset, and group/condition power comparisons. Triggers: PSD,
  power spectral density, 功率谱, 频谱, 频谱分析, band power, 频带功率, relative power, 相对功率,
  alpha power, theta, spectral slope, 谱斜率, 1/f, aperiodic, FOOOF, specparam, resting state,
  静息态, Welch, multitaper, 个体 alpha 峰.
---

# MNE Spectral Analysis (grill → analyze → critic)

Power-spectral analysis of neurophysiology data via the MNE MCP server. This skill is **skeptical by
design**: most spectral mistakes (relative-power compositionality, conflating oscillations with 1/f,
asserting normality at small n) run *without any error* — so the discipline is to **grill before
computing and critique before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety; `mne-methodology-critic` for
> Phase 3. Loaded objects persist in one MNE session.

---

## PHASE 1 — GRILL (before computing anything)

Do **not** compute a PSD until these are answered. If the user can't answer one, propose a sensible
default **and explicitly flag the open risk** — never silently choose.

**Design & claim**
- What is the hypothesis, and what is the *comparison*? (group × group, condition × condition,
  pre × post)
- Within- or between-subject? Paired or independent? n per cell?
- Confirmatory (hypothesis + ROI/band pre-specified) or exploratory (whole-head, corrected)?

**The two questions that decide validity**
- **Absolute or relative power?** If relative (band/total): ⚠️ relative bands are **compositional**
  (they sum to ~1, are not independent). Per-band t-tests + FDR will be invalid. Plan a log-ratio
  (CLR/ALR) transform, or use absolute power. (This is the single most common fatal error here.)
- **Will you separate the 1/f aperiodic component?** If not, a difference in spectral slope or total
  power can masquerade as a band effect. Plan **specparam/FOOOF** (report exponent/offset + peaks),
  or justify why raw band power is adequate.

**Data & parameters**
- State: resting (eyes open/closed?) or task-locked? Stationary segment chosen how?
- Epoching: length (⇒ frequency resolution ≈ 1/length), overlap, rejection threshold — **and its
  justification**. Will the two groups have *different* rejection rates? (differential rejection
  fabricates differences)
- PSD method: Welch (window, overlap, n_fft) or multitaper (bandwidth)?
- Band definitions and edges; align to **individual alpha frequency**?
- Reference, channel selection, units.

**Inference plan (pin this down NOW, not after seeing results)**
- ROI: pre-registered or data-driven? (data-driven = double-dipping)
- Multiple comparisons across **bands × channels × conditions** — which correction, and is its
  independence assumption valid? (neighbouring channels/freqs are correlated → consider
  cluster-based permutation across the spectrum)
- Small n (≲ 15–20)? Then plan **permutation / non-parametric**, not a normality assertion.

---

## PHASE 2 — ANALYZE

1. **Capability + look first.** `mne_check_status`; `mne_plot_psd` and **read the PNG** — find line
   noise, bad channels, and whether the spectrum even looks like the expected 1/f + peaks shape.
2. **Compute the PSD** (via `mne_run_code` for full control). Welch on (clean, epoched) data:

   ```python
   # epochs already in the session; compute per-epoch PSD then average
   spec = epochs.compute_psd(method="welch", fmin=1, fmax=45, n_fft=int(epochs.info["sfreq"]*2))
   psds, freqs = spec.get_data(return_freqs=True)      # (n_epochs, n_ch, n_freqs)
   psd_mean = psds.mean(axis=0)                          # average over epochs
   ```
   (Multitaper: `method="multitaper", bandwidth=2`.)

3. **Band power.** Integrate the PSD over each band (trapezoid), not a single bin:

   ```python
   import numpy as np
   bands = {"delta":(1,4),"theta":(4,8),"alpha":(8,13),"beta":(13,30),"gamma":(30,45)}
   def band_power(psd, freqs, lo, hi):
       m = (freqs>=lo)&(freqs<hi)
       return np.trapz(psd[..., m], freqs[m], axis=-1)
   abs_pow = {b: band_power(psd_mean, freqs, lo, hi) for b,(lo,hi) in bands.items()}
   ```

4. **Relative power — handle compositionality.** If relative power is required, compute it but carry
   it into analysis via a **centered log-ratio (CLR)** so downstream tests are valid:

   ```python
   total = sum(abs_pow.values())
   rel = {b: abs_pow[b]/total for b in bands}            # compositional, sums to 1
   # CLR for valid statistics:
   import numpy as np
   comp = np.stack([rel[b] for b in bands])              # (n_bands, n_ch)
   clr = np.log(comp) - np.log(comp).mean(axis=0, keepdims=True)
   ```

5. **Aperiodic separation (recommended).** Fit specparam/FOOOF to separate the 1/f background from
   oscillatory peaks; report the **exponent** and **offset** plus periodic peak params:

   ```python
   from specparam import SpectralModel       # (or: from fooof import FOOOF)
   sm = SpectralModel(peak_width_limits=(1,12), max_n_peaks=6, aperiodic_mode="fixed")
   sm.fit(freqs, psd_mean[ch_idx], freq_range=[1,45])
   exponent = sm.get_params("aperiodic", "exponent"); offset = sm.get_params("aperiodic", "offset")
   ```

6. **Archive** the equivalent code + figures (the `mne-analyst` archiving convention).

Best-practice reminders: high-pass + line-notch before PSD; ≥ a few seconds per epoch for low
bands; report **per-group rejection rate**; prefer ROI/band that was pre-specified.

---

## PHASE 3 — CRITIC (before believing the result)

Hand the design + result to **`mne-methodology-critic`** (invoke the skill, or dispatch it as a
subagent with `references/methodology-checklist.md`). For spectral work it will specifically check:

- relative-power **compositionality** (sum-to-1 → independence violated);
- **proportion vs log** transform (logit, not log, for relative power);
- **aperiodic 1/f** confound (specparam) vs raw band power;
- epoch length ↔ **frequency resolution**;
- **multiple-comparison scope** (bands × channels) and correction validity;
- **double-dipping** on a data-driven ROI;
- **differential rejection** between groups;
- **small-n normality** asserted vs tested.

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating conclusions.

See `references/spectral-methods.md` for deeper recipes (Welch vs multitaper, CLR statistics,
specparam, individual alpha frequency, and spectral inference choices).
