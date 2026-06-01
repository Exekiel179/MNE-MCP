---
name: mne-mcp-setup
description: >
  Install, configure, and verify MNE-MCP end to end in one go. Use when the user wants to set up /
  install / configure MNE-MCP, get MNE-Python working inside Claude Code or opencode, register the
  `mne` MCP server, install the mne-analyst / mne-mcp-guard skills, or fix a broken MNE-MCP setup.
  Triggers: 安装 mne-mcp, 配置 mne-mcp, 一键安装, 装一下脑电 mcp, set up mne mcp, install mne-mcp,
  接入 Claude Code, 注册 mne 服务器, mne mcp 装不上 / 连不上.
---

# MNE-MCP Setup

Set up MNE-MCP with a **single install script**, then hand off. Do the work for the user: run the
command, read its output, fix anything that fails, and report clearly.

> **The one limit you must state up front.** An MCP server is loaded by the client **at startup**.
> This skill installs and configures everything in one shot, but the `mne_*` tools only become
> callable **after the user restarts Claude Code / opencode**. You cannot install and then call the
> MCP tools in the same session — always end with "restart, then test". (This is how MCP works, not a
> limitation of the script.)

## Step 1 — Locate the repo

Ask where the MNE-MCP folder is, or clone it:
```bash
git clone https://github.com/Exekiel179/MNE-MCP.git
```
Call that folder `<REPO>`.

## Step 2 — Run the one-shot installer

It is idempotent (safe to re-run) and does the whole job: create `.venv`, install MNE-MCP + the ICA
extra, verify, register the `mne` server in Claude Code (backing up `~/.claude.json` first), and copy
the `mne-analyst` + `mne-mcp-guard` skills.

**Windows (PowerShell):**
```powershell
pwsh -File <REPO>\scripts\install.ps1
```
**macOS / Linux:**
```bash
bash <REPO>/scripts/install.sh
```

Useful flags / env: `-Mirror` / `MIRROR=1` (faster PyPI mirror in CN); `-SkipClaude` / `SKIP_CLAUDE=1`
(install only, don't touch `~/.claude.json`); `-SkipSkills` / `SKIP_SKILLS=1`. Pass a specific
interpreter with `-Python C:\path\python.exe` / `PYTHON=python3.12`.

**Read the output.** Success ends with "Done." and a yellow "restart" line, and the status block shows
`MNE-Python : OK`. If it errors, jump to [Troubleshooting](#troubleshooting).

## Step 3 — (Optional) set defaults

If the user has preferences, set them now (no restart needed for these):
```bash
<REPO>/.venv/Scripts/python.exe -m mne_mcp.cli configure --set line_freq=60 default_montage=biosemi64 reject_eeg_uv=120
```
(macOS/Linux: `<REPO>/.venv/bin/python -m mne_mcp.cli configure`)

## Step 4 — Restart and verify

1. Tell the user to **restart Claude Code (or opencode)** — required for the new server + skills to load.
2. After restart, confirm by asking them to type `检查一下 MNE 环境` (should call `mne_check_status`).
3. First real run, e.g.: `加载 sub-01_raw.fif，画功率谱`.

## If the script can't be used (manual fallback)

Run, from `<REPO>`, the same steps the script automates:
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[ica]"        # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m mne_mcp.cli status              # verify -> MNE-Python OK
.venv/Scripts/python -m mne_mcp.cli configure-claude    # register (uses THIS interpreter)
# copy skills/mne-analyst and skills/mne-mcp-guard into ~/.claude/skills
```
Key rule: run `configure-claude` with the **venv's** interpreter so the registered launch command pins
to the right Python.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python` not found / version < 3.10 | Install Python 3.10+, or pass `-Python` / `PYTHON=` pointing to a 3.10+ interpreter |
| PowerShell won't run the script | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or `pwsh -ExecutionPolicy Bypass -File ...` |
| pip install slow / fails (CN) | Re-run with `-Mirror` / `MIRROR=1` |
| After restart, `mne` tools missing | Check the `command` in `~/.claude.json` points to `<REPO>\.venv\...\python` and that `... -m mne_mcp.cli status` works |
| ICA says scikit-learn missing | Re-run the installer (it includes the `[ica]` extra) |

## Notes

- Reversible: `configure-claude` backs up `~/.claude.json`; skills are plain folders under `~/.claude/skills`.
- This skill cannot call `mne_*` tools in the same session it installs them (MCP loads at startup).
- If the user would rather not run a separate MCP server, MNE can also be driven purely via the Bash
  tool (no server, no restart) — mention this only if they ask; it trades away the persistent session
  and the structured tool surface.
