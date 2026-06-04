---
name: mne-source
description: >
  Source localization of EEG/MEG via MNE — noise covariance (from baseline / empty-room), forward
  modeling (BEM; template fsaverage vs individual MRI), minimum-norm inverse (MNE/dSPM/sLORETA/
  eLORETA), beamformers (LCMV/DICS), sparse/mixed-norm, and source-space statistics — run
  SKEPTICALLY: grill the head model, co-registration, and the spatial claim before computing,
  execute with best-practice defaults, then submit the result to methodology critique. Use for
  estimating cortical generators of an ERP/ERF or band power, picking an inverse method, and judging
  whether a source claim is supportable. Triggers: source localization, 源定位, 源分析, 逆问题,
  inverse problem, forward model, 正向模型, MNE, dSPM, sLORETA, eLORETA, beamformer, LCMV, DICS,
  minimum norm, 最小范数, mixed norm, noise covariance, 噪声协方差, BEM, fsaverage, 皮层源, cortical
  source, source estimate, stc.
---

# MNE Source Localization (grill → analyze → critic)

Source (inverse) modeling of neurophysiology data via the MNE MCP server. This skill is **skeptical
by design**: the inverse problem is **ill-posed** — many source configurations explain the same
sensor data — so every estimate depends on choices (head model, covariance, regularization, method)
that all run *without any error* and silently shape "where" the activity is. The single biggest trap
is a **quantitative source claim resting on a template head with no individual MRI** — so the
discipline is to **grill the model before computing and critique the localization before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety; `mne-methodology-critic` for
> Phase 3. Loaded objects persist in one MNE session. Source tools need the **`[full]`** extra
> (`nibabel` for the forward model, `pyvista` for rendering).

---

## PHASE 1 — GRILL (before computing anything)

Do **not** build a forward model or apply an inverse until these are answered. If the user can't
answer one, propose a sensible default **and explicitly flag the open risk** — never silently choose.

**The question that decides validity**
- **Template head (fsaverage) or individual MRI?** ⚠️ The MCP forward model uses **fsaverage** — a
  *template* head. That makes any source estimate **exploratory / qualitative**: it cannot support a
  quantitative anatomical claim ("the generator is in left BA44"). Quantitative localization needs an
  **individual MRI + BEM + co-registration**. (This is the single most common fatal overreach here.)

**Geometry & co-registration**
- Are electrode positions **digitized and co-registered** to the head, or **nominal** (idealized
  montage on a template)? Nominal positions add localization error on top of the template-head error.
- EEG or MEG? **EEG source localization is harder** (volume conduction, skull-conductivity
  uncertainty) and is more easily overinterpreted than MEG.

**Noise covariance (drives the whitening — get it wrong and the map is wrong)**
- Source: **pre-stimulus baseline** (for evoked) or **empty-room** (MEG)? Enough samples to estimate
  it stably (rank!)? Was the data **rank-reduced** by average reference / interpolation / ICA — and
  does the covariance reflect that rank?

**Inverse method & regularization**
- Which inverse: **MNE / dSPM / sLORETA / eLORETA** (distributed) or **LCMV / DICS** (beamformer) or
  **mixed-norm** (sparse)? Each carries a different bias — and ⚠️ **MNE/dSPM have a depth bias**
  (superficial sources favored); sLORETA/eLORETA reduce location bias; beamformers assume
  uncorrelated sources.
- **SNR / regularization (λ²)**: arbitrary or justified? λ² ≈ 1/SNR² controls spread vs noise; an
  unjustified value is a hidden free parameter.

**The spatial claim & inference**
- What is the **spatial claim**, and at what **resolution**? (a lobe? a gyrus? a single vertex?)
  Template-head EEG cannot license gyral-level claims.
- **Source-space multiple comparisons**: source maps are **smooth** → neighbouring vertices are
  **dependent** → no single-vertex/single-time claim without correction. Plan **cluster-based
  permutation** in source space, not per-vertex thresholding.

---

## PHASE 2 — ANALYZE

1. **Capability + look first.** `mne_check_status` (confirm the `[full]` extra: `nibabel`, `pyvista`);
   review the evoked/epochs you will invert (`mne_plot_evoked` / `mne_describe`) — a clean, baselined
   evoked with a sensible reference and montage is the prerequisite for a meaningful inverse.

2. **Noise covariance** from the pre-stimulus **baseline** (or empty-room for MEG):

   ```python
   # epochs already in the session; baseline = up to t=0
   noise_cov = mne.compute_covariance(epochs, tmax=0.0, method="auto", rank="info")
   ```
   (Structured form: `mne_compute_noise_cov(name="epochs", tmax=0.0, cov_name="noise_cov")`.
   `rank="info"` respects rank loss from average reference / interpolation / ICA.)

3. **Forward model** — **template head (fsaverage)**, downloaded once. State the caveat aloud:

   ```python
   # template-head EEG forward for the object's montage (fsaverage BEM)
   # -> estimates are EXPLORATORY; no individual MRI / co-registration
   ```
   (Structured form: `mne_make_forward(name="evoked", fwd_name="fwd")` — fetches fsaverage on first
   use.)

4. **Apply the inverse** (start with **dSPM**; report the peak vertex/time):

   ```python
   inv = mne.minimum_norm.make_inverse_operator(evoked.info, fwd, noise_cov)
   stc = mne.minimum_norm.apply_inverse(evoked, inv, lambda2=1.0/3.0**2, method="dSPM")
   ```
   (Structured form: `mne_apply_inverse(evoked_name="evoked", fwd_name="fwd", cov_name="noise_cov",
   method="dSPM", snr=3.0, stc_name="stc")`. Try **sLORETA/eLORETA** to check depth-bias sensitivity.)

5. **Beamformer (LCMV) / DICS / mixed-norm** via `mne_run_code` when appropriate:

   ```python
   from mne.beamformer import make_lcmv, apply_lcmv
   data_cov = mne.compute_covariance(epochs, tmin=0.0, tmax=0.3)     # active window
   filters  = make_lcmv(evoked.info, fwd, data_cov, reg=0.05, noise_cov=noise_cov)
   stc_lcmv = apply_lcmv(evoked, filters)                            # uncorrelated-source assumption
   ```
   (DICS: `make_dics` on a CSD from `csd_morlet`. Sparse: `mne.inverse_sparse.mixed_norm`.)

6. **Plot + report.** Render the cortical map and state the **peak location/time** with the
   template-head caveat:
   `mne_plot_source_estimate(stc_name="stc", hemi="both", time=None)` — **read the PNG**, then
   **archive** the equivalent code + figures (the `mne-analyst` archiving convention).

Best-practice reminders: baseline-correct and choose the reference *before* inverting; estimate
covariance with the correct **rank**; always state the **template-head / exploratory** caveat;
compare methods (dSPM vs sLORETA) rather than trusting one map.

---

## PHASE 3 — CRITIC (before believing the result)

Hand the model + result (head model, co-registration, covariance source, method, λ²/SNR, the spatial
claim) to **`mne-methodology-critic`** (invoke the skill, or dispatch it as a subagent with
`references/methodology-checklist.md`). For source work it will specifically check:

- **template-head localization**: a quantitative source claim with **no individual MRI /
  co-registration** is exploratory — WARN, or FAIL if stated quantitatively (gyral/Brodmann claim);
- **depth bias** of MNE/dSPM (superficial sources favored) — was it acknowledged / mitigated?
- **arbitrary regularization / SNR** (λ² a hidden free parameter) — justified or swept?
- **single-vertex / single-time inference without correction** — source maps are smooth →
  neighbours are dependent → **cluster-based permutation** in source space, not per-vertex;
- **misestimated noise covariance** (wrong baseline, too few samples, ignored rank loss);
- **EEG source localization overinterpreted** (volume conduction + skull conductivity uncertainty).

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating *where* the
activity is.

See `references/source-methods.md` for deeper recipes (covariance & rank, BEM/template vs individual
MRI, MNE/dSPM/sLORETA/eLORETA depth bias, LCMV/DICS, mixed-norm, and source-space inference choices).
