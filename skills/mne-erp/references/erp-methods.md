# ERP / ERF analysis — deeper recipes & decisions

Companion to `mne-erp/SKILL.md`. All snippets assume the MNE MCP session has loaded objects
(`raw`, `epochs`, `evoked`) and run inside `mne_run_code` (where `mne`, `np`, `plt`, and loaded
objects are pre-bound).

## Events: triggers vs annotations

- **Trigger channel** (`mne_find_events`) — TTL/STI codes. Verify the integer codes match the
  protocol; watch for split/merged triggers and a non-zero `min_duration`.
- **Annotations** (`mne_events_from_annotations`) — EDF/BrainVision/EEGLAB. Returns an `event_id`
  *dict mapping description → code*; check that mapping before trusting condition labels.
- Name conditions explicitly: `event_id="target:1,standard:2"`. Confirm trial counts per code
  *before* averaging — a typo in a code silently averages the wrong trials.

## Averaging per condition — distinct names (the overwrite trap)

`mne_average_evoked` defaults `evoked_name="evoked"`. Averaging two conditions without changing it
**overwrites the first**, and a later "difference wave" is then `evoked − evoked = 0` or nonsense.
Always give each condition its own name:

```python
mne_average_evoked(condition="target",   evoked_name="evk_target")
mne_average_evoked(condition="standard", evoked_name="evk_standard")
```

Equalize trial counts before contrasting, so SNR is matched:

```python
epochs.equalize_event_counts(["target", "standard"])   # drops trials to the smaller n
```

## Difference waves

The contrast, not the raw waveform, usually carries the hypothesis (MMN = deviant − standard, N2pc =
contra − ipsi, P300 oddball = target − standard):

```python
evk_diff = mne.combine_evoked([evk_target, evk_standard], weights=[1, -1])  # target - standard
evk_diff.comment = "target - standard"
```

Use `weights="equal"`/`"nave"` only when forming a grand mean, not a contrast. A difference wave
isolates the differential component but also **sums the noise** of both conditions — equalize trials.

## Mean vs peak amplitude, and latency

- **Mean amplitude in a pre-specified window** is the robust default; it is unbiased by window
  length and far less noise-sensitive than peak.
- **Peak amplitude** is biased upward by noise (the more noise/the longer the window, the larger the
  apparent peak) — only with a fixed, pre-registered window and decent SNR.
- **Peak latency** at the single-subject level is very noisy. For *group* latency differences use the
  **jackknife** (Miller/Kiesel): measure latency on the n grand averages each leaving one subject
  out, then correct the *t* statistic.

```python
roi = ["Pz", "CPz", "POz"]; tmin, tmax = 0.30, 0.50              # pre-registered window + ROI
ev  = evk_diff.copy().pick(roi)
mean_amp = ev.get_data(tmin=tmin, tmax=tmax).mean()             # volts; robust measure
ch, lat, amp = evk_diff.get_peak(tmin=tmin, tmax=tmax, mode="abs", return_amplitude=True)

# Jackknife latency across subjects (subj_evokeds = list of per-subject Evoked):
def peak_latency(ev):
    return ev.copy().pick(roi).get_peak(tmin=tmin, tmax=tmax, mode="abs")[1]
n   = len(subj_evokeds)
jk  = [peak_latency(mne.grand_average(subj_evokeds[:i] + subj_evokeds[i+1:])) for i in range(n)]
# variance of the jackknife replicates → corrected SE (multiply naive t by sqrt(n-1)/... per Miller)
```

## Global field power (GFP)

Reference-free measure of overall response strength = spatial standard deviation across channels;
GFP peaks mark topographic stability / component timing without choosing a channel:

```python
gfp = evk_diff.data.std(axis=0)                  # (n_times,)
peak_t = evk_diff.times[np.argmax(gfp)]
```

## Component windows & topography by modality

Naming a component commits you to a latency, polarity, **and topography for that modality**. Mismatch
= misnamed component.

| Component | Modality | Typical latency | Topography |
|---|---|---|---|
| P1  | visual | ~80–130 ms | occipital / lateral occipital |
| N1  | **visual** | **~150–200 ms** | **occipito-temporal** |
| N1  | **auditory** | **~100 ms** | **fronto-central** |
| N170 | visual (faces) | ~170 ms | lateral occipito-temporal |
| MMN | auditory | ~150–250 ms | fronto-central (inverts at mastoids) |
| P300 / P3b | task/oddball | ~300–500 ms | centro-parietal |
| N400 | semantic | ~300–500 ms | centro-parietal |

A **~100 ms occipital** deflection to a *visual* stimulus is almost certainly **P1**, not "N1" — the
classic identity error. Check polarity against your reference too.

## Filtering: latency & polarity distortion

- **High-pass.** > ~0.3 Hz introduces overshoots and can **shift or invert** apparent latency and
  polarity of slow components (P300, LPP, CNV, CDA). Use ≤ 0.1 Hz (offline) when slow components or
  latency matter; report the exact edge.
- **Low-pass.** Smooths and **delays** peaks, reducing apparent peak amplitude; state the cutoff.
- Apply filters on continuous `raw` **before** epoching; report filter type/edges with the result.

## Statistical inference for ERPs

- **Pre-registered window/ROI** → mean amplitude per subject → paired/independent test over the
  *actual* family (components × electrodes × conditions), assumptions checked.
- **No pre-chosen window/channel** → **cluster-based permutation** across the channel × time grid;
  inference is **cluster-level**, not a specific channel/time.
- **Group latency** → jackknife; **small n** → permutation / Wilcoxon, not asserted normality.
- Always report **per-condition trial counts, rejection rate, effect sizes + CIs**.

## Common failure modes (handed to mne-methodology-critic)

| Symptom | Likely problem | Fix |
|---|---|---|
| Window/channel picked off the grand average, then tested | circular / double-dipping | pre-register window + ROI, or orthogonal selection |
| "Occipital N1 at 100 ms" (visual) | topography/modality mismatch | it is P1; re-identify the component |
| P300 latency shifted vs literature | high-pass > 0.3 Hz distortion | high-pass ≤ 0.1 Hz; report edge |
| Two conditions, very unequal n | SNR / differential rejection | `equalize_event_counts`; report rejection per condition |
| Single-subject peak latency compared | peak-latency noise | jackknife group latency (Miller) |
| Difference wave is ~0 / nonsense | `evoked` overwritten by default name | distinct `evoked_name` per condition |
| Per-channel t at many electrodes | uncorrected multiplicity | cluster permutation / correct over the family |
| Peak amplitude in a long window | noise-biased peak | mean amplitude in a fixed window |
