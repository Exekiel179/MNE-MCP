"""Paired score differences between conditions (Table S1, Fig. 2A) and per-task-family means.
Usage: python paired_analysis.py full-evaluation.csv  -> writes paired-differences.csv, task-family-scores.csv"""
import sys, numpy as np, pandas as pd
from scipy import stats
df = pd.read_csv(sys.argv[1], encoding="utf-8-sig")
df["s"] = df.score / df.max_score * 100
w = df.pivot(index="instance_id", columns="condition", values="s")
meta = df.drop_duplicates("instance_id").set_index("instance_id")
fam = meta.task_family.reindex(w.index)
rng = np.random.default_rng(20261012); B = 10000; fams = fam.unique(); rows = []
for a, b in [("mne", "python"), ("mne-skills", "mne"), ("mne-skills", "python")]:
    d = w[a] - w[b]; nz = d[d.abs() > 1e-6]
    byf = {f: d[fam == f].values for f in fams}
    cl = [np.concatenate([byf[f] for f in rng.choice(fams, len(fams))]).mean() for _ in range(B)]
    it = [rng.choice(d.values, len(d)).mean() for _ in range(B)]
    rows.append(dict(comparison=f"{a} - {b}", mean_diff=d.mean(), improved=(d > 1e-6).sum(), tied=(d.abs() <= 1e-6).sum(),
        declined=(d < -1e-6).sum(), family_cluster_ci_low=np.percentile(cl, 2.5), family_cluster_ci_high=np.percentile(cl, 97.5),
        item_ci_low=np.percentile(it, 2.5), item_ci_high=np.percentile(it, 97.5), wilcoxon_p_nonzero=stats.wilcoxon(nz).pvalue))
out = pd.DataFrame(rows); print(out.to_string()); out.to_csv("paired-differences.csv", index=False)
ft = w.groupby(fam).mean().round(2); ft["n_tasks"] = fam.value_counts(); ft.to_csv("task-family-scores.csv")
