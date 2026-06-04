# Decoding / MVPA — deeper recipes & decisions

Companion to `mne-decoding/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`epochs`) and run inside `mne_run_code` (where `mne`, `np`, `plt`, and loaded objects are
pre-bound). Decoding needs **scikit-learn**.

## Sliding vs generalizing estimator

- **SlidingEstimator** — fits one classifier **per time point** and scores it at the same time
  point. Output is decodability-vs-time (the diagonal). Good default for "when does the brain
  distinguish A from B?".
  `SlidingEstimator(clf, scoring="roc_auc", n_jobs=-1)` → `cross_val_multiscore(sl, X, y, cv=5)`.
- **GeneralizingEstimator** — trains at time *t*, tests at **all** times *t'*; output is a
  train × test matrix. The **diagonal** equals the SlidingEstimator result; the **off-diagonal**
  asks whether a code trained early still classifies later (generalization).
  `GeneralizingEstimator(clf, scoring="roc_auc", n_jobs=-1)`.
- **Reading the matrix**: a square/blocky off-diagonal suggests a *sustained, stable* code; a
  thin diagonal suggests a *sequence of transient* codes. Off-diagonal generalization ≠ proof of
  active reactivation — a slow evoked component can produce it too.

## Leakage-free pipelines (the central discipline)

Every transform that learns parameters from data — scaling, PCA, feature selection, CSP, baseline
z-scoring — must be `fit` on **training trials only**, inside each CV fold. The only safe way is to
put them in an sklearn `Pipeline` and pass the *pipeline* to the estimator / `cross_val_*`:

```python
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest
from sklearn.linear_model import LogisticRegression
from mne.decoding import Vectorizer, cross_val_multiscore, SlidingEstimator
clf = make_pipeline(StandardScaler(), SelectKBest(k=50), LogisticRegression(max_iter=1000))
```

For a **single feature vector per trial** (e.g. mean over a window, all sensors), flatten with
`Vectorizer` and cross-validate with a plain sklearn CV:

```python
from mne.decoding import Scaler
clf = make_pipeline(Scaler(epochs.info), Vectorizer(), LogisticRegression(max_iter=1000))
```

`mne.decoding.Scaler` standardizes per channel-type using `info` (correct for mixed mag/grad/EEG);
it still fits inside the fold. **Never** `StandardScaler().fit(X_all)` before CV — that is leakage.

## Cross-validation structure

- **Trial-level CV on one subject** — `StratifiedKFold` stratified by class; fine for within-subject
  decodability.
- **Pooled multi-subject data** — use **leave-one-subject-out** (`GroupKFold`/`LeaveOneGroupOut`
  with `groups=subject_id`). Plain `KFold` on pooled trials lets trials of the *same* subject sit in
  both train and test, so the classifier decodes **subject identity / session drift**, not the
  condition — accuracy is inflated and the claim is invalid.
- **Imbalance** — stratify folds; prefer **ROC-AUC** or **balanced accuracy** as `scoring`.

## CSP for oscillatory BCI

Common Spatial Patterns finds spatial filters maximizing variance (band power) difference between
two classes — the workhorse for motor-imagery BCI. Band-pass first (e.g. mu/beta 8–30 Hz), then:

```python
from mne.decoding import CSP
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
clf = make_pipeline(CSP(n_components=4, reg=None, log=True), LinearDiscriminantAnalysis())
```

CSP **learns filters from data** ⇒ it must live inside the CV pipeline (above), never fit on all
trials first. For multiclass, CSP extends via one-vs-rest.

## RSA (representational similarity analysis)

Instead of classifying, compare **representational geometry**: build a neural RDM (1 − correlation,
or cross-validated Mahalanobis / crossnobis, between condition patterns) and correlate it with a
model RDM (Spearman). Crossnobis distances are cross-validated ⇒ unbiased (expected 0 under the
null), unlike raw correlation distance. Significance via **permutation of condition labels**.

## Encoding / receptive-field (mTRF)

The encoding direction: predict the continuous **neural response** from a stimulus feature
(envelope, spectrogram) via a regularized lag model — the temporal receptive field. Use
`mne.decoding.ReceptiveField` with ridge (`estimator=`λ); evaluate by **r** on held-out data, tune λ
by nested CV. Backward (decoding/stimulus-reconstruction) models are higher-variance — keep the
train/test split clean exactly as above.

## Establishing chance & inference across time

- **Chance** = **label permutation**, not 1/n. Shuffle `y`, re-run the *whole* CV pipeline many
  times, build the null. `sklearn.model_selection.permutation_test_score` does this for one window.
- **Across time** — a score per time point is many tests; use **cluster-based permutation** of
  scores-vs-chance (sign-flip / label-shuffle) for family-wise control. Inference is **cluster-level**,
  not per-time-point: you may say "decoding exceeds chance in this cluster", not "at exactly 184 ms".

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| `StandardScaler/PCA/CSP.fit(X_all)` then CV | **data leakage** | put transforms in a Pipeline, fit in-fold |
| "Above chance (>50%)" with imbalance | nominal chance wrong | label-permutation chance; ROC-AUC |
| Raw accuracy on 80/20 classes | imbalance inflates accuracy | balanced accuracy / ROC-AUC; report n/class |
| Pooled-subject KFold, high accuracy | subject identity leaks across folds | leave-one-subject-out (GroupKFold) |
| "Maintained representation" off-diagonal | over-read generalization | pre-plan; consider sustained component |
| Significant at 184 ms (per-time tests) | multiple comparisons across time | cluster-based permutation; cluster-level claim |
| RSA with raw correlation distance | biased (non-zero null) | crossnobis / cross-validated distance |
