"""
Matplotlib figure capture for MNE MCP.

MNE analysis is heavily visual (PSDs, sensor topographies, ICA components,
evoked responses, time-frequency maps). The MCP server runs headless, so we
force the non-interactive Agg backend and capture any figures a step produces
into PNG files. Tool results return the PNG paths; the assistant can then read
those images to actually *see* the data.
"""

from __future__ import annotations

import os

# Force a headless backend before anything imports pyplot for real.
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Keep MNE's interactive browsers (raw.plot / epochs.plot) on the matplotlib
# backend so they render to capturable figures instead of a Qt window.
os.environ.setdefault("MNE_BROWSER_BACKEND", "matplotlib")


def open_figure_numbers() -> set[int]:
    """Return the set of currently-open matplotlib figure numbers."""
    return set(plt.get_fignums())


def _next_index(results_dir, prefix: str) -> int:
    """Return the next integer index for files named ``prefix_NN.png``."""
    existing = list(results_dir.glob(f"{prefix}_*.png"))
    max_idx = 0
    for p in existing:
        stem = p.stem  # prefix_NN
        tail = stem[len(prefix) + 1 :]
        if tail.isdigit():
            max_idx = max(max_idx, int(tail))
    return max_idx + 1


def capture_new_figures(before: set[int], results_dir, prefix: str = "fig") -> list[str]:
    """
    Save every figure opened since ``before`` was sampled, then close them.

    Returns the list of saved PNG paths (as strings). Figures are saved in
    ascending figure-number order so multi-panel sequences stay ordered.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    after = set(plt.get_fignums())
    new_nums = sorted(after - before)

    saved: list[str] = []
    idx = _next_index(results_dir, prefix)
    for num in new_nums:
        fig = plt.figure(num)
        # Skip blank figures (some MNE calls open and immediately reuse a fig).
        if not fig.get_axes():
            plt.close(fig)
            continue
        out_path = results_dir / f"{prefix}_{idx:02d}.png"
        try:
            fig.savefig(out_path, dpi=110, bbox_inches="tight")
            saved.append(str(out_path))
            idx += 1
        finally:
            plt.close(fig)

    # Defensive: close anything else still lingering so state never leaks
    # between operations.
    for num in sorted(set(plt.get_fignums()) - before):
        plt.close(num)

    return saved


def close_all() -> None:
    """Close all open figures (used on session reset)."""
    plt.close("all")
