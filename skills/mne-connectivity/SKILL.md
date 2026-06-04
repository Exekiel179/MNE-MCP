---
name: mne-connectivity
description: >
  Functional connectivity of EEG/MEG/iEEG via MNE — spectral connectivity (coherence, imaginary
  coherence, PLV, PLI, wPLI), time-resolved connectivity, phase-amplitude / cross-frequency coupling
  (PAC), and Granger causality, in sensor or source space — run SKEPTICALLY: grill the design and
  field-spread assumptions before computing, execute with field-spread-robust defaults, then submit
  the result to methodology critique. Use for functional/effective connectivity, network strength,
  seed-based or all-to-all maps, and condition/group connectivity comparisons. Triggers: connectivity,
  连接性, 功能连接, coherence, 相干, PLV, wPLI, PLI, imaginary coherence, 虚部相干, PAC, 跨频耦合,
  phase-amplitude coupling, cross-frequency, Granger, 格兰杰, 脑网络, brain network, seed-based.
---

# MNE Connectivity (grill → analyze → critic)

Functional/effective connectivity of neurophysiology data via the MNE MCP server. This skill is
**skeptical by design**: most connectivity mistakes (volume conduction inflating zero-lag coherence,
trial-count/SNR bias, common-reference artifact) run *without any error* and produce a beautiful
heatmap — so the discipline is to **grill before computing and critique before believing.**

> Companion skills: `mne-mcp-guard` for technical execution safety; `mne-methodology-critic` for
> Phase 3. Loaded objects persist in one MNE session. Connectivity needs the **`[full]`** extra
> (`mne-connectivity`; PAC via `pactools`/`tensorpac`).

---

## PHASE 1 — GRILL (before computing anything)

Do **not** compute connectivity until these are answered. If the user can't answer one, propose a
sensible default **and explicitly flag the open risk** — never silently choose.

**Design & claim**
- What is the hypothesis, and what is the *comparison*? (group × group, condition × condition,
  pre × post) Is the claim **undirected** (coupling) or **directed/effective** (who drives whom)?
- Within- or between-subject? Paired or independent? n per cell?
- Confirmatory (seed/edge/band pre-specified) or exploratory (all-to-all, corrected)?

**The question that decides validity**
- **Which measure, and WHY?** ⚠️ **Volume conduction / field spread** makes a single source appear at
  many sensors with **zero phase lag**, which **inflates coherence and PLV** — they cannot tell true
  coupling from one spread-out source. For sensor-space EEG/MEG, prefer measures that discard the
  zero-lag component: **imaginary coherence, wPLI, or PLI**. (Using coh/PLV to claim genuine sensor
  connectivity without this caveat is the single most common fatal error here.)

**Data & parameters**
- **Sensor or source space?** Anatomical claims ("frontoparietal coupling") need **source space**;
  sensor-space edges are between *electrodes*, not brain regions.
- **Reference?** A common reference (and the average reference) injects a shared signal that **inflates
  apparent connectivity**; consider source space, current-source-density / Laplacian, or a
  reference-robust measure.
- Frequency band(s) and width; epoching length (⇒ low-frequency resolution), rejection threshold.
- For **PAC**: which phase band drives which amplitude band, and over what window?

**Inference plan (pin this down NOW, not after seeing results)**
- **Seed-based or all-to-all?** All-to-all is **n_channels² pairs** → a large multiple-comparison
  family; pre-register the seed/edges or plan a network-level/cluster correction.
- **Are trial counts matched across conditions?** Most connectivity metrics are **trial-count- and
  SNR-biased** — fewer/noisier trials *lowers* estimated connectivity. Match n, or correct.
- For **Granger / directed** measures: **stationarity** and **SNR / pre-whitening** assumptions, and
  sensitivity to differential SNR between the two signals.
- Small n (≲ 15–20)? Then plan **permutation / non-parametric**, not a normality assertion.

---

## PHASE 2 — ANALYZE

1. **Capability + look first.** `mne_check_status` (confirm `mne-connectivity` is importable);
   `mne_plot_psd` and **read the PNG** — connectivity is band-specific, so confirm the band of
   interest actually has power and is line-noise-free.
2. **Pick a field-spread-robust measure** and compute the channel×channel map with `mne_connectivity`
   (returns a heatmap + strongest pairs):

   ```
   mne_connectivity(epochs_name="epochs", method="wpli", fmin=8, fmax=13)   # alpha-band wPLI
   ```
   (`method="imcoh"` / `"pli"` for field-spread-robust; `"coh"`/`"plv"` only with an explicit caveat.)

3. **Advanced / full control** via `mne_run_code` with the `mne_connectivity` library:

   ```python
   from mne_connectivity import spectral_connectivity_epochs
   con = spectral_connectivity_epochs(
       epochs, method=["wpli", "imcoh"], mode="multitaper",
       fmin=8, fmax=13, faverage=True, mt_adaptive=True)
   wpli = con[0].get_data(output="dense")[:, :, 0]      # (n_ch, n_ch) band-averaged
   ```
   Time-resolved: `spectral_connectivity_time(...)` for a per-epoch / sliding estimate.

4. **Phase-amplitude coupling (cross-frequency).** Use `pactools` or `tensorpac` (needs the extra):

   ```python
   from tensorpac import Pac
   p = Pac(idpac=(2, 0, 0), f_pha=(4, 8, 1, 0.5), f_amp=(30, 80, 5, 2))   # MI; theta phase × gamma amp
   pac = p.filterfit(epochs.info["sfreq"], epochs.get_data(picks=ch)[:, 0, :])
   ```
   Always compare against a **surrogate distribution** (shuffle phase) — raw PAC values are biased.

5. **Granger / directed.** Stationarize first (high-pass, possibly difference), match SNR, and
   validate model order; report that stationarity/SNR were checked. Prefer source space for any
   anatomical directional claim.

6. **Match trial counts** across conditions (subsample to the smaller n) before comparing, and
   consider **source space** for any anatomical interpretation. **Archive** the equivalent code +
   figures (the `mne-analyst` archiving convention).

Best-practice reminders: report **per-group rejection rate and retained trial count**; state
sensor-vs-source explicitly; pre-register seed/edges/band or correct over the real pair family.

---

## PHASE 3 — CRITIC (before believing the result)

Hand the design + result to **`mne-methodology-critic`** (invoke the skill, or dispatch it as a
subagent with `references/methodology-checklist.md`). For connectivity work it will specifically check:

- **zero-lag-sensitive measures** (coherence / PLV) used to claim genuine sensor connectivity without
  a volume-conduction caveat (**FAIL**);
- **common-reference / average-reference** inflation of apparent connectivity;
- **trial-count / SNR bias** across conditions (unmatched n fakes a difference);
- **all-to-all multiple comparisons** over channel pairs left uncorrected;
- **Granger / directed** measures without stationarity & SNR checks;
- **sensor-space connectivity interpreted anatomically** (electrode edges ≠ region coupling).

Report its **BLOCK / REVISE / PASS** verdict to the user and act on it before stating conclusions.

See `references/connectivity-methods.md` for deeper recipes (measure selection vs field spread,
spectral_connectivity_epochs, PAC with surrogates, Granger caveats, and source-space connectivity).
