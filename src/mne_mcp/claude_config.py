"""
Helpers for registering the MNE MCP server with MCP clients (Claude Code,
OpenAI Codex CLI, PsyClaw, opencode) and installing the companion skills.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from mne_mcp.config import get_results_dir, get_timeout

SERVER_KEY = "mne"
DEFAULT_CLIENTS = ("claude", "codex", "psyclaw", "opencode")


def select_clients(value: str) -> list[str]:
    clients = list(
        dict.fromkeys(c.strip().lower() for c in value.split(",") if c.strip())
    )
    if clients == ["all"]:
        return list(DEFAULT_CLIENTS)
    if not clients:
        raise ValueError("At least one client is required")
    if set(clients) - set(DEFAULT_CLIENTS):
        raise ValueError(f"Select clients from: {', '.join(DEFAULT_CLIENTS)}, all")
    return clients


def get_entrypoint_config() -> tuple[str, list[str]]:
    """Launch with the exact interpreter that performed registration.

    Looking up ``mne-mcp`` on PATH is ambiguous when several virtual
    environments exist. An absolute interpreter path keeps the registered
    server tied to the verified installation.
    """
    executable = str(Path(sys.executable).absolute())
    return executable, ["-m", "mne_mcp", "serve", "--transport", "stdio"]


def server_env() -> dict:
    """Environment variables passed to the server, shared across all clients."""
    return {
        "MNE_MCP_TIMEOUT": str(get_timeout()),
        "MNE_MCP_RESULTS_DIR": str(get_results_dir()),
    }


def build_mcp_server_config() -> dict:
    """Build the Claude Code `mcpServers.mne` config block (stdio)."""
    executable_command, executable_args = get_entrypoint_config()
    return {
        "type": "stdio",
        "command": executable_command,
        "args": executable_args,
        "env": server_env(),
    }


def get_default_settings_path(local: bool = False) -> Path:
    """Return the default Claude Code settings file path."""
    override = os.environ.get("MNE_MCP_CLAUDE_CONFIG")
    if override:
        return Path(override)
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
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


# ─── OpenAI Codex CLI (~/.codex/config.toml) ─────────────────────────────────────


def get_codex_config_path() -> Path:
    override = os.environ.get("MNE_MCP_CODEX_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".codex" / "config.toml"


def _toml_basic_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _codex_block() -> str:
    command, args = get_entrypoint_config()
    args_toml = "[" + ", ".join(_toml_basic_string(a) for a in args) + "]"
    env_toml = (
        "{ "
        + ", ".join(f"{k} = {_toml_basic_string(v)}" for k, v in server_env().items())
        + " }"
    )
    return "\n".join(
        [
            f"[mcp_servers.{SERVER_KEY}]",
            f"command = {_toml_basic_string(command)}",
            f"args = {args_toml}",
            f"env = {env_toml}",
            "enabled = true",
        ]
    )


def _merge_codex_block(text: str, block: str) -> tuple[str, bool]:
    """Insert/replace the `[mcp_servers.mne]` table. Returns (new_text, had_existing)."""
    lines = text.splitlines()
    header = f"[mcp_servers.{SERVER_KEY}]"
    start = next((i for i, ln in enumerate(lines) if ln.strip() == header), None)
    if start is None:
        base = text.rstrip("\n")
        new = (base + "\n\n" + block + "\n") if base else (block + "\n")
        return new, False
    # The block uses an inline env table, so it ends at the next table header.
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].lstrip().startswith("["):
            end = j
            break
    merged = lines[:start] + block.splitlines() + lines[end:]
    return "\n".join(merged).rstrip("\n") + "\n", True


def configure_codex(path: Path | None = None) -> dict:
    """Register the MNE server in the Codex CLI config (TOML)."""
    path = path or get_codex_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    text = path.read_text(encoding="utf-8") if existed else ""
    backup = _backup_settings(path) if existed else None
    new_text, had = _merge_codex_block(text, _codex_block())
    path.write_text(new_text, encoding="utf-8")
    status = "updated" if had else ("added" if existed else "created")
    return {
        "client": "codex",
        "status": status,
        "path": str(path),
        "backup": str(backup) if backup else None,
    }


# ─── opencode (~/.config/opencode/opencode.json) ────────────────────────────────


def get_opencode_config_path() -> Path:
    override = os.environ.get("MNE_MCP_OPENCODE_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".config" / "opencode" / "opencode.json"


def build_opencode_entry() -> dict:
    command, args = get_entrypoint_config()
    return {
        "type": "local",
        "command": [command, *args],
        "enabled": True,
        "environment": server_env(),
    }


def configure_opencode(path: Path | None = None) -> dict:
    """Register the MNE server in opencode's JSON config."""
    path = path or get_opencode_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    data: dict = {}
    if existed:
        content = path.read_text(encoding="utf-8").strip()
        if content:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError(f"Expected a JSON object in {path}")
    data.setdefault("$schema", "https://opencode.ai/config.json")
    mcp = data.setdefault("mcp", {})
    if not isinstance(mcp, dict):
        raise ValueError(f"`mcp` must be a JSON object in {path}")
    previous = mcp.get(SERVER_KEY)
    entry = build_opencode_entry()
    backup = _backup_settings(path) if existed else None
    mcp[SERVER_KEY] = entry
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if previous is None:
        status = "created" if not existed else "added"
    elif previous == entry:
        status = "unchanged"
    else:
        status = "updated"
    return {
        "client": "opencode",
        "status": status,
        "path": str(path),
        "backup": str(backup) if backup else None,
    }


def get_psyclaw_config_path() -> Path:
    override = os.environ.get("MNE_MCP_PSYCLAW_CONFIG")
    return (
        Path(override).expanduser()
        if override
        else Path.home() / ".psyclaw" / "mcp" / "mne.json"
    )


def build_psyclaw_entry() -> dict:
    command, args = get_entrypoint_config()
    # PsyClaw deliberately does not inherit the full parent environment.
    # Forward only runtime/scientific settings, never provider credentials.
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        in {
            "SYSTEMROOT",
            "SystemRoot",
            "WINDIR",
            "USERPROFILE",
            "HOME",
            "TEMP",
            "TMP",
            "TMPDIR",
            "PATH",
            "LANG",
            "MPLCONFIGDIR",
            "MPLBACKEND",
            "MNE_DONTWRITE_HOME",
            "_MNE_FAKE_HOME_DIR",
            "MNE_MCP_TIMEOUT",
            "MNE_MCP_RESULTS_DIR",
            "MNE_MCP_DATA_DIR",
            "MNE_MCP_TEMP_DIR",
            "MNE_MCP_CONFIG",
        }
    }
    env.update(server_env())
    return {
        "id": SERVER_KEY,
        "name": "MNE-Python",
        "transport": "stdio",
        "command": command,
        "args": args,
        "env": env,
        "enabled": True,
        "trusted": True,
    }


def configure_psyclaw(path: Path | None = None) -> dict:
    """Write PsyClaw's standalone server record, preserving custom fields."""
    path = path or get_psyclaw_config_path()
    previous, existed = _load_settings(path)
    if previous.get("id", SERVER_KEY) != SERVER_KEY:
        raise ValueError(f"Refusing to replace a different PsyClaw server in {path}")
    env = previous.get("env", {})
    if not isinstance(env, dict) or any(not isinstance(v, str) for v in env.values()):
        raise ValueError(f"PsyClaw env must be a string mapping in {path}")
    entry = build_psyclaw_entry()
    entry["env"] = {**env, **entry["env"]}
    updated = {**previous, **entry}
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup_settings(path) if existed and updated != previous else None
    if updated != previous:
        path.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    if updated == previous:
        status = "unchanged"
    else:
        status = "updated" if existed else "created"
    return {
        "client": "psyclaw",
        "path": str(path),
        "status": status,
        "backup": str(backup) if backup else None,
    }


# ─── Companion skills ────────────────────────────────────────────────────────────

SKILL_NAMES = (
    "mne-analyst",
    "mne-mcp-guard",
    "mne-methodology-critic",
    "mne-preprocess",
    "mne-artifacts",
    "mne-erp",
    "mne-spectral",
    "mne-timefreq",
    "mne-connectivity",
    "mne-source",
    "mne-decoding",
    "mne-stats",
    "mne-advanced",
    "mne-writeup",
)


def get_skills_source_dir() -> Path | None:
    """Locate the skills/ dir: bundled inside the installed wheel, else the repo checkout."""
    bundled = Path(__file__).resolve().parent / "_bundled" / "skills"
    if bundled.exists():
        return bundled
    candidate = Path(__file__).resolve().parents[2] / "skills"
    return candidate if candidate.exists() else None


def install_skills(dest: Path | None = None) -> dict:
    """Copy the bundled MNE skills (analyst, guard, methodology critic + the analysis suite) into the Claude Code skills directory."""
    dest = dest or (Path.home() / ".claude" / "skills")
    src = get_skills_source_dir()
    if src is None:
        return {
            "installed": [],
            "dest": str(dest),
            "error": "skills source not found (run from a source checkout)",
        }
    dest.mkdir(parents=True, exist_ok=True)
    installed = []
    for name in SKILL_NAMES:
        s = src / name
        if not (s / "SKILL.md").is_file():
            raise ValueError(f"Bundled skill is missing: {name}")
        d = dest / name
        if d.exists():
            backup = (
                dest.parent
                / "mne-mcp-backups"
                / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                / name
            )
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(d, backup)
        shutil.copytree(s, d, dirs_exist_ok=True)
        installed.append(name)
    return {"installed": installed, "dest": str(dest), "error": None}


# ─── Companion subagents ─────────────────────────────────────────────────────────

AGENT_NAMES = ("mne-methodology-critic",)


def get_agents_source_dir() -> Path | None:
    """Locate the agents/ dir: bundled inside the installed wheel, else the repo checkout."""
    bundled = Path(__file__).resolve().parent / "_bundled" / "agents"
    if bundled.exists():
        return bundled
    candidate = Path(__file__).resolve().parents[2] / "agents"
    return candidate if candidate.exists() else None


def install_agents(dest: Path | None = None) -> dict:
    """Copy the bundled subagents (e.g. mne-methodology-critic) into the Claude Code agents dir."""
    dest = dest or (Path.home() / ".claude" / "agents")
    src = get_agents_source_dir()
    if src is None:
        return {
            "installed": [],
            "dest": str(dest),
            "error": "agents source not found (run from a source checkout)",
        }
    dest.mkdir(parents=True, exist_ok=True)
    installed = []
    for name in AGENT_NAMES:
        s = src / f"{name}.md"
        if not s.exists():
            raise ValueError(f"Bundled agent is missing: {name}")
        _backup_settings(dest / f"{name}.md")
        shutil.copy2(s, dest / f"{name}.md")
        installed.append(name)
    return {"installed": installed, "dest": str(dest), "error": None}


# ─── One-click orchestrator ──────────────────────────────────────────────────────

_CLIENT_FUNCS = {
    "claude": lambda: _claude_summary(),
    "codex": configure_codex,
    "opencode": configure_opencode,
    "psyclaw": configure_psyclaw,
}


def _claude_summary() -> dict:
    r = configure_claude_settings()
    return {
        "client": "claude",
        "status": r["status"],
        "path": r["settings_path"],
        "backup": r["backup_path"],
    }


def configure_clients(clients, with_skills: bool = True) -> dict:
    """Register the server in each named client and (optionally) install skills."""
    if not clients:
        raise ValueError("At least one client is required")
    clients = list(dict.fromkeys(clients))
    unknown = set(clients) - _CLIENT_FUNCS.keys()
    if unknown:
        raise ValueError(f"Unknown clients: {sorted(unknown)}")
    if with_skills:
        source = get_skills_source_dir()
        if source is None or any(
            not (source / n / "SKILL.md").is_file() for n in SKILL_NAMES
        ):
            raise ValueError(
                "The installed package has an incomplete skill suite; reinstall MNE-MCP."
            )
        if "claude" in clients:
            agents_source = get_agents_source_dir()
            if agents_source is None or any(
                not (agents_source / f"{n}.md").is_file() for n in AGENT_NAMES
            ):
                raise ValueError(
                    "The installed package has an incomplete agent bundle."
                )
    results = []
    for c in clients:
        func = _CLIENT_FUNCS.get(c)
        if func is None:
            raise ValueError(f"Unknown client: {c}. Valid: {sorted(_CLIENT_FUNCS)}")
        results.append(func())
    skills = None
    if with_skills:
        destinations = {
            "claude": Path.home() / ".claude" / "skills",
            "codex": Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
            / "skills",
            "psyclaw": get_psyclaw_config_path().parent.parent / "skills",
            "opencode": Path(
                os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
            )
            / "opencode"
            / "skills",
        }
        installs = [install_skills(destinations[c]) for c in clients]
        skills = {
            "installed": list(SKILL_NAMES),
            "dest": ", ".join(r["dest"] for r in installs),
            "error": None,
        }
    agents = install_agents() if with_skills and "claude" in clients else None
    return {"clients": results, "skills": skills, "agents": agents}
