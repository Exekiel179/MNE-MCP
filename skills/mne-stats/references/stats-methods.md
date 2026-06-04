# Statistical inference — deeper recipes & decisions

Companion to `mne-stats/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`epochs`, `evoked`, TFR/connectivity/stc arrays) and run inside `mne_run_code` (where `mne`, `np`,
`plt`, and loaded objects are pre-bound). This skill is **cross-cutting**: it tests the outputs of
`mne-erp`, `mne-timefreq`, `mne-connectivity`, and `mne-source`.

## Mass-univariate testing & the multiplicity problem

A test at every channel × time × frequency is thousands of comparisons, almost all of them
**correlated** (neighbouring sensors and adjacent samples move together). Two consequences: an
uncorrected map is hopelessly anti-conservative, and a correction that *assumes independence*
(per-point Bonferroni or naive FDR) is simultaneously **invalid** (dependence) and **underpowered**
(it ignores that real effects are spatially/temporally contiguous). The fix is to exploit the
structure — cluster the contiguous evidence and permute.

## Parametric vs non-parametric — and small n

- **Parametric** (t/F + analytic p) needs normality / sphericity / homoscedasticity. At **n ≲ 15–20
  you cannot establish normality** in *this* sample; "the literature says EEG is normal" is asserted,
  not tested.
- **Non-parametric permutation** builds the null by shuffling labels (or sign-flipping for
  1-sample), so it needs no distributional assumption — preferred at small n. Always set `seed`.

## Cluster-based permutation (the workhorse)

Threshold the statistic to form clusters, sum the statistic within each cluster (cluster mass),
then build the null distribution of the **largest** cluster mass under permutation. A cluster is
significant if its mass exceeds the permutation null.

```python
from mne.stats import (permutation_cluster_1samp_test, permutation_cluster_test,
                      spatio_temporal_cluster_test, spatio_temporal_cluster_1samp_test)

# 1-sample: within-subject contrast vs 0. X = (n_subj, n_times, n_chan)
T_obs, clusters, cluster_pv, H0 = permutation_cluster_1samp_test(
    X, adjacency=adjacency, n_permutations=5000, tail=0, seed=42)   # sign-flips

# Independent groups: list of arrays, label permutation
T_obs, clusters, cluster_pv, H0 = permutation_cluster_test(
    [Xg1, Xg2], adjacency=adjacency, n_permutations=5000, seed=42)

good = [c for c, p in zip(clusters, cluster_pv) if p < 0.05]
```

**The inference is cluster-level.** A significant cluster says *"there is an effect somewhere in this
spatio-temporal blob."* It does **not** license "channel Cz at 320 ms is significant" or "the peak is
at 340 ms" — the location and extent of a cluster are not themselves tested. State this explicitly.

The default **cluster-forming threshold** (a t/F value) is arbitrary; it changes which effects cluster
(a high threshold favours strong-focal effects, a low one favours weak-broad ones). Either justify it
or use TFCE.

## Channel adjacency & spatio-temporal lattices

Clustering needs to know which channels are neighbours, or it will never join them:

```python
adjacency, ch_names = mne.channels.find_ch_adjacency(epochs.info, ch_type="eeg")  # from montage
# spatio-temporal-(spectral) lattice for (n_obs, n_freqs, n_times, n_chan):
from mne.stats import combine_adjacency
st_adj = combine_adjacency(n_freqs, n_times, adjacency)
```

`spatio_temporal_cluster_test` expects the observation axis first and the spatial axis **last**;
reshape/transpose so the array, the adjacency, and your mental model agree before you trust a result.

## Threshold-free cluster enhancement (TFCE)

TFCE integrates over all cluster-forming thresholds, removing the arbitrary single threshold and
returning a per-point enhanced statistic (still with family-wise control via permutation):

```python
T_obs, clusters, cluster_pv, H0 = permutation_cluster_1samp_test(
    X, adjacency=adjacency, threshold=dict(start=0, step=0.2),
    n_permutations=5000, tail=0, seed=42)
sig = cluster_pv.reshape(T_obs.shape) < 0.05   # per-point corrected map
```

TFCE gives a corrected p **per point**, but the inference is still family-wise — it does not
resurrect a free claim about an individual sample without the same correction.

## FDR vs Bonferroni — for a *small, pre-specified* family

When the family is a handful of pre-registered ROIs/windows (not a dense correlated grid):

```python
from mne.stats import fdr_correction
reject, p_fdr = fdr_correction(p_values, alpha=0.05, method="indep")  # Benjamini-Hochberg
p_bonf = np.minimum(p_values * len(p_values), 1.0)                    # Bonferroni (FWER)
```

- **Bonferroni** controls the family-wise error rate; correct but conservative and assumes (for the
  simple form) independence.
- **FDR-BH** controls the expected false-discovery proportion; more powerful but `method="indep"`
  assumes independence / positive dependence — use `method="negcorr"` (BY) otherwise. Neither is a
  substitute for cluster permutation on a dense correlated grid.

`ttest_1samp_no_p` gives the t-statistic (no p) for feeding hat-corrected variance or custom stat
functions into the permutation machinery.

## Linear mixed models (LMM) — don't average away trials

Averaging trials to one value per subject discards trial-level variance and treats pseudo-replicates
as independent. For nested/repeated data, model the structure:

```python
import statsmodels.formula.api as smf
# df: one row per trial, columns amp, condition, subject (+ item, etc.)
md = smf.mixedlm("amp ~ condition", df, groups=df["subject"],
                 re_formula="~condition").fit()      # random slope + intercept per subject
print(md.summary())
```

Crossed random effects (subjects × items) and the fixed-effect contrast carry the inference; report
the fixed-effect estimate, its CI, and the random-effect structure.

## Effect sizes & bootstrap CIs

A significant p with no effect size is not a finding. Report Cohen's d / Hedges' g (or cluster mass)
**with a CI**; bootstrap when the distribution is unknown:

```python
def boot_ci(x, fn=np.mean, n=10000, seed=42):
    rng = np.random.default_rng(seed)
    bs = [fn(rng.choice(x, size=len(x), replace=True)) for _ in range(n)]
    return np.percentile(bs, [2.5, 97.5])
```

## Choosing the inference

- **Whole grid, no pre-chosen ROI/window** → **cluster-based permutation** (or TFCE) with channel
  adjacency; inference is **cluster-level**, not per-point.
- **A few pre-registered ROIs/windows** → point tests with **FDR/Bonferroni** over the *actual*
  family (assumptions checked); CLR space if the data are compositional (relative power).
- **Trial-level / nested / repeated** → **LMM**, not subject-averaged tests.
- **Small n** → permutation / sign / Wilcoxon, never asserted normality.
- Always report **effect sizes + CIs** (bootstrap if non-parametric) and the exact test, tail, and
  pairing.

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| "Cz at 320 ms is significant" from a cluster test | cluster-level read as point inference | report the cluster + its extent only |
| One hand-picked cluster-forming threshold | arbitrary threshold drives the result | justify it, or use TFCE |
| n=12, "data are normal", t-test | normality not establishable at small n | permutation / Wilcoxon |
| FDR over "5 bands" but 64 channels tested too | correction family undercounted | correct over the full family, or cluster permute |
| Per-point Bonferroni/FDR across the time course | independence assumption fails (adjacency) | cluster permutation / TFCE with adjacency |
| One value per subject from many trials | trial variance averaged away / pseudo-replication | linear mixed model |
| Significant p, no effect size | not actually a quantified finding | report d/g + bootstrap CI |
| Tail chosen after seeing the sign | post-hoc one-tailed test | pre-specify tail; two-tailed if unsure |
