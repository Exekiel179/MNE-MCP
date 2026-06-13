"""
On-demand provisioning of the heavy analysis backend.

The MCP server itself is intentionally lightweight: installing the ``mne-mcp``
package pulls in only the protocol layer (``mcp``, ``fastmcp``, ``pydantic``,
``python-dotenv``). The scientific stack that actually performs the analysis —
MNE-Python plus numpy/scipy/matplotlib/pandas, and scikit-learn for ICA/decoding —
is installed *into the very Python environment that runs the server*, the first
time an analysis needs it (see :func:`install_backend`).

This keeps a fresh ``pipx install mne-mcp`` / ``uv tool install mne-mcp`` / plain
``pip install mne-mcp`` near-instant, and lets users who never run an analysis
skip the multi-hundred-megabyte download entirely. After installation,
``importlib.invalidate_caches()`` makes the new packages importable in the
already-running process — **no client restart required**.

The package lists per profile below are kept in sync with the optional
dependencies in ``pyproject.toml``; ``tests/test_backend.py`` fails if they drift.
"""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys

_ANALYSIS = [
    "mne>=1.6.0",
    "numpy>=1.23.0",
    "scipy>=1.9.0",
    "matplotlib>=3.6.0",
    "pandas>=2.0.0",
    "tabulate>=0.9.0",
]
_ICA = ["scikit-learn>=1.1.0"]
_FULL = [
    "mne-connectivity>=0.5",
    "mne-bids>=0.13",
    "autoreject>=0.4",
    "nibabel>=5.0",
    "pymatreader>=0.0.30",
    "edfio>=0.4",
    "h5io>=0.2",
    "pyvista>=0.43",
    "python-picard>=0.7",
]

#: Installable profiles, smallest to largest. ``analysis`` ⊂ ``ica`` ⊂ ``full``.
PROFILES: dict[str, list[str]] = {
    "analysis": list(_ANALYSIS),
    "ica": _ANALYSIS + _ICA,
    "full": _ANALYSIS + _ICA + _FULL,
}

#: Default profile (ICA is the common case and scikit-learn is cheap).
DEFAULT_PROFILE = "ica"

# Import names used for a quick "is the core backend present?" check.
_CORE_IMPORTS = ["mne", "numpy", "scipy", "matplotlib", "pandas"]


def backend_available() -> bool:
    """True if MNE-Python can be imported in this environment."""
    try:
        return importlib.util.find_spec("mne") is not None
    except Exception:
        return False


def missing_core() -> list[str]:
    """Return the core import names that are not yet installed."""
    missing = []
    for name in _CORE_IMPORTS:
        try:
            if importlib.util.find_spec(name) is None:
                missing.append(name)
        except Exception:
            missing.append(name)
    return missing


def _in_virtualenv() -> bool:
    """True when running inside a venv/virtualenv (incl. pipx / uv tool envs)."""
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def pip_command(profile: str = DEFAULT_PROFILE) -> list[str]:
    """Build the pip command that installs ``profile`` into the running interpreter.

    Uses ``sys.executable -m pip`` so it always targets *this* environment,
    whatever it is (venv, pipx/uv tool venv, or a bare global Python). When not
    inside a virtual environment, ``--user`` is added so the install needs no
    admin rights and does not fight an externally-managed global interpreter.
    """
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile {profile!r}. Valid: {sorted(PROFILES)}")
    cmd = [sys.executable, "-m", "pip", "install"]
    if not _in_virtualenv():
        cmd.append("--user")
    cmd.extend(PROFILES[profile])
    return cmd


def install_backend(profile: str = DEFAULT_PROFILE, timeout: int = 1800) -> dict:
    """
    Install the analysis backend into the current Python environment.

    Runs pip in a subprocess (output captured), then invalidates Python's import
    caches so the freshly-installed packages become importable in this live
    process without a restart. Returns a status dict with ``ok``, ``profile``,
    ``command``, ``returncode``, ``available`` and truncated output tails.
    """
    cmd = pip_command(profile)
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        returncode = proc.returncode
        out, err = proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as e:
        returncode = -1
        out = e.stdout or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        err = e.stderr or ""
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
        err += f"\n(timed out after {timeout}s)"
        timed_out = True

    # Make the newly-installed packages visible to the already-running interpreter.
    importlib.invalidate_caches()
    try:
        from mne_mcp._compat import apply_numpy_compat

        apply_numpy_compat()
    except Exception:
        pass

    available = backend_available()
    return {
        "ok": returncode == 0 and available,
        "profile": profile,
        "command": " ".join(cmd),
        "returncode": returncode,
        "timed_out": timed_out,
        "available": available,
        "stdout_tail": out[-4000:],
        "stderr_tail": err[-4000:],
    }
