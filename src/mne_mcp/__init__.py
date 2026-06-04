"""MNE MCP server package."""

# Restore NumPy aliases removed in NumPy 2.x (e.g. np.trapz/np.in1d) that some
# transitive dependencies still call, before any operation runs. No-op on older NumPy.
from mne_mcp._compat import apply_numpy_compat as _apply_numpy_compat
from mne_mcp._version import __version__

_apply_numpy_compat()

__all__ = ["__version__"]
