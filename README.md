<!-- mcp-name: io.github.Exekiel179/mne-mcp -->

# MNE-MCP

[![CI](https://github.com/Exekiel179/MNE-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/Exekiel179/MNE-MCP/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io)

**English** | [简体中文](README.zh-CN.md)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives AI assistants
direct, conversational access to **[MNE-Python](https://mne.tools/)** for analyzing human
neurophysiology data — **EEG, MEG, sEEG, ECoG, and fNIRS**.

Describe your analysis in plain language — MNE-MCP loads your recording, runs the MNE pipeline
(filtering, ICA, epoching, ERP/ERF averaging, time-frequency, source-level work via code),
saves the figures, and explains the results.

> Works in **Claude Code**, **Codex**, **PsyClaw** and **opencode**. Pairs with bundled
> Agent **Skills** — `mne-analyst`, `mne-mcp-guard`, plus a skeptical **analysis suite**
> (`mne-methodology-critic` + per-category skills) for reliable, archived workflows.

---

## Why an MCP for MNE-Python?

MNE analysis is **stateful and visual** — unlike a one-shot statistics batch job:

- You load a `Raw` recording once, then filter → re-reference → fit ICA → epoch → average →
  time-frequency, each step mutating large in-memory objects. MNE-MCP keeps **one persistent
  session** so recordings never get re-loaded between steps.
- Every decision is driven by **looking** (PSD, sensor maps, ICA components, ERPs). Every plotting
  tool saves a **PNG** the assistant can read and interpret.
- MNE has a large Python API. MNE-MCP gives you **41 structured tools** spanning the common
  pipeline *and* advanced analysis (source localization, connectivity, decoding), plus an
  **`mne_run_code`** escape hatch that reaches the entire MNE API in the same live session.
- Defaults (line frequency, montage, filter band, rejection threshold, ICA settings, epoch window,
  dirs, timeout) are **user-configurable** via an interactive `mne-mcp configure` wizard.

---

## Requirements

- Python **3.12+** (no package upper-version gate; full-test baseline: 3.12)
- Git
- Claude Code, Codex, PsyClaw, opencode, or another MCP client

> Cross-platform: unlike a closed engine, MNE-Python is pure Python, so analysis tools work on
> Windows, macOS, and Linux.

---

## Installation

### Install with your agent

Send this to a coding agent with terminal access:

> Follow https://github.com/Exekiel179/MNE-MCP/blob/v0.4.1/INSTALL_AGENT.md to install MNE-MCP and all companion skills in my existing MNE environment, configure my current client, and verify the result.

The agent checks the environment, installs missing MNE/core libraries when needed, installs the lightweight interface and all 14 skills, and
registers the selected client. A client restart is required. See the
[installation guide](INSTALL_AGENT.md) for environment checks and verification.

### Manual installation

Activate your existing Python 3.12+ MNE environment, then install the lightweight interface:

```bash
python -m pip install mne-mcp
python -m mne_mcp.cli setup
```

Release downloads: [latest release](https://github.com/Exekiel179/MNE-MCP/releases/latest).
For a downloaded source archive, extract it and use `python -m pip install .` in that directory.
Setup defaults to all four clients, including their skills. To configure only PsyClaw,
use `python -m mne_mcp.cli setup --clients psyclaw`; `claude`, `codex` and `opencode`
are also supported (comma-separated). Restart clients after setup; PsyClaw supports `/reload`.
MNE and scientific libraries are user-managed; installing this package does not install them.
See [installation instructions](docs/INSTALL.md) for dependencies and troubleshooting.

## Configuration

### Repair or reconfigure

To update an existing installation, run `python -m pip install --upgrade mne-mcp`.
Run `python -m mne_mcp.cli setup --clients codex` in the same MNE environment.
Setup registers that exact interpreter and installs the bundled skills for the selected clients.
Existing configuration and skill files are backed up before updates.

### PsyClaw verification

PsyClaw registration writes `~/.psyclaw/mcp/mne.json`; all 14 skills and references
go to `~/.psyclaw/skills`. Setup checks a real MCP handshake, tool discovery and
`mne_check_status`, including a second check of the saved PsyClaw command.

```bash
python -m mne_mcp.cli verify --client psyclaw
```

This checks the saved command without modifying registration. `connected` and
`mne_available` are separate: the lightweight server can connect without MNE installed.
After `/reload`, ask PsyClaw to list tools for server `mne` and call `mne_check_status`.
Project `.psyclaw/mcp/*.json` entries with the same id override user configuration.
The setup check does not claim your already-running chat has reloaded.

### Environment variables (optional `.env`)

```ini
MNE_MCP_TIMEOUT=300          # per-operation timeout (s); raise for ICA / TFR / large files
MNE_MCP_RESULTS_DIR=...      # where figures + exported objects are saved
MNE_MCP_DATA_DIR=...         # default directory mne_list_files scans
```

### Configure analysis defaults (interactive wizard)

Set the defaults the structured tools fall back to — mains line frequency (50/60 Hz), default
montage, filter band, EEG rejection threshold, ICA method/components, epoch window, directories,
and timeout:

```bash
mne-mcp configure            # interactive prompts (Enter keeps current value)
mne-mcp configure --show     # print current defaults
mne-mcp configure --reset    # back to built-in defaults
mne-mcp configure --set line_freq=60 default_montage=biosemi64 reject_eeg_uv=120   # non-interactive
```

Defaults are saved to `~/.mne-mcp/config.json` (override path with `MNE_MCP_CONFIG`). Precedence at
runtime: **environment variable > config file > built-in**. View the active config in-session with the
`mne_get_config` tool. Restart the MCP server for changes to take effect.

### Skills

Setup installs all 14 skills into the selected client's skill directory, including their references.
Claude also receives the methodology-review subagent. Other clients use the methodology-critic skill.
Rerun setup after updating the package.

---

## Usage

Just describe what you want:

```
加载 sub-01_raw.fif，看一下功率谱
```
```
对 raw 做 1–40 Hz 带通、50 Hz 陷波，然后跑 ICA 去眼电
```
```
Epoch around the 'target' trigger, -0.2 to 0.8 s, average it, and show the ERP topomaps at 100/200/300 ms
```

The assistant will:
1. Check capabilities (`mne_check_status`)
2. Load your recording into the persistent session
3. Run the pipeline step by step, showing figures as PNGs
4. Interpret each result in plain language
5. Archive figures + the equivalent MNE code to `mne_result/`

---

## Output

Every plotting tool saves a PNG to the results dir and returns its path:

```
> Figure: `C:\...\mne-mcp\results\psd_01.png`
```

With the `mne-analyst` skill installed, results and the exact MNE code that produced them are
archived to `mne_result/` in your working directory (sequence-numbered), so the analysis is
fully reproducible.

---

## Available Tools (41)

### Status & Session (7)
`mne_check_status` · `mne_session_info` · `mne_describe` · `mne_get_info` ·
`mne_reset_session` · `mne_run_code` · `mne_get_config`

### Data IO (2)
`mne_list_files` · `mne_load_raw`

### Preprocessing (7)
`mne_filter` · `mne_resample` · `mne_crop` · `mne_set_montage` ·
`mne_set_reference` · `mne_mark_bad_channels` · `mne_interpolate_bads`

### Visualization (3)
`mne_plot_psd` · `mne_plot_raw` · `mne_plot_sensors`

### ICA (4)
`mne_fit_ica` · `mne_plot_ica_components` · `mne_plot_ica_sources` · `mne_apply_ica`

### Events / Epochs / ERP (7)
`mne_find_events` · `mne_events_from_annotations` · `mne_make_epochs` ·
`mne_plot_epochs_image` · `mne_average_evoked` · `mne_plot_evoked` · `mne_plot_topomap`

### Time-frequency (2)
`mne_compute_tfr` (Morlet/multitaper, custom cycles, ITC, trial power, baseline) · `mne_tfr_morlet`

### Advanced analysis (8)
`mne_decode` (MVPA) · `mne_connectivity` · `mne_compute_connectivity` (bands, pairs, estimators) · `mne_compute_noise_cov` · `mne_make_forward` ·
`mne_apply_inverse` · `mne_plot_source_estimate`

`mne_decoding_group_test` provides participant-level max-T or cluster-corrected inference.
Decoding reports separate numerical evidence, methods, interpretation, limitations
and a results draft requiring scientific review. The code escape hatch is not
equivalent to validated structured coverage of every MNE API.

### Export (1)
`mne_save`

Anything still not covered — BIDS, custom statistics, beamformers, autoreject — is reachable through
**`mne_run_code`** in the same live session. See [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) for full
parameter details. Advanced dependencies are checked per feature and are not bundled.

---

## Development

```bash
# Compile check
python -m compileall src/mne_mcp

# Run tests
pytest

# CLI commands
mne-mcp status            # Check environment
mne-mcp setup --clients codex # Register in Claude Code / Codex / opencode + install skills
mne-mcp configure-claude  # Claude Code only
```

---

## License

MIT — see [LICENSE](LICENSE)

## Documentation

- **项目介绍 / Introduction**: [docs/INTRODUCTION.md](docs/INTRODUCTION.md) · [.docx](docs/INTRODUCTION.docx)
- **安装说明 / Install guide**: [docs/INSTALL.md](docs/INSTALL.md) · [.docx](docs/INSTALL.docx)
- **使用介绍 / Usage guide**: [docs/USAGE.md](docs/USAGE.md) · [.docx](docs/USAGE.docx)
- **Quick start**: [QUICK_START.md](QUICK_START.md)
- **Tool reference**: [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md)

## Links

- **MNE-Python**: https://mne.tools/
- **MCP Protocol**: https://modelcontextprotocol.io
