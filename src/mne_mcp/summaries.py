"""
Human-readable Markdown summaries of MNE objects.

These give the assistant a compact, reliable textual view of session state
(channel counts, sampling rate, montage, bad channels, event ids, etc.) without
having to serialize the whole object. Detection is by class name so the module
never hard-fails if a given MNE submodule is unavailable.
"""

from __future__ import annotations


def object_kind(obj) -> str:
    """Return a short label for an MNE/numpy object."""
    cls = type(obj).__name__
    mod = type(obj).__module__ or ""
    if cls.startswith("Raw"):
        return "Raw"
    if cls == "Epochs" or cls.startswith("Epochs") or cls == "EpochsArray":
        return "Epochs"
    if cls in ("Evoked", "EvokedArray"):
        return "Evoked"
    if cls == "ICA":
        return "ICA"
    if cls == "Info":
        return "Info"
    if cls in ("AverageTFR", "EpochsTFR", "RawTFR"):
        return "TFR"
    if cls == "ndarray":
        return "ndarray"
    if "forward" in mod or cls == "Forward":
        return "Forward"
    if cls in ("SourceEstimate", "VolSourceEstimate", "VectorSourceEstimate"):
        return "SourceEstimate"
    if cls == "Covariance":
        return "Covariance"
    return cls


def _fmt_ch_types(info) -> str:
    try:
        import mne

        counts: dict[str, int] = {}
        types = info.get_channel_types()
        for t in types:
            counts[t] = counts.get(t, 0) + 1
        return ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    except Exception:
        return "unknown"


def _info_block(info) -> list[str]:
    lines = []
    try:
        lines.append(f"- Channels: {info['nchan']} ({_fmt_ch_types(info)})")
    except Exception:
        pass
    try:
        lines.append(f"- Sampling rate: {info['sfreq']:.1f} Hz")
    except Exception:
        pass
    try:
        hp = info.get("highpass")
        lp = info.get("lowpass")
        lines.append(f"- Filter band (info): highpass={hp} Hz, lowpass={lp} Hz")
    except Exception:
        pass
    try:
        bads = info.get("bads") or []
        lines.append(f"- Bad channels: {bads if bads else 'none'}")
    except Exception:
        pass
    try:
        dig = info.get("dig")
        lines.append(f"- Montage/digitization: {'present' if dig else 'none set'}")
    except Exception:
        pass
    return lines


def _describe_raw(raw) -> str:
    lines = ["**Raw** recording", ""]
    lines += _info_block(raw.info)
    try:
        lines.append(f"- Duration: {raw.times[-1]:.2f} s ({raw.n_times} samples)")
    except Exception:
        pass
    try:
        n_annot = len(raw.annotations)
        lines.append(f"- Annotations: {n_annot}")
    except Exception:
        pass
    return "\n".join(lines)


def _describe_epochs(epochs) -> str:
    lines = ["**Epochs**", ""]
    try:
        lines.append(f"- Number of epochs: {len(epochs)}")
    except Exception:
        pass
    try:
        ev = epochs.event_id
        lines.append(f"- Conditions (event_id): {dict(ev)}")
    except Exception:
        pass
    try:
        lines.append(f"- Time window: {epochs.tmin:.3f} to {epochs.tmax:.3f} s")
    except Exception:
        pass
    try:
        lines.append(f"- Baseline: {epochs.baseline}")
    except Exception:
        pass
    lines += _info_block(epochs.info)
    return "\n".join(lines)


def _describe_evoked(evoked) -> str:
    lines = ["**Evoked** (averaged response)", ""]
    try:
        lines.append(f"- Comment/condition: {evoked.comment}")
    except Exception:
        pass
    try:
        lines.append(f"- Averaged epochs (nave): {evoked.nave}")
    except Exception:
        pass
    try:
        lines.append(f"- Time window: {evoked.times[0]:.3f} to {evoked.times[-1]:.3f} s")
    except Exception:
        pass
    lines += _info_block(evoked.info)
    return "\n".join(lines)


def _describe_ica(ica) -> str:
    lines = ["**ICA** decomposition", ""]
    for attr, label in [
        ("n_components_", "Fitted components"),
        ("method", "Method"),
        ("exclude", "Excluded components"),
    ]:
        try:
            lines.append(f"- {label}: {getattr(ica, attr)}")
        except Exception:
            pass
    return "\n".join(lines)


def _describe_array(arr) -> str:
    return f"**ndarray** shape={arr.shape}, dtype={arr.dtype}"


def describe(obj) -> str:
    """Return a Markdown description of an MNE/numpy object."""
    kind = object_kind(obj)
    try:
        if kind == "Raw":
            return _describe_raw(obj)
        if kind == "Epochs":
            return _describe_epochs(obj)
        if kind == "Evoked":
            return _describe_evoked(obj)
        if kind == "ICA":
            return _describe_ica(obj)
        if kind == "Info":
            return "**Info**\n\n" + "\n".join(_info_block(obj))
        if kind == "ndarray":
            return _describe_array(obj)
    except Exception as e:  # pragma: no cover - defensive
        return f"**{kind}** (could not summarize: {e})\n\n```\n{repr(obj)[:500]}\n```"

    # Fallback: truncated repr
    text = repr(obj)
    if len(text) > 800:
        text = text[:800] + " ..."
    return f"**{kind}**\n\n```\n{text}\n```"
