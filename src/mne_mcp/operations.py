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
from mne_mcp.summaries import describe, object_kind

# Extensions MNE can read as raw recordings (not exhaustive, but the common set).
_RAW_EXTENSIONS = {
    ".fif", ".fif.gz", ".edf", ".bdf", ".gdf", ".vhdr", ".set", ".cnt",
    ".egi", ".mff", ".nxe", ".eeg", ".data", ".sqd", ".con", ".ds",
    ".nwb", ".snirf",
}

# Directories never worth scanning for user data (envs, VCS, caches, package data).
_SKIP_DIRS = {
    ".venv", "venv", "env", ".git", "node_modules", "__pycache__", "site-packages",
    ".idea", ".vscode", ".pytest_cache", "build", "dist", ".eggs", ".mypy_cache",
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
    code = f'{name} = mne.io.read_raw({p.as_posix()!r}, preload={preload})'
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

def filter_data(
    name: str,
    l_freq: float | None = None,
    h_freq: float | None = None,
    notch: float | None = None,
    picks: str | None = None,
) -> dict:
    s = get_session()
    obj = s.get(name)
    _require_kind(obj, name, ("Raw", "Epochs", "Evoked"))
    # No band and no notch given → fall back to the configured default filter band.
    if l_freq is None and h_freq is None and notch is None:
        l_freq, h_freq = get_filter_band()
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
    return _result(md, code="\n".join(code_lines))


def resample(name: str, sfreq: float) -> dict:
    s = get_session()
    obj = s.get(name)
    _require_kind(obj, name, ("Raw", "Epochs"))
    obj.resample(sfreq, verbose="ERROR")
    return _result(
        f"Resampled `{name}` to {sfreq} Hz.\n\n" + describe(obj),
        code=f"{name}.resample({sfreq})",
    )


def crop(name: str, tmin: float = 0.0, tmax: float | None = None) -> dict:
    s = get_session()
    obj = s.get(name)
    _require_kind(obj, name, ("Raw", "Epochs", "Evoked"))
    obj.crop(tmin=tmin, tmax=tmax)
    return _result(
        f"Cropped `{name}` to [{tmin}, {tmax}] s.\n\n" + describe(obj),
        code=f"{name}.crop(tmin={tmin}, tmax={tmax})",
    )


def set_montage(name: str, montage: str | None = None, on_missing: str = "warn") -> dict:
    import mne

    s = get_session()
    obj = s.get(name)
    montage = montage or get_default_montage()
    try:
        m = mne.channels.make_standard_montage(montage)
    except ValueError as e:
        available = ", ".join(mne.channels.get_builtin_montages())
        raise ValueError(f"Unknown montage '{montage}'. Built-in montages: {available}") from e
    obj.set_montage(m, on_missing=on_missing, verbose="ERROR")
    return _result(
        f"Applied montage `{montage}` to `{name}`.\n\n" + describe(obj),
        code=f"{name}.set_montage(mne.channels.make_standard_montage({montage!r}), on_missing={on_missing!r})",
    )


def set_reference(name: str, ref_channels: str = "average") -> dict:
    s = get_session()
    obj = s.get(name)
    _require_kind(obj, name, ("Raw", "Epochs", "Evoked"))
    ref = ref_channels
    if isinstance(ref_channels, str) and ref_channels not in ("average", "REST"):
        # comma-separated list of explicit reference channel names
        ref = [c.strip() for c in ref_channels.split(",") if c.strip()]
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

def plot_psd(name: str, fmin: float = 0.0, fmax: float | None = None, picks: str | None = None) -> dict:
    s = get_session()
    obj = s.get(name)
    before = figures.open_figure_numbers()
    kwargs = {"fmin": fmin}
    if fmax is not None:
        kwargs["fmax"] = fmax
    if picks is not None:
        kwargs["picks"] = picks
    psd = obj.compute_psd(**kwargs, verbose="ERROR")
    psd.plot(show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="psd")
    return _result(
        f"Power spectral density of `{name}`.",
        figs=figs,
        code=f"{name}.compute_psd(fmin={fmin}, fmax={fmax}).plot()",
    )


def plot_raw(name: str, start: float = 0.0, duration: float = 20.0, n_channels: int = 20) -> dict:
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
        n_components=n_components, method=method, random_state=random_state, verbose="ERROR"
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

def find_events(raw_name: str = "raw", stim_channel: str | None = None, events_name: str = "events") -> dict:
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
    return _result(md, code=f"{events_name} = mne.find_events({raw_name}, stim_channel={stim_channel!r})")


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
    event_id: str | None = None,
    tmin: float | None = None,
    tmax: float | None = None,
    baseline: str | None = "default",
    reject_eeg: float | None = None,
    epochs_name: str = "epochs",
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
    if event_id:
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
        bl = ast.literal_eval(baseline)  # safe: only literals, e.g. "(None, 0.1)"
    if reject_eeg is None:
        cfg_reject = get_reject_eeg()
        reject = {"eeg": cfg_reject} if cfg_reject else None
    else:
        reject = {"eeg": reject_eeg}

    epochs = mne.Epochs(
        raw, events, event_id=eid, tmin=tmin, tmax=tmax,
        baseline=bl, reject=reject, preload=True, verbose="ERROR",
    )
    s.set(epochs_name, epochs)
    md = f"Created epochs `{epochs_name}` from `{raw_name}`.\n\n" + describe(epochs)
    code = (
        f"{epochs_name} = mne.Epochs({raw_name}, {events_name}, event_id={eid!r}, "
        f"tmin={tmin}, tmax={tmax}, baseline={bl!r}, reject={reject!r}, preload=True)"
    )
    return _result(md, code=code)


def plot_epochs_image(name: str = "epochs", picks: str | None = None) -> dict:
    s = get_session()
    epochs = s.get(name)
    _require_kind(epochs, name, ("Epochs",))
    before = figures.open_figure_numbers()
    epochs.plot_image(picks=picks, show=False)
    figs = figures.capture_new_figures(before, get_results_dir(), prefix="epo_img")
    return _result(
        f"Epochs image (ERP image) for `{name}`.",
        figs=figs,
        code=f"{name}.plot_image(picks={picks!r})",
    )


def average_evoked(epochs_name: str = "epochs", condition: str | None = None, evoked_name: str = "evoked") -> dict:
    s = get_session()
    epochs = s.get(epochs_name)
    _require_kind(epochs, epochs_name, ("Epochs",))
    src = epochs[condition] if condition else epochs
    evoked = src.average()
    if condition:
        evoked.comment = condition
    s.set(evoked_name, evoked)
    sel = f"[{condition!r}]" if condition else ""
    md = f"Averaged `{epochs_name}`{sel} → evoked `{evoked_name}`.\n\n" + describe(evoked)
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
        method="morlet", freqs=freqs, n_cycles=n_cycles,
        return_itc=False, average=True, verbose="ERROR",
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
