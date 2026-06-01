"""
Persistent analysis session for MNE MCP.

MNE pipelines are *stateful*: you load a Raw recording once, then filter it,
re-reference it, fit ICA, epoch it, average it — each step mutating or deriving
from large in-memory objects. A stateless "read file / write file" tool model
(fine for SPSS batch jobs) would force re-loading multi-gigabyte recordings on
every step.

So the MCP server process keeps one long-lived :class:`Session` holding a Python
namespace of named MNE objects. Tools operate on that namespace, and a flexible
``run_code`` escape hatch executes arbitrary MNE/Python against it — Jupyter-like,
but driven by conversation.
"""

from __future__ import annotations

import ast
import io
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from mne_mcp import figures
from mne_mcp.config import get_results_dir
from mne_mcp.summaries import describe, object_kind

# Names that are always present in the namespace and should not be listed as
# user data objects.
_PRELOADED = {"mne", "np", "plt", "pd", "__builtins__", "session", "SESSION"}


class Session:
    """A persistent MNE analysis namespace."""

    def __init__(self) -> None:
        self.namespace: dict = {}
        self.history: list[str] = []
        self._init_namespace()

    def _init_namespace(self) -> None:
        import matplotlib.pyplot as plt  # noqa
        import mne
        import numpy as np
        import pandas as pd

        # Quiet MNE's very chatty default logging; tools surface what matters.
        try:
            mne.set_log_level("WARNING")
        except Exception:
            pass

        self.namespace = {
            "mne": mne,
            "np": np,
            "pd": pd,
            "plt": plt,
            "session": self,
        }

    # ── object registry ────────────────────────────────────────────────────

    def set(self, name: str, obj) -> None:
        self.namespace[name] = obj

    def get(self, name: str):
        if name not in self.namespace:
            raise KeyError(name)
        return self.namespace[name]

    def has(self, name: str) -> bool:
        return name in self.namespace and name not in _PRELOADED

    def data_names(self) -> list[str]:
        """Names of user data objects currently held (excludes preloaded modules)."""
        import types

        skip_types = (
            types.ModuleType,
            types.FunctionType,
            types.BuiltinFunctionType,
            type,
        )
        out = []
        for key, val in self.namespace.items():
            if key in _PRELOADED or key.startswith("_"):
                continue
            if isinstance(val, skip_types):
                # modules / user-defined functions / classes are not data objects
                continue
            out.append(key)
        return out

    def summary(self) -> str:
        names = self.data_names()
        if not names:
            return "_Session is empty — no objects loaded yet._"
        lines = ["| Name | Kind | Detail |", "|---|---|---|"]
        for name in names:
            obj = self.namespace[name]
            kind = object_kind(obj)
            detail = self._one_line(obj, kind)
            lines.append(f"| `{name}` | {kind} | {detail} |")
        return "\n".join(lines)

    @staticmethod
    def _one_line(obj, kind: str) -> str:
        try:
            if kind == "Raw":
                return (
                    f"{obj.info['nchan']} ch, {obj.info['sfreq']:.0f} Hz, "
                    f"{obj.times[-1]:.1f} s"
                )
            if kind == "Epochs":
                return f"{len(obj)} epochs, {obj.info['nchan']} ch, ids={list(obj.event_id)}"
            if kind == "Evoked":
                return f"nave={obj.nave}, {obj.info['nchan']} ch, '{obj.comment}'"
            if kind == "ICA":
                return f"{getattr(obj, 'n_components_', '?')} comps, excl={getattr(obj, 'exclude', [])}"
            if kind == "ndarray":
                return f"shape={obj.shape}, dtype={obj.dtype}"
        except Exception:
            pass
        text = repr(obj)
        return (text[:60] + "…") if len(text) > 60 else text

    def describe(self, name: str) -> str:
        obj = self.get(name)
        return describe(obj)

    def reset(self) -> None:
        figures.close_all()
        self.history.clear()
        self._init_namespace()

    # ── code execution ───────────────────────────────────────────────────────

    def run_code(
        self,
        code: str,
        *,
        capture_figures: bool = True,
        fig_prefix: str = "code",
    ) -> dict:
        """
        Execute ``code`` in the persistent namespace.

        Mimics a notebook cell: if the final statement is an expression, its
        value is returned in ``result_repr``. Captures stdout/stderr and any
        matplotlib figures produced (saved as PNG, paths returned in
        ``figures``).
        """
        results_dir = get_results_dir()
        before = figures.open_figure_numbers() if capture_figures else set()

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        result_value = None
        error = None
        tb = None

        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as e:
            return {
                "stdout": "",
                "stderr": "",
                "result_repr": None,
                "figures": [],
                "error": f"SyntaxError: {e}",
                "traceback": None,
            }

        last_expr = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last_expr = tree.body.pop()

        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                if tree.body:
                    exec(
                        compile(tree, "<mne-mcp>", "exec"),
                        self.namespace,
                        self.namespace,
                    )
                if last_expr is not None:
                    result_value = eval(
                        compile(ast.Expression(last_expr.value), "<mne-mcp>", "eval"),
                        self.namespace,
                        self.namespace,
                    )
        except Exception as e:  # noqa: BLE001 - surface any analysis error verbatim
            error = f"{type(e).__name__}: {e}"
            tb = traceback.format_exc()

        saved = (
            figures.capture_new_figures(before, Path(results_dir), prefix=fig_prefix)
            if capture_figures
            else []
        )

        self.history.append(code)

        result_repr = None
        if result_value is not None:
            kind = object_kind(result_value)
            if kind in ("Raw", "Epochs", "Evoked", "ICA", "Info", "ndarray"):
                result_repr = describe(result_value)
            else:
                text = repr(result_value)
                result_repr = (text[:2000] + " …") if len(text) > 2000 else text

        return {
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "result_repr": result_repr,
            "figures": saved,
            "error": error,
            "traceback": tb,
        }


# Module-level singleton — the MCP server process holds exactly one session.
_SESSION: Session | None = None


def get_session() -> Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = Session()
    return _SESSION
