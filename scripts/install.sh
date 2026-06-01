#!/usr/bin/env bash
# One-shot installer for MNE-MCP (macOS / Linux).
#
# Creates an isolated virtual environment, installs MNE-MCP (+ ICA extra),
# verifies, registers the `mne` server in Claude Code, and installs the
# companion skills. Idempotent: safe to re-run.
#
# Usage:
#   bash scripts/install.sh
#   MIRROR=1 bash scripts/install.sh                 # faster PyPI mirror (CN)
#   CLIENTS=claude,codex bash scripts/install.sh     # only configure these clients
#   SKIP_CONFIGURE=1 bash scripts/install.sh         # install only; don't register clients / skills
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
CLIENTS="${CLIENTS:-claude,codex,opencode}"
VENV="$REPO/.venv"
VENVPY="$VENV/bin/python"
MIRROR_ARGS=()
[ "${MIRROR:-0}" = "1" ] && MIRROR_ARGS=(-i https://pypi.tuna.tsinghua.edu.cn/simple)

info() { printf '\033[36m==> %s\033[0m\n' "$1"; }
ok()   { printf '\033[32m    %s\033[0m\n' "$1"; }

info "MNE-MCP installer"
echo "    Repo: $REPO"

# 1) Virtual environment (reuse if present)
if [ ! -x "$VENVPY" ]; then
    pyv="$("$PYTHON" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
    if [ "$(printf '%s\n3.10\n' "$pyv" | sort -V | head -1)" != "3.10" ]; then
        echo "Python >= 3.10 required (found $pyv via '$PYTHON')." >&2; exit 1
    fi
    info "Creating virtual environment (.venv) with Python $pyv"
    "$PYTHON" -m venv "$VENV"
else
    info "Reusing existing virtual environment (.venv)"
fi
ok "venv Python $("$VENVPY" -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])')"

# 2) Install MNE-MCP + ICA extra
info "Installing MNE-MCP and dependencies (this can take a few minutes)"
( cd "$REPO" && "$VENVPY" -m pip install --upgrade pip "${MIRROR_ARGS[@]}" \
              && "$VENVPY" -m pip install -e ".[ica]" "${MIRROR_ARGS[@]}" )

# 3) Verify
info "Verifying installation"
"$VENVPY" -m mne_mcp.cli status
"$VENVPY" -c "import mne" && ok "MNE-Python import OK"

# 4) Register the server in the chosen clients + install skills (one step)
if [ "${SKIP_CONFIGURE:-0}" != "1" ]; then
    info "Registering 'mne' in clients ($CLIENTS) and installing skills"
    "$VENVPY" -m mne_mcp.cli setup --clients "$CLIENTS"
else
    info "Skipped client configuration (SKIP_CONFIGURE=1)"
fi

echo
info "Done."
printf '\033[33m    NEXT STEP: restart Claude Code so the "mne" tools and skills load.\033[0m\n'
echo  '    Then say:  检查一下 MNE 环境   (should call mne_check_status)'
echo  "    Optional:  $VENVPY -m mne_mcp.cli configure   # set default line freq / montage / etc."
