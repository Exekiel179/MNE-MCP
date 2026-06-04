---
name: mne-stats
description: >
  Statistical inference for EEG/MEG/iEEG via MNE — the CROSS-CUTTING statistics skill that operates
  on the outputs of the other analysis skills (evoked, TFR, connectivity, source). Mass-univariate
  testing, cluster-based permutation (1-sample and independent), threshold-free cluster enhancement
  (TFCE), FDR (Benjamini-Hochberg) and Bonferroni, parametric vs non-parametric, spatio-temporal
  clustering with channel adjacency, linear mixed models (LMM), and bootstrap CIs — run SKEPTICALLY:
  grill the statistical family and assumptions before testing, execute with best-practice defaults,
  then submit the result to methodology critique. Use to test condition/group differences across
  channels × times × freqs × ROIs, choose a multiple-comparison correction, or build an LMM.
  Triggers: statistics, 统计, 统计检验, cluster-based permutation, 簇置换, TFCE, FDR, Bonferroni,
  多重比较, permutation test, 置换检验, mixed model, LMM, 效应量.
---

# MNE Statistics (grill → analyze → critic)

Statistical inference on neurophysiology data via the MNE MCP server. This is the **cross-cutting**
skill: it consumes the outputs of `mne-erp`, `mne-timefreq`, `mne-connectivity`, and `mne-source`
and decides what can actually be *claimed* from them. It is **skeptical by design**: most statistical
mistakes (conflating cluster-level with point inference, an incomplete correction family, asserting
normality at small n) run *without any error* — so the discipline is to **grill before testing and
critique before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety; `mne-methodology-critic` for
> Phase 3. Loaded objects (evoked / TFR / connectivity / stc arrays) persist in one MNE session.

---

## PHASE 1 — GRILL (before testing anything)

Do **not** run a test until these are answered. If the user can't answer one, propose a sensible
default **and explicitly flag the open risk** — never silently choose.

**Design & claim**
- What is the hypothesis, and what is the *comparison*? (condition × condition, group × group,
  pre × post, vs a baseline / vs zero)
- Within- or between-subject? **Paired or independent?** n per cell, and is there **power** for it?
- Confirmatory (hypothesis + ROI/window/band pre-specified) or exploratory (whole grid, corrected)?

**The two questions that decide validity**
- **What is the statistical FAMILY — exactly which dimensions are tested?** Enumerate
  channels × times × freqs × ROIs × conditions. The correction must cover the *entire* family,
  including exploratory tests you ran but won't headline. An undercounted family is the single most
  common fatal error here.
- **Cluster-level or point inference?** ⚠️ A cluster-based permutation test licenses a claim about a
  *cluster* (a contiguous blob in space/time/freq), **not** about any specific channel, time, or
  frequency inside it. You may NOT say "Cz at 320 ms is significant" from a cluster test. If you need
  point/peak inference, you need a different, pre-specified test. Decide which claim you're making
  *before* you run.

**Assumptions & correction**
- Are **parametric assumptions** (normality, sphericity, homoscedasticity) going to be *tested* or
  just asserted? At small n (≲ 15–20) normality is **not establishable** → prefer permutation /
  non-parametric.
- Which correction — **cluster permutation, TFCE, FDR-BH, or Bonferroni** — and does its assumption
  hold? FDR-BH assumes independence / positive dependence; neighbouring channels/times/freqs are
  correlated, so per-point FDR can be both invalid *and* underpowered → cluster permutation / TFCE.
- **One- or two-tailed?** Stated and justified (`tail=0/1/-1`), not chosen after seeing the sign.

**Inference plan (pin this down NOW, not after seeing results)**
- ROI / window / band: pre-registered or data-driven? (data-driven = double-dipping)
- Is there **spatial/temporal adjacency** to respect? Sensor neighbours and time samples are not
  independent → build channel **adjacency** and use spatio-temporal clustering.
- Is this **trial-level, nested, or repeated-measures** data? Averaging trials away discards
  variance and pseudo-replicates → plan a **linear mixed model (LMM)**.
- Will you report **effect sizes + CIs** (bootstrap if non-parametric), not just p-values?

---

## PHASE 2 — ANALYZE

1. **Capability + assemble the data.** `mne_check_status`; gather the contrast array from the prior
   skill's output. Cluster tests want an array shaped **(n_observations, …)** — e.g.
   `(n_subjects, n_times, n_channels)` for spatio-temporal — where the observation axis is what gets
   permuted. Confirm the axis order matches the adjacency.
2. **Build channel adjacency from the montage** (so neighbouring sensors cluster together):

   ```python
   adjacency, ch_names = mne.channels.find_ch_adjacency(epochs.info, ch_type="eeg")
   ```
   (Combine with a time/freq lattice via `mne.stats.combine_adjacency` for spatio-temporal-spectral.)

3. **Run the test that matches the design** (via `mne_run_code`, prefer **non-parametric at small n**):

   ```python
   from mne.stats import (permutation_cluster_1samp_test, permutation_cluster_test,
                          spatio_temporal_cluster_test, fdr_correction)

   # 1-sample (within-subject difference vs 0): X = (n_subj, n_times, n_chan) of conditionA - conditionB
   T_obs, clusters, p_vals, H0 = permutation_cluster_1samp_test(
       X, adjacency=adjacency, n_permutations=5000, tail=0, seed=42)

   # Independent groups: [X_group1, X_group2]
   T_obs, clusters, p_vals, H0 = spatio_temporal_cluster_test(
       [Xg1, Xg2], adjacency=adjacency, n_permutations=5000, seed=42)
   ```
   Significant clusters are `clusters[i]` where `p_vals[i] < .05`.

4. **TFCE instead of an arbitrary cluster-forming threshold** (no hard threshold to justify):

   ```python
   T_obs, clusters, p_vals, H0 = permutation_cluster_1samp_test(
       X, adjacency=adjacency, threshold=dict(start=0, step=0.2),  # TFCE
       n_permutations=5000, tail=0, seed=42)
   ```

5. **Pre-specified point tests → FDR / Bonferroni** over the *actual* family (assumptions checked):

   ```python
   from scipy import stats
   t, p = stats.ttest_1samp(X_roi, 0)            # one value per pre-registered ROI/window
   reject, p_fdr = fdr_correction(p, alpha=0.05) # Benjamini-Hochberg
   p_bonf = np.minimum(p * len(p), 1.0)          # Bonferroni (conservative, independent only)
   ```

6. **Report cluster-level results + effect size.** State each significant cluster's **extent**
   (channels and time/freq span), its cluster p-value, and an effect size with a **bootstrap CI** —
   not just p. Plot the significant clusters (mask the topomap / TFR to the cluster mask).
7. **Trial-level / nested data → LMM** instead of averaging away variance (statsmodels):

   ```python
   import statsmodels.formula.api as smf
   md = smf.mixedlm("amp ~ condition", df, groups=df["subject"]).fit()  # random intercept per subject
   ```

8. **Archive** the equivalent code + figures (the `mne-analyst` archiving convention).

Best-practice reminders: permute the correct (observation) axis; fix a `seed`; prefer non-parametric
at small n; keep the cluster mask and report cluster **extent**, never an interior point.

---

## PHASE 3 — CRITIC (before believing the result)

Hand the design + result to **`mne-methodology-critic`** (invoke the skill, or dispatch it as a
subagent with `references/methodology-checklist.md`). For statistical work it will specifically check:

- **cluster-level vs point/peak inference** conflated (claiming a specific channel/time/freq is
  significant from a cluster test — you may not);
- **arbitrary cluster-forming threshold** (consider TFCE);
- **normality asserted at small n** (use permutation / non-parametric);
- **correction family incomplete** (uncounted exploratory tests, wrong dimension count);
- **spatial/temporal adjacency ignored** (per-point FDR on correlated data);
- **trial-level variance averaged away** (use an LMM for nested/repeated data);
- **effect sizes + CIs missing** (p-values only);
- **one- vs two-tailed** and paired vs independent unstated.

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating conclusions.

See `references/stats-methods.md` for deeper recipes (cluster permutation variants, adjacency
construction, TFCE, FDR vs Bonferroni, LMM, bootstrap CIs, and the inference-choice decision tree).
