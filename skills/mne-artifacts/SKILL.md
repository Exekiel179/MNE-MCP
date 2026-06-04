---
name: mne-artifacts
description: >
  Artifact correction of EEG/MEG/iEEG via MNE — ICA (fastica/infomax/picard), SSP projections,
  autoreject, and regression-based EOG removal — to remove ocular (blink/saccade), cardiac (ECG),
  muscle, and line-noise contamination while preserving neural signal — run SKEPTICALLY: grill the
  artifact inventory and decontamination plan before fitting, execute with best-practice defaults,
  then submit the cleaned data to methodology critique. Use for blink/eye-movement/heartbeat/muscle
  removal, ICA component selection, ICLabel automatic labelling, SSP, and automated epoch repair.
  Triggers: ICA, 伪迹, 去伪迹, artifact removal, 眼电, 心电, EOG, ECG, 肌电, blink, saccade,
  眨眼, 眼动, 去眼电, SSP, autoreject, ICLabel, picard, infomax, component rejection, 成分剔除.
---

# MNE Artifact Correction (grill → analyze → critic)

Artifact correction of neurophysiology data via the MNE MCP server. This skill is **skeptical by
design**: a bad decontamination *runs without any error* — ICA happily over-fits, removes neural
signal, or is fit on the wrong data — so the discipline is to **grill the artifact inventory before
cleaning and critique the cleaned data before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety (ICA convergence, units); and
> `mne-methodology-critic` for Phase 3. Loaded objects persist in one MNE session.

---

## PHASE 1 — GRILL (before cleaning anything)

Do **not** fit ICA or reject anything until these are answered. If the user can't answer one, propose
a sensible default **and explicitly flag the open risk** — never silently choose.

**Artifact inventory & claim**
- Which artifacts are actually present — **blink, saccade, ECG, muscle, line noise**, electrode pop,
  drift? (Look first; don't assume.) Do EOG/ECG reference channels exist?
- What downstream analysis is this for, and could cleaning **bias the comparison**? (e.g. removing an
  ECG component differently across groups)

**The two questions that decide validity**
- **Is ICA fit on a ~1 Hz high-passed COPY?** ICA assumes stationarity; slow drifts make components
  unstable. Fit on a 1 Hz high-passed copy, then **apply the unmixing to the 0.1 Hz data** you
  actually analyze. (This is the single most common fatal error here.)
- **Is `n_components` ≤ the data rank?** Asking for more components than the rank yields unstable,
  uninterpretable components. ⚠️ An **average reference** and each **interpolated channel** REDUCE
  rank by ≥1 — count them.

**Identification & selection**
- How are artifact components identified — **objectively** (EOG/ECG correlation, ICLabel) or **by
  eye**? Subjective selection is not reproducible.
- How many components removed, and is the rule **fixed across subjects** (same threshold/labeller),
  or hand-picked per subject?

**Bias & reporting (pin this down NOW)**
- Will the **artifact rate differ across groups/conditions** (clinical vs control blink rates;
  high- vs low-load muscle)? Differential cleaning manufactures effects.
- Over-cleaning: how do you guard against removing **neural** signal (e.g. an occipital alpha or a
  genuine frontal component)?
- Plan to report **n components removed**, the labelling method, and per-group rejection rates.

---

## PHASE 2 — ANALYZE

1. **Capability + look first.** `mne_check_status`; `mne_plot_raw` and **read the PNG** — confirm
   which artifacts are present (blinks, heartbeat, muscle bursts, line noise) before deciding.
2. **High-pass a copy for fitting** (do *not* high-pass the data you analyze):

   ```python
   raw_for_ica = raw.copy().filter(l_freq=1.0, h_freq=None)   # ICA-only copy
   ```

3. **Fit ICA on the copy**, with `n_components` ≤ rank. Use the structured tool, or `mne_run_code`
   when you need the copy / rank control: `mne_fit_ica(name="raw_for_ica", n_components=0.99,
   method="picard")`. (`fastica`/`infomax`/`picard`; pass `random_state` for reproducibility.)
4. **Plot and read the components.** `mne_plot_ica_components` (scalp topographies) and
   `mne_plot_ica_sources` (time courses) — **read both PNGs**: blink = frontal topo + slow square
   waves; ECG = ~1 Hz periodic spikes; muscle = high-freq edge/temporal; line = narrowband.
5. **Identify objectively, not by eye** (via `mne_run_code`): correlate with EOG/ECG channels, or
   label with ICLabel:

   ```python
   eog_idx, _ = ica.find_bads_eog(raw)        # needs an EOG channel (or by name)
   ecg_idx, _ = ica.find_bads_ecg(raw, method="correlation")
   ica.exclude = sorted(set(eog_idx + ecg_idx))
   # automatic labelling (extra deps): from mne_icalabel import label_components
   #   labels = label_components(raw_for_ica, ica, method="iclabel")
   ```

6. **Exclude and apply to the 0.1 Hz data** (not the high-passed copy):
   `mne_apply_ica(ica_name="ica", inst_name="raw", exclude="0,3")`.
7. **Alternatives where appropriate** — **SSP** (project out a blink/ECG subspace), or **autoreject**
   (automated per-channel epoch thresholds / interpolation). Both via `mne_run_code` and **need extra
   deps from the `[full]` extra** (`autoreject`, `mne-icalabel`).
8. **Archive** the equivalent code + figures, and **report n components removed** (the `mne-analyst`
   archiving convention).

Best-practice reminders: fit on the 1 Hz copy, apply to the 0.1 Hz data; count avg-ref/interp toward
rank; use a **fixed, objective** selection rule across subjects; report per-group rejection.

---

## PHASE 3 — CRITIC (before believing the cleaned data)

Hand the plan + cleaned data to **`mne-methodology-critic`** (invoke the skill, or dispatch it as a
subagent with `references/methodology-checklist.md`). For artifact work it will specifically check:

- ICA fit on **non-high-passed** data (unstable components);
- `n_components` **> data rank** (avg-ref / interpolated channels reduce rank by ≥1);
- **subjective / inconsistent** component selection vs objective (EOG/ECG/ICLabel);
- **over-cleaning** that removes neural signal;
- **differential rejection** between conditions/groups manufacturing an effect;
- **not reporting** the number of components removed or the labelling method.

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating conclusions.

See `references/artifact-methods.md` for deeper recipes (ICA prerequisites & rank, fastica/infomax/
picard, component identification, ICLabel, SSP, autoreject, and regression EOG).
