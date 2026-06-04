# Advanced / rare methods — recipes, parameters & decisions

Companion to `mne-advanced/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`raw`, `epochs`) and run inside `mne_run_code` (where `mne`, `np`, `plt`, and loaded objects are
pre-bound). **Every external library named below is an OPTIONAL dependency** — install it explicitly
(`pip install <lib>`), flag it to the user, and **record its version** (these tools move fast).

| Method | External library (optional) | Install |
|---|---|---|
| EEG microstates | `pycrostates` | `pip install pycrostates` |
| Entropy / complexity | `antropy`, `neurokit2` | `pip install antropy neurokit2` |
| Graph / network metrics | `networkx`, `bctpy` | `pip install networkx bctpy` |
| Aperiodic 1/f | `specparam` (was FOOOF) | `pip install specparam` |
| fNIRS GLM | `mne-nirs` | `pip install mne-nirs` |
| Real-time / online | `mne-realtime`, `pylsl` | `pip install mne-realtime pylsl` |

## EEG microstates (pycrostates)

Segments the continuous EEG into a small set of quasi-stable **canonical topographies** (maps),
fitted on **GFP peaks** of clean, average-referenced data. Report per map: **GEV** (global explained
variance), **coverage** (% time), **mean duration**, **occurrence** (per second), and transition
probabilities.

```python
from pycrostates.cluster import ModKMeans                  # optional dependency
eeg = raw.copy().pick("eeg").set_eeg_reference("average")  # clean, ICA'd, avg-ref
mk  = ModKMeans(n_clusters=4, random_state=42).fit(eeg, n_jobs=1)
segm   = mk.predict(eeg, factor=10, half_window_size=8)
params = segm.compute_parameters()                         # gev, coverage, meandurs, occurrences
```

- **`n_clusters` (n_maps)** — canonically **4**, often 4–7; **not** fixed by nature. Justify via a
  cluster-validity / cross-validation criterion across k, and **report sensitivity to k**.
- **GFP-peak selection** and polarity-invariance (microstates ignore sign) are assumptions — verify.
- **Random seed** matters (k-means is non-deterministic); pin it and ideally run multiple restarts.
- Group analysis: fit group-level template maps, back-fit to subjects, then compare parameters.

## Complexity / entropy (antropy, neurokit2)

"Complexity" is a **family of distinct metrics**, not one thing — state exactly which and why it maps
to the hypothesis (it is easy to use entropy as a vague proxy for an effect better captured by power).

```python
import antropy as ant                                      # optional dependency
x = raw.get_data(picks="eeg")[0]
samp = ant.sample_entropy(x, order=2)                       # m=2; r defaults to 0.2*std
perm = ant.perm_entropy(x, order=3, normalize=True)
lziv = ant.lziv_complexity((x > np.median(x)).astype(int), normalize=True)
import neurokit2 as nk                                      # optional dependency
mse, _ = nk.entropy_multiscale(x, scale=range(1, 21))       # multiscale entropy curve
```

- **Sample entropy** parameters: embedding `m` (often 2), tolerance `r` (often 0.15–0.25·SD), and
  **series length** — all change the value; keep them fixed across compared conditions and report.
- **Lempel-Ziv** needs a **binarization** rule (median / mean threshold) and **normalization** — both
  are choices; state them.
- **Multiscale entropy** depends on the **scale range** and coarse-graining; long, stationary epochs
  needed for high scales.
- Entropy is sensitive to **sampling rate, filtering, length, and SNR** — match these across groups or
  the "complexity difference" is an artifact.

## Graph / network metrics (networkx, bctpy)

From a channel×channel (or source×source) **connectivity matrix** `C` (build it with a
volume-conduction-robust measure — see `mne-spectral` and the critic's connectivity notes). The
**thresholding scheme is the dominant confound**: most metrics depend on edge **density**.

```python
import networkx as nx                                       # optional dependency
A = (np.abs(C) > thr).astype(int); np.fill_diagonal(A, 0)    # binary, undirected
G = nx.from_numpy_array(A)
deg   = dict(G.degree())
clust = nx.average_clustering(G)
Lpath = nx.average_shortest_path_length(G) if nx.is_connected(G) else np.inf
mod   = nx.algorithms.community.modularity(G, nx.algorithms.community.greedy_modularity_communities(G))
```

- **Thresholding / density** — an absolute threshold gives groups **different densities**, and
  clustering / path length are density-dependent → differences can be pure density artifacts. Use
  **proportional (density-matched) thresholding**, or sweep a **range of densities** and report the
  metric across the range — never a single arbitrary `thr`.
- **Small-worldness** (σ = (C/C_rand)/(L/L_rand)) must be compared against **degree-matched random
  null networks** (e.g. `bctpy` `randmio_und`), not a single Erdős–Rényi graph.
- **Weighted vs binary**, directed vs undirected — decide and justify; weighted metrics avoid an
  arbitrary threshold but inherit the connectivity metric's bias.
- **Disconnected graphs** make path length infinite — handle the largest connected component or use
  efficiency instead.

## Aperiodic 1/f deep-dive (specparam)

Cross-reference **`mne-spectral`** for the canonical PSD + specparam workflow. The deep-dive here:
verify the **aperiodic mode**, examine fit quality, and treat exponent/offset as the quantities of
interest.

```python
from specparam import SpectralModel                         # optional dependency
sm = SpectralModel(peak_width_limits=(1, 12), max_n_peaks=6, aperiodic_mode="knee")  # vs "fixed"
sm.fit(freqs, psd, freq_range=[1, 45])
exponent = sm.get_params("aperiodic", "exponent")
offset   = sm.get_params("aperiodic", "offset")
r2, err  = sm.get_params("r_squared"), sm.get_params("error")   # ALWAYS check fit quality
```

- Choose **`aperiodic_mode`** by whether the log-log spectrum has a **knee**; report `r_squared` and
  error, and exclude poor fits. Compare exponent/offset across groups, not raw band power alone.

## Intracranial sEEG / ECoG specifics

- **Referencing first.** A distant/scalp reference is wrong for intracranial data. Use **bipolar**
  (`mne.set_bipolar_reference(raw, anode, cathode)`) or **Laplacian/common-average within a grid**;
  the chosen reference changes everything downstream.
- **High-gamma (70–150 Hz)** is the workhorse signal: band-pass → **Hilbert envelope** → log-power,
  often z-scored to baseline. It indexes local neural activity better than raw broadband.
  ```python
  hg = raw.copy().filter(70, 150).apply_hilbert(envelope=True)   # then log + baseline z-score
  ```
- **HFOs** (ripples 80–250 Hz, fast ripples 250–500 Hz) need a **high sampling rate** (≥2 kHz),
  aggressive artifact rejection, and a **detector with explicit thresholds** — report detector,
  thresholds, and false-positive control; HFO findings are detector-sensitive.

## fNIRS GLM (mne-nirs)

Raw fNIRS **intensity is not analyzable** — convert and QC first.

```python
import mne_nirs                                              # optional dependency
od  = mne.preprocessing.nirs.optical_density(raw)            # 1) intensity → optical density
sci = mne.preprocessing.nirs.scalp_coupling_index(od)        # 2) QC: drop channels with SCI < ~0.5
hb  = mne.preprocessing.nirs.beer_lambert_law(od, ppf=6.0)   # 3) modified Beer-Lambert → HbO/HbR
# 4) design matrix (HRF-convolved) → GLM:
glm = mne_nirs.statistics.run_glm(hb_epochs, design_matrix)
```

- **OD → Hb (modified Beer-Lambert)** with a stated **PPF / DPF**; analyze **HbO and HbR** (HbR is
  less motion-contaminated) — never raw intensity.
- **Scalp coupling index (SCI)** QC is mandatory: reject poorly-coupled channels before the GLM.
- **Short-separation channels** regress out systemic (scalp/cardiac) signal; motion correction (TDDR)
  and an HRF-convolved design matrix complete the standard GLM pipeline.

## Real-time / online (mne-realtime / LSL) — pointer only

For online acquisition, an **LSL** stream (`pylsl`) feeds `mne-realtime` for online epoching and
decoding (e.g. real-time BCI). This is a **separate, latency-aware pipeline**, out of scope for
offline file analysis; flag it as such and treat buffering, causal filtering, and timing as
first-class concerns.

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| Entropy "complexity differs" with no power check | rare metric where a standard one fits | justify metric vs band power; match length/SNR/filtering |
| Microstate `n_maps=4` taken as given | k not validated; sensitivity unreported | validate k; report sensitivity; pin seed + restarts |
| Graph metrics at one absolute threshold | density-dependent, groups differ in density | proportional/density-matched threshold; sweep densities |
| "Small-world brain" claimed | no proper random null | compare to degree-matched random nulls |
| fNIRS GLM on raw intensity | no OD→Hb / no SCI QC | Beer-Lambert (state PPF); SCI channel rejection; HbR too |
| sEEG high-gamma with scalp/distant ref | wrong referencing | bipolar / Laplacian within-grid reference |
| HFO counts compared across patients | detector-threshold sensitivity | report detector + thresholds; false-positive control |
| Specparam exponent reported, no `r²` | poor fit unflagged | report r_squared/error; pick fixed vs knee deliberately |
| Exploratory metric stated as confirmatory | over-interpretation, small literature | frame as hypothesis-generating; pre-register to confirm |
| Different result on re-run | non-determinism unpinned | pin seeds + library versions; archive equivalent code |
