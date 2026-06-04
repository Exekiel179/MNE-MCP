"""
MNE MCP server — all tool definitions.

The server holds one persistent :class:`~mne_mcp.kernel.Session` for the whole
process, so loaded recordings and derived objects survive across tool calls.
Tools are thin wrappers over :mod:`mne_mcp.operations`; the flexible
``mne_run_code`` tool reaches the rest of the MNE API.
"""

import asyncio
import sys
from contextlib import asynccontextmanager

from fastmcp import Context, FastMCP

from mne_mcp import operations as ops
from mne_mcp.config import (
    DEFAULT_CONFIG,
    detect_capabilities,
    get_config_path,
    get_runtime_config,
    get_timeout,
    load_config,
)
from mne_mcp.kernel import get_session

# ─── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    sys.stderr.write("Starting MNE MCP server...\n")
    caps = detect_capabilities()
    if caps.get("mne"):
        sys.stderr.write(f"  MNE-Python : available v{caps['mne_version']}\n")
    else:
        sys.stderr.write("  MNE-Python : NOT FOUND (pip install mne)\n")
    sys.stderr.write(
        f"  scikit-learn (ICA): {'available v' + caps['sklearn_version'] if caps['sklearn'] else 'NOT FOUND'}\n"
    )
    sys.stderr.write("  Session    : empty (objects load on demand)\n")
    yield {"capabilities": caps}
    sys.stderr.write("Shutting down MNE MCP server.\n")


mcp = FastMCP("MNE", lifespan=server_lifespan)

# Matplotlib's pyplot figure registry and the single shared Session are global,
# mutable state. Serialize all execution so overlapping tool calls can't cross-
# capture figures or race on session objects. (MNE steps are CPU-bound and the
# session is shared anyway, so there is nothing to gain from running them in
# parallel.)
_EXEC_LOCK = asyncio.Lock()


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _require_mne() -> str | None:
    caps = detect_capabilities()
    if not caps.get("mne"):
        return (
            "This tool requires MNE-Python. Install it into the server's "
            "environment with `pip install mne` (and `scikit-learn` for ICA)."
        )
    return None


def _require_sklearn() -> str | None:
    caps = detect_capabilities()
    if not caps.get("sklearn"):
        return "ICA requires scikit-learn. Install it with `pip install scikit-learn`."
    return None


def _require_module(modname: str, pip_name: str = None) -> str | None:
    import importlib

    try:
        importlib.import_module(modname)
        return None
    except Exception:
        return (
            f"This tool requires `{modname}`. Install it with "
            f'`pip install {pip_name or modname}` (or `pip install -e ".[full]"`).'
        )


def _format(result: dict) -> str:
    parts = []
    md = result.get("markdown")
    if md:
        parts.append(md)
    for fig in result.get("figures", []):
        parts.append(f"\n> Figure: `{fig}`")
    if result.get("figures"):
        parts.append("\n_(Read the PNG path(s) above to view the figure.)_")
    code = result.get("code")
    if code:
        parts.append(f"\n```python\n{code}\n```")
    return "\n".join(parts) if parts else "_No output._"


async def _exec(fn, ctx, *args, **kwargs) -> str:
    """Run a synchronous operation in a worker thread with a timeout."""
    err = _require_mne()
    if err:
        return f"Error: {err}"
    try:
        async with _EXEC_LOCK:
            result = await asyncio.wait_for(
                asyncio.to_thread(fn, *args, **kwargs), timeout=get_timeout()
            )
    except asyncio.TimeoutError:
        return (
            f"Error: operation timed out after {get_timeout()}s. "
            "Increase MNE_MCP_TIMEOUT for slow steps (ICA, time-frequency, large files)."
        )
    except KeyError as e:
        return (
            f"Error: no session object named {e}. "
            "Call `mne_session_info` to list loaded objects, or load data first."
        )
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:  # noqa: BLE001
        if ctx:
            await ctx.error(f"{fn.__name__} error: {e}")
        return f"Error: {type(e).__name__}: {e}"
    return _format(result)


# ─── Group 1: Status & Session ─────────────────────────────────────────────────


@mcp.tool(
    name="mne_check_status",
    description=(
        "Check MNE MCP capabilities: MNE-Python version, scikit-learn (needed for ICA), "
        "numpy/scipy/matplotlib versions, and runtime directories. Call this first."
    ),
)
async def mne_check_status(ctx: Context = None) -> str:
    caps = detect_capabilities()
    cfg = get_runtime_config()
    lines = [
        "## MNE MCP Status",
        "",
        f"- MNE-Python: {'OK v' + caps['mne_version'] if caps['mne'] else 'NOT FOUND (pip install mne)'}",
        f"- scikit-learn (ICA): {'OK v' + caps['sklearn_version'] if caps['sklearn'] else 'NOT FOUND'}",
        f"- numpy: {caps['numpy_version']}  |  scipy: {caps['scipy_version']}",
        f"- matplotlib: {caps['matplotlib_version']}  |  pandas: {caps['pandas_version']}",
        "",
        f"- Results/figures dir: `{cfg['results_dir']}`",
        f"- Data scan dir: `{cfg['data_dir']}`",
        f"- Operation timeout: {cfg['timeout']}s",
        f"- Config file: `{cfg['config_path']}`  (edit with `mne-mcp configure`)",
    ]
    return "\n".join(lines)


@mcp.tool(
    name="mne_get_config",
    description=(
        "Show the configured default analysis parameters (line frequency, default montage, "
        "filter band, rejection threshold, ICA method/components, epoch window, dirs, timeout) "
        "that the structured tools fall back to when a parameter is omitted. Users change these "
        "by running `mne-mcp configure` in a terminal."
    ),
)
async def mne_get_config(ctx: Context = None) -> str:
    cfg = load_config()
    lines = [
        "## Configured defaults",
        "",
        f"_File: `{get_config_path()}`_",
        "",
        "| Key | Value | Built-in |",
        "|---|---|---|",
    ]
    for key in DEFAULT_CONFIG:
        mark = "" if cfg[key] == DEFAULT_CONFIG[key] else " *(custom)*"
        lines.append(f"| `{key}` | `{cfg[key]}`{mark} | `{DEFAULT_CONFIG[key]}` |")
    lines.append(
        "\nChange these with `mne-mcp configure` (interactive) or "
        "`mne-mcp configure --set key=value`."
    )
    return "\n".join(lines)


@mcp.tool(
    name="mne_session_info",
    description=(
        "List every object currently held in the persistent analysis session "
        "(raw recordings, epochs, evoked, ICA, events, arrays) with a one-line summary. "
        "Use this to see what is loaded before operating on it."
    ),
)
async def mne_session_info(ctx: Context = None) -> str:
    err = _require_mne()
    if err:
        return f"Error: {err}"
    return "## Session objects\n\n" + get_session().summary()


@mcp.tool(
    name="mne_describe",
    description="Show a detailed summary of one named session object (channels, sfreq, montage, bads, etc.).",
)
async def mne_describe(name: str, ctx: Context = None) -> str:
    return await _exec(ops.describe_object, ctx, name)


@mcp.tool(
    name="mne_get_info",
    description="Show the full channel list and measurement info for a named session object.",
)
async def mne_get_info(name: str, ctx: Context = None) -> str:
    return await _exec(ops.get_info, ctx, name)


@mcp.tool(
    name="mne_reset_session",
    description="Clear all loaded objects and figures from the session, starting fresh. Irreversible.",
)
async def mne_reset_session(ctx: Context = None) -> str:
    err = _require_mne()
    if err:
        return f"Error: {err}"
    get_session().reset()
    return "Session reset — all objects cleared."


@mcp.tool(
    name="mne_run_code",
    description=(
        "Execute arbitrary Python/MNE code in the persistent session namespace. "
        "Pre-bound names: `mne`, `np`, `pd`, `plt`, plus every object you have loaded "
        "(e.g. `raw`, `epochs`, `evoked`, `ica`). Like a notebook cell: the value of a "
        "final expression is returned, stdout is captured, and any matplotlib figures are "
        "saved as PNG (paths returned). Use this for anything the structured tools do not cover."
    ),
)
async def mne_run_code(code: str, ctx: Context = None) -> str:
    err = _require_mne()
    if err:
        return f"Error: {err}"
    session = get_session()
    try:
        async with _EXEC_LOCK:
            result = await asyncio.wait_for(
                asyncio.to_thread(session.run_code, code), timeout=get_timeout()
            )
    except asyncio.TimeoutError:
        return (
            f"Error: code timed out after {get_timeout()}s. Increase MNE_MCP_TIMEOUT."
        )

    parts = []
    if result.get("stdout"):
        parts.append(f"**stdout:**\n```\n{result['stdout'].rstrip()}\n```")
    if result.get("stderr"):
        parts.append(f"**stderr:**\n```\n{result['stderr'].rstrip()}\n```")
    if result.get("result_repr") is not None:
        parts.append(f"**result:**\n{result['result_repr']}")
    for fig in result.get("figures", []):
        parts.append(f"> Figure: `{fig}`")
    if result.get("error"):
        parts.append(f"**Error:** {result['error']}")
        if result.get("traceback"):
            parts.append(f"```\n{result['traceback'][-1500:]}\n```")
    return "\n\n".join(parts) if parts else "_(code ran, no output)_"


# ─── Group 2: IO ────────────────────────────────────────────────────────────────


@mcp.tool(
    name="mne_list_files",
    description=(
        "List neurophysiology data files (.fif, .edf, .bdf, .vhdr, .set, .cnt, .egi/.mff, "
        ".ds, .snirf, …) under a directory. Defaults to MNE_MCP_DATA_DIR / current dir. "
        "Optionally pass a glob pattern."
    ),
)
async def mne_list_files(
    directory: str = None, pattern: str = None, ctx: Context = None
) -> str:
    return await _exec(ops.list_files, ctx, directory, pattern)


@mcp.tool(
    name="mne_load_raw",
    description=(
        "Load a raw recording from disk into the session. Auto-detects the format by "
        "extension (FIF/EDF/BDF/BrainVision/EEGLAB/CNT/EGI/…). Stores it under `name` "
        "(default `raw`). Set preload=False for very large files."
    ),
)
async def mne_load_raw(
    path: str, name: str = "raw", preload: bool = True, ctx: Context = None
) -> str:
    return await _exec(ops.load_raw, ctx, path, name, preload)


# ─── Group 3: Preprocessing ─────────────────────────────────────────────────────


@mcp.tool(
    name="mne_filter",
    description=(
        "Band-pass / high-pass / low-pass and/or notch filter a Raw/Epochs/Evoked object "
        "in place. l_freq=high-pass edge, h_freq=low-pass edge (either may be null), "
        "notch=line-noise frequency (e.g. 50 or 60). picks optional ('eeg', 'meg', or null)."
    ),
)
async def mne_filter(
    name: str = "raw",
    l_freq: float = None,
    h_freq: float = None,
    notch: float = None,
    picks: str = None,
    ctx: Context = None,
) -> str:
    return await _exec(ops.filter_data, ctx, name, l_freq, h_freq, notch, picks)


@mcp.tool(
    name="mne_resample",
    description="Resample a Raw/Epochs object to a new sampling frequency (Hz), in place.",
)
async def mne_resample(
    name: str = "raw", sfreq: float = 250.0, ctx: Context = None
) -> str:
    return await _exec(ops.resample, ctx, name, sfreq)


@mcp.tool(
    name="mne_crop",
    description="Crop a Raw/Epochs/Evoked object to the time window [tmin, tmax] seconds, in place.",
)
async def mne_crop(
    name: str = "raw", tmin: float = 0.0, tmax: float = None, ctx: Context = None
) -> str:
    return await _exec(ops.crop, ctx, name, tmin, tmax)


@mcp.tool(
    name="mne_set_montage",
    description=(
        "Apply a standard electrode montage (e.g. 'standard_1020', 'standard_1005', "
        "'biosemi64', 'GSN-HydroCel-128') to set channel positions. Needed before "
        "topographic plots and interpolation. If montage is omitted, uses the configured "
        "default (set via `mne-mcp configure`)."
    ),
)
async def mne_set_montage(
    name: str = "raw", montage: str = None, ctx: Context = None
) -> str:
    return await _exec(ops.set_montage, ctx, name, montage)


@mcp.tool(
    name="mne_set_reference",
    description=(
        "Set the EEG reference. Use 'average' for average reference, 'REST', or a "
        "comma-separated list of channel names (e.g. 'TP9,TP10')."
    ),
)
async def mne_set_reference(
    name: str = "raw", ref_channels: str = "average", ctx: Context = None
) -> str:
    return await _exec(ops.set_reference, ctx, name, ref_channels)


@mcp.tool(
    name="mne_mark_bad_channels",
    description=(
        "Mark channels as bad (comma-separated names, e.g. 'Fp1,T7'). By default appends "
        "to existing bads; set replace=true to overwrite."
    ),
)
async def mne_mark_bad_channels(
    name: str = "raw", bads: str = "", replace: bool = False, ctx: Context = None
) -> str:
    return await _exec(ops.mark_bad_channels, ctx, name, bads, replace)


@mcp.tool(
    name="mne_interpolate_bads",
    description="Interpolate currently-marked bad channels using spherical splines (requires a montage).",
)
async def mne_interpolate_bads(
    name: str = "raw", reset_bads: bool = True, ctx: Context = None
) -> str:
    return await _exec(ops.interpolate_bads, ctx, name, reset_bads)


# ─── Group 4: Visualization ─────────────────────────────────────────────────────


@mcp.tool(
    name="mne_plot_psd",
    description="Plot the power spectral density of a Raw/Epochs/Evoked object. Returns a PNG path.",
)
async def mne_plot_psd(
    name: str = "raw",
    fmin: float = 0.0,
    fmax: float = None,
    picks: str = None,
    ctx: Context = None,
) -> str:
    return await _exec(ops.plot_psd, ctx, name, fmin, fmax, picks)


@mcp.tool(
    name="mne_plot_raw",
    description="Plot raw signal traces (a window of channels over time). Returns a PNG path.",
)
async def mne_plot_raw(
    name: str = "raw",
    start: float = 0.0,
    duration: float = 20.0,
    n_channels: int = 20,
    ctx: Context = None,
) -> str:
    return await _exec(ops.plot_raw, ctx, name, start, duration, n_channels)


@mcp.tool(
    name="mne_plot_sensors",
    description="Plot the sensor/electrode layout (kind='topomap' 2D or '3d'). Returns a PNG path.",
)
async def mne_plot_sensors(
    name: str = "raw",
    kind: str = "topomap",
    show_names: bool = True,
    ctx: Context = None,
) -> str:
    return await _exec(ops.plot_sensors, ctx, name, kind, show_names)


# ─── Group 5: ICA ───────────────────────────────────────────────────────────────


@mcp.tool(
    name="mne_fit_ica",
    description=(
        "Fit Independent Component Analysis on a (preferably 1 Hz high-pass filtered) Raw/Epochs "
        "object for artifact removal. n_components can be an int, a float (variance fraction), or null. "
        "method: 'fastica' (default), 'infomax', 'picard'. Stored under ica_name (default 'ica'). "
        "Requires scikit-learn."
    ),
)
async def mne_fit_ica(
    name: str = "raw",
    n_components: float = None,
    method: str = None,
    ica_name: str = "ica",
    random_state: int = 97,
    ctx: Context = None,
) -> str:
    err = _require_sklearn()
    if err:
        return f"Error: {err}"
    return await _exec(
        ops.fit_ica, ctx, name, n_components, method, ica_name, random_state
    )


@mcp.tool(
    name="mne_plot_ica_components",
    description="Plot ICA component scalp topographies (to identify eye/heart/muscle artifacts). Returns PNG path(s).",
)
async def mne_plot_ica_components(ica_name: str = "ica", ctx: Context = None) -> str:
    return await _exec(ops.plot_ica_components, ctx, ica_name)


@mcp.tool(
    name="mne_plot_ica_sources",
    description="Plot ICA component time courses for an instrument (raw/epochs). Returns a PNG path.",
)
async def mne_plot_ica_sources(
    ica_name: str = "ica", inst_name: str = "raw", ctx: Context = None
) -> str:
    return await _exec(ops.plot_ica_sources, ctx, ica_name, inst_name)


@mcp.tool(
    name="mne_apply_ica",
    description=(
        "Remove ICA components from an instrument in place. exclude = comma-separated component "
        "indices to drop (e.g. '0,3'); if omitted, uses the ICA object's current exclude list."
    ),
)
async def mne_apply_ica(
    ica_name: str = "ica",
    inst_name: str = "raw",
    exclude: str = None,
    ctx: Context = None,
) -> str:
    return await _exec(ops.apply_ica, ctx, ica_name, inst_name, exclude)


# ─── Group 6: Events / Epochs / ERP ─────────────────────────────────────────────


@mcp.tool(
    name="mne_find_events",
    description="Find stimulus/trigger events on a stim channel of a Raw object. Stores them under events_name.",
)
async def mne_find_events(
    raw_name: str = "raw",
    stim_channel: str = None,
    events_name: str = "events",
    ctx: Context = None,
) -> str:
    return await _exec(ops.find_events, ctx, raw_name, stim_channel, events_name)


@mcp.tool(
    name="mne_events_from_annotations",
    description="Convert a Raw object's annotations into an events array + event_id map (for EDF/BrainVision/EEGLAB data).",
)
async def mne_events_from_annotations(
    raw_name: str = "raw", events_name: str = "events", ctx: Context = None
) -> str:
    return await _exec(ops.events_from_annotations, ctx, raw_name, events_name)


@mcp.tool(
    name="mne_make_epochs",
    description=(
        "Segment a Raw object into Epochs around events. tmin/tmax in seconds relative to the "
        "event; baseline 'default' = (None, 0); event_id like 'target:1,standard:2' to name/select "
        "conditions; reject_eeg = peak-to-peak EEG rejection threshold in volts (e.g. 100e-6). "
        "Stored under epochs_name."
    ),
)
async def mne_make_epochs(
    raw_name: str = "raw",
    events_name: str = "events",
    event_id: str = None,
    tmin: float = None,
    tmax: float = None,
    baseline: str = "default",
    reject_eeg: float = None,
    epochs_name: str = "epochs",
    ctx: Context = None,
) -> str:
    return await _exec(
        ops.make_epochs,
        ctx,
        raw_name,
        events_name,
        event_id,
        tmin,
        tmax,
        baseline,
        reject_eeg,
        epochs_name,
    )


@mcp.tool(
    name="mne_plot_epochs_image",
    description="Plot an ERP image (epochs × time heatmap) for an Epochs object. Returns PNG path(s).",
)
async def mne_plot_epochs_image(
    name: str = "epochs", picks: str = None, ctx: Context = None
) -> str:
    return await _exec(ops.plot_epochs_image, ctx, name, picks)


@mcp.tool(
    name="mne_average_evoked",
    description=(
        "Average Epochs into an Evoked (ERP/ERF) response. condition = an event_id name to "
        "average just that condition (else averages all). Stored under evoked_name."
    ),
)
async def mne_average_evoked(
    epochs_name: str = "epochs",
    condition: str = None,
    evoked_name: str = "evoked",
    ctx: Context = None,
) -> str:
    return await _exec(ops.average_evoked, ctx, epochs_name, condition, evoked_name)


@mcp.tool(
    name="mne_plot_evoked",
    description="Plot an Evoked response. style: 'joint' (butterfly + topomaps, default), 'topo', or 'butterfly'. Returns PNG path.",
)
async def mne_plot_evoked(
    name: str = "evoked", style: str = "joint", ctx: Context = None
) -> str:
    return await _exec(ops.plot_evoked, ctx, name, style)


@mcp.tool(
    name="mne_plot_topomap",
    description="Plot scalp topographies of an Evoked at given times. times='auto', 'peaks', or comma-separated seconds (e.g. '0.1,0.2,0.3'). Returns PNG path.",
)
async def mne_plot_topomap(
    name: str = "evoked", times: str = "auto", ctx: Context = None
) -> str:
    return await _exec(ops.plot_topomap, ctx, name, times)


# ─── Group 7: Time-frequency ─────────────────────────────────────────────────────


@mcp.tool(
    name="mne_tfr_morlet",
    description=(
        "Compute Morlet-wavelet time-frequency power on Epochs and plot it. fmin/fmax = frequency "
        "range (Hz), n_freqs = number of frequencies. Stored under tfr_name. Returns PNG path."
    ),
)
async def mne_tfr_morlet(
    epochs_name: str = "epochs",
    fmin: float = 4.0,
    fmax: float = 40.0,
    n_freqs: int = 20,
    tfr_name: str = "power",
    ctx: Context = None,
) -> str:
    return await _exec(ops.tfr_morlet, ctx, epochs_name, fmin, fmax, n_freqs, tfr_name)


# ─── Group 8: Export ─────────────────────────────────────────────────────────────


@mcp.tool(
    name="mne_save",
    description=(
        "Save a session object to disk. MNE naming rules: Raw → '*_raw.fif', Epochs → '*-epo.fif', "
        "Evoked → '*-ave.fif'. Other formats follow the object's .save() support."
    ),
)
async def mne_save(
    name: str, path: str, overwrite: bool = True, ctx: Context = None
) -> str:
    return await _exec(ops.save_object, ctx, name, path, overwrite)


# ─── Group 9: Advanced analysis (decoding / connectivity / source) ───────────────


@mcp.tool(
    name="mne_decode",
    description=(
        "Time-resolved decoding (MVPA): train a classifier at each time point to discriminate two "
        "conditions, with cross-validation. cond_a/cond_b are event_id names (e.g. 'target','standard'). "
        "Returns mean/peak score over time + a scores-vs-time plot. Requires scikit-learn."
    ),
)
async def mne_decode(
    epochs_name: str = "epochs",
    cond_a: str = None,
    cond_b: str = None,
    scoring: str = "roc_auc",
    cv: int = 5,
    name: str = "decoding",
    ctx: Context = None,
) -> str:
    err = _require_sklearn()
    if err:
        return f"Error: {err}"
    return await _exec(
        ops.decode_time, ctx, epochs_name, cond_a, cond_b, scoring, cv, name
    )


@mcp.tool(
    name="mne_connectivity",
    description=(
        "Spectral connectivity between channels over Epochs in a frequency band. method: 'coh', 'plv', "
        "'wpli', 'pli', 'imcoh', etc. Returns a channel×channel connectivity heatmap + strongest pairs. "
        "Requires mne-connectivity."
    ),
)
async def mne_connectivity(
    epochs_name: str = "epochs",
    method: str = "coh",
    fmin: float = 8.0,
    fmax: float = 13.0,
    con_name: str = "con",
    ctx: Context = None,
) -> str:
    err = _require_module("mne_connectivity", "mne-connectivity")
    if err:
        return f"Error: {err}"
    return await _exec(ops.connectivity, ctx, epochs_name, method, fmin, fmax, con_name)


@mcp.tool(
    name="mne_compute_noise_cov",
    description=(
        "Compute a noise covariance matrix from the Epochs baseline (data up to tmax seconds, default 0). "
        "Needed before building an inverse operator for source localization."
    ),
)
async def mne_compute_noise_cov(
    name: str = "epochs",
    tmax: float = 0.0,
    cov_name: str = "noise_cov",
    ctx: Context = None,
) -> str:
    return await _exec(ops.compute_noise_cov, ctx, name, tmax, cov_name)


@mcp.tool(
    name="mne_make_forward",
    description=(
        "Build a template-head (fsaverage) EEG forward model for the named object's montage. Downloads "
        "the fsaverage template once (~ tens of MB). Use for EEG source localization without an individual "
        "MRI. Stored under fwd_name."
    ),
)
async def mne_make_forward(
    name: str = "evoked", fwd_name: str = "fwd", ctx: Context = None
) -> str:
    err = _require_module("nibabel")
    if err:
        return f"Error: {err}"
    return await _exec(ops.fsaverage_forward, ctx, name, fwd_name)


@mcp.tool(
    name="mne_apply_inverse",
    description=(
        "Estimate cortical sources from an Evoked using a forward model and noise covariance. "
        "method: 'dSPM' (default), 'MNE', 'sLORETA', 'eLORETA'. Stores the source estimate (stc) and "
        "reports the peak activation time. Pair with mne_make_forward + mne_compute_noise_cov."
    ),
)
async def mne_apply_inverse(
    evoked_name: str = "evoked",
    fwd_name: str = "fwd",
    cov_name: str = "noise_cov",
    method: str = "dSPM",
    snr: float = 3.0,
    stc_name: str = "stc",
    ctx: Context = None,
) -> str:
    return await _exec(
        ops.apply_inverse_op,
        ctx,
        evoked_name,
        fwd_name,
        cov_name,
        method,
        snr,
        stc_name,
    )


@mcp.tool(
    name="mne_plot_source_estimate",
    description=(
        "Render a source estimate (stc) as a cortical activation map (PNG) at its peak time or a given "
        "time. hemi: 'both' / 'lh' / 'rh'. Requires PyVista with off-screen rendering; if 3D rendering "
        "is unavailable the estimate is still computed and can be inspected via mne_run_code."
    ),
)
async def mne_plot_source_estimate(
    stc_name: str = "stc", hemi: str = "both", time: float = None, ctx: Context = None
) -> str:
    err = _require_module("pyvista")
    if err:
        return f"Error: {err}"
    return await _exec(ops.plot_source_estimate, ctx, stc_name, hemi, time)
