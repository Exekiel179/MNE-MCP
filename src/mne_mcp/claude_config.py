"""
Helpers for generating and updating Claude Code MCP configuration.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from mne_mcp.config import get_results_dir, get_timeout

SERVER_KEY = "mne"


def get_entrypoint_config() -> tuple[str, list[str]]:
    """Return the preferred command/args pair for launching this MCP server."""
    installed_entrypoint = shutil.which("mne-mcp")
    if installed_entrypoint:
        return "mne-mcp", ["serve", "--transport", "stdio"]
    return sys.executable, ["-m", "mne_mcp.cli", "serve", "--transport", "stdio"]


def build_mcp_server_config() -> dict:
    """Build the Claude Code `mcpServers.mne` config block."""
    executable_command, executable_args = get_entrypoint_config()

    return {
        "type": "stdio",
        "command": executable_command,
        "args": executable_args,
        "env": {
            "MNE_MCP_TIMEOUT": str(get_timeout()),
            "MNE_MCP_RESULTS_DIR": str(get_results_dir()),
        },
    }


def get_default_settings_path(local: bool = False) -> Path:
    """Return the default Claude Code settings file path."""
    if local:
        return Path.home() / ".claude" / "settings.local.json"
    return Path.home() / ".claude.json"


def _load_settings(path: Path) -> tuple[dict, bool]:
    """Load an existing settings file or return a fresh config."""
    if not path.exists():
        return {}, False

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return {}, True

    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data, True


def _backup_settings(path: Path) -> Path | None:
    """Create a timestamped backup of a settings file if it exists."""
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.backup.{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def configure_claude_settings(
    settings_path: Path | None = None,
    *,
    local: bool = False,
) -> dict:
    """
    Merge the MNE MCP entry into Claude Code user config and write the file.

    Returns a status payload describing what changed.
    """
    path = settings_path or get_default_settings_path(local=local)
    path.parent.mkdir(parents=True, exist_ok=True)

    settings, existed = _load_settings(path)
    servers = settings.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"`mcpServers` must be a JSON object in {path}")

    new_entry = build_mcp_server_config()
    previous_entry = servers.get(SERVER_KEY)

    backup_path = _backup_settings(path) if existed else None
    servers[SERVER_KEY] = new_entry

    path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if previous_entry is None:
        status = "created"
    elif previous_entry == new_entry:
        status = "unchanged"
    else:
        status = "updated"

    return {
        "status": status,
        "settings_path": str(path),
        "backup_path": str(backup_path) if backup_path else None,
        "entry": new_entry,
    }
