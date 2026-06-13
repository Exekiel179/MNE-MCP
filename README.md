<!-- mcp-name: io.github.Exekiel179/mne-mcp -->

# MNE-MCP

[![CI](https://github.com/Exekiel179/MNE-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/Exekiel179/MNE-MCP/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io)

**English** | [简体中文](README.zh-CN.md)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives AI assistants
direct, conversational access to **[MNE-Python](https://mne.tools/)** for analyzing human
neurophysiology data — **EEG, MEG, sEEG, ECoG, and fNIRS**.

Describe your analysis in plain language — MNE-MCP loads your recording, runs the MNE pipeline
(filtering, ICA, epoching, ERP/ERF averaging, time-frequency, source-level work via code),
saves the figures, and explains the results.

> Works in **Claude Code** and **opencode** (any MCP-capable client). Pairs with bundled
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
- MNE is a huge pure-Python API. MNE-MCP gives you **38 structured tools** spanning the common
  pipeline *and* advanced analysis (source localization, connectivity, decoding), plus an
  **`mne_run_code`** escape hatch that reaches the entire MNE API in the same live session.
- Defaults (line frequency, montage, filter band, rejection threshold, ICA settings, epoch window,
  dirs, timeout) are **user-configurable** via an interactive `mne-mcp configure` wizard.

---

## Requirements

- Python 3.10+
- [MNE-Python](https://mne.tools/) ≥ 1.6 — **provisioned on demand** (see [Lightweight by default](#lightweight-by-default--on-demand-backend)); install it up front with `mne-mcp[analysis]` if you prefer
- `scikit-learn` for ICA (in the `ica` / `full` extras, or `mne-mcp install-backend`)
- Claude Code (or any MCP client) with MCP support

> Cross-platform: unlike a closed engine, MNE-Python is pure Python, so analysis tools work on
> Windows, macOS, and Linux.

---

## Quick Install

```bash
git clone https://github.com/Exekiel179/MNE-MCP.git
cd MNE-MCP

# 1. Install (pulls in mne, numpy, scipy, matplotlib, scikit-learn for ICA)
pip install -e ".[ica]"

# 2. Register in your MCP client(s) — Claude Code, Codex, opencode — and install skills
mne-mcp setup

# 3. Restart your client
```

Or run the **one-shot installer** (creates the venv, installs, verifies, registers, installs skills):

```powershell
pwsh -File scripts\install.ps1     # Windows
```
```bash
bash scripts/install.sh            # macOS / Linux
```

See [QUICK_START.md](QUICK_START.md) for a guided first session, or [docs/INSTALL.md](docs/INSTALL.md)
for the full guide.

> **One command does everything:** `mne-mcp setup` registers the `mne` server in **Claude Code,
> Codex, and opencode** (whichever you use) *and* installs the companion skills. Narrow it with
> `--clients claude,codex`. The `mne_*` tools require **one client restart** afterwards (MCP servers
> load at startup).

### Run via `uvx` / `pipx` (standard MCP — recommended)

`mne-mcp` is [published on PyPI](https://pypi.org/project/mne-mcp/), so the most portable path is the
standard MCP launcher — no clone, no `setup`. Add this to your client config (`~/.claude.json` for
Claude Code, `claude_desktop_config.json` for Claude Desktop):

```json
{ "mcpServers": { "mne": { "command": "uvx", "args": ["--from", "mne-mcp[ica]", "mne-mcp", "serve", "--transport", "stdio"] } } }
```

`uvx` (from [uv](https://docs.astral.sh/uv/)) fetches and runs `mne-mcp` on demand. The `[ica]` extra
pulls in scikit-learn so ICA works out of the box; swap it for **`mne-mcp[full]`** to also get the
advanced tools (source localization, connectivity, decoding, BIDS). Because MNE pulls in a large
scientific stack, a **persistent** install is usually snappier than re-resolving each run:

```bash
pipx install "mne-mcp[ica]"        # or: uv tool install "mne-mcp[ica]"  (use [full] for advanced tools)
```

then set the config `command` to `mne-mcp` with `args: ["serve", "--transport", "stdio"]`. The source
install above remains the path for development.

> **Skills are bundled in the package (since 0.2.2).** A PyPI install carries the skill suite and the
> `mne-methodology-critic` agent, so one extra command installs them — `mne-mcp setup` (after `pipx`/
> `uv tool install`) or `uvx mne-mcp setup`. No clone required.

### Lightweight by default — on-demand backend

Since **0.3.0** the package itself is tiny: a bare `pip install mne-mcp` / `pipx install mne-mcp`
pulls in only the MCP protocol layer (`mcp`, `fastmcp`, `pydantic`, `python-dotenv`), so it installs
in seconds. The heavy scientific stack (MNE-Python + numpy/scipy/matplotlib/pandas, and scikit-learn
for ICA) is **provisioned the first time an analysis needs it**:

- In a session, just ask — when a tool reports the backend is missing, call the **`mne_install_backend`**
  tool (or it is offered by `mne_check_status`). It `pip install`s into the server's own environment and
  becomes usable **without a client restart**.
- From a terminal: `mne-mcp install-backend` (add `--profile full` for source localization / connectivity
  / decoding / BIDS).

```bash
pipx install mne-mcp            # tiny, instant
mne-mcp install-backend        # add MNE + ICA when you're ready (or let the tool do it)
```

Prefer everything up front? Install an extra instead: **`mne-mcp[analysis]`** (MNE core), **`[ica]`**
(+ scikit-learn), or **`[full]`** (+ advanced tools). For ephemeral `uvx` runs, pin the extra in the
config (`--from mne-mcp[ica]`, as above) since an `uvx` environment is discarded between runs, so an
on-demand install would not persist.

---

## Configuration

### Auto-configure (recommended)

```bash
mne-mcp setup                          # Claude Code + Codex + opencode, plus skills
mne-mcp setup --clients claude,codex   # only specific clients
mne-mcp configure-claude               # Claude Code only (subset of setup)
```

`setup` registers the `mne` server in each client and installs the skills, writing a timestamped
backup of any file it touches:

| Client | Config file | Key |
|---|---|---|
| Claude Code | `~/.claude.json` | `mcpServers.mne` |
| OpenAI Codex CLI | `~/.codex/config.toml` | `[mcp_servers.mne]` |
| opencode | `~/.config/opencode/opencode.json` | `mcp.mne` |

### Manual setup

Point `command` at the Python where you installed the package (or `mne-mcp` if it is on PATH).

**Claude Code** — `~/.claude.json`:
```json
{ "mcpServers": { "mne": { "type": "stdio", "command": "mne-mcp", "args": ["serve", "--transport", "stdio"] } } }
```

**Codex CLI** — `~/.codex/config.toml`:
```toml
[mcp_servers.mne]
command = "mne-mcp"
args = ["serve", "--transport", "stdio"]
enabled = true
```

**opencode** — `~/.config/opencode/opencode.json`:
```json
{ "mcp": { "mne": { "type": "local", "command": ["mne-mcp", "serve", "--transport", "stdio"], "enabled": true } } }
```

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

### Install the Skills

`mne-mcp setup` installs all bundled skills automatically. To do it by hand, copy every folder under
`skills/` into your skills dir — the suite is `mne-analyst`, `mne-mcp-guard`, `mne-methodology-critic`,
plus the per-category analysis skills (`mne-preprocess`, `mne-artifacts`, `mne-erp`, `mne-spectral`,
`mne-timefreq`, `mne-connectivity`, `mne-source`, `mne-decoding`, `mne-stats`, `mne-advanced`) and the
write-up skill (`mne-writeup`):

```cmd
set SKILLS_DIR=%USERPROFILE%\.claude\skills
for %S in (mne-analyst mne-mcp-guard mne-methodology-critic mne-preprocess mne-artifacts mne-erp mne-spectral mne-timefreq mne-connectivity mne-source mne-decoding mne-stats mne-advanced mne-writeup) do xcopy /E /I skills\%S "%SKILLS_DIR%\%S"
```

> `mne-mcp setup` also installs the `mne-methodology-critic` **subagent** to `~/.claude/agents/` (the
> skills' Phase 3 dispatches it in an isolated context). Copy `agents\mne-methodology-critic.md` there
> by hand if installing manually.

Restart your client after installation. (Skills are a Claude Code feature; Codex / opencode use the
MCP server directly.)

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

## Available Tools (38)

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

### Time-frequency (1)
`mne_tfr_morlet`

### Advanced analysis (6)
`mne_decode` (MVPA) · `mne_connectivity` · `mne_compute_noise_cov` · `mne_make_forward` ·
`mne_apply_inverse` · `mne_plot_source_estimate`

### Export (1)
`mne_save`

Anything still not covered — BIDS, custom statistics, beamformers, autoreject — is reachable through
**`mne_run_code`** in the same live session. See [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) for full
parameter details. Advanced tools need the `[full]` extra (`pip install -e ".[full]"`).

---

## Development

```bash
# Compile check
python -m compileall src/mne_mcp

# Run tests
pytest

# CLI commands
mne-mcp status            # Check environment
mne-mcp setup             # Register in Claude Code / Codex / opencode + install skills
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
