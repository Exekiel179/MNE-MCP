---
name: mne-writeup
description: >
  Turn completed, critic-PASSED MNE analyses into a publication-ready write-up — Methods and Results
  (and optionally Abstract/Introduction/Discussion) in APA 7 — modeled on the ARS academic-paper
  workflow but specialised for EEG/MEG/iEEG. It reads the project's archived artifacts (preprocessing
  parameters and equivalent code from mne_result/, statistics from stats/, and the methodology
  verdicts from critic/), writes a reproducible Methods section and a correctly-reported Results
  section (effect sizes + CIs + corrected p, with figures/tables), and refuses to report any claim the
  methodology critic marked BLOCK. Use after analysis + critique, when the user wants to write up
  results, draft a methods/results section, or produce a manuscript. Triggers: write up, 撰写, 写作,
  论文, manuscript, 手稿, methods section, 方法部分, results section, 结果部分, 写方法, 写结果,
  report, 研究报告, APA, 投稿稿件.
---

# MNE Write-up (verified results → manuscript)

The **back end** of the analysis suite: after the per-category skills have run and
`mne-methodology-critic` has ruled, this skill writes the result up. It mirrors the ARS
`academic-paper` workflow (config → outline → draft → citation/integrity → format) but is specialised
for neurophysiology and is **gated by the critic**.

> Companion: `mne-methodology-critic` (the gate); the per-category analysis skills (the source of
> results); `mne-analyst` (the archiving convention this reads from). For a *full* multi-section paper
> with literature search and peer review, hand off to the ARS `academic-paper` / `academic-pipeline`
> skills — this skill specialises in the Methods + Results of an MNE study.

## ⚠️ IRON RULES

1. **Only write what PASSED.** A result the critic marked **BLOCK** is **not reported** as a finding;
   either fix-and-re-critique first, or move it to Limitations as an acknowledged problem. **WARN**
   items must appear as explicit qualifications/limitations, never silently dropped.
2. **Every number traces to an artifact.** Each reported statistic must come from a file under
   `stats/` (or the analysis tool's output) — **never invent or round-guess a value**. If it isn't in
   an artifact, it isn't written.
3. **Methods must be reproducible.** Pull exact parameters from the equivalent code archived in
   `mne_result/` (filter band, reference, ICA method/components removed, epoch window, rejection
   threshold, TFR/connectivity/decoding settings, software versions). Vague methods = rejected.

## Workflow

### 1. CONFIG (intake)
Confirm: output target (full paper / Methods+Results section / report), discipline + venue, citation
format (**APA 7** default), language (and whether a bilingual abstract is needed), output format
(Markdown → DOCX via Pandoc). Locate the project layout (see `references/writeup-guide.md`): `data/`,
`mne_result/`, `stats/`, `critic/`, `paper/`.

### 2. INTAKE & GATE
Read `critic/` verdicts. Build a result inventory: each finding → its figure(s) in `mne_result/`, its
numbers in `stats/`, and its **critic verdict**. Drop/flag BLOCKed claims (IRON RULE 1). List exactly
what will be reported and what becomes a limitation.

### 3. OUTLINE
IMRaD (or just Methods + Results). Map every reported result to a figure or table and to its source
artifact. Allocate the figures that will be copied into `paper/figures/`.

### 4. DRAFT
- **Methods** — participants/data, recording, preprocessing (filter, reference, montage, bad
  channels), artifact correction (ICA method, # components removed and how identified), epoching
  (window, baseline, rejection + per-group rejection rate), the analysis method and its parameters,
  the statistics (test, correction, software + versions). Source every parameter from `mne_result/`.
- **Results** — report with effect sizes + CIs + corrected p, in APA 7 (see the reporting templates
  in `references/writeup-guide.md`); reference figures/tables; state cluster-level (not point)
  inference where cluster tests were used.
- Apply a brief **writing-quality pass** (varied sentence rhythm; avoid AI-typical filler and em-dash
  overuse; no throat-clearing openers) — good-writing rules, à la ARS.

### 5. INTEGRITY & CRITIC GATE
- **Citations**: every reference cited is in the list and vice-versa; APA 7 formatting; verify DOIs
  exist (don't fabricate). 
- **Methodology gate**: re-confirm no BLOCKed claim is reported as a finding, every WARN is
  reflected as a limitation, and every number traces to a `stats/` artifact. If anything is
  unverified, dispatch `mne-methodology-critic` on the draft before proceeding.

### 6. FORMAT & OUTPUT
Write `paper/manuscript.md`; convert to `paper/manuscript.docx` via Pandoc (APA 7); copy/refine the
selected figures into `paper/figures/`; keep references in `paper/references.bib`. (Reuse the repo's
`paper/` convention — see `MNE_ANALYSIS_SUITE.md` for the full project layout.)

See `references/writeup-guide.md` for the project layout, APA 7 reporting templates (t-test, ANOVA,
correlation, cluster-permutation, decoding AUC, connectivity, source), and a reproducible Methods
boilerplate.
