---
name: mne-decoding
description: >
  Decoding / MVPA & BCI analysis of EEG/MEG/iEEG via MNE — time-resolved decoding (a classifier per
  time point), temporal generalization (train-time × test-time), CSP for oscillatory BCI,
  representational similarity analysis (RSA), and encoding/receptive-field models (mTRF) — run
  SKEPTICALLY: grill the design and the cross-validation before fitting, execute with leakage-free
  pipelines, then submit the result to methodology critique. Use for classifying conditions from
  brain activity, time courses of decodability, maintenance/reactivation claims, BCI feature
  extraction, and representational geometry. Triggers: decoding, 解码, MVPA, 多变量模式分析,
  classification, 分类, temporal generalization, 时间泛化, CSP, RSA, 表征相似性, receptive field,
  mTRF, BCI, 脑机接口, SlidingEstimator, classifier, ROC-AUC, leave-one-subject-out.
---

# MNE Decoding / MVPA & BCI (grill → analyze → critic)

Multivariate decoding of neurophysiology data via the MNE MCP server. This skill is **skeptical by
design**: the most damaging decoding mistakes — **data leakage** and a **wrongly assumed chance
level** — produce a clean, plausible accuracy curve *without any error*, so the discipline is to
**grill the cross-validation before fitting and critique before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety; `mne-methodology-critic` for
> Phase 3. Loaded objects persist in one MNE session. Decoding needs **scikit-learn**.

---

## PHASE 1 — GRILL (before fitting anything)

Do **not** fit a classifier until these are answered. If the user can't answer one, propose a
sensible default **and explicitly flag the open risk** — never silently choose.

**What is being decoded**
- Which two (or more) conditions / labels, and what is the scientific *claim* tied to decodability?
- **Class balance and sizes** — n trials per class, per subject? (Imbalance silently inflates
  accuracy and breaks the nominal chance level.)
- Feature space: sensors × time? band power? source space? What is the classifier actually seeing?

**The two questions that decide validity**
- **Cross-validation structure.** Subject-level (**leave-one-subject-out**) or trial-level? If
  trial-level on pooled multi-subject data, do trials from one subject leak across train/test folds
  (⇒ identity decoding, inflated)? Is the split stratified by class? (This + leakage are the two
  fatal errors here.)
- **Is every transform fit INSIDE the fold?** Scaling, feature selection, ICA, PCA, even baseline
  z-scoring must be `fit` on **training data only** within each CV fold (use an sklearn `Pipeline`).
  Anything fit on the full dataset before CV = **leakage** ⇒ optimistic, invalid.

**Inference plan (pin this down NOW, not after seeing results)**
- **Chance level** — established by **label permutation** (shuffle labels, re-decode many times), not
  the nominal 1/n_classes. Imbalance and small n move true chance off 1/n.
- **Multiple comparisons across time** — a classifier per time point ⇒ many tests; plan a
  **cluster-based permutation** test of scores-vs-chance, not per-time-point thresholding.
- **Temporal-generalization claims.** Will off-diagonal generalization be read as
  *maintenance / reactivation* of a representation? That is a strong claim — state it in advance and
  guard it (it can also reflect a slow/sustained component, not reactivation).
- Metric: ROC-AUC / balanced accuracy (imbalance-robust) over raw accuracy?

---

## PHASE 2 — ANALYZE

1. **Capability + look first.** `mne_check_status` (confirm scikit-learn present); inspect class
   counts (`epochs["condA"]`, `epochs["condB"]`) — balance and totals decide metric and CV.
2. **Time-resolved decoding (quick path).** `mne_decode(cond_a, cond_b, scoring="roc_auc", cv=5)`
   returns mean/peak AUC + a scores-vs-time plot. **Read the PNG** — where does AUC rise above chance?
3. **Custom path (full control via `mne_run_code`).** Build a leakage-free `Pipeline` and slide it
   over time, cross-validated:

   ```python
   from sklearn.pipeline import make_pipeline
   from sklearn.preprocessing import StandardScaler
   from sklearn.linear_model import LogisticRegression
   from mne.decoding import SlidingEstimator, Scaler, Vectorizer, cross_val_multiscore
   X = epochs.get_data();  y = epochs.events[:, 2]          # transforms fit INSIDE folds
   clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
   sl  = SlidingEstimator(clf, scoring="roc_auc", n_jobs=-1)
   scores = cross_val_multiscore(sl, X, y, cv=5).mean(0)    # (n_times,)
   ```

4. **Temporal generalization.** Swap `SlidingEstimator` → `GeneralizingEstimator`; the result is a
   train-time × test-time matrix. Read the **diagonal** for decodability; **off-diagonal** only for
   maintenance/reactivation, and only if pre-planned.
5. **CSP for oscillatory BCI.** Band-pass first, then `mne.decoding.CSP` inside the pipeline:

   ```python
   from mne.decoding import CSP
   clf = make_pipeline(CSP(n_components=4), LogisticRegression(max_iter=1000))
   ```

6. **Establish chance by permutation** (not 1/n): shuffle `y` many times, re-run CV, build the null
   distribution of scores; compare the observed curve to it (`sklearn.model_selection.permutation_test_score`
   for a single window). Then **cluster-test** scores-vs-chance across time.
7. **Archive** the equivalent code + figures (the `mne-analyst` archiving convention).

Best-practice reminders: ROC-AUC / balanced accuracy under imbalance; `Vectorizer` to flatten
features for plain sklearn estimators; report per-class n and the CV scheme explicitly.

---

## PHASE 3 — CRITIC (before believing the result)

Hand the design + result to **`mne-methodology-critic`** (invoke the skill, or dispatch it as a
subagent with `references/methodology-checklist.md`). For decoding work it will specifically check:

- **data leakage** — any transform fit on the full dataset before CV (*FAIL*);
- **nominal chance vs label-permutation** chance level;
- **class imbalance** — raw accuracy vs balanced accuracy / ROC-AUC, class sizes reported;
- **trial-level CV leaking** trials of one subject across folds (vs leave-one-subject-out);
- **temporal-generalization off-diagonal** over-interpretation (maintenance / reactivation);
- **multiple comparisons across time** — cluster-based permutation vs per-time-point thresholding.

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating conclusions.

See `references/decoding-methods.md` for deeper recipes (sliding vs generalizing estimators,
leakage-free pipelines, CSP, RSA, mTRF encoding, and permutation/cluster inference).
