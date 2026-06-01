---
name: mne-mcp-setup
description: >
  Install, configure, and verify the MNE-MCP server end to end. Use when the user wants to set up /
  install / configure MNE-MCP, get MNE-Python working inside Claude Code or opencode, register the
  `mne` MCP server, install the mne-analyst / mne-mcp-guard skills, or troubleshoot a broken MNE-MCP
  setup. Triggered by phrases like 安装 mne-mcp, 配置 mne-mcp, 一键安装, set up mne mcp, install mne-mcp,
  接入 Claude Code, 注册 mne 服务器, 脑电 MCP 装不上.
---

# MNE-MCP Setup

This skill drives the full install + configuration of MNE-MCP by running shell commands. Follow the
steps in order, **run each command and read its output before continuing**, and adapt the commands to
the user's OS (Windows PowerShell vs macOS/Linux bash).

> **Important limitation — read first.** An MCP server is loaded by Claude Code/opencode **at
> startup**. So this skill can fully *install and configure* MNE-MCP, but the `mne_*` tools will
> **not become callable until the client is restarted**. You cannot install and then call the MCP
> tools in the same session. End by telling the user to restart, then how to test.

## Step 0 — Locate the project & Python

1. Ask the user where the MNE-MCP repo is (or `git clone https://github.com/Exekiel179/MNE-MCP.git`
   if they don't have it). Treat that folder as `<REPO>`.
2. Verify Python ≥ 3.10: `python --version` (or `python3 --version`). If older/missing, stop and tell
   the user to install Python 3.10+.
3. Prefer `uv` if available (`uv --version`); otherwise use `python -m venv`.

## Step 1 — Create an isolated environment + install

Windows (PowerShell):
```powershell
cd <REPO>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[ica]"
```
macOS / Linux:
```bash
cd <REPO>
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[ica]"
```
With uv (faster): `uv venv .venv --python 3.12 && uv pip install --python .venv/<bin>/python -e ".[ica]"`.

If install is slow in China, append `-i https://pypi.tuna.tsinghua.edu.cn/simple`.

## Step 2 — Verify the install

Run the **venv's** `mne-mcp` (not a global one):
- Windows: `.\.venv\Scripts\mne-mcp.exe status`
- macOS/Linux: `./.venv/bin/mne-mcp status`

Confirm the output shows `MNE-Python : OK v...`. If `scikit-learn` is missing, re-run the install with
the `[ica]` extra.

## Step 3 — Register the MCP server in Claude Code

Run `configure-claude` **with the venv's interpreter** so the registered launch command pins to the
right Python:
- Windows: `.\.venv\Scripts\mne-mcp.exe configure-claude`
- macOS/Linux: `./.venv/bin/mne-mcp configure-claude`

This merges `mcpServers.mne` into `~/.claude.json` and writes a timestamped backup first. Tell the user
a backup was made (`~/.claude.json.backup.*`) so the change is reversible. For **opencode**, instead add
the same stdio server (command = the venv python, args = `-m mne_mcp.cli serve --transport stdio`) to
its MCP config.

## Step 4 — Install the companion skills

Windows (cmd):
```cmd
set SKILLS_DIR=%USERPROFILE%\.claude\skills
xcopy /E /I <REPO>\skills\mne-analyst    "%SKILLS_DIR%\mne-analyst"
xcopy /E /I <REPO>\skills\mne-mcp-guard  "%SKILLS_DIR%\mne-mcp-guard"
```
macOS / Linux:
```bash
mkdir -p ~/.claude/skills
cp -r <REPO>/skills/mne-analyst   ~/.claude/skills/
cp -r <REPO>/skills/mne-mcp-guard ~/.claude/skills/
```

## Step 5 — (Optional) set analysis defaults

If the user has preferences (e.g. 60 Hz mains, a specific montage), run the wizard non-interactively:
`mne-mcp configure --set line_freq=60 default_montage=biosemi64 reject_eeg_uv=120`

## Step 6 — Restart and hand off

1. Tell the user to **restart Claude Code** (or opencode) — this is required for the new MCP server and
   skills to load.
2. After restart, they can verify and start working by typing:
   - `检查一下 MNE 环境`  → should call `mne_check_status`
   - `加载 <file>_raw.fif，画功率谱`  → first real analysis
3. If, after restart, the `mne` tools don't appear: confirm the registered `command` in `~/.claude.json`
   points to the venv's Python, and that `mne-mcp status` works from that interpreter.

## Notes

- This skill **cannot** call `mne_*` tools in the same session it installs them (MCP loads at startup).
- It modifies `~/.claude.json` and `~/.claude/skills` — both are reversible (backup + folder deletion).
- If the user would rather **not run a separate MCP server at all**, MNE can also be driven purely
  through code via the Bash tool; mention this alternative only if they ask.
