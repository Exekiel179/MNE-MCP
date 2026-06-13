"""MNE MCP server package."""

import os as _os

# Force a headless matplotlib backend *before* anything (this package or MNE)
# imports matplotlib, so plotting never tries to open a GUI window on a server.
# This is just an env var — no matplotlib import here — so the bare package stays
# importable even when the scientific backend has not been provisioned yet.
_os.environ.setdefault("MPLBACKEND", "Agg")

from mne_mcp._compat import apply_numpy_compat as _apply_numpy_compat
from mne_mcp._version import __version__

# Restore NumPy 2.x-removed aliases that some transitive deps still call. This is
# import-safe and a no-op when numpy is not installed (lightweight install, before
# `mne-mcp install-backend` / the mne_install_backend tool has provisioned it).
_apply_numpy_compat()

__all__ = ["__version__"]
