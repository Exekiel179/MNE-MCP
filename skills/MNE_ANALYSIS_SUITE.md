# MNE Analysis Suite — skeptical, per-category analysis skills

A family of MNE analysis skills, **one per major analysis category**, that share a single
discipline: **grill before you compute, critique before you believe.** Each skill runs a
three-phase workflow and defers methodological judgement to a shared, independent critic.

This complements the two existing skills rather than replacing them:

| Skill | Role |
|---|---|
| `mne-analyst` | The general pipeline + figure interpretation + result archiving. |
| `mne-mcp-guard` | **Technical** failure prevention (units, montage, ICA convergence, timeouts). |
| **`mne-methodology-critic`** | **Methodological** review — statistical/scientific validity. Shipped as **both a skill and a subagent** (`agents/mne-methodology-critic.md`, installed to `~/.claude/agents/`); analysis skills' Phase 3 dispatches it in an isolated context for an uncontaminated review. |
| **`mne-writeup`** | Back end: turns critic-PASSED results into APA 7 Methods + Results (modeled on ARS academic-paper). |
| **per-category skills** (below) | Method-specific GRILL questions + best-practice ANALYZE recipe + CRITIC handoff. |

## The three-phase pattern (every analysis skill)

1. **PHASE 1 — GRILL (before touching data).** A method-specific, *skeptical* intake checklist.
   Interrogate the design, hypotheses, assumptions, parameter justifications, multiple-comparison
   plan, sample size, and whether any region/window/feature was chosen *after* seeing the data.
   **Do not run the analysis until the answers are nailed down** (or defaults are proposed AND the
   open risks are flagged). Mirrors the `grill-me` skill, scoped to one method.
2. **PHASE 2 — ANALYZE.** Execute via MNE-MCP tools / `mne_run_code`, following the method's
   best practices, reading every figure, and leaving the equivalent MNE code as an audit trail.
3. **PHASE 3 — CRITIC (before believing).** Hand the plan/result to **`mne-methodology-critic`**
   (invoke the skill, or dispatch it as a subagent). It returns per-issue **FAIL / WARN / INFO**
   with the specific assumption violated and a concrete fix. Surface its verdict to the user.

## Generic GRILL skeleton (each skill specialises it)

- **Question & design**: What is the hypothesis? Within- or between-subject? Paired or independent?
  Confirmatory or exploratory?
- **Sample**: n per group/condition? Power? (Small n ⇒ prefer non-parametric / permutation.)
- **Assumptions**: Which does this method assume, and will they be *tested* (not just asserted)?
- **Multiple comparisons**: Across which dimensions (channels × times × freqs × ROIs × conditions)?
  Which correction? Is its independence assumption valid here?
- **Circularity**: Was any ROI / time window / component / feature selected using the same data the
  test is run on? (double-dipping / peak-picking / selection bias)
- **Reporting**: Effect sizes + CIs, not just p? Trial counts balanced across conditions?
- **Reproducibility**: Random seeds, software versions, equivalent code archived?

## Project / output layout (where everything goes)

Analysis projects follow one structure so raw data, code, figures, stats, verdicts, and the paper each
have a home — **raw stays read-only, every step self-archives, and the write-up reads from these**:

```
your-study/
├─ data/raw/          原始记录（只读，绝不改写）        ├─ stats/   统计产物（含效应量 / CI）
├─ data/derivatives/  预处理 / 中间对象                ├─ critic/  方法学审查裁定(BLOCK/REVISE/PASS)
├─ mne_result/        每步：图 + 等效代码（带序号）      └─ paper/   manuscript + figures/ + references
```

- **原始数据 → `data/raw/`**（只读）；预处理产物 → `data/derivatives/`。
- **代码（每步等效 MNE 代码）+ 图 → `mne_result/`**（带序号，既有 `mne-analyst` 约定）。
- **统计数字 → `stats/`**；**审查裁定 → `critic/`**；**论文 → `paper/`**（发表图为 `mne_result/` 精选副本）。

Full tree + rules: `mne-writeup/references/writeup-guide.md`.

## Skills (11 + shared critic)

| # | Skill | Category | Status |
|---|---|---|---|
| — | `mne-methodology-critic` | Shared methodology reviewer | ✅ built (exemplar phase) |
| 1 | `mne-preprocess` | Preprocessing & data quality | ✅ built |
| 2 | `mne-artifacts` | Artifact correction (ICA/SSP/autoreject) | ✅ built |
| 3 | `mne-erp` | ERP / ERF (evoked) | ✅ built |
| 4 | `mne-spectral` | Spectral / PSD / band power / 1-f | ✅ built (exemplar) |
| 5 | `mne-timefreq` | Time-frequency (Morlet/multitaper, ERSP/ITC) | ✅ built |
| 6 | `mne-connectivity` | Connectivity (coh/PLV/wPLI, PAC, Granger) | ✅ built |
| 7 | `mne-source` | Source localization (MNE/dSPM/beamformer) | ✅ built |
| 8 | `mne-decoding` | Decoding / MVPA / CSP / RSA / mTRF | ✅ built |
| 9 | `mne-stats` | Statistics (cluster permutation, TFCE, FDR, LMM) | ✅ built |
| 10 | `mne-advanced` | Rare/advanced: microstates, entropy, graph, real-time | ✅ built |
| 11 | `mne-writeup` | Write-up: verified results → APA 7 Methods + Results | ✅ built |

> Each skill is self-contained (survives per-folder install via `mne-mcp setup`). The GRILL
> skeleton is repeated inline; the CRITIC is shared by name (`mne-methodology-critic`).
