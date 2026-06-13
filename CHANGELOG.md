# Changelog

All notable changes to MNE-MCP are documented here. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions are pre-1.0 and may move quickly.

## [0.3.0] — 2026-06-13

### Changed
- **Lightweight by default — the heavy analysis stack is now installed on demand.**
  Hard dependencies are reduced to the protocol layer only (`mcp`, `fastmcp`,
  `pydantic`, `python-dotenv`), so `pip install mne-mcp` / `pipx install mne-mcp` /
  `uv tool install mne-mcp` is near-instant. MNE-Python and the scientific stack
  (numpy/scipy/matplotlib/pandas, plus scikit-learn for ICA) moved into the new
  **`analysis`** extra; `ica` and `full` now build on it (`mne-mcp[analysis|ica|full]`
  still install everything up front).
- All startup-path imports are now lazy: importing the server no longer pulls in
  numpy or matplotlib (`_compat` and `figures` defer them), so the bare shell runs
  with zero scientific dependencies (proven by `tests/test_lightweight.py`).

### Added
- **On-demand backend provisioning** (`mne_mcp/backend.py`): `mne-mcp install-backend
  [--profile analysis|ica|full]` and the **`mne_install_backend`** MCP tool install the
  analysis stack into the *running server's own* Python environment, then call
  `importlib.invalidate_caches()` so it becomes importable **without a client restart**.
- `mne_check_status` / `mne-mcp status` now report when the backend is absent and how
  to provision it; the missing-backend errors from every `mne_*` tool point at
  `mne_install_backend`.

## [0.2.2] — 2026-06-05

### Changed
- **Skills + the methodology-critic subagent now ship inside the wheel** (hatch
  `force-include` → `mne_mcp/_bundled/`). A plain `pip install`/`pipx install`/`uvx`
  of `mne-mcp` now carries them, so `mne-mcp setup` installs the full skill suite
  even when there is no source checkout. `get_skills_source_dir()` /
  `get_agents_source_dir()` prefer the bundled copy and fall back to the repo.

## [0.2.1] — 2026-06-05

### Added
- **Official MCP Registry** listing (`server.json`): the server is publishable to
  `registry.modelcontextprotocol.io` under `io.github.Exekiel179/mne-mcp`, launched via
  `uvx --from "mne-mcp[ica]" mne-mcp serve`. README carries the `mcp-name:` ownership marker
  required by the registry's PyPI verification.

### Changed
- The documented standard `uvx` / `pipx` launch config now pulls the **`[ica]`** extra (and notes
  `[full]`) so ICA and the advanced tools work out of the box — the bare package shipped neither.

### Fixed
- `.gitignore`: ignore `.coverage` artifacts.

## [0.2.0] — 2026-06-05

### Added
- Test **coverage** in CI (pytest-cov); CLI, server-layer, and broad operation-layer tests lift
  coverage to ~71%, with a 65% regression floor.
- **`py.typed`** marker (PEP 561) — the package ships inline type hints.
- **`CONTRIBUTING.md`**, GitHub issue/PR templates, and a **`release.yml`** workflow that publishes
  to PyPI via Trusted Publishing on a version tag.
- Opt GitHub Actions into **Node.js 24** (clears the Node 20 deprecation warning).
- **Continuous integration** (`.github/workflows/ci.yml`): unit tests on Linux/macOS/Windows ×
  Python 3.10/3.12; a **NumPy 1.x / 2.x compatibility matrix**; a **real-data eegbci smoke test**;
  and a black/isort lint job.
- **Real-data smoke test** (`tests/smoke_eegbci.py`): downloads PhysioNet eegbci S001 eyes-open vs
  eyes-closed baselines and asserts the **Berger effect** (occipital alpha higher eyes-closed) end
  to end through the operation layer — covering the real EDF-reading path the synthetic smoke test
  never exercised.
- **Regression tests** (`tests/test_regressions.py`) for the two bugs fixed below.
- **Analysis skill suite** (`skills/`): `mne-methodology-critic` (shared methodology reviewer, also
  shipped as a subagent in `agents/`), per-category skills (`mne-preprocess`, `mne-artifacts`,
  `mne-erp`, `mne-spectral`, `mne-timefreq`, `mne-connectivity`, `mne-source`, `mne-decoding`,
  `mne-stats`, `mne-advanced`), and `mne-writeup`; all installed by `mne-mcp setup`.

### Fixed
- **NumPy 2.x compatibility** (`mne_mcp/_compat.py`, applied at package import): restore aliases
  removed in NumPy ≥ 2.0 (`np.trapz`→`trapezoid`, `np.in1d`→`isin`, `np.row_stack`→`vstack`, …)
  that a transitive dependency still calls while reading EDF. Previously this raised
  `AttributeError` and **blocked all recording loads under NumPy 2.x**.
- **`picks` comma lists**: `plot_psd` / `plot_epochs_image` now accept `"O1,Oz,O2"` (split via
  `operations._parse_picks`) instead of treating the whole string as one nonexistent channel.
- Docs: corrected the unit-test count in `docs/INTRODUCTION.md` (31 → 39).

## [0.1.0]

- Initial release: 38-tool MCP server for MNE-Python (EEG/MEG/sEEG/ECoG/fNIRS), persistent
  in-memory session, `mne_run_code` escape hatch, one-command multi-client setup, and the
  `mne-analyst` + `mne-mcp-guard` skills.
