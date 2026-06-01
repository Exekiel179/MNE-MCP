#requires -Version 5.1
<#
.SYNOPSIS
  One-shot installer for MNE-MCP (Windows / PowerShell).
.DESCRIPTION
  Creates an isolated virtual environment, installs MNE-MCP (+ ICA extra),
  verifies the install, registers the `mne` server in Claude Code, and installs
  the companion skills. Idempotent: safe to re-run.
.EXAMPLE
  pwsh -File scripts\install.ps1
.EXAMPLE
  pwsh -File scripts\install.ps1 -Mirror          # use Tsinghua PyPI mirror (faster in CN)
  pwsh -File scripts\install.ps1 -SkipClaude       # install only, don't touch ~/.claude.json
#>
[CmdletBinding()]
param(
    [string]$Python = "python",                      # interpreter used only when creating the venv
    [string]$Clients = "claude,codex,opencode",      # which MCP clients to configure
    [switch]$Mirror,                                 # use a faster PyPI mirror
    [switch]$SkipConfigure                           # install only; don't register clients / install skills
)

$ErrorActionPreference = "Stop"
function Info($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "    $m" -ForegroundColor Green }

$repo   = Split-Path $PSScriptRoot -Parent
$venv   = Join-Path $repo ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"
$mirrorArgs = if ($Mirror) { @("-i", "https://pypi.tuna.tsinghua.edu.cn/simple") } else { @() }

Info "MNE-MCP installer"
Write-Host "    Repo: $repo"

# 1) Virtual environment (reuse if present)
if (-not (Test-Path $venvPy)) {
    $pyv = (& $Python -c "import sys;print('%d.%d'%sys.version_info[:2])").Trim()
    if ([version]$pyv -lt [version]"3.10") { throw "Python >= 3.10 required (found $pyv via '$Python')." }
    Info "Creating virtual environment (.venv) with Python $pyv"
    & $Python -m venv $venv
} else {
    Info "Reusing existing virtual environment (.venv)"
}
$vv = (& $venvPy -c "import sys;print('%d.%d.%d'%sys.version_info[:3])").Trim()
Ok "venv Python $vv"

# 2) Install MNE-MCP + ICA extra
Info "Installing MNE-MCP and dependencies (this can take a few minutes)"
Push-Location $repo
try {
    & $venvPy -m pip install --upgrade pip @mirrorArgs
    & $venvPy -m pip install -e ".[ica]" @mirrorArgs
} finally { Pop-Location }

# 3) Verify
Info "Verifying installation"
& $venvPy -m mne_mcp.cli status
$mneOk = (& $venvPy -c "import mne,sys;sys.stdout.write('ok')") 2>$null
if ($mneOk -ne "ok") { throw "MNE-Python failed to import after install." }
Ok "MNE-Python import OK"

# 4) Register the server in the chosen clients + install skills (one step)
if (-not $SkipConfigure) {
    Info "Registering 'mne' in clients ($Clients) and installing skills"
    & $venvPy -m mne_mcp.cli setup --clients $Clients
} else {
    Info "Skipped client configuration (-SkipConfigure)"
}

Write-Host ""
Info "Done."
Write-Host "    NEXT STEP: restart Claude Code so the 'mne' tools and skills load." -ForegroundColor Yellow
Write-Host "    Then say:  检查一下 MNE 环境   (should call mne_check_status)"
Write-Host "    Optional:  $venvPy -m mne_mcp.cli configure   # set default line freq / montage / etc."
