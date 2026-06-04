# Connectivity analysis — deeper recipes & decisions

Companion to `mne-connectivity/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`raw`, `epochs`) and run inside `mne_run_code` (where `mne`, `np`, `plt`, and loaded objects are
pre-bound). Connectivity needs the **`[full]`** extra: `mne-connectivity` (and `pactools`/`tensorpac`
for PAC).

## Choosing a measure — the field-spread problem

A single brain source projects to **many sensors simultaneously with zero time lag** (volume
conduction in EEG, field spread in MEG). Any measure that rewards zero-lag phase agreement therefore
reports strong "connectivity" between channels that merely share one source. This is the dominant
artifact in sensor-space connectivity.

| Measure | Zero-lag sensitive? | Use when |
|---|---|---|
| **Coherence (coh)** | **Yes** — inflated by field spread | source space, or with explicit caveat |
| **PLV** | **Yes** — inflated by field spread | source space, or with explicit caveat |
| **Imaginary coherence (imcoh)** | No (keeps only the imaginary part) | sensor-space EEG/MEG default |
| **PLI** | No (sign of phase lag only) | sensor-space; robust but discards magnitude |
| **wPLI** | No, and less noise-biased than PLI | **sensor-space default** (debiased variant best) |

Caveat: discarding zero lag also discards *genuine* zero-lag coupling and reduces sensitivity — the
trade is accepted because true zero-lag interaction is generally indistinguishable from field spread.

## Spectral connectivity (mne-connectivity)

```python
from mne_connectivity import spectral_connectivity_epochs
con = spectral_connectivity_epochs(
    epochs, method=["wpli", "imcoh"], mode="multitaper",
    fmin=(4, 8, 13), fmax=(8, 13, 30), faverage=True, mt_adaptive=True)
wpli_alpha = con[0].get_data(output="dense")[:, :, 1]    # second band = alpha
```
- `mode="multitaper"` (controlled smoothing) or `"fourier"`/`"cwt_morlet"` (time-resolved).
- `faverage=True` averages within each (fmin, fmax) band; otherwise you get per-frequency.
- **Seed-based**: pass `indices=(seeds, targets)` to compute only the edges of interest and shrink the
  comparison family dramatically.
- **Time-resolved**: `spectral_connectivity_time(epochs, freqs=..., method="wpli")` gives a per-epoch /
  sliding estimate for dynamics.

## Phase-amplitude coupling (PAC / cross-frequency)

PAC asks whether the **phase** of a slow rhythm modulates the **amplitude** of a fast rhythm (e.g.,
theta phase → gamma amplitude). Raw PAC indices (MI, MVL) are **positively biased** by SNR, epoch
length, and filtering — a non-zero value alone means nothing.

```python
from tensorpac import Pac
p = Pac(idpac=(2, 2, 4), f_pha=(4, 8, 1, 0.5), f_amp=(30, 80, 5, 2))  # MI + surrogate normalization
sig = epochs.get_data(picks=ch)[:, 0, :]
pac = p.filterfit(epochs.info["sfreq"], sig, n_perm=200)             # z-scored vs surrogates
```
- Always normalize against a **surrogate distribution** (block-shuffle / time-shift the phase signal),
  not against zero.
- Filter bandwidths matter: the amplitude band must be **wider than twice the phase frequency**, or the
  coupling cannot be represented — a classic spurious-PAC trap.
- `pactools` (`Comodulogram`) is the MNE-adjacent alternative.

## Granger causality / directed connectivity

Directed measures (Granger, DTF, PDC) claim *who drives whom* and carry strong assumptions:

- **Stationarity** — high-pass, detrend, and possibly difference the series; non-stationarity fabricates
  directionality. Check (e.g., split-half stability) and report it.
- **SNR asymmetry** — the noisier of two signals appears to be *driven* even when it is the driver;
  match or report SNR per channel.
- **Model order / pre-whitening** — validate via AIC/BIC; report the order.
- Prefer **source space** for any anatomical directional claim; sensor-space Granger is between
  electrodes and is especially vulnerable to the common-reference mixing above.

## Sensor vs source space, and the reference

- **Sensor space** = edges between *electrodes/sensors*, not brain regions. Do not label them
  anatomically ("frontoparietal") — that is a source-space claim.
- **Common / average reference** injects a shared component into every channel, inflating coherence and
  PLV everywhere; current-source-density (surface Laplacian) or source projection mitigates it.
- **Source space**: project epochs through the inverse (`apply_inverse_epochs`) to labels, then run
  `spectral_connectivity_epochs` on the label time courses — but source leakage is the source-space
  analogue of field spread, so still prefer imcoh/wPLI and orthogonalize signals if needed.

## Statistical inference for connectivity

- **Match trial counts** across conditions before comparing (subsample to the smaller n); metrics are
  trial-count/SNR biased.
- **All-to-all** → a network/cluster-based permutation over the channel-pair graph for family-wise
  control; inference is at the **network/cluster level**, not per edge.
- **Seed-based / pre-registered edges** → test the actual family of edges with correction.
- **Small n** → permutation / non-parametric; don't assert normality.
- Always report **effect sizes + CIs**, **per-group rejection rates**, and the **retained trial count**.

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| Sensor coherence/PLV "connectivity" claim | volume conduction / field spread | imcoh / wPLI / PLI, or caveat |
| Average-reference + strong global coupling | common-reference inflation | CSD/Laplacian or source space |
| Condition A > B with fewer trials in B | trial-count / SNR bias | match n; subsample; correct |
| All-to-all heatmap, "these pairs significant" | uncorrected pair-wise family | network/cluster permutation or seed |
| Granger "X drives Y", noisier Y | SNR asymmetry / non-stationarity | match SNR; stationarize; check order |
| "Frontoparietal coupling" from sensors | sensor edges read anatomically | source-space connectivity |
| PAC value reported vs zero | positive bias of raw PAC | surrogate normalization (z/perm) |
