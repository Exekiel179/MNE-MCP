# Data S1

Supplementary data for *MNE-MCP: A Neurophysiological Analysis Interface for LLM Agents and Ablation of Tools and Skills* (Xue, Wei & Zhu).

The evaluation covers all 181 BrainBench foundational-analysis tasks on PhysioNet EEGMAT, run under three conditions (Python, MNE MCP, MNE MCP + skills), giving 543 runs. Scores are the official BrainBench scores. A task counts as full-score when its normalized score is within 1e-9 of 1.

## data/

| File | Content | Used in |
|---|---|---|
| full-evaluation.csv | One row per run (543 rows): score, timing, context size, token use, tool-call counts and error flags | Table 4; Tables S2, S4, S5 |
| verified-summary.json | Per-condition summary, skill-layer pairing outcomes and the list of 41 registered tools | Table 4; Table S8 |
| paired-differences.csv | Paired differences for the three comparisons, with task-family cluster and task bootstrap 95% CIs and signed-rank p | Fig. 2A; Table S1 |
| task-family-scores.csv | Mean score of each of the 39 task families under each condition | Fig. 2 |
| skill-paired-audit.json | Per-task audit of the skill-layer pairs, including weighted scores by official metric type | Table S3 |
| log-metrics.csv | Per-task statistics from the 362 event logs of the two MCP conditions: MCP call composition, skill reading, methodological review and sensitivity-analysis flags | Fig. 3; Table S6 |
| log-summary.csv, tool-counts.csv | Condition-level log summary and call counts per tool | Fig. 3A; Table S6 |
| failure-attribution.csv | Attribution of each task whose score differed between conditions, with the evidence for each | Fig. 3; Table S7 |
| welch_window_by_task.csv | Welch window length used in each task's submitted code (MCP conditions) | Fig. 3; Table S7 |

## scripts/

| File | Purpose |
|---|---|
| paired_analysis.py | `python paired_analysis.py full-evaluation.csv` writes paired-differences.csv and task-family-scores.csv (seed 20261012; 10,000 resamples) |
| parse_logs.py | `python parse_logs.py <run_dir> full-evaluation.csv <out_dir>` derives the log statistics from each run's event log (target-01.jsonl) |
| fig1.py, figs.py | Draw Fig. 1 and Figs. 2 and 3 |

Requirements: Python 3.10 or later with numpy, pandas, scipy and matplotlib.

## Notes

- Runs with a connection failure keep the scorer's raw output with `evaluation_valid=false` and `infrastructure_error=true`, and are excluded from comparisons. Missing token counts are left empty; one task in the skills condition has incomplete usage records.
- A target-analysis timeout is an unfinished task within budget and keeps its official score.
- Failure attribution was classified by the authors from scoring details, parsed answers and submitted code, without double coding.
- The raw run directories are not included because the agent client directories contain login credentials.
