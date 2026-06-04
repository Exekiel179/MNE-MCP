"""
Configuration loading and capability detection for MNE MCP.

Unlike SPSS (a closed external engine), MNE-Python is an importable library,
so "capabilities" here means: is `mne` importable, what version, and which
optional companions (scikit-learn for ICA, matplotlib for plotting) are present.
"""

import json
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from project root first and let repo-local settings override inherited shell values.
load_dotenv(_PROJECT_ROOT / ".env", override=True)
load_dotenv()


# ─── User-configurable defaults (set via `mne-mcp configure`) ───────────────────
#
# These are *preferences*, not MNE facts. They seed the structured tools' defaults
# so a user can, e.g., make 60 Hz line noise and a biosemi64 montage the norm.
# Precedence for the runtime values: environment variable > config file > built-in.

DEFAULT_CONFIG: dict = {
    "line_freq": 50,  # mains line-noise frequency (50 CN/EU, 60 US)
    "default_montage": "standard_1020",
    "filter_l_freq": 0.1,  # default high-pass edge (Hz)
    "filter_h_freq": 40.0,  # default low-pass edge (Hz)
    "reject_eeg_uv": None,  # default peak-to-peak EEG rejection in microvolts
    "ica_method": "fastica",  # fastica | infomax | picard
    "ica_n_components": None,  # int, float (variance frac), or null
    "epoch_tmin": -0.2,  # default epoch start (s)
    "epoch_tmax": 0.5,  # default epoch end (s)
    "results_dir": None,  # null → temp dir
    "data_dir": None,  # null → current dir
    "timeout": 300,  # per-operation timeout (s)
}

# Keys that are validated as one of a fixed set.
CONFIG_CHOICES = {
    "line_freq": [50, 60],
    "ica_method": ["fastica", "infomax", "picard"],
}


def get_config_path() -> Path:
    """Path of the persisted defaults file (override with MNE_MCP_CONFIG)."""
    env = os.environ.get("MNE_MCP_CONFIG")
    if env:
        return Path(env)
    return Path.home() / ".mne-mcp" / "config.json"


def load_config() -> dict:
    """Return built-in defaults merged with the on-disk config file."""
    cfg = dict(DEFAULT_CONFIG)
    path = get_config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
        except (ValueError, OSError):
            pass
    return cfg


def save_config(values: dict) -> Path:
    """Merge ``values`` into the config file and write it. Returns the path."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = load_config()
    current.update({k: v for k, v in values.items() if k in DEFAULT_CONFIG})
    path.write_text(
        json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def reset_config() -> Path:
    """Delete the config file (revert to built-in defaults). Returns the path."""
    path = get_config_path()
    if path.exists():
        path.unlink()
    return path


def get_config_value(key: str):
    return load_config().get(key, DEFAULT_CONFIG.get(key))


def _get_positive_int_env(name: str, default: int) -> int:
    """Return a positive integer env var value or a default."""
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


# ─── Resolved default accessors (used by the operation layer) ────────────────────


def get_default_montage() -> str:
    return get_config_value("default_montage") or "standard_1020"


def get_filter_band() -> tuple:
    return (get_config_value("filter_l_freq"), get_config_value("filter_h_freq"))


def get_line_freq() -> float:
    return get_config_value("line_freq") or 50


def get_reject_eeg() -> float | None:
    """Configured EEG rejection threshold in volts (config stores microvolts)."""
    uv = get_config_value("reject_eeg_uv")
    return float(uv) * 1e-6 if uv else None


def get_ica_method() -> str:
    return get_config_value("ica_method") or "fastica"


def get_ica_n_components():
    return get_config_value("ica_n_components")


def get_epoch_window() -> tuple:
    return (get_config_value("epoch_tmin"), get_config_value("epoch_tmax"))


def get_timeout() -> int:
    """Return the per-operation execution timeout in seconds (default 300).

    Precedence: MNE_MCP_TIMEOUT env > config file > 300. Some MNE steps (ICA,
    time-frequency, source localization) are genuinely slow, so the default is
    generous.
    """
    if os.environ.get("MNE_MCP_TIMEOUT"):
        return _get_positive_int_env("MNE_MCP_TIMEOUT", 300)
    try:
        value = int(get_config_value("timeout") or 300)
    except (TypeError, ValueError):
        return 300
    return value if value > 0 else 300


def get_data_dir() -> Path:
    """Return the default directory to scan for data files (env > config > cwd)."""
    env = os.environ.get("MNE_MCP_DATA_DIR")
    if env:
        return Path(env)
    cfg = get_config_value("data_dir")
    return Path(cfg) if cfg else Path.cwd()


def get_temp_dir() -> Path:
    """Return the directory for temporary MNE MCP files, creating it if needed."""
    default = Path(tempfile.gettempdir()) / "mne-mcp"
    temp_dir = Path(os.environ.get("MNE_MCP_TEMP_DIR", str(default)))
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_results_dir() -> Path:
    """Return directory where figures/exports are saved (env > config > temp)."""
    env = os.environ.get("MNE_MCP_RESULTS_DIR")
    if env:
        out_dir = Path(env)
    else:
        cfg = get_config_value("results_dir")
        out_dir = Path(cfg) if cfg else (get_temp_dir() / "results")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def get_runtime_config() -> dict:
    """Return the effective runtime configuration used for MNE execution."""
    return {
        "timeout": get_timeout(),
        "temp_dir": str(get_temp_dir()),
        "results_dir": str(get_results_dir()),
        "data_dir": str(get_data_dir()),
        "config_path": str(get_config_path()),
    }


def _safe_version(module_name: str) -> str | None:
    try:
        mod = __import__(module_name)
        return getattr(mod, "__version__", "unknown")
    except Exception:
        return None


def detect_capabilities() -> dict:
    """
    Detect what neurophysiology-analysis capabilities are available.

    Returns a dict with:
        mne: bool
        mne_version: str | None
        numpy_version / scipy_version / pandas_version / matplotlib_version: str | None
        sklearn: bool  (required for ICA)
        sklearn_version: str | None
    """
    caps: dict = {
        "mne": False,
        "mne_version": None,
        "numpy_version": None,
        "scipy_version": None,
        "pandas_version": None,
        "matplotlib_version": None,
        "sklearn": False,
        "sklearn_version": None,
    }

    mne_version = _safe_version("mne")
    if mne_version is not None:
        caps["mne"] = True
        caps["mne_version"] = mne_version

    caps["numpy_version"] = _safe_version("numpy")
    caps["scipy_version"] = _safe_version("scipy")
    caps["pandas_version"] = _safe_version("pandas")
    caps["matplotlib_version"] = _safe_version("matplotlib")

    sklearn_version = _safe_version("sklearn")
    if sklearn_version is not None:
        caps["sklearn"] = True
        caps["sklearn_version"] = sklearn_version

    return caps
