# Structured decoding

Use `mne_decode` for binary sensor-space sliding or temporal-generalization decoding.
Use `mne_decoding_group_test` for independent-subject sign-flip inference; read
[group-inference.md](group-inference.md) first. Use `mne_run_code` for multiclass, CSP, RSA,
encoding, custom estimators, nested tuning or within-subject label permutations.
Do not imply those methods are built into `mne_decode`.

## Parameters

| Parameter | Meaning |
|---|---|
| `epochs_name`, `name` | Input Epochs and output prefix; defaults `epochs`, `decoding` |
| `cond_a`, `cond_b` | Two distinct, disjoint event selections, or omit both for binary input |
| `method` | `sliding` (default) or `generalizing` |
| `scoring` | sklearn scorer name, default `roc_auc`; consider `balanced_accuracy` for imbalance |
| `cv_strategy` | `stratified`, `stratified_group`, `leave_one_group_out` |
| `cv` | Integer >=2; default 5; LOGO uses the number of groups instead |
| `groups` | Homogeneous integer or nonempty string labels for ALL retained input epochs |
| `picks` | Channel type, name list, or zero-based index list; default data channels; bads excluded |
| `tmin`, `tmax` | Optional inclusive time window in seconds, within the epoch range; crops a copy |
| `C` | Positive inverse regularization strength for logistic regression; default 1.0 |
| `class_weight` | `null` or `balanced`; weights computed from each training fold |
| `max_iter` | Positive integer optimization limit; default 1000 |
| `shuffle`, `random_state` | Default false and 97; LOGO does not allow shuffle |
| `plot` | Default true; false avoids figure generation |

Groups align with the current Epochs object after rejected trials have been removed, but
before `cond_a/cond_b` filtering. Use `epochs.selection` to align source trial metadata after
rejection. Passing groups with ordinary stratified CV is rejected, not silently ignored.
Every train and test fold must contain both classes. Do not drop grouping to make a failed
split pass: reconsider the experimental design, label distribution or fold count.

## Calls

Single-subject, independent trials:

```json
{"cond_a":"target","cond_b":"standard","cv":5,"scoring":"roc_auc","plot":true}
```

Grouped temporal generalization, a minimal example with 12 retained epochs and both
classes represented within each group (replace labels with actual subject/run metadata):

```json
{
  "cond_a":"target", "cond_b":"standard", "name":"generalization",
  "method":"generalizing", "cv_strategy":"leave_one_group_out",
  "groups":["s1","s1","s1","s1","s2","s2","s2","s2","s3","s3","s3","s3"],
  "tmin":0.0, "tmax":0.5, "C":0.5, "class_weight":"balanced", "plot":true
}
```

Preplanned window with explicit channels and reproducible shuffled trial folds:

```json
{
  "cond_a":"target", "cond_b":"standard", "picks":["Cz","Pz"],
  "cv":3, "shuffle":true, "random_state":97,
  "tmin":0.1, "tmax":0.3, "max_iter":2000, "plot":false
}
```

## Inspect and interpret

- `name`: unweighted mean across folds, shape `(time,)` or `(train_time, test_time)`.
- `name_folds`: per-fold scores with a leading fold axis. Unequal test sizes are not pooled.
- `name_details`: actual times, channel order, event codes/counts, positive class code,
  selected input rows, aligned groups, train/test indices relative to selected rows,
  per-fold class counts, classifier options, scoring axes and fit warnings.
- Generated code reproduces selection, crop, fold indices and scoring without mutating input.

Positive class is the higher numeric event code, not necessarily `cond_b`; inspect diagnostics
before interpreting directional metrics. StandardScaler and logistic regression fit inside
each training fold. `balanced` class weights do not balance the held-out test set.
Inspect fit warnings; a nonconverged classifier needs investigation even if scores are finite.

Generalization has quadratic time-grid scoring/output cost. Choose a scientifically justified
time window before fitting. Do not decimate without considering aliasing, or treat a timeout as
cancellation: the shared session may still be busy.

Changing `C`, channels, windows or preprocessing after seeing CV scores is model selection.
Use nested CV or an untouched test set to evaluate a tuned procedure. Overlapping CV folds are
not independent subjects, and 0.5 reference lines are not significance thresholds. Permutation
schemes must respect exchangeability; temporal-generalization inference must account for both axes.

Upstream: [MNE GeneralizingEstimator](https://mne.tools/stable/generated/mne.decoding.GeneralizingEstimator.html),
[sklearn LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).
