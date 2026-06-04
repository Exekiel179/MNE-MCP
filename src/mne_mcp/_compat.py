"""Runtime compatibility shims.

NumPy 2.x removed a number of long-standing aliases (``np.trapz`` -> ``np.trapezoid``,
``np.in1d`` -> ``np.isin``, ``np.row_stack`` -> ``np.vstack``, several scalar/constant
aliases, ...). Some scientific dependencies in the transitive stack still call the old
names, which raises ``AttributeError: module 'numpy' has no attribute '...'`` at runtime
(e.g. while reading an EDF). We restore the missing aliases on the numpy module so the
server keeps working under NumPy >= 2.0 even when a dependency lags behind.

This only ever *adds* attributes that are absent; it never overwrites an existing one,
so on older NumPy it is a no-op. Call ``apply_numpy_compat()`` once at import time.
"""

from __future__ import annotations

import numpy as np

# old name -> attribute on numpy to alias it to
_FUNC_ALIASES = {
    "trapz": "trapezoid",
    "in1d": "isin",
    "row_stack": "vstack",
    "product": "prod",
    "cumproduct": "cumprod",
    "sometrue": "any",
    "alltrue": "all",
    "round_": "round",
    "float_": "float64",
    "complex_": "complex128",
    "unicode_": "str_",
    "string_": "bytes_",
    "bool8": "bool_",
}
# old constant name -> value
_CONST_ALIASES = {
    "infty": "inf",
    "Inf": "inf",
    "NaN": "nan",
    "NAN": "nan",
}

_applied = False


def apply_numpy_compat() -> list[str]:
    """Restore NumPy aliases removed in NumPy 2.x. Idempotent. Returns names restored."""
    global _applied
    restored: list[str] = []
    for old, new in _FUNC_ALIASES.items():
        if not hasattr(np, old) and hasattr(np, new):
            setattr(np, old, getattr(np, new))
            restored.append(old)
    for old, new in _CONST_ALIASES.items():
        if not hasattr(np, old) and hasattr(np, new):
            setattr(np, old, getattr(np, new))
            restored.append(old)
    _applied = True
    return restored
