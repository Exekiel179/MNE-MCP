# Time-frequency analysis — deeper recipes & decisions

Companion to `mne-timefreq/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`raw`, `epochs`) and run inside `mne_run_code` (where `mne`, `np`, `plt`, and loaded objects are
pre-bound).

## Morlet vs multitaper vs Stockwell

- **Morlet wavelets** — the intuitive default; a Gaussian-windowed complex sinusoid per frequency.
  Time/frequency resolution is set by `n_cycles` (per frequency). Gives power **and** ITC.
  `mne.time_frequency.tfr_morlet(epochs, freqs, n_cycles, use_fft=True, return_itc=True)`.
- **Multitaper** — averages several DPSS (Slepian) tapers for explicit, controlled spectral
  smoothing via `time_bandwidth`; lower-variance estimates, good for higher frequencies.
  `tfr_multitaper(epochs, freqs, n_cycles, time_bandwidth=4.0, return_itc=True)`.
- **Stockwell (S-transform)** — frequency-dependent Gaussian window, no `n_cycles` to set; convenient
  for a quick whole-band map. `tfr_stockwell(epochs, fmin=4, fmax=40, width=1.0)`.

## The n_cycles tradeoff (and why fmin × epoch length matters)

A Morlet wavelet at frequency `f` with `n_cycles` cycles has temporal SD `σ_t = n_cycles/(2πf)` and
spectral SD `σ_f = f/(2·n_cycles)`. So:

- **Fewer cycles** → narrower in time (better temporal localization), **broader in frequency**, and
  a **shorter wavelet** (less edge contamination).
- **More cycles** → sharper frequency resolution but blurred in time and a longer wavelet.
- The default `n_cycles = freqs/2` scales cycles with frequency (constant relative bandwidth).

The wavelet **half-length** ≈ `n_cycles/(2f)` seconds. The epoch must extend that far beyond every
time point you interpret. Example: 4 Hz, `n_cycles=7` ⇒ half-length ≈ 0.875 s — a `-0.2` to `0.5` s
epoch cannot support a clean 4 Hz estimate anywhere. **Re-epoch wider** (`-0.5` to `1.0+` s) and
crop the *display*, not the computation.

## Power: evoked vs induced (total)

- **Evoked power** = TFR of the **averaged** signal (`epochs.average()`): only phase-locked activity
  survives averaging.
- **Induced / total power** = TFR per trial, **then** averaged across trials: captures both
  phase-locked and non-phase-locked (induced) oscillations.
- Strictly, *induced* = total − evoked. Most "oscillatory power increase" claims mean total/induced;
  state explicitly which you computed. Conflating the two is a substantive error, not a cosmetic one.

```python
# total / induced (per-trial then average):
power = mne.time_frequency.tfr_morlet(epochs, freqs, n_cycles, average=True, return_itc=False)
# evoked (power of the average):
evk_power = mne.time_frequency.tfr_morlet(epochs.average(), freqs, n_cycles, return_itc=False)
```

## Inter-trial coherence (ITC)

ITC measures **phase consistency across trials** at each time–frequency point, in [0, 1]: 0 = uniform
phase, 1 = perfect phase locking. It is independent of amplitude — a response can be strongly
phase-locked (high ITC) with little power change. ITC requires single-trial (un-averaged) data:

```python
power, itc = mne.time_frequency.tfr_morlet(epochs, freqs, n_cycles, return_itc=True, average=True)
itc.plot([ch_idx], baseline=None)        # ITC is already a normalized [0,1] quantity
```
Note ITC is **biased upward by low trial counts** — match trial counts across conditions before
comparing, or correct for n.

## Baseline normalization modes

Raw TFR power is dominated by the 1/f scaling across frequencies, so a baseline correction is almost
always required to compare across frequencies/time. State the **mode** and the **window**:

| mode | formula (per freq) | interpretation |
|---|---|---|
| `mean` | `P − P̄_base` | raw difference |
| `ratio` | `P / P̄_base` | fold change |
| `logratio` | `log10(P / P̄_base)` | dB-like, symmetric (recommended) |
| `percent` | `(P − P̄_base) / P̄_base` | percent change |
| `zscore` | `(P − P̄_base) / SD_base` | SD units |

The baseline window must sit in the **clean pre-stimulus** period — clear of the wavelet edge zone
and of anticipatory/preparatory activity, and free of spillover from the previous trial.

## Statistical inference for time-frequency maps

- **Whole map, no pre-chosen window/ROI** → **cluster-based permutation** across the
  time × frequency (× channel) grid handles the heavy correlation between neighbouring pixels and
  gives family-wise control. Inference is **cluster-level**, not per-pixel.
- **A few pre-registered time-freq windows / ROIs** → tests over the *actual* family
  (windows × channels), assumptions checked.
- **Small n** → permutation / non-parametric; don't assert normality.
- Always report **effect sizes + CIs**, the **edge/cone region excluded**, and **per-group trial
  counts** (ITC and power are both trial-count biased).

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| Low-freq "effect" at the epoch edges | wavelet half-length > available pad | re-epoch wider; exclude cone |
| No baseline mode stated / "we baselined" | normalization type ambiguous | state mode (logratio…) + window |
| Baseline overlaps prior trial or cue | contaminated baseline | choose a clean pre-stimulus window |
| "Oscillatory power" from `epochs.average()` | evoked, not induced, power | per-trial TFR then average (total) |
| `n_cycles` unstated / default unjustified | time/freq resolution unjustified | report and justify n_cycles |
| "Theta at 300 ms, FCz" with no pre-reg | data-driven window / double-dipping | pre-register, or whole-map cluster test |
| Per-pixel t-tests across the map | massive correlated multiplicity | cluster-based permutation in TF |
| ITC compared across unequal trial counts | upward bias at low n | match trial counts / correct |
