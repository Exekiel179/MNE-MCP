---
name: mne-advanced
description: >
  Rare / advanced neurophysiology analyses on EEG/MEG/iEEG/fNIRS via MNE — a hub for the
  less-standard methods that mostly run through mne_run_code with an EXTERNAL, OPTIONAL library:
  EEG microstates (pycrostates), complexity/entropy (antropy / neurokit2), graph & network metrics
  (networkx / bctpy), aperiodic 1/f deep-dive (specparam), intracranial sEEG/ECoG (bipolar
  referencing, high-gamma, HFO), fNIRS GLM (mne-nirs), and real-time/online (mne-realtime / LSL).
  Run ESPECIALLY skeptically: these have a smaller literature and more researcher degrees of freedom,
  so grill appropriateness and parameter-sensitivity HARD before computing, execute exploratorily,
  then submit to methodology critique. Triggers: microstates, 微状态, entropy, 熵, complexity,
  复杂度, Lempel-Ziv, sample entropy, multiscale entropy, graph theory, 图论, 脑网络指标,
  small-worldness, modularity, real-time, 实时, LSL, sEEG, ECoG, 颅内, high gamma, HFO, fNIRS,
  近红外, Beer-Lambert, scalp coupling index, aperiodic, 1/f, specparam.
---

# MNE Advanced / Rare Methods (grill → analyze → critic)

A hub for the **non-standard** analyses — microstates, entropy/complexity, graph metrics, the 1/f
deep-dive, intracranial specifics, fNIRS GLM, real-time. Each runs mostly via `mne_run_code` with an
**external library that is an optional dependency** (named per method below). This skill is **extra
skeptical**: a smaller literature means more researcher degrees of freedom and easier
over-interpretation, so the discipline is to **grill appropriateness and parameter-sensitivity before
computing, frame as exploratory, and critique before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety; `mne-methodology-critic` for
> Phase 3; `mne-spectral` for the canonical PSD / aperiodic workflow. Loaded objects persist in one
> MNE session. **Install the named library first** (e.g. `pip install pycrostates`); flag it as an
> optional dependency to the user before running.

---

## PHASE 1 — GRILL (before computing anything)

These methods are non-standard, so the intake is harsher. Do **not** compute until these are
answered. If the user can't answer one, propose a sensible default **and explicitly flag the open
risk** — never silently choose.

**Appropriateness (the gate question)**
- Is this method **validated for this data type and question**, or would a **standard method answer
  it better**? (e.g. "network hubs" via graph theory when a simple ROI contrast suffices; entropy as
  a vague "complexity" proxy when band power is the real hypothesis.) Justify choosing the rare tool.
- Confirmatory (metric + ROI/band pre-specified) or **exploratory** (then say so, and frame every
  number as hypothesis-generating)? With a small literature, default to exploratory.

**Parameters & sensitivity (these methods are parameter-hungry)**
- What are the **key parameters**, and how **sensitive** are results to them? Plan a sensitivity
  sweep, not a single setting. Examples: microstates `n_maps` (4–7) + GFP-peak selection; sample
  entropy `m`, `r`, length; multiscale entropy scales; graph **threshold / density**; HFO detector
  thresholds; specparam `peak_width_limits` / `aperiodic_mode`.

**Method-specific preprocessing assumptions**
- **Microstates** need a clean, artifact-free signal and a well-behaved **GFP** (average reference,
  ICA-cleaned); fit on GFP peaks.
- **fNIRS** must go **optical density → haemoglobin (modified Beer-Lambert)** and pass a **scalp
  coupling index (SCI)** QC before any GLM — raw intensity is not analyzable.
- **sEEG/ECoG** need **appropriate referencing** (bipolar / Laplacian, not a distant scalp ref);
  high-gamma is **70–150 Hz** band-limited power; HFOs need high sampling rate + artifact rejection.
- **Graph metrics** assume a defensible **connectivity matrix** (volume-conduction-robust measure;
  see `mne-spectral` / critic connectivity notes) **and** a justified thresholding scheme.

**Inference & reproducibility (small-literature methods need this more, not less)**
- **Multiple comparisons** across maps × channels × scales × thresholds — corrected, or framed as
  exploratory?
- Given the **smaller literature**, what justifies the chosen **defaults** (cite a method paper)?
- **Reproducibility**: random **seeds** (microstates k-means, permutations), **library + version**
  pinned (these tools change fast), equivalent code archived?

---

## PHASE 2 — ANALYZE

Capability + look first: `mne_check_status`; plot the relevant signal/PSD and **read the PNG**.
Then run the matching skeleton via `mne_run_code` (objects `raw`/`epochs` are pre-bound). **Each
library is an optional dependency — install and flag it.** Keep the framing **exploratory**.

**Microstates** — `pip install pycrostates` (optional):
```python
from pycrostates.cluster import ModKMeans          # optional dependency
gfp = raw.copy().pick("eeg").set_eeg_reference("average")
mk = ModKMeans(n_clusters=4, random_state=42).fit(gfp, n_jobs=1)   # fits on GFP peaks
segm = mk.predict(gfp); params = segm.compute_parameters()         # GEV, coverage, duration, occurrence
```

**Complexity / entropy** — `pip install antropy neurokit2` (optional):
```python
import antropy as ant                              # optional dependency
x = raw.get_data(picks="eeg")[0]
samp = ant.sample_entropy(x)                        # tune m, r
lziv = ant.lziv_complexity((x > np.median(x)).astype(int), normalize=True)
# multiscale entropy via neurokit2.entropy_multiscale(x, scale=range(1,21))
```

**Graph / network metrics** from a connectivity matrix `C` (`pip install networkx bctpy`, optional):
```python
import networkx as nx                               # optional dependency
A = (np.abs(C) > thr).astype(int); np.fill_diagonal(A, 0)   # threshold → caveat: density-dependent
G = nx.from_numpy_array(A)
deg = dict(G.degree()); clust = nx.average_clustering(G); L = nx.average_shortest_path_length(G)
# small-worldness vs degree-matched random nulls; modularity via community detection
```

**Aperiodic 1/f deep-dive** — `pip install specparam` (optional); see **`mne-spectral`** for the full
workflow. Report exponent/offset + peaks; compare `aperiodic_mode="fixed"` vs `"knee"`.

**Intracranial sEEG/ECoG**: re-reference **bipolar** (`mne.set_bipolar_reference`); high-gamma =
filter 70–150 Hz → Hilbert envelope → log-power; HFO via a detector (ripples 80–250 Hz).

**fNIRS GLM** — `pip install mne-nirs` (optional):
```python
import mne_nirs                                     # optional dependency
od = mne.preprocessing.nirs.optical_density(raw)
sci = mne.preprocessing.nirs.scalp_coupling_index(od)          # QC: drop channels with low SCI
hb = mne.preprocessing.nirs.beer_lambert_law(od, ppf=6.0)      # OD → HbO/HbR
# design matrix + GLM via mne_nirs.statistics.run_glm
```

**Real-time / online** — brief pointer: `mne-realtime` + an **LSL** stream (`pylsl`) for online
epoching/decoding; out of scope for offline files. Treat as a separate, latency-aware pipeline.

**Archive** the equivalent code + figures (the `mne-analyst` archiving convention), and **record the
library version** for every external tool.

---

## PHASE 3 — CRITIC (before believing the result)

Hand the design + result to **`mne-methodology-critic`** (invoke the skill, or dispatch it as a
subagent with `references/methodology-checklist.md`). For rare/advanced work it will specifically
check:

- **method appropriateness** — is the rare metric justified, or would a standard method answer the
  question? (FAIL if a complexity/graph metric is used where a direct contrast suffices);
- **parameter sensitivity unreported** — single-setting microstate `n_maps`, entropy `m`/`r`, graph
  threshold with no sweep;
- **method-specific assumption violations** — fNIRS without OD→Hb + SCI QC; sEEG without bipolar/
  Laplacian referencing; microstates without a clean GFP;
- **over-interpretation** of an exploratory metric (entropy, "small-worldness") as confirmatory;
- **multiple comparisons** across maps × channels × scales × thresholds;
- **graph metrics sensitive to thresholding / density** — compare across thresholds or use degree-
  matched random nulls; never report a single arbitrary density;
- **reproducibility** of a less-standard pipeline — seeds, pinned library versions, archived code.

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating conclusions.

See `references/advanced-methods.md` for per-method recipes, parameters, the optional-dependency
list, and failure modes.
