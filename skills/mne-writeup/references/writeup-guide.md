# Write-up guide — project layout, APA 7 reporting templates, Methods boilerplate

Companion to `mne-writeup/SKILL.md`. Defines where artifacts live and how to report them.

## Project / output layout (the canonical structure)

```
your-study/
├─ data/
│  ├─ raw/                原始记录（只读，绝不改写）：sub-01_raw.fif, *.edf, *.vhdr, *.set …
│  └─ derivatives/        预处理 / 中间对象：sub-01_proc-clean_raw.fif, *-epo.fif, *-ave.fif
├─ mne_result/            【既有归档约定】逐步、带序号：每步的图 + 等效 MNE 代码
│  ├─ 01_psd.png   02_ica_components.png   03_evoked_joint.png  …   (figures)
│  └─ 01_psd.py    02_ica.py               03_average.py        …   (equivalent code)
├─ stats/                 统计产物：cluster / FDR / 效应量与 CI 的数表（.csv / .json）
├─ critic/                方法学审查裁定：<analysis>_verdict.md（BLOCK / REVISE / PASS）
└─ paper/                 写作产物（mne-writeup 输出）：
   ├─ manuscript.md / manuscript.docx
   ├─ figures/            发表用图（从 mne_result 精选并精修）
   └─ references.bib
```

**Rules that keep this clean and reproducible**
- **Raw is read-only.** Never write into `data/raw/`. Preprocessing outputs go to `data/derivatives/`.
- **Every step self-archives.** Figures + the equivalent MNE code land in `mne_result/` (the
  `mne-analyst` convention), sequence-numbered, so Methods can be reconstructed exactly.
- **Numbers live in `stats/`.** Results prose cites these files; it never invents values.
- **Verdicts live in `critic/`.** `mne-writeup` reads them and reports only PASSED results.
- **`paper/` is the only place prose + publication figures live.** Figures there are *copies* selected
  from `mne_result/`, refined for publication.

## APA 7 results-reporting templates

Report effect sizes + CIs, not just p. Examples:

- **Paired t-test**: "Target amplitude (M = 4.21 µV, SD = 1.8) exceeded standard (M = 1.07 µV,
  SD = 1.5), *t*(19) = 5.32, *p* < .001, *d* = 1.19, 95% CI [2.0, 4.3] µV."
- **One-way ANOVA**: "*F*(2, 57) = 6.41, *p* = .003, η²_p = .18," + post-hoc with corrected p.
- **Correlation**: "*r*(28) = .46, *p* = .011, 95% CI [.11, .71]."
- **Cluster-based permutation** (report **cluster-level**, not per-point): "A significant
  positive cluster spanned ~300–480 ms over centro-parietal sensors (cluster *p* = .004); no claim is
  made about individual sensors/time points within the cluster."
- **Time-resolved decoding**: "Decoding exceeded chance from ~120 ms (peak AUC = .78, cluster
  *p* < .001); chance established by label permutation."
- **Connectivity**: name the metric and that it is field-spread-robust: "Alpha-band wPLI between …
  differed between conditions (cluster *p* = .02)." State sensor vs source space.
- **Source**: state the head model: "dSPM estimates on a template (fsaverage) head — exploratory;
  no individual MRI."
- **Spectral**: if relative power, state the transform used (CLR/logit) and that 1/f was separated
  (report aperiodic exponent/offset).

## Reproducible Methods boilerplate (fill from `mne_result/` equivalent code)

> Data were analyzed in MNE-Python (v__) [Gramfort et al., 2013]. Recordings were band-pass filtered
> __–__ Hz with a __ Hz notch, re-referenced to __, and set to the __ montage; __ channels were marked
> bad and spline-interpolated. Ocular/cardiac artifacts were removed via ICA (__ method, fit on
> ~1 Hz high-passed data; __ of __ components removed, identified by __). Data were epoched __ to __ s
> relative to __, baseline-corrected to __, and epochs exceeding __ µV peak-to-peak were rejected
> (__ % rejected; per-group __ % / __ %). [Method-specific parameters: TFR/connectivity/decoding/
> source …]. Statistics used __ (e.g., cluster-based permutation, __ permutations, cluster-forming
> threshold __ / TFCE), with __ correction; effect sizes and 95% CIs are reported.

Every blank must come from an archived artifact — if it isn't recorded, re-run or mark it unknown,
don't guess. Software versions come from `mne_check_status`.

## Hand-off boundaries
- Full multi-section paper with literature search + simulated peer review → ARS `academic-paper` /
  `academic-pipeline`.
- Methodology doubts about any result → `mne-methodology-critic` (gate before writing).
- This skill specialises in the **reproducible Methods + correctly-reported Results** of an MNE study.
