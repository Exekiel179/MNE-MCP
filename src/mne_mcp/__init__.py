"""MNE MCP server package."""

import os as _os

# Force a headless matplotlib backend *before* anything (this package or MNE)
# imports matplotlib, so plotting never tries to open a GUI window on a server.
# This is just an env var, so matplotlib is not imported until analysis starts.
_os.environ.setdefault("MPLBACKEND", "Agg")

from mne_mcp._compat import apply_numpy_compat as _apply_numpy_compat
from mne_mcp._version import __version__

# Restore NumPy 2.x-removed aliases that some transitive dependencies still call.
_apply_numpy_compat()

__all__ = ["__version__"]
