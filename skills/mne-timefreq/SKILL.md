---
name: mne-timefreq
description: >
  Time-frequency analysis of EEG/MEG/iEEG via MNE — Morlet wavelets, multitaper and Stockwell
  transforms, event-related spectral perturbation (ERSP) power and inter-trial coherence (ITC),
  evoked vs induced (total) power, baseline normalization (logratio / zscore / percent), and the
  n_cycles time–frequency resolution tradeoff — run SKEPTICALLY: grill the design and assumptions
  before computing, execute with best-practice defaults, then submit the result to methodology
  critique. Use for time-frequency maps, ERSP, ITC, induced vs evoked oscillatory power, theta/alpha
  bursts over time, and phase-locking across trials. Triggers: time-frequency, 时频, 时频分析, Morlet,
  小波, wavelet, multitaper, Stockwell, ERSP, ITC, inter-trial coherence, 试间相位锁定, phase locking,
  induced, evoked power, total power, n_cycles, baseline normalization, 基线归一化.
---

# MNE Time-Frequency Analysis (grill → analyze → critic)

Time-frequency analysis of neurophysiology data via the MNE MCP server. This skill is **skeptical by
design**: most time-frequency mistakes (edge artifacts read as real low-frequency effects, an
unstated or contaminated baseline, evoked-vs-induced confusion) run *without any error* — so the
discipline is to **grill before computing and critique before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety (wavelet-length errors);
> `mne-methodology-critic` for Phase 3. Loaded objects persist in one MNE session.

---

## PHASE 1 — GRILL (before computing anything)

Do **not** compute a TFR until these are answered. If the user can't answer one, propose a sensible
default **and explicitly flag the open risk** — never silently choose.

**Design & claim**
- What is the hypothesis, and what is the *comparison*? (condition × condition, group × group,
  pre × post, post-stimulus × baseline)
- Within- or between-subject? Paired or independent? n per cell?
- Confirmatory (hypothesis + time-freq window/ROI pre-specified) or exploratory (whole map,
  corrected)?

**The two questions that decide validity**
- **Power or inter-trial coherence (ITC)?** Power = spectral magnitude over time; ITC = phase
  consistency across trials (0–1). They answer different questions — a stimulus can drive ITC with
  little power change (and vice versa). State which, or both.
- **Evoked or induced (total) power?** ⚠️ Power of the *average* (evoked) captures only
  phase-locked activity; per-trial power *then* averaged (total/induced) also captures
  non-phase-locked oscillations. These are **different claims**; mixing them (e.g. computing total
  power but interpreting it as the evoked response) is the most common fatal error here.

**Data & parameters**
- **Frequencies of interest**, and is the **LOWEST freq resolvable** given epoch length? A Morlet
  wavelet at `f` Hz with `n_cycles` cycles has half-length ≈ `n_cycles / (2f)` s — the epoch must
  extend that far beyond every time point you interpret, or you read **edge artifacts**.
- **n_cycles** choice (default `freqs/2`) and its **time ↔ frequency resolution tradeoff**: fewer
  cycles = better time, worse frequency resolution (and shorter wavelet → less edge contamination).
- **Baseline window + normalization TYPE** (logratio / zscore / percent / mean) — and is the
  baseline clean (no spillover from the previous trial, no anticipatory activity)?
- Method: Morlet, multitaper (DPSS smoothing), or Stockwell (S-transform)?
- Reference, channel selection, decimation, units.

**Inference plan (pin this down NOW, not after seeing results)**
- Time-freq window / ROI: pre-registered or data-driven? (data-driven = double-dipping)
- Multiple comparisons across **time × frequency × channels** — which correction? Per-pixel tests
  are massively multiple and correlated → plan **cluster-based permutation in time-frequency**.
- Small n (≲ 15–20)? Then plan **permutation / non-parametric**, not a normality assertion.

---

## PHASE 2 — ANALYZE

1. **Capability + look first.** `mne_check_status`; `mne_describe("epochs")` to read the epoch
   window. **Check the epoch is wide enough**: for the lowest frequency, you need
   ≈ `n_cycles/(2·fmin)` s of pad on *each* side of the interpretable window. If not, **re-epoch
   wider** (e.g. `-0.5` to `1.0+` s) from `raw` before computing.
2. **Compute Morlet power (+ ITC).** Quick path: `mne_tfr_morlet(fmin=, fmax=, n_freqs=)`. For ITC
   and full control use `mne_run_code`:

   ```python
   import numpy as np
   freqs = np.linspace(4, 40, 20)
   n_cycles = freqs / 2.0                       # default tradeoff; raise for fine freq resolution
   power, itc = mne.time_frequency.tfr_morlet(
       epochs, freqs=freqs, n_cycles=n_cycles,
       use_fft=True, return_itc=True, average=True)   # average=True ⇒ total/induced power + ITC
   ```
   (Multitaper: `tfr_multitaper(..., time_bandwidth=4.0)`. Stockwell: `tfr_stockwell(epochs, fmin=4,
   fmax=40)`. Evoked power: compute on `epochs.average()` instead of per-trial.)

3. **Baseline-normalize — state the type.** Apply on plot or in code; never leave it implicit:

   ```python
   power.plot([0], baseline=(-0.5, 0), mode="logratio")   # or: zscore / percent / mean
   ```
   `logratio`/`percent` = relative to baseline; `zscore` = SD units. Baseline must sit in the
   **clean pre-stimulus** window, clear of edge and anticipatory activity.

4. **Plot and read the PNG.** Inspect the time-frequency map; identify where the **edge zone** lies
   (the cone of influence widens at low frequencies) and **explicitly avoid interpreting it**.

5. **Induced vs evoked, explicitly.** If the claim is about non-phase-locked oscillations, confirm
   you used per-trial power (`average=True` over single-trial TFRs), not power of the evoked average.

6. **Archive** the equivalent code + figures (the `mne-analyst` archiving convention).

Best-practice reminders: epoch **wide** then crop the display; report `n_cycles`, baseline window +
mode, and method; mark the edge/cone region; prefer a time-freq window that was pre-specified.

---

## PHASE 3 — CRITIC (before believing the result)

Hand the design + result to **`mne-methodology-critic`** (invoke the skill, or dispatch it as a
subagent with `references/methodology-checklist.md`). For time-frequency work it will specifically
check:

- **edge / wavelet-length** effects read as real low-frequency effects (too-short epoch);
- **baseline normalization** unstated, or baseline window contaminated;
- **evoked vs induced** confusion (power of average vs per-trial power averaged);
- **n_cycles** time/freq-resolution tradeoff unjustified;
- **double-dipping** on a data-driven time-freq window / ROI;
- **multiple comparisons** across time × freq × channels (recommend cluster-based permutation);
- **small-n normality** asserted vs tested.

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating conclusions.

See `references/timefreq-methods.md` for deeper recipes (Morlet vs multitaper vs Stockwell, ITC,
baseline modes, the n_cycles/edge tradeoff, and time-frequency inference choices).
