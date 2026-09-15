// Run PsyClaw's actual config loader, skill discovery and stdio client in a test project.
import assert from "node:assert/strict";
import { resolve } from "node:path";
const [rootArg, runtimeUrl, skillsUrl] = process.argv.slice(2);
const root = resolve(rootArg);
const { RuntimeMcpRegistry } = await import(runtimeUrl);
const { scanLocalSkills } = await import(skillsUrl);
const registry = new RuntimeMcpRegistry();
function text(result) {
  assert.notEqual(result.isError, true, JSON.stringify(result));
  return result.content.filter((part) => part.type === "text").map((part) => part.text).join("\n");
}
try {
  const servers = await registry.list(root, "mne");
  assert(servers[0].tools.some((tool) => tool.name === "mne_check_status"));
  assert.match(text(await registry.call(root, "mne", "mne_check_status", {})), /MNE-Python: OK v/);
  const discovered = await scanLocalSkills(root);
  const names = discovered.filter((skill) => skill.scope === "project" && skill.name.startsWith("mne-"));
  assert.equal(names.length, 14);
  const code = `
import mne, numpy as np
info = mne.create_info(['Fz', 'Cz'], 200, 'eeg')
times = np.arange(2000) / 200
raw = mne.io.RawArray(np.tile(10e-6 * np.sin(2 * np.pi * 10 * times), (2, 1)), info, verbose=False)
raw.filter(1, 40, verbose=False)
epochs = mne.make_fixed_length_epochs(raw, duration=1, preload=True, verbose=False)
evoked = epochs.average()
spectrum = epochs.compute_psd(method='welch', n_fft=200, fmin=1, fmax=40, verbose=False)
peak = spectrum.freqs[spectrum.get_data().mean(axis=(0, 1)).argmax()]
assert abs(peak - 10) < 1, f'Unexpected peak: {peak}'
assert evoked.data.shape == (2, 200), f'Unexpected shape: {evoked.data.shape}'
print('SYNTHETIC_ANALYSIS_OK')
`;
  assert.match(text(await registry.call(root, "mne", "mne_run_code", { code })), /SYNTHETIC_ANALYSIS_OK/);
  const invalid = await registry.call(root, "mne", "mne_filter", { name: "raw", l_freq: 40, h_freq: 1 });
  assert(invalid.isError || /error|must|invalid/i.test(text(invalid)));
  console.log(JSON.stringify({ connected: true, skills: names.length, synthetic_analysis: true, tools: servers[0].tools.length }));
} finally {
  registry.close();
}
