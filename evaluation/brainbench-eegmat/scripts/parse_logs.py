"""Parse target-agent event logs (Codex JSONL) for the MNE MCP and MNE MCP + skills conditions.
Usage: python parse_logs.py <run_dir> <full-evaluation.csv> <out_dir>"""
import json, re, sys, collections
from pathlib import Path
import pandas as pd
run, evalcsv, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]); out.mkdir(exist_ok=True)
EXTRA = {  # extra-step markers in submitted code / messages (case-insensitive)
 'sensitivity_check': r'sensitivit|robustness|alternative (window|parameter)|cross-check',
 'methodology_review': r'(?i:methodology review|self-review|pseudoreplication|circular analysis)|\b(?:PASS|REVISE|BLOCK)\b',
 'review_file_written': r'review\.md|methodology.*\.(md|json|txt)',
}
rows = []
for cond in ['mne', 'mne-skills']:
    for d in sorted((run / cond).iterdir()):
        f = d / d.name / 'logs' / 'target-01.jsonl'
        if not f.exists(): continue
        ev = [json.loads(l) for l in f.open(encoding='utf-8') if l.strip()]
        items = [e['item'] for e in ev if e.get('type') == 'item.completed' and 'item' in e]
        mcp = [i for i in items if i.get('type') == 'mcp_tool_call']
        sh = [i for i in items if i.get('type') == 'command_execution']
        code = ' '.join(str(i.get('arguments', '')) for i in mcp if i.get('tool') == 'mne_run_code')
        msgs = ' '.join(i.get('text', '') for i in items if i.get('type') == 'agent_message')
        skill_reads = [i for i in sh if re.search(r'\.agents[/\\]skills', i.get('command', ''))]
        skill_files = set()
        for i in skill_reads:
            skill_files |= set(re.findall(r'skills/([\w\-]+)/', i.get('command', '').replace('\\', '/')))
        r = dict(condition=cond, instance_id=d.name,
                 mcp_calls=len(mcp),
                 run_code_calls=sum(i.get('tool') == 'mne_run_code' for i in mcp),
                 structured_calls=sum(i.get('tool') != 'mne_run_code' for i in mcp),
                 shell_calls=len(sh), skill_read_calls=len(skill_reads),
                 skill_read_chars=sum(len(i.get('aggregated_output') or '') for i in skill_reads),
                 skills_read=';'.join(sorted(skill_files)),
                 read_methodology_critic=int('mne-methodology-critic' in skill_files),
                 mcp_errors=sum(1 for i in mcp if i.get('error') not in (None, 'None', '') ),
                 shell_nonzero=sum(1 for i in sh if str(i.get('exit_code')) not in ('0', 'None')),
                 tools=';'.join(i.get('tool', '') for i in mcp))
        for k, pat in EXTRA.items():
            r[k] = int(bool(re.search(pat, code) if k == 'methodology_review' else re.search(pat, code, re.I)))
        r['review_in_answer'] = int(bool(re.search(EXTRA['methodology_review'], msgs)))
        rows.append(r)
df = pd.DataFrame(rows)
ev = pd.read_csv(evalcsv, encoding='utf-8-sig')
ev['s'] = ev.score / ev.max_score * 100
df = df.merge(ev[['condition', 'instance_id', 's', 'task_family']], on=['condition', 'instance_id'], how='left')
df.to_csv(out / 'log-metrics.csv', index=False)
# summaries
g = df.groupby('condition')
summ = pd.DataFrame({
 'tasks': g.size(), 'mcp_calls': g.mcp_calls.sum(), 'structured_calls': g.structured_calls.sum(),
 'run_code_calls': g.run_code_calls.sum(),
 'run_code_share_%': (g.run_code_calls.sum() / g.mcp_calls.sum() * 100).round(1),
 'tasks_using_run_code': g.apply(lambda x: (x.run_code_calls > 0).sum()),
 'tasks_only_structured': g.apply(lambda x: ((x.run_code_calls == 0) & (x.mcp_calls > 0)).sum()),
 'shell_calls': g.shell_calls.sum(), 'skill_read_calls': g.skill_read_calls.sum(),
 'tasks_reading_skills': g.apply(lambda x: (x.skill_read_calls > 0).sum()),
 'median_skill_read_chars': g.skill_read_chars.median(),
 'tasks_read_critic': g.read_methodology_critic.sum(),
 'tasks_sensitivity': g.sensitivity_check.sum(), 'tasks_review_code': g.methodology_review.sum(),
 'tasks_review_file': g.review_file_written.sum(), 'tasks_review_in_answer': g.review_in_answer.sum(),
})
summ.T.to_csv(out / 'log-summary.csv')
print(summ.T.to_string())
tc = collections.Counter(t for c, s in zip(df.condition, df.tools) for t in s.split(';') if t)
by = {c: collections.Counter(t for s in df[df.condition == c].tools for t in s.split(';') if t) for c in ['mne', 'mne-skills']}
tt = pd.DataFrame(by).fillna(0).astype(int).sort_values('mne', ascending=False)
tt.to_csv(out / 'tool-counts.csv'); print(tt.to_string())
sk = collections.Counter(s for x in df[df.condition == 'mne-skills'].skills_read for s in x.split(';') if s)
print('skills read (tasks):', sk.most_common())
