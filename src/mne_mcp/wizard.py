"""
Interactive configuration wizard for MNE MCP (`mne-mcp configure`).

Lets a user set the default parameters the structured tools fall back to — line
frequency, default montage, filter band, rejection threshold, ICA method/components,
epoch window, directories, and timeout — and persists them to the config file.

Also supports non-interactive use:
    mne-mcp configure --show
    mne-mcp configure --reset
    mne-mcp configure --set line_freq=60 default_montage=biosemi64 reject_eeg_uv=120
"""

from __future__ import annotations

import sys

from mne_mcp.config import (
    CONFIG_CHOICES,
    DEFAULT_CONFIG,
    get_config_path,
    load_config,
    reset_config,
    save_config,
)

# Ordered fields shown by the interactive wizard: (key, label, type)
# types: int | float | floatn(nullable) | numn(int/float/null) | str | strn(nullable)
FIELDS = [
    ("line_freq", "Mains line-noise frequency (Hz, 50=CN/EU 60=US)", "int"),
    ("default_montage", "Default electrode montage", "str"),
    ("filter_l_freq", "Default high-pass edge (Hz, 'none' to disable)", "floatn"),
    ("filter_h_freq", "Default low-pass edge (Hz, 'none' to disable)", "floatn"),
    ("reject_eeg_uv", "Default EEG rejection (peak-to-peak µV, 'none'=off)", "floatn"),
    ("ica_method", "Default ICA method (fastica/infomax/picard)", "str"),
    (
        "ica_n_components",
        "Default ICA n_components (int, 0.xx frac, or 'none')",
        "numn",
    ),
    ("epoch_tmin", "Default epoch start (s)", "float"),
    ("epoch_tmax", "Default epoch end (s)", "float"),
    ("results_dir", "Results/figures directory ('none'=temp)", "strn"),
    ("data_dir", "Default data directory ('none'=current dir)", "strn"),
    ("timeout", "Per-operation timeout (s)", "int"),
]

_TYPES = {key: typ for key, _, typ in FIELDS}

_NULL_TOKENS = {"none", "null", ""}


def coerce(key: str, raw: str):
    """Convert a raw string to the typed value for ``key``."""
    typ = _TYPES[key]
    raw = raw.strip()
    if typ.endswith("n") and raw.lower() in _NULL_TOKENS:
        return None
    if typ == "int":
        return int(raw)
    if typ in ("float", "floatn"):
        return float(raw)
    if typ == "numn":
        return float(raw) if ("." in raw or "e" in raw.lower()) else int(raw)
    return raw  # str / strn


def validate(key: str, value) -> None:
    """Raise ValueError if ``value`` is invalid for ``key``."""
    if value is None:
        return
    if key in CONFIG_CHOICES and value not in CONFIG_CHOICES[key]:
        raise ValueError(f"{key} must be one of {CONFIG_CHOICES[key]} (got {value!r})")
    if key == "default_montage":
        try:
            import mne

            builtins = mne.channels.get_builtin_montages()
            if value not in builtins:
                sys.stderr.write(
                    f"  warning: '{value}' is not a built-in montage; keeping it anyway.\n"
                )
        except Exception:
            pass


def show_config() -> None:
    cfg = load_config()
    print(f"=== MNE MCP defaults ===  ({get_config_path()})")
    for key, label, _ in FIELDS:
        marker = "" if cfg[key] == DEFAULT_CONFIG[key] else "  *"
        print(f"  {key:18s} = {cfg[key]!r}{marker}")
    print("\n(* = differs from built-in default)")


def set_values(pairs: list[str]) -> None:
    """Apply a list of 'key=value' strings non-interactively."""
    updates = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Expected key=value, got {pair!r}")
        key, raw = pair.split("=", 1)
        key = key.strip()
        if key not in DEFAULT_CONFIG:
            raise ValueError(
                f"Unknown config key: {key}. Valid: {sorted(DEFAULT_CONFIG)}"
            )
        value = coerce(key, raw)
        validate(key, value)
        updates[key] = value
    path = save_config(updates)
    print(f"Updated {len(updates)} setting(s) → {path}")
    show_config()


def run_wizard() -> None:
    """Interactive prompt loop. Blank input keeps the current value."""
    cfg = load_config()
    print("=== MNE MCP configuration ===")
    print("Press Enter to keep the current value shown in [brackets].")
    print(f"Config file: {get_config_path()}\n")

    updates = {}
    for key, label, _ in FIELDS:
        current = cfg[key]
        while True:
            try:
                raw = input(f"{label} [{current}]: ")
            except EOFError:
                raw = ""
            if raw.strip() == "":
                break  # keep current
            try:
                value = coerce(key, raw)
                validate(key, value)
            except ValueError as e:
                print(f"  invalid: {e}")
                continue
            updates[key] = value
            break

    if not updates:
        print("\nNo changes made.")
        return
    path = save_config(updates)
    print(f"\nSaved {len(updates)} change(s) → {path}")
    show_config()
    print("\nRestart Claude Code (or the MCP server) for changes to take effect.")
