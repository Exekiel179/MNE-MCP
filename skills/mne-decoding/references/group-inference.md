# Group decoding inference

`mne_decoding_group_test(params)` tests independent-subject mean decoding curves or
temporal-generalization matrices against an explicit reference using MNE sign flips.
It does not shuffle trial labels, refit classifiers, or infer population prevalence.

## Choose the correct observation

Run `mne_decode` independently per subject with the same predeclared analysis and unique
output names, then supply one mean result per subject. Keep each accompanying `_details`
object. Never supply `_folds`, multiple runs of one subject, pooled-subject CV folds, or
duplicated scores as independent subjects. Reusing training subjects across held-out
subject folds does not create independent subject estimates for this test.

The caller must supply unique `subject_ids` and `independent_subjects=true`. This is an
explicit design confirmation, not proof that data are independent. Verify source data,
subject identity, condition semantics, preprocessing, channels/features, and the analysis
plan before confirming. Matching numeric event codes alone does not establish matching
condition semantics. The tool checks shapes, times, metric, method, classifier settings,
numeric labels, fit warnings and simple aliases; it cannot detect copied participant data.

Only ROC AUC and balanced accuracy are supported. `null_value` is required; 0.5 is a
theoretical reference, not an empirical label-permutation null. Sign flipping assumes
independent subject effects with symmetric distributions under the null. Bounded decoding
metrics and small samples can violate this approximation. A group-mean rejection against
0.5 does not establish prevalence or that every subject carries decodable information.
Use a design-appropriate label-permutation/hierarchical procedure through `mne_run_code`
when these assumptions or the desired inference do not fit this test.

## Parameters and examples

`score_names` and `subject_ids` must be equally sized unique lists (at least two).
`name="decoding_stats"` stores a result dictionary. `n_permutations=1024` (2..100000),
`seed=97`, `alpha=0.05`, `plot=true`. Tiny permutation counts are for software smoke tests,
not scientific reporting. The result reports the actual null sample count; MNE may perform
an exact test when requested permutations exhaust the finite sign-flip space. No extra
manual '+1' correction should be applied to MNE's returned p values.

Two-sided max-t FWER over every time point, or every train/test cell:

```json
{
  "params": {
    "score_names":["decode_s01","decode_s02","decode_s03","decode_s04"],
    "subject_ids":["s01","s02","s03","s04"],
    "independent_subjects":true, "null_value":0.5,
    "correction":"max_t", "tail":0, "n_permutations":5000,
    "name":"group_max_t", "plot":true
  }
}
```

The four-subject list illustrates syntax only: the exact permutation space is too small
for a two-sided 0.05 rejection. More requested permutations cannot fix too few subjects.

Cluster-mass FWER, same inputs but predeclared positive direction:

```json
{
  "params": {
    "score_names":["decode_s01","decode_s02","decode_s03","decode_s04"],
    "subject_ids":["s01","s02","s03","s04"],
    "independent_subjects":true, "null_value":0.5,
    "correction":"cluster", "tail":1, "threshold":null,
    "n_permutations":5000, "name":"group_cluster"
  }
}
```

`threshold` is a cluster-forming **t statistic**, not a p value. Null uses MNE's p=0.05
forming threshold (separate from corrected `alpha`). An explicit threshold must be positive
for tail 0/+1, negative for tail -1. Max-t currently accepts tail 0 only, without threshold.
For a negative-direction cluster hypothesis, set `tail=-1` and e.g. `threshold=-2.5`;
justify the direction and threshold before viewing results.

Sliding curves use neighboring time samples; generalization uses a two-dimensional
train-time/test-time lattice, not a one-dimensional flattened chain. Correction covers the
entire supplied grid, not other windows, metrics, channel sets or contrasts tried separately.
Do not crop a result post hoc to reduce the correction family. Custom adjacency, TFCE,
joint correction across multiple contrasts, nested tuning and single-subject label shuffling
remain explicit `mne_run_code` workflows.

## Results and reporting

Inspect `name` with `mne_run_code` or `mne_describe`:

- `statistic`, `mean_effect`: original curve/matrix shape; effect is group mean minus reference.
- Max-t: `p_values` are pointwise FWER-adjusted values over the full supplied grid.
- Cluster: `p_values=null`; `clusters` contain flattened C-order point indices, and
  `cluster_p_values` hold cluster-level corrected values. Use `np.unravel_index(indices,
  result['statistic'].shape)` to recover axes. No cluster means empty clusters and empty H0,
  not a test crash or evidence of equivalence.
- `significant_mask`: corrected points for max-t, or union of significant cluster extents.
  Cluster masks do not localize precise effect onset, offset or individual significant cells.
- `H0`, `null_samples`, `family_size`, `n_subjects`, `parameters`, `times`, `score_axes`,
  `scoring`, `inference_level`, `warnings`: audit metadata. Generated MNE code reproduces
  statistical arrays and null distribution, not every report/plot field.

Report independent-subject n, metric/reference, test direction, correction family, seed,
requested/actual permutations, cluster threshold if relevant, effect magnitude and assumptions.
This tool does not compute confidence intervals. Zero between-subject variance, nonfinite
scores, incompatible grids, and unresolved fit warnings stop before replacing the prior result.
Repeated testing under different choices is model selection and is not covered by this correction.

Sources: [MNE permutation_t_test](https://mne.tools/stable/generated/mne.stats.permutation_t_test.html),
[MNE permutation_cluster_1samp_test](https://mne.tools/stable/generated/mne.stats.permutation_cluster_1samp_test.html).
