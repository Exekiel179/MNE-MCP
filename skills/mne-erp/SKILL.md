---
name: mne-erp
description: >
  ERP / ERF (evoked-response) analysis of EEG/MEG/iEEG via MNE — event extraction, epoching with
  baseline + peak-to-peak rejection, per-condition averaging, difference waves, peak vs mean
  amplitude, component latency (jackknife for groups), GFP, and condition contrasts — run
  SKEPTICALLY: grill the design and component identity before averaging, execute with best-practice
  defaults, then submit the result to methodology critique. Use for evoked responses, named
  components (N1/P1/N170/MMN/N400/P300), difference waves, peak amplitude/latency, and
  group/condition ERP comparisons. Triggers: ERP, ERF, 事件相关电位, 诱发响应, 叠加平均, 差异波,
  evoked, N1, P1, P300, N170, N400, MMN, peak amplitude, 峰值幅度, latency, 潜伏期, difference wave,
  GFP, component, 成分, condition contrast.
---

# MNE ERP / ERF Analysis (grill → analyze → critic)

Evoked-response analysis of neurophysiology data via the MNE MCP server. This skill is **skeptical by
design**: most ERP mistakes (peak-picking a window after seeing the grand average, a high-pass that
shifts latency, calling an occipital 100 ms deflection "N1") run *without any error* — so the
discipline is to **grill the component identity and measurement plan before averaging, and critique
before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety; `mne-methodology-critic` for
> Phase 3. Loaded objects persist in one MNE session.

---

## PHASE 1 — GRILL (before averaging anything)

Do **not** average until these are answered. If the user can't answer one, propose a sensible
default **and explicitly flag the open risk** — never silently choose.

**Design & claim**
- What is the hypothesis, and what is the *comparison*? (condition × condition, group × group,
  pre × post)
- Within- or between-subject? Paired or independent? n per cell?
- Confirmatory (component + window + electrodes pre-specified) or exploratory (whole-head, corrected)?

**The questions that decide validity**
- **Which components, and what are their EXPECTED latency, topography, AND stimulus modality?**
  Latency/polarity/topography must match the named component *for that modality*. ⚠️ auditory N1 is
  **fronto-central** (~100 ms); visual N1 is **occipito-temporal ~150–200 ms** — a **~100 ms
  occipital** deflection in vision is most likely **P1**, not N1. A topography/modality mismatch
  means the component is misnamed. (This is the single most common identity error here.)
- **Is the measurement window + electrode set PRE-SPECIFIED?** A mean/peak amplitude measured in a
  window/channel chosen *after* seeing this dataset's grand average is **circular (double-dipping)**.
  Pin the window and ROI down NOW, from prior literature, not from the data.

**Data & parameters**
- Baseline window (length + placement)? Baseline noise propagates into every component.
- **Filter.** ⚠️ high-pass **> 0.3 Hz distorts slow components and shifts/inverts apparent latency
  and polarity** (CDA, LPP, P300, CNV especially); low-pass smooths and delays peaks. State the band.
- Epoching: `tmin/tmax`, peak-to-peak **rejection threshold + its justification**.
- Reference, montage, channel selection, units.

**Inference plan (pin this down NOW, not after seeing results)**
- **Trial counts balanced across conditions?** Unequal trials → unequal ERP SNR → spurious
  amplitude/latency differences. Will rejection differ *between* conditions/groups (differential
  rejection fabricates effects)?
- **Mean or peak amplitude?** Mean-in-window is more robust; peak is biased by noise and by window
  length. **Single-subject peak latency is noisy → plan a jackknife** (group latency) with the
  adjusted *t*.
- Multiple comparisons across **components × electrodes × conditions** — which correction, and is
  its independence assumption valid? (neighbouring channels/times are correlated → consider
  cluster-based permutation rather than per-channel tests)

---

## PHASE 2 — ANALYZE

1. **Capability + look first.** `mne_check_status`; confirm the epoching inputs (events, montage,
   units) before averaging.
2. **Get events.** `mne_find_events` (trigger channel) or `mne_events_from_annotations`
   (EDF/BrainVision/EEGLAB). Verify the **event codes** map to the intended conditions.
3. **Epoch** with a justified baseline and peak-to-peak rejection, naming the conditions:

   ```text
   mne_make_epochs(event_id="target:1,standard:2", tmin=-0.2, tmax=0.8,
                   baseline="default", reject_eeg=100e-6)   # (None,0); 100 µV p2p
   ```
   Inspect with `mne_plot_epochs_image` and **read the PNG** (single-trial consistency, latency
   jitter, residual artifact).
4. **Average per condition — use DISTINCT evoked names.** ⚠️ `mne_average_evoked` defaults
   `evoked_name="evoked"`; calling it twice **overwrites** the first condition. Name each one:

   ```text
   mne_average_evoked(condition="target",   evoked_name="evk_target")
   mne_average_evoked(condition="standard", evoked_name="evk_standard")
   ```
5. **Difference wave** (the contrast carries the hypothesis), via `mne_run_code`:

   ```python
   evk_diff = mne.combine_evoked([evk_target, evk_standard], weights=[1, -1])
   evk_diff.comment = "target - standard"
   ```
6. **Plot at the PRE-SPECIFIED times**, then read the PNGs: `mne_plot_evoked(name="evk_diff",
   style="joint")` and `mne_plot_topomap(name="evk_diff", times="0.3")` (your registered latency,
   **not** `"peaks"` on this data).
7. **Measure in the pre-registered window** (mean is robust; peak/latency via `mne_run_code`):

   ```python
   # MEAN amplitude in a pre-specified window over a pre-specified ROI
   roi = ["Pz", "CPz", "POz"]; tmin, tmax = 0.30, 0.50           # registered, not picked here
   ev = evk_diff.copy().pick(roi)
   m = ev.get_data(tmin=tmin, tmax=tmax).mean()                  # volts
   # PEAK amplitude + latency (note: single-subject peak latency is noisy → jackknife for groups)
   ch, lat, amp = evk_diff.get_peak(tmin=tmin, tmax=tmax, mode="abs", return_amplitude=True)
   gfp = evk_diff.data.std(axis=0)                               # global field power over time
   print(f"mean={m*1e6:.2f} µV | peak={amp*1e6:.2f} µV @ {lat*1e3:.0f} ms ({ch})")
   ```
8. **Archive** the equivalent code + figures (the `mne-analyst` archiving convention).

Best-practice reminders: high-pass ≤ 0.1–0.3 Hz + line-notch before epoching; equalize trial counts
(`epochs.equalize_event_counts`) before comparing; report **per-condition trial counts and rejection
rate**; measure where you pre-registered, not where the peak landed.

---

## PHASE 3 — CRITIC (before believing the result)

Hand the design + result to **`mne-methodology-critic`** (invoke the skill, or dispatch it as a
subagent with `references/methodology-checklist.md`). For ERP/ERF work it will specifically check:

- **measurement window / peak channel chosen post-hoc** (circular / double-dipping);
- **component topography vs stimulus modality** mismatch (mislabelled N1/P1, etc.);
- **high-pass filter** distorting slow-component latency/polarity;
- **baseline** window length/placement and propagated noise;
- **unequal trial counts → SNR** and differential rejection between conditions;
- **multiple comparisons** across components × electrodes × conditions;
- **single-subject peak-latency noise** (use jackknife for group latency).

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating conclusions.

See `references/erp-methods.md` for deeper recipes (event handling, difference waves, mean vs peak
vs jackknife latency, GFP, component windows by modality, and ERP inference choices).
