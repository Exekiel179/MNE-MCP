# Artifact correction — deeper recipes & decisions

Companion to `mne-artifacts/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`raw`, `epochs`, `ica`) and run inside `mne_run_code` (where `mne`, `np`, `plt`, and loaded objects
are pre-bound). The structured tools `mne_fit_ica`, `mne_plot_ica_components`,
`mne_plot_ica_sources`, and `mne_apply_ica` wrap the common path; drop to `mne_run_code` for the
high-passed copy, rank control, objective identification, ICLabel, SSP, and autoreject.

## ICA prerequisites — the high-passed copy and the rank

ICA assumes the sources are (roughly) stationary. Low-frequency drift violates this and yields
unstable, non-reproducible components. The fix is a two-object workflow:

```python
raw_for_ica = raw.copy().filter(l_freq=1.0, h_freq=None)   # fit on THIS
ica.fit(raw_for_ica)
ica.apply(raw)                                              # apply unmixing to the 0.1 Hz data
```

**Rank determines the maximum number of components.** Requesting more than the data rank produces
degenerate components. Two operations silently reduce rank, and you must subtract them:

- **Average reference** → rank − 1 (one linear constraint).
- **Each interpolated bad channel** → rank − 1 (it is a linear combination of its neighbours).

So 64 EEG channels, average-referenced, with 2 interpolated channels has rank ≈ 61. Set
`n_components` ≤ that (or pass a variance fraction like `0.99`, or check `mne.compute_rank(raw)`).

## fastica vs infomax vs picard

- **fastica** — fast, the historical default; can be sensitive to initialization.
- **infomax** (esp. *extended* infomax) — handles sub- and super-Gaussian sources; the algorithm
  ICLabel was trained against, so prefer it when you intend to use ICLabel.
- **picard** — modern, fast, well-converging; `fit_params={"extended": True}` approximates extended
  infomax. Good general default.

Always set `random_state` so the decomposition is reproducible across runs and subjects.

## Identifying artifact components — objectively, not by eye

Read the topography **and** the time course **and** the spectrum together:

| Artifact | Topography | Time course | Spectrum |
|---|---|---|---|
| Blink | frontal, symmetric | slow square deflections | low-freq dominated |
| Saccade | frontal, left/right opposite | step at movement | low-freq |
| ECG | broad / diagonal gradient | ~1 Hz periodic QRS spikes | peak near heart rate |
| Muscle | focal, edge/temporal | high-freq bursts | rising toward high freq |
| Line | any | continuous | narrow 50/60 Hz peak |

Make the selection **reproducible** with reference channels or a trained labeller:

```python
eog_idx, eog_scores = ica.find_bads_eog(raw)                 # correlate with EOG (or a frontal ch)
ecg_idx, ecg_scores = ica.find_bads_ecg(raw, method="correlation")
ica.exclude = sorted(set(eog_idx + ecg_idx))
```

**ICLabel** (needs `mne-icalabel`, from the `[full]` extra) labels every component as brain / eye /
heart / muscle / line / channel-noise / other with probabilities — apply a **fixed probability
threshold** so selection is identical across subjects:

```python
from mne_icalabel import label_components
res = label_components(raw_for_ica, ica, method="iclabel")   # infomax-fit ICA
labels, probs = res["labels"], res["y_pred_proba"]
exclude = [i for i, lab in enumerate(labels)
           if lab not in ("brain", "other") and probs[i] > 0.8]
```

## SSP — signal-space projection

SSP builds a small set of projectors from blink/ECG **epochs** and projects that subspace out. It
removes fewer degrees of freedom than ICA and is reproducible, but is less selective. Needs the EOG/
ECG epoch helpers (`[full]` extra for some readers):

```python
eog_epochs = mne.preprocessing.create_eog_epochs(raw)
proj_eog, _ = mne.preprocessing.compute_proj_eog(raw, n_eeg=1, average=True)
raw.add_proj(proj_eog); raw.apply_proj()
```

Report how many projectors were added — each one also reduces rank.

## autoreject — automated epoch repair

`autoreject` (from the `[full]` extra) learns per-channel peak-to-peak thresholds by cross-validation
and either interpolates or drops epochs, replacing arbitrary fixed-µV rejection:

```python
from autoreject import AutoReject
ar = AutoReject(random_state=97)
epochs_clean, log = ar.fit_transform(epochs, return_log=True)   # use it AFTER ICA
```

Report the reject log and the **per-group** drop rate — automated thresholds still differ across
noisier datasets and can drive differential rejection.

## Regression-based EOG removal

When dedicated EOG channels exist, a linear regression of EOG onto each EEG channel subtracts the
ocular projection without an ICA decomposition — fast and deterministic, but assumes a fixed, linear
EOG→EEG transfer and removes any true neural signal correlated with the EOG regressor:

```python
from mne.preprocessing import EOGRegression
model = EOGRegression(picks="eeg", picks_artifact="eog").fit(epochs)
epochs_clean = model.apply(epochs)
```

## Order of operations

Filter (high-pass + line notch) → mark/interpolate bads → **fit ICA on the 1 Hz copy** → identify →
apply to the 0.1 Hz data → epoch → **autoreject** on the cleaned epochs. ICA before autoreject so
ocular/cardiac artifacts don't blow the learned thresholds; autoreject after to catch the residual.

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| ICA fit on the 0.1 Hz analysis data | drift → unstable components | fit on a 1 Hz high-passed copy, apply to 0.1 Hz |
| `n_components=64` on avg-ref + 2 interp | n_components > rank | use ≤ rank (≈61) or a variance fraction |
| "I removed the obvious blink comps" | subjective, irreproducible | find_bads_eog/ecg or ICLabel threshold |
| Hand-picked count per subject | inconsistent across subjects | fixed objective rule for all subjects |
| Clean topomaps but alpha gone | over-cleaning removed neural signal | tighten threshold; verify excluded comps |
| Patients cleaned harder than controls | differential rejection | same rule both groups; report rates |
| No mention of how many comps removed | unreproducible reporting | report n removed + labelling method |
