"""
High-level MNE operations.

Each function performs one common neurophysiology pipeline step against the
persistent :class:`~mne_mcp.kernel.Session`, captures any figures it produces,
and returns a result dict::

    {"markdown": str, "figures": [png_path, ...], "code": "equivalent MNE code"}

The ``code`` field makes every step transparent and archivable (the skill saves
it to ``mne_result/``), mirroring how SPSS-MCP emits the ``.sps`` syntax it ran.

Operations raise on failure; the server layer formats the error for the user.
"""

from __future__ import annotations

import ast
import math
import os
from pathlib import Path

from mne_mcp import figures
from mne_mcp.config import (
    get_data_dir,
    get_default_montage,
    get_epoch_window,
    get_filter_band,
    get_ica_method,
    get_ica_n_components,
    get_reject_eeg,
    get_results_dir,
)
from mne_mcp.kernel import get_session
from mne_mcp.parameters import ConnectivityParameters, TFRParameters
from mne_mcp.summaries import describe, object_kind

# Extensions MNE can read as raw recordings (not exhaustive, but the common set).
_RAW_EXTENSIONS = {
    ".fif",
    ".fif.gz",
    ".edf",
    ".bdf",
    ".gdf",
    ".vhdr",
    ".set",
    ".cnt",
    ".egi",
    ".mff",
    ".nxe",
    ".eeg",
    ".data",
    ".sqd",
    ".con",
    ".ds",
    ".nwb",
    ".snirf",
}

# Directories never worth scanning for user data (envs, VCS, caches, package data).
_SKIP_DIRS = {
    ".venv",
    "venv",
    "env",
    ".git",
    "node_modules",
    "__pycache__",
    "site-packages",
    ".idea",
    ".vscode",
    ".pytest_cache",
    "build",
    "dist",
    ".eggs",
    ".mypy_cache",
    ".ipynb_checkpoints",
}


def _is_raw_file(p: Path) -> bool:
    return (
        p.suffix.lower() in _RAW_EXTENSIONS
        or "".join(p.suffixes[-2:]).lower() in _RAW_EXTENSIONS
    )


def _result(markdown: str, figs=None, code: str = "") -> dict:
    return {"markdown": markdown, "figures": list(figs or []), "code": code}


def _require_kind(obj, name: str, allowed: tuple[str, ...]) -> None:
    kind = object_kind(obj)
    if kind not in allowed:
        raise ValueError(
            f"`{name}` is a {kind}; this operation needs one of {allowed}."
        )


# ── IO & inspection ──────────────────────────────────────────────────────────


def list_files(directory: str | None = None, pattern: str | None = None) -> dict:
    base = Path(directory) if directory else get_data_dir()
    if not base.exists():
        raise FileNotFoundError(f"Directory not found: {base}")

    hits: list[Path] = []
    if pattern:
        hits = sorted(p for p in base.glob(pattern) if p.is_file())
    else:
        for root, dirnames, filenames in os.walk(base):
            # Prune env/VCS/cache/package dirs in place so we never descend into them.
            dirnames[:] = [
                d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")
            ]
            for fn in filenames:
                p = Path(root) / fn
                if _is_raw_file(p):
                    hits.append(p)
        hits.sort()

    if not hits:
        return _result(f"_No neurophysiology data files found in_ `{base}`")

    shown = hits[:200]
    header = f"Found {len(hits)} file(s) under `{base}`"
    if len(hits) > len(shown):
        header += f" (showing first {len(shown)})"
    lines = [header + ":", ""]
    for p in shown:
        try:
            size_mb = p.stat().st_size / 1e6
            lines.append(f"- `{p}` ({size_mb:.1f} MB)")
        except OSError:
            lines.append(f"- `{p}`")
    return _result("\n".join(lines))


def load_raw(path: str, name: str = "raw", preload: bool = True) -> dict:
    import mne

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    try:
        raw = mne.io.read_raw(str(p), preload=preload, verbose="ERROR")
    except (ValueError, RuntimeError):
        # Fall back to extension-specific readers when the generic dispatcher
        # cannot guess the format.
        ext = p.suffix.lower()
        reader = {
            ".set": mne.io.read_raw_eeglab,
            ".vhdr": mne.io.read_raw_brainvision,
            ".edf": mne.io.read_raw_edf,
            ".bdf": mne.io.read_raw_bdf,
            ".cnt": mne.io.read_raw_cnt,
            ".egi": mne.io.read_raw_egi,
            ".mff": mne.io.read_raw_egi,
        }.get(ext)
        if reader is None:
            raise
        raw = reader(str(p), preload=preload, verbose="ERROR")

    s = get_session()
    s.set(name, raw)
    md = f"Loaded `{p.name}` into session as `{name}`.\n\n" + describe(raw)
    code = f"{name} = mne.io.read_raw({p.as_posix()!r}, preload={preload})"
    return _result(md, code=code)


def describe_object(name: str) -> dict:
    s = get_session()
    obj = s.get(name)
    return _result(f"### `{name}`\n\n" + describe(obj))


def get_info(name: str) -> dict:
    s = get_session()
    obj = s.get(name)
    info = getattr(obj, "info", None)
    if info is None:
        raise ValueError(f"`{name}` ({object_kind(obj)}) has no `info`.")
    ch_names = info["ch_names"]
    types = info.get_channel_types()
    lines = [describe(obj), "", "**Channels:**", ""]
    for ch, t in zip(ch_names, types):
        bad = " *(bad)*" if ch in (info.get("bads") or []) else ""
        lines.append(f"- `{ch}` — {t}{bad}")
    return _result("\n".join(lines))


# ── Preprocessing ──────────────────────────────────────────────────────────────


def _finite_number(value, label: str, *, positive: bool = False) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} must be a finite number, not a boolean.")
    if positive and value <= 0:
        raise ValueError(f"{label} must be positive.")


def filter_data(
    name: str,
    l_freq: float | None = None,
    h_freq: float | None = None,
    notch: float | None = None,
    picks: str | list[str] | list[int] | None = None,
) -> dict:
    s = get_session()
    obj = s.get(name)
    _require_kind(obj, name, ("Raw", "Epochs", "Evoked"))
    picks = _parse_picks(picks)
    # No band and no notch given → fall back to the configured default filter band.
    if l_freq is None and h_freq is None and notch is None:
        l_freq, h_freq = get_filter_band()
    nyquist = obj.info["sfreq"] / 2
    for label, value in (("l_freq", l_freq), ("h_freq", h_freq), ("notch", notch)):
        if value is not None:
            _finite_number(value, label)
            if value < 0 or value >= nyquist or (label != "l_freq" and value == 0):
                raise ValueError(
                    f"{label} must be below Nyquist ({nyquist:g} Hz) and positive (l_freq may be zero)."
                )
    if l_freq is not None and h_freq is not None and l_freq >= h_freq:
        raise ValueError(
            "l_freq must be less than h_freq for this band-pass tool. Use mne_run_code for an explicit band-stop design."
        )
    if notch is not None and not callable(getattr(obj, "notch_filter", None)):
        raise ValueError(
            "This object does not support notch_filter. Notch continuous Raw before epoching, or use mne_run_code for an explicit array workflow."
        )
    code_lines = []
    if l_freq is not None or h_freq is not None:
        obj.filter(l_freq, h_freq, picks=picks, verbose="ERROR")
        code_lines.append(f"{name}.filter({l_freq}, {h_freq}, picks={picks!r})")
    if notch is not None:
        obj.notch_filter(freqs=notch, picks=picks, verbose="ERROR")
        code_lines.append(f"{name}.notch_filter(freqs={notch}, picks={picks!r})")
    if not code_lines:
        raise ValueError("Provide at least one of l_freq, h_freq, or notch.")
    md = f"Filtered `{name}`.\n\n" + describe(obj)
    result = _result(md, code="\n".join(code_lines))
    result["guidance"] = {
        "status": "processed_not_quality_certified",
        "checks": [
            "Inspect pre/post PSD and traces; parameter validity is not proof of artifact removal.",
            "Choose cutoffs for the target ERP or frequency range; filtering can alter amplitude and latency.",
        ],
        "limits": [
            "Processing is in place; runtime failures may still leave partial changes."
        ],
    }
    return result


def resample(name: str, sfreq: float) -> dict:
    s = get_session()
    obj = s.get(name)
    _require_kind(obj, name, ("Raw", "Epochs"))
    _finite_number(sfreq, "sfreq", positive=True)
    obj.resample(sfreq, verbose="ERROR")
    return _result(
        f"Resampled `{name}` to {sfreq} Hz.\n\n" + describe(obj),
        code=f"{name}.resample({sfreq})",
    )


def crop(name: str, tmin: float = 0.0, tmax: float | None = None) -> dict:
    s = get_session()
    obj = s.get(name)
    _require_kind(obj, name, ("Raw", "Epochs", "Evoked"))
    _finite_number(tmin, "tmin")
    if tmax is not None:
        _finite_number(tmax, "tmax")
    end = obj.times[-1] if tmax is None else tmax
    if tmin > end or tmin < obj.times[0] or end > obj.times[-1]:
        raise ValueError(
            "Crop bounds must be ordered and inside the current time range (seconds)."
        )
    obj.crop(tmin=tmin, tmax=tmax)
    return _result(
        f"Cropped `{name}` to [{tmin}, {tmax}] s.\n\n" + describe(obj),
        code=f"{name}.crop(tmin={tmin}, tmax={tmax})",
    )


def set_montage(
    name: str, montage: str | None = None, on_missing: str = "warn"
) -> dict:
    import mne

    s = get_session()
    obj = s.get(name)
    montage = montage or get_default_montage()
    try:
        m = mne.channels.make_standard_montage(montage)
    except ValueError as e:
        available = ", ".join(mne.channels.get_builtin_montages())
        raise ValueError(
            f"Unknown montage '{montage}'. Built-in montages: {available}"
        ) from e
    obj.set_montage(m, on_missing=on_missing, verbose="ERROR")
    return _result(
        f"Applied montage `{montage}` to `{name}`.\n\n" + describe(obj),
        code=f"{name}.set_montage(mne.channels.make_standard_montage({montage!r}), on_missing={on_missing!r})",
    )


def set_reference(name: str, ref_channels: str = "average") -> dict:
    s = get_session()
    obj = s.get(name)
    _require_kind(obj, name, ("Raw", "Epochs", "Evoked"))
    if ref_channels == "REST":
        raise ValueError(
            "REST requires a forward model. Use mne_run_code: inst.set_eeg_reference('REST', forward=fwd); this shortcut has no forward parameter."
        )
    ref = ref_channels
    if isinstance(ref_channels, str) and ref_channels not in ("average", "REST"):
        # comma-separated list of explicit reference channel names
        ref = [c.strip() for c in ref_channels.split(",") if c.strip()]
        if not ref:
            raise ValueError("Provide at least one reference channel, or 'average'.")
    obj.set_eeg_reference(ref_channels=ref, verbose="ERROR")
    return _result(
        f"Re-referenced `{name}` to `{ref_channels}`.\n\n" + describe(obj),
        code=f"{name}.set_eeg_reference(ref_channels={ref!r})",
    )


def mark_bad_channels(name: str, bads: str, replace: bool = False) -> dict:
    s = get_session()
    obj = s.get(name)
    info = obj.info
    new = [c.strip() for c in bads.split(",") if c.strip()]
    unknown = [c for c in new if c not in info["ch_names"]]
    if unknown:
        raise ValueError(f"Unknown channel(s): {unknown}")
    if replace:
        info["bads"] = new
    else:
        info["bads"] = sorted(set(info["bads"]) | set(new))
    return _result(
        f"Bad channels for `{name}`: {info['bads']}",
        code=f"{name}.info['bads'] = {info['bads']!r}",
    )


def interpolate_bads(name: str, reset_bads: bool = True) -> dict:
    s = get_session()
    obj = s.get(name)
    if not (obj.info.get("bads")):
        raise ValueError(f"`{name}` has no bad channels marked to interpolate.")
    bads = list(obj.info["bads"])
    obj.interpolate_bads(reset_bads=reset_bads, verbose="ERROR")
    return _result(
        f"Interpolated bad channels {bads} in `{name}`.\n\n" + describe(obj),
        code=f"{name}.interpolate_bads(reset_bads={reset_bads})",
    )


# ── Visualization ──────────────────────────────────────────────────────────────


def _parse_picks(picks):
    """Turn a comma-separated picks string into a list of channel names.

    A bare string (e.g. ``'eeg'`` or a single channel name) is passed through unchanged
    so MNE can still interpret it as a channel type or single name.
    """
    if picks is None:
        return None
    if isinstance(picks, str) and "," in picks:
        return [p.strip() for p in picks.split(",") if p.strip()]
    return picks


def plot_psd(
    name: str, fmin: float = 0.0, fmax: float | None = None, picks: str | None = None
) -> dict:
    s = get_session()
    obj = s.get(name)
    before = figures.open_figure_numbers()
    kwargs = {"fmin": fmin}
    if fmax is not None:
        kwargs["fmax"] = fmax
    if picks is not None:
        kwargs["picks"] = _parse_picks(picks)
    psd = obj.compute_psd(**kwargs, verbose="ERROR")
    psd.plot(show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="psd")
    return _result(
        f"Power spectral density of `{name}`.",
        figs=figs,
        code=f"{name}.compute_psd(fmin={fmin}, fmax={fmax}).plot()",
    )


def plot_raw(
    name: str, start: float = 0.0, duration: float = 20.0, n_channels: int = 20
) -> dict:
    s = get_session()
    obj = s.get(name)
    _require_kind(obj, name, ("Raw",))
    before = figures.open_figure_numbers()
    obj.plot(start=start, duration=duration, n_channels=n_channels, show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="raw")
    return _result(
        f"Raw traces of `{name}` ({duration}s from {start}s, {n_channels} channels).",
        figs=figs,
        code=f"{name}.plot(start={start}, duration={duration}, n_channels={n_channels})",
    )


def plot_sensors(name: str, kind: str = "topomap", show_names: bool = True) -> dict:
    s = get_session()
    obj = s.get(name)
    before = figures.open_figure_numbers()
    obj.plot_sensors(kind=kind, show_names=show_names, show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="sensors")
    return _result(
        f"Sensor layout of `{name}`.",
        figs=figs,
        code=f"{name}.plot_sensors(kind={kind!r}, show_names={show_names})",
    )


# ── ICA ──────────────────────────────────────────────────────────────────────


def fit_ica(
    name: str,
    n_components: float | int | None = None,
    method: str | None = None,
    ica_name: str = "ica",
    random_state: int = 97,
) -> dict:
    import mne

    s = get_session()
    inst = s.get(name)
    _require_kind(inst, name, ("Raw", "Epochs"))
    method = method or get_ica_method()
    if n_components is None:
        n_components = get_ica_n_components()
    ica = mne.preprocessing.ICA(
        n_components=n_components,
        method=method,
        random_state=random_state,
        verbose="ERROR",
    )
    ica.fit(inst, verbose="ERROR")
    s.set(ica_name, ica)
    md = f"Fitted ICA on `{name}` → stored as `{ica_name}`.\n\n" + describe(ica)
    code = (
        f"{ica_name} = mne.preprocessing.ICA(n_components={n_components}, "
        f"method={method!r}, random_state={random_state})\n{ica_name}.fit({name})"
    )
    return _result(md, code=code)


def plot_ica_components(ica_name: str = "ica") -> dict:
    s = get_session()
    ica = s.get(ica_name)
    _require_kind(ica, ica_name, ("ICA",))
    before = figures.open_figure_numbers()
    ica.plot_components(show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="ica_comp")
    return _result(
        f"ICA component topographies for `{ica_name}`.",
        figs=figs,
        code=f"{ica_name}.plot_components()",
    )


def plot_ica_sources(ica_name: str = "ica", inst_name: str = "raw") -> dict:
    s = get_session()
    ica = s.get(ica_name)
    inst = s.get(inst_name)
    _require_kind(ica, ica_name, ("ICA",))
    before = figures.open_figure_numbers()
    ica.plot_sources(inst, show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="ica_src")
    return _result(
        f"ICA source time courses (`{ica_name}` on `{inst_name}`).",
        figs=figs,
        code=f"{ica_name}.plot_sources({inst_name})",
    )


def apply_ica(ica_name: str, inst_name: str, exclude: str | None = None) -> dict:
    s = get_session()
    ica = s.get(ica_name)
    inst = s.get(inst_name)
    _require_kind(ica, ica_name, ("ICA",))
    if exclude is not None:
        idx = [int(x.strip()) for x in str(exclude).split(",") if str(x).strip() != ""]
        ica.exclude = idx
    ica.apply(inst, verbose="ERROR")
    md = (
        f"Applied `{ica_name}` to `{inst_name}`, removing components "
        f"{ica.exclude}.\n\n" + describe(inst)
    )
    code = f"{ica_name}.exclude = {ica.exclude!r}\n{ica_name}.apply({inst_name})"
    return _result(md, code=code)


# ── Events / Epochs / ERP ──────────────────────────────────────────────────────


def find_events(
    raw_name: str = "raw", stim_channel: str | None = None, events_name: str = "events"
) -> dict:
    import mne

    s = get_session()
    raw = s.get(raw_name)
    _require_kind(raw, raw_name, ("Raw",))
    events = mne.find_events(raw, stim_channel=stim_channel, verbose="ERROR")
    s.set(events_name, events)
    import numpy as np

    ids, counts = np.unique(events[:, 2], return_counts=True)
    rows = "\n".join(f"- id `{int(i)}`: {int(c)} events" for i, c in zip(ids, counts))
    md = f"Found {len(events)} events in `{raw_name}` → stored as `{events_name}`.\n\n{rows}"
    return _result(
        md,
        code=f"{events_name} = mne.find_events({raw_name}, stim_channel={stim_channel!r})",
    )


def events_from_annotations(raw_name: str = "raw", events_name: str = "events") -> dict:
    import mne

    s = get_session()
    raw = s.get(raw_name)
    _require_kind(raw, raw_name, ("Raw",))
    events, event_id = mne.events_from_annotations(raw, verbose="ERROR")
    s.set(events_name, events)
    s.set(events_name + "_id", event_id)
    md = (
        f"Derived {len(events)} events from annotations of `{raw_name}` "
        f"→ `{events_name}`.\n\n- event_id map: `{event_id}`"
    )
    code = f"{events_name}, {events_name}_id = mne.events_from_annotations({raw_name})"
    return _result(md, code=code)


def make_epochs(
    raw_name: str = "raw",
    events_name: str = "events",
    event_id: str | dict[str, int] | None = None,
    tmin: float | None = None,
    tmax: float | None = None,
    baseline: str | list[float | None] | None = "default",
    reject_eeg: float | None = None,
    epochs_name: str = "epochs",
    *,
    reject: dict[str, float] | None = None,
    flat: dict[str, float] | None = None,
    picks: str | list[str] | list[int] | None = None,
    detrend: int | None = None,
    reject_by_annotation: bool = True,
    event_repeated: str = "error",
) -> dict:
    import mne

    s = get_session()
    raw = s.get(raw_name)
    events = s.get(events_name)
    _require_kind(raw, raw_name, ("Raw",))

    cfg_tmin, cfg_tmax = get_epoch_window()
    if tmin is None:
        tmin = cfg_tmin
    if tmax is None:
        tmax = cfg_tmax

    eid = None
    if isinstance(event_id, dict):
        if not event_id or any(
            not isinstance(k, str) or not k.strip() or type(v) is not int
            for k, v in event_id.items()
        ):
            raise ValueError(
                "event_id must be a nonempty mapping of labels to integer codes."
            )
        eid = event_id.copy()
    elif event_id:
        eid = {}
        for pair in event_id.split(","):
            if ":" in pair:
                k, v = pair.split(":")
                eid[k.strip()] = int(v.strip())
            else:
                eid[pair.strip()] = int(pair.strip())

    if baseline == "default":
        bl = (None, 0)
    elif baseline is None or str(baseline).strip().lower() == "none":
        bl = None
    else:
        bl = ast.literal_eval(baseline) if isinstance(baseline, str) else baseline
        if not isinstance(bl, (tuple, list)) or len(bl) != 2:
            raise ValueError("baseline must be [start, end], 'default', or null.")
        bl = tuple(bl)
    if reject is not None and reject_eeg is not None:
        raise ValueError("Provide reject or reject_eeg, not both.")
    if reject is None and reject_eeg is None:
        cfg_reject = get_reject_eeg()
        reject = {"eeg": cfg_reject} if cfg_reject else None
    elif reject_eeg is not None:
        reject = {"eeg": reject_eeg}
    for label, thresholds in (("reject", reject), ("flat", flat)):
        if thresholds is not None and any(
            isinstance(value, bool) or not math.isfinite(value) or value < 0
            for value in thresholds.values()
        ):
            raise ValueError(
                f"{label} thresholds must be finite, nonnegative SI values."
            )
    picks = _parse_picks(picks)

    epochs = mne.Epochs(
        raw,
        events,
        event_id=eid,
        tmin=tmin,
        tmax=tmax,
        baseline=bl,
        reject=reject,
        flat=flat,
        picks=picks,
        detrend=detrend,
        reject_by_annotation=reject_by_annotation,
        event_repeated=event_repeated,
        preload=True,
        verbose="ERROR",
    )
    s.set(epochs_name, epochs)
    md = f"Created epochs `{epochs_name}` from `{raw_name}`.\n\n" + describe(epochs)
    code = (
        f"{epochs_name} = mne.Epochs({raw_name}, {events_name}, event_id={eid!r}, "
        f"tmin={tmin}, tmax={tmax}, baseline={bl!r}, reject={reject!r}, "
        f"flat={flat!r}, picks={picks!r}, detrend={detrend!r}, "
        f"reject_by_annotation={reject_by_annotation!r}, "
        f"event_repeated={event_repeated!r}, preload=True)"
    )
    return _result(md, code=code)


def plot_epochs_image(name: str = "epochs", picks: str | None = None) -> dict:
    s = get_session()
    epochs = s.get(name)
    _require_kind(epochs, name, ("Epochs",))
    before = figures.open_figure_numbers()
    epochs.plot_image(picks=_parse_picks(picks), show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="epo_img")
    return _result(
        f"Epochs image (ERP image) for `{name}`.",
        figs=figs,
        code=f"{name}.plot_image(picks={picks!r})",
    )


def average_evoked(
    epochs_name: str = "epochs",
    condition: str | None = None,
    evoked_name: str = "evoked",
) -> dict:
    s = get_session()
    epochs = s.get(epochs_name)
    _require_kind(epochs, epochs_name, ("Epochs",))
    src = epochs[condition] if condition else epochs
    evoked = src.average()
    if condition:
        evoked.comment = condition
    s.set(evoked_name, evoked)
    sel = f"[{condition!r}]" if condition else ""
    md = f"Averaged `{epochs_name}`{sel} → evoked `{evoked_name}`.\n\n" + describe(
        evoked
    )
    code = f"{evoked_name} = {epochs_name}{sel}.average()"
    return _result(md, code=code)


def plot_evoked(name: str = "evoked", style: str = "joint") -> dict:
    s = get_session()
    evoked = s.get(name)
    _require_kind(evoked, name, ("Evoked",))
    before = figures.open_figure_numbers()
    if style == "joint":
        evoked.plot_joint(show=False)
    elif style == "topo":
        evoked.plot_topo(show=False)
    else:
        evoked.plot(show=False, spatial_colors=True)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="evoked")
    return _result(
        f"Evoked response `{name}` ({style}).",
        figs=figs,
        code=f"{name}.plot_{'joint' if style=='joint' else style}()",
    )


def plot_topomap(name: str = "evoked", times: str = "auto") -> dict:
    s = get_session()
    evoked = s.get(name)
    _require_kind(evoked, name, ("Evoked",))
    before = figures.open_figure_numbers()
    t = times
    if times not in ("auto", "peaks", "interactive"):
        t = [float(x.strip()) for x in str(times).split(",") if str(x).strip()]
    evoked.plot_topomap(times=t, show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="topomap")
    return _result(
        f"Scalp topographies of `{name}` at times={times}.",
        figs=figs,
        code=f"{name}.plot_topomap(times={t!r})",
    )


# ── Time-frequency ─────────────────────────────────────────────────────────────


def compute_tfr(params: TFRParameters) -> dict:
    """Compute total power/ITC without changing the input epochs."""
    s = get_session()
    epochs = s.get(params.epochs_name)
    _require_kind(epochs, params.epochs_name, ("Epochs",))
    if params.freqs[-1] >= epochs.info["sfreq"] / 2:
        raise ValueError(
            "All freqs must be below the data Nyquist frequency (sfreq / 2)."
        )
    if not len(epochs):
        raise ValueError(
            "No epochs remain. Inspect the epoch drop log before computing TFR."
        )
    kwargs = dict(
        method=params.method,
        freqs=params.freqs,
        n_cycles=params.n_cycles,
        picks=_parse_picks(params.picks),
        average=params.average,
        return_itc=params.return_itc,
        decim=params.decim,
        output="power",
    )
    if params.time_bandwidth is not None:
        kwargs["time_bandwidth"] = params.time_bandwidth
    result = epochs.compute_tfr(**kwargs, verbose="ERROR")
    power, itc = result if params.return_itc else (result, None)
    if params.baseline is not None:
        power.apply_baseline(
            params.baseline, mode=params.baseline_mode, verbose="ERROR"
        )
    figs = []
    if params.plot:
        before = figures.open_figure_numbers()
        display = power if params.average else power.average()
        display.plot(combine="mean", show=False)
        figs = figures.capture_new_figures(before, get_results_dir(), prefix="tfr")
    s.set(params.tfr_name, power)
    if itc is not None:
        s.set(params.itc_name, itc)
    target = (
        f"{params.tfr_name}, {params.itc_name}"
        if params.return_itc
        else params.tfr_name
    )
    arguments = ", ".join(f"{key}={value!r}" for key, value in kwargs.items())
    code = f"{target} = {params.epochs_name}.compute_tfr({arguments})"
    if params.baseline is not None:
        code += f"\n{params.tfr_name}.apply_baseline({params.baseline!r}, mode={params.baseline_mode!r})"
    if params.plot:
        display_code = (
            params.tfr_name if params.average else f"{params.tfr_name}.average()"
        )
        code += f"\n{display_code}.plot(combine='mean', show=False)"
    md = (
        f"{params.method} power: `{params.epochs_name}` -> `{params.tfr_name}`; "
        f"shape={power.data.shape}, average={params.average}, decim={params.decim}. "
        f"Baseline={params.baseline!r}, mode={params.baseline_mode if params.baseline is not None else 'none'}."
    )
    if itc is not None:
        md += f" ITC stored as `{params.itc_name}` (not baseline-normalized)."
    if params.decim > 1:
        md += " Decimation is post-transform subsampling and can alias."
    return _result(md, figs=figs, code=code)


def tfr_morlet(
    epochs_name: str = "epochs",
    fmin: float = 4.0,
    fmax: float = 40.0,
    n_freqs: int = 20,
    tfr_name: str = "power",
) -> dict:
    import numpy as np

    s = get_session()
    epochs = s.get(epochs_name)
    _require_kind(epochs, epochs_name, ("Epochs",))
    freqs = np.linspace(fmin, fmax, int(n_freqs))
    n_cycles = freqs / 2.0
    power = epochs.compute_tfr(
        method="morlet",
        freqs=freqs,
        n_cycles=n_cycles,
        return_itc=False,
        average=True,
        verbose="ERROR",
    )
    s.set(tfr_name, power)
    before = figures.open_figure_numbers()
    power.plot(combine="mean", show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="tfr")
    md = f"Morlet time-frequency power for `{epochs_name}` → `{tfr_name}` ({fmin}-{fmax} Hz)."
    code = (
        f"freqs = np.linspace({fmin}, {fmax}, {n_freqs})\n"
        f"{tfr_name} = {epochs_name}.compute_tfr('morlet', freqs=freqs, "
        f"n_cycles=freqs/2, return_itc=False, average=True)\n{tfr_name}.plot(combine='mean')"
    )
    return _result(md, figs=figs, code=code)


# ── Export ─────────────────────────────────────────────────────────────────────


def save_object(name: str, path: str, overwrite: bool = True) -> dict:
    s = get_session()
    obj = s.get(name)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    obj.save(str(p), overwrite=overwrite)
    return _result(
        f"Saved `{name}` ({object_kind(obj)}) to `{p}`.",
        code=f"{name}.save({p.as_posix()!r}, overwrite={overwrite})",
    )


# ── Decoding (MVPA) ─────────────────────────────────────────────────────────────


def decoding_group_test(params) -> dict:
    from mne_mcp.inference import decoding_group_test as run_test

    return run_test(params)


def decode_time(
    epochs_name: str = "epochs",
    cond_a: str | None = None,
    cond_b: str | None = None,
    scoring: str = "roc_auc",
    cv: int = 5,
    name: str = "decoding",
    *,
    cv_strategy: str = "stratified",
    groups: list[str] | list[int] | None = None,
    picks: str | list[str] | list[int] | None = None,
    shuffle: bool = False,
    random_state: int = 97,
    plot: bool = True,
    method: str = "sliding",
    tmin: float | None = None,
    tmax: float | None = None,
    C: float = 1.0,
    class_weight: str | None = None,
    max_iter: int = 1000,
) -> dict:
    from mne_mcp.decoding import run_decoding

    return run_decoding(
        epochs_name,
        cond_a,
        cond_b,
        scoring,
        cv,
        name,
        cv_strategy=cv_strategy,
        groups=groups,
        picks=_parse_picks(picks),
        shuffle=shuffle,
        random_state=random_state,
        plot=plot,
        method=method,
        tmin=tmin,
        tmax=tmax,
        C=C,
        class_weight=class_weight,
        max_iter=max_iter,
    )


# ── Connectivity ────────────────────────────────────────────────────────────────


def connectivity(
    epochs_name: str = "epochs",
    method: str = "coh",
    fmin: float = 8.0,
    fmax: float = 13.0,
    con_name: str = "con",
) -> dict:
    return compute_connectivity(
        ConnectivityParameters(
            epochs_name=epochs_name,
            method=method,
            fmin=fmin,
            fmax=fmax,
            con_name=con_name,
        ),
        _legacy_dense=True,
    )


def compute_connectivity(
    params: ConnectivityParameters, *, _legacy_dense: bool = False
) -> dict:
    """Keep ordered edges, signs and complex values intact in the stored result."""
    import warnings

    import numpy as np
    from mne_connectivity import spectral_connectivity_epochs

    s = get_session()
    epochs = s.get(params.epochs_name)
    _require_kind(epochs, params.epochs_name, ("Epochs",))
    if len(epochs) < 2:
        raise ValueError(
            "Connectivity across epochs requires at least two retained trials; few trials remain unreliable."
        )
    selected = epochs.copy().pick(
        _parse_picks(params.picks) if params.picks is not None else "data",
        exclude="bads",
    )
    names = selected.ch_names
    if len(names) < 2:
        raise ValueError("Select at least two non-bad data channels.")
    lows = params.fmin if isinstance(params.fmin, list) else [params.fmin]
    highs = params.fmax if isinstance(params.fmax, list) else [params.fmax]
    if max(highs + (params.cwt_freqs or [])) >= epochs.info["sfreq"] / 2:
        raise ValueError(
            "Frequency edges and cwt_freqs must be below Nyquist (sfreq / 2)."
        )
    tmin = epochs.times[0] if params.tmin is None else params.tmin
    tmax = epochs.times[-1] if params.tmax is None else params.tmax
    if tmin < epochs.times[0] or tmax > epochs.times[-1] or tmin >= tmax:
        raise ValueError("Time window must lie inside the epoch and have tmin < tmax.")
    if params.pairs is not None:
        unknown = sorted({ch for pair in params.pairs for ch in pair} - set(names))
        if unknown:
            raise ValueError(
                f"Pair channels absent after picks/bad-channel exclusion: {unknown}"
            )
        seeds = [names.index(a) for a, _ in params.pairs]
        targets = [names.index(b) for _, b in params.pairs]
    elif params.method == "dpli":
        seeds, targets = np.where(~np.eye(len(names), dtype=bool))
        seeds, targets = seeds.tolist(), targets.tolist()
    else:
        seeds, targets = np.tril_indices(len(names), k=-1)
        seeds, targets = seeds.tolist(), targets.tolist()
    kwargs = dict(
        method=params.method,
        mode=params.mode,
        indices=(seeds, targets),
        fmin=tuple(lows),
        fmax=tuple(highs),
        faverage=params.faverage,
        tmin=params.tmin,
        tmax=params.tmax,
        block_size=params.block_size,
        n_jobs=1,
    )
    if _legacy_dense:
        kwargs["indices"] = None
        if params.method == "dpli":
            # Compute both directions rather than infer them; keep n_channels**2 storage.
            rows, cols = np.indices((len(names), len(names)))
            kwargs["indices"] = (rows.ravel().tolist(), cols.ravel().tolist())
    if params.mode == "multitaper":
        kwargs.update(
            mt_bandwidth=params.mt_bandwidth,
            mt_adaptive=params.mt_adaptive,
            mt_low_bias=params.mt_low_bias,
        )
    elif params.mode == "cwt_morlet":
        kwargs.update(
            cwt_freqs=np.asarray(params.cwt_freqs),
            cwt_n_cycles=(
                params.cwt_n_cycles if params.cwt_n_cycles is not None else 7.0
            ),
        )
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        con = spectral_connectivity_epochs(selected, **kwargs, verbose="WARNING")
    values = np.asarray(con.get_data())
    if _legacy_dense:
        values = con.get_data(output="dense")[seeds, targets]
    labels = [f"{names[a]} -> {names[b]}" for a, b in zip(seeds, targets)]
    # Summaries never infer reverse edges or discard imaginary/sign information.
    display = np.abs(values) if np.iscomplexobj(values) else values
    if display.ndim == 3:
        display = display.mean(axis=-1)
    nonfinite = int((~np.isfinite(values)).sum())
    figs = []
    if params.plot:
        import matplotlib.pyplot as plt

        before = figures.open_figure_numbers()
        count = min(len(labels), 30)
        fig, ax = plt.subplots(figsize=(8, max(3, min(10, count * 0.3))))
        metric = f"abs({params.method})" if np.iscomplexobj(values) else params.method
        color_options = {"cmap": "viridis"}
        if params.method == "imcoh":
            color_options = {"cmap": "RdBu_r", "vmin": -1, "vmax": 1}
        elif params.method == "dpli":
            color_options = {"cmap": "RdBu_r", "vmin": 0, "vmax": 1}
        im = ax.imshow(
            np.ma.masked_invalid(display[:count]), aspect="auto", **color_options
        )
        fig.colorbar(im, ax=ax, label=metric)
        ax.set_yticks(range(count), labels[:count])
        if params.faverage:
            ax.set_xticks(
                range(len(lows)), [f"{lo:g}-{hi:g} Hz" for lo, hi in zip(lows, highs)]
            )
        elif len(con.freqs) <= 12:
            ax.set_xticks(range(len(con.freqs)), [f"{f:g}" for f in con.freqs])
        ax.set(
            xlabel=(
                "Band" if params.faverage else "Frequency bin (Hz labels where shown)"
            ),
            ylabel="Ordered edge",
            title=f"{metric}: first {count}/{len(labels)} edges"
            + (" (time mean)" if values.ndim == 3 else ""),
        )
        fig.tight_layout()
        figs = figures.capture_new_figures(before, get_results_dir(), prefix="conn")
    s.set(params.con_name, con)
    md = (
        f"Spectral connectivity ({params.method}, {params.mode}) for `{params.epochs_name}` "
        f"-> `{params.con_name}`; {len(epochs)} trials, {len(names)} channels, {len(labels)} ordered edges, "
        f"stored_shape={con.get_data().shape}, edge_shape={values.shape}, "
        f"bands={list(zip(lows, highs))}, faverage={params.faverage}. "
        "Stored values retain sign/complex components; uncomputed reverse edges are not inferred."
    )
    if params.method == "dpli":
        md += " dPLI is an ordered phase-lag statistic, not evidence of causality."
    if params.mode == "cwt_morlet":
        md += " Time points are retained in the result; the plot averages over time. Estimates are across trials, not single-trial connectivity."
    if nonfinite:
        md += f" Warning: {nonfinite} non-finite values; inspect flat channels, trial count and spectral support."
    warning_messages = list(dict.fromkeys(str(w.message) for w in captured))
    if warning_messages:
        md += "\n\nUpstream warnings:\n" + "\n".join(
            f"- {message}" for message in warning_messages[:5]
        )
        if len(warning_messages) > 5:
            md += (
                f"\n- {len(warning_messages) - 5} additional distinct warnings omitted."
            )
    md += "\n\nFirst edges (mean over returned frequencies/bands and time; descriptive only):\n"
    for label, value in zip(labels[:10], values[:10]):
        md += f"- {label}: {value.mean():.5g}\n"
    arguments = ", ".join(
        (
            f"{key}=np.array({value.tolist()!r})"
            if isinstance(value, np.ndarray)
            else f"{key}={value!r}"
        )
        for key, value in kwargs.items()
    )
    code = (
        "import numpy as np\nfrom mne_connectivity import spectral_connectivity_epochs\n"
        f"{params.con_name} = spectral_connectivity_epochs("
        f"{params.epochs_name}.copy().pick({names!r}), {arguments})"
    )
    return _result(md, figs=figs, code=code)


# ── Source localization ─────────────────────────────────────────────────────────


def compute_noise_cov(
    name: str = "epochs", tmax: float = 0.0, cov_name: str = "noise_cov"
) -> dict:
    import mne

    s = get_session()
    epochs = s.get(name)
    _require_kind(epochs, name, ("Epochs",))
    cov = mne.compute_covariance(epochs, tmax=tmax, method="empirical", verbose="ERROR")
    s.set(cov_name, cov)
    return _result(
        f"Noise covariance from `{name}` baseline (tmax={tmax}) → `{cov_name}` "
        f"({cov['data'].shape[0]} channels).",
        code=f"{cov_name} = mne.compute_covariance({name}, tmax={tmax}, method='empirical')",
    )


def fsaverage_forward(name: str = "evoked", fwd_name: str = "fwd") -> dict:
    import os

    import mne

    s = get_session()
    inst = s.get(name)
    fs_dir = mne.datasets.fetch_fsaverage(verbose="ERROR")
    src = os.path.join(fs_dir, "bem", "fsaverage-ico-5-src.fif")
    bem = os.path.join(fs_dir, "bem", "fsaverage-5120-5120-5120-bem-sol.fif")
    fwd = mne.make_forward_solution(
        inst.info,
        trans="fsaverage",
        src=src,
        bem=bem,
        eeg=True,
        meg=False,
        verbose="ERROR",
    )
    s.set(fwd_name, fwd)
    return _result(
        f"Built fsaverage (template head) forward model for `{name}` → `{fwd_name}` "
        f"({fwd['nsource']} sources, EEG). Suitable for group/template EEG source estimation.",
        code=(
            "fs = mne.datasets.fetch_fsaverage()\n"
            f"{fwd_name} = mne.make_forward_solution({name}.info, trans='fsaverage', "
            "src=fs+'/bem/fsaverage-ico-5-src.fif', "
            "bem=fs+'/bem/fsaverage-5120-5120-5120-bem-sol.fif', eeg=True, meg=False)"
        ),
    )


def apply_inverse_op(
    evoked_name: str = "evoked",
    fwd_name: str = "fwd",
    cov_name: str = "noise_cov",
    method: str = "dSPM",
    snr: float = 3.0,
    stc_name: str = "stc",
) -> dict:
    from mne.minimum_norm import apply_inverse, make_inverse_operator

    s = get_session()
    evoked = s.get(evoked_name)
    fwd = s.get(fwd_name)
    cov = s.get(cov_name)
    inv = make_inverse_operator(evoked.info, fwd, cov, verbose="ERROR")
    lambda2 = 1.0 / float(snr) ** 2
    stc = apply_inverse(evoked, inv, lambda2, method=method, verbose="ERROR")
    s.set(stc_name, stc)
    s.set(stc_name + "_inv", inv)
    vtx, t_peak = stc.get_peak()
    md = (
        f"Source estimate ({method}, SNR={snr}) for `{evoked_name}` → `{stc_name}`. "
        f"Peak activation at t={t_peak:.3f}s (vertex {vtx}). "
        f"Use `mne_plot_source_estimate` to render the cortical map."
    )
    code = (
        "from mne.minimum_norm import make_inverse_operator, apply_inverse\n"
        f"inv = make_inverse_operator({evoked_name}.info, {fwd_name}, {cov_name})\n"
        f"{stc_name} = apply_inverse({evoked_name}, inv, lambda2=1/{snr}**2, method={method!r})"
    )
    return _result(md, code=code)


def plot_source_estimate(
    stc_name: str = "stc", hemi: str = "both", time: float | None = None
) -> dict:
    import os

    import mne

    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    os.environ.setdefault("MNE_3D_OPTION_MULTI_SAMPLES", "1")
    s = get_session()
    stc = s.get(stc_name)
    fs_dir = mne.datasets.fetch_fsaverage(verbose="ERROR")
    subjects_dir = os.path.dirname(fs_dir)
    t = time if time is not None else stc.get_peak()[1]
    try:
        brain = stc.plot(
            subjects_dir=subjects_dir,
            hemi=hemi,
            initial_time=t,
            size=(700, 600),
            background="white",
            time_viewer=False,
            verbose="ERROR",
        )
        out = Path(get_results_dir()) / f"stc_{stc_name}.png"
        brain.save_image(str(out))
        brain.close()
    except Exception as e:  # 3D rendering is not always possible headless
        raise RuntimeError(
            f"Could not render the source estimate ({type(e).__name__}: {e}). "
            "Headless 3D rendering needs a working PyVista/VTK off-screen backend. "
            "The source estimate itself is computed and stored; inspect it numerically via mne_run_code."
        ) from e
    return _result(
        f"Cortical source map for `{stc_name}` at t={t:.3f}s.",
        figs=[str(out)],
        code=f"{stc_name}.plot(subjects_dir=..., hemi={hemi!r}, initial_time={t})",
    )
