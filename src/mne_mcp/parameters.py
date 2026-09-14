"""Validated, JSON-native parameters for extended analysis tools."""

import keyword
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PositiveFloat = Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]


def _session_name(value: str) -> str:
    if (
        not value.isidentifier()
        or keyword.iskeyword(value)
        or value.startswith("_")
        or value in {"mne", "np", "pd", "plt", "session", "SESSION"}
    ):
        raise ValueError("Use a non-reserved Python identifier for the session name.")
    return value


class DecodingOptions(BaseModel):
    """Validated options shared by direct and MCP decoding calls."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    method: Literal["sliding", "generalizing"] = "sliding"
    tmin: float | None = None
    tmax: float | None = None
    C: PositiveFloat = 1.0
    class_weight: Literal["balanced"] | None = None
    max_iter: Annotated[int, Field(ge=1)] = 1000
    cv: Annotated[int, Field(ge=2)] = 5
    shuffle: bool = False
    random_state: Annotated[int, Field(ge=0, le=2**32 - 1)] = 97
    plot: bool = True

    @model_validator(mode="after")
    def valid_window(self) -> Self:
        if self.tmin is not None and self.tmax is not None and self.tmin > self.tmax:
            raise ValueError("tmin must not exceed tmax.")
        return self


class DecodingGroupTestParameters(BaseModel):
    """One mean decoding result per independent subject, never CV folds."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    score_names: list[str] = Field(
        min_length=2,
        description="One mne_decode mean result per subject; not name_folds.",
    )
    subject_ids: list[str] = Field(
        min_length=2, description="Unique independent-subject IDs in score_names order."
    )
    independent_subjects: bool = Field(
        strict=True,
        description="Explicit confirmation of independent subjects, not folds/runs of one subject.",
    )
    null_value: Annotated[float, Field(strict=True, ge=0, le=1)] = Field(
        description="Predeclared reference, usually 0.5 for ROC AUC or balanced accuracy; not estimated here."
    )
    correction: Literal["max_t", "cluster"] = "max_t"
    tail: Annotated[int, Field(strict=True, ge=-1, le=1)] = 0
    n_permutations: Annotated[int, Field(strict=True, ge=2, le=100000)] = 1024
    seed: Annotated[int, Field(strict=True, ge=0, le=2**32 - 1)] = 97
    alpha: Annotated[float, Field(strict=True, gt=0, lt=1)] = 0.05
    threshold: Annotated[float, Field(strict=True)] | None = Field(
        default=None,
        description="Cluster-forming t threshold, not p; null uses MNE's p=0.05 threshold.",
    )
    name: str = "decoding_stats"
    plot: bool = Field(default=True, strict=True)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        return _session_name(value)

    @model_validator(mode="after")
    def valid_design(self) -> Self:
        if not self.independent_subjects:
            raise ValueError(
                "Confirm independent subjects; folds and repeated runs are not independent observations."
            )
        for values in (self.score_names, self.subject_ids):
            if any(not value.strip() or value != value.strip() for value in values):
                raise ValueError(
                    "Names and IDs must be nonempty and have no surrounding whitespace."
                )
            if len(set(values)) != len(values):
                raise ValueError(
                    "Duplicate score names or subject IDs are not independent observations."
                )
        if len(self.score_names) != len(self.subject_ids):
            raise ValueError("subject_ids must align with score_names.")
        for value in self.score_names:
            _session_name(value)
        if self.name in self.score_names or self.name in [
            n + "_details" for n in self.score_names
        ]:
            raise ValueError("Output must not overwrite input scores or diagnostics.")
        if self.correction == "max_t" and (
            self.tail != 0 or self.threshold is not None
        ):
            raise ValueError(
                "max_t supports two-sided tail=0 only and no cluster threshold."
            )
        if self.threshold is not None:
            if (self.tail == -1 and self.threshold >= 0) or (
                self.tail != -1 and self.threshold <= 0
            ):
                raise ValueError(
                    "Cluster threshold must be negative for tail=-1 and positive otherwise."
                )
        return self


class TFRParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    epochs_name: str = Field(
        default="epochs", description="Existing Epochs session object."
    )
    method: Literal["morlet", "multitaper"] = "morlet"
    freqs: list[PositiveFloat] = Field(
        min_length=1,
        description="Strictly increasing frequencies in Hz, below Nyquist.",
    )
    n_cycles: PositiveFloat | list[PositiveFloat] = Field(
        default=7.0, description="Cycles per frequency: one value or one per frequency."
    )
    time_bandwidth: Annotated[float, Field(ge=2)] | None = Field(
        default=None, description="Multitaper only; MNE default is 4.0."
    )
    picks: str | list[str] | list[int] | None = Field(
        default=None, description="Channel type, channel names, or zero-based indices."
    )
    average: bool = Field(
        default=True, description="Average single-trial power (total power)."
    )
    return_itc: bool = Field(default=False, description="ITC requires average=true.")
    decim: Annotated[int, Field(strict=True, ge=1)] = Field(
        default=1,
        description="Post-transform decimation; may alias, not an anti-alias filter.",
    )
    baseline: tuple[float | None, float | None] | None = Field(
        default=None,
        description="Optional power normalization interval [start, end], seconds.",
    )
    baseline_mode: Literal[
        "mean", "ratio", "logratio", "percent", "zscore", "zlogratio"
    ] = "mean"
    tfr_name: str = Field(default="power", description="Output power session name.")
    itc_name: str = Field(default="itc", description="Output ITC name when requested.")
    plot: bool = Field(
        default=True, description="Plot mean across channels (and trials if retained)."
    )

    @field_validator("epochs_name", "tfr_name", "itc_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        return _session_name(value)

    @model_validator(mode="after")
    def compatible_options(self) -> Self:
        if any(b <= a for a, b in zip(self.freqs, self.freqs[1:])):
            raise ValueError("freqs must be strictly increasing.")
        if isinstance(self.n_cycles, list) and len(self.n_cycles) != len(self.freqs):
            raise ValueError("n_cycles must have one value per frequency.")
        if self.method != "multitaper" and self.time_bandwidth is not None:
            raise ValueError("time_bandwidth is only supported by multitaper.")
        if self.return_itc and not self.average:
            raise ValueError("return_itc requires average=true.")
        if self.baseline is not None:
            start, end = self.baseline
            if start is not None and end is not None and start > end:
                raise ValueError("baseline start must not exceed its end.")
        names = [self.epochs_name, self.tfr_name]
        if self.return_itc:
            names.append(self.itc_name)
        if len(set(names)) != len(names):
            raise ValueError("Input, power, and requested ITC names must be distinct.")
        return self


ConnectivityMethod = Literal[
    "coh",
    "cohy",
    "imcoh",
    "plv",
    "ciplv",
    "ppc",
    "pli",
    "pli2_unbiased",
    "dpli",
    "wpli",
    "wpli2_debiased",
]


class ConnectivityParameters(BaseModel):
    """Bivariate connectivity only; multivariate indices have different semantics."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    epochs_name: str = Field(default="epochs", description="Existing Epochs object.")
    con_name: str = Field(
        default="con", description="Output name; replaces an existing result."
    )
    method: ConnectivityMethod = "coh"
    mode: Literal["multitaper", "fourier", "cwt_morlet"] = "multitaper"
    fmin: PositiveFloat | list[PositiveFloat] = Field(
        default=8.0, description="Lower band edge(s), Hz."
    )
    fmax: PositiveFloat | list[PositiveFloat] = Field(
        default=13.0, description="Upper edge(s), matching fmin."
    )
    faverage: bool = Field(
        default=True, description="Average within bands; false retains frequency bins."
    )
    picks: str | list[str] | list[Annotated[int, Field(strict=True, ge=0)]] | None = (
        Field(
            default=None,
            description="Channel type, names or indices. Null selects data channels excluding bads.",
        )
    )
    pairs: list[tuple[str, str]] | None = Field(
        default=None,
        min_length=1,
        description="Ordered [seed, target] channel-name pairs after picks.",
    )
    tmin: float | None = Field(
        default=None, description="Epoch-relative start time, seconds."
    )
    tmax: float | None = Field(
        default=None, description="Epoch-relative end time, seconds."
    )
    mt_bandwidth: PositiveFloat | None = Field(
        default=None, description="Multitaper smoothing bandwidth, Hz."
    )
    mt_adaptive: bool = False
    mt_low_bias: bool = True
    cwt_freqs: list[PositiveFloat] | None = Field(
        default=None, min_length=1, description="Morlet frequencies, ascending Hz."
    )
    cwt_n_cycles: PositiveFloat | list[PositiveFloat] | None = Field(
        default=None,
        description="Morlet only; scalar or one value per cwt frequency; defaults to 7.",
    )
    block_size: Annotated[int, Field(strict=True, ge=1)] = Field(
        default=1000, description="Connections per computation block."
    )
    plot: bool = Field(
        default=True,
        description="Edge-by-frequency/band heatmap; first 30 edges, time mean for CWT.",
    )

    @field_validator("epochs_name", "con_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        return _session_name(value)

    @model_validator(mode="after")
    def compatible_options(self) -> Self:
        if self.epochs_name == self.con_name:
            raise ValueError("Input and connectivity output names must be distinct.")
        lows = self.fmin if isinstance(self.fmin, list) else [self.fmin]
        highs = self.fmax if isinstance(self.fmax, list) else [self.fmax]
        if (
            not lows
            or len(lows) != len(highs)
            or any(lo > hi for lo, hi in zip(lows, highs))
        ):
            raise ValueError(
                "fmin/fmax must contain matching nonempty bands with lower <= upper."
            )
        if any(b <= a for a, b in zip(lows, lows[1:])):
            raise ValueError(
                "Frequency bands must be ordered by increasing lower edge."
            )
        if self.tmin is not None and self.tmax is not None and self.tmin >= self.tmax:
            raise ValueError("tmin must be less than tmax.")
        if self.mode != "multitaper" and (
            self.mt_bandwidth is not None or self.mt_adaptive or not self.mt_low_bias
        ):
            raise ValueError("mt_* options require mode='multitaper'.")
        if self.mode == "cwt_morlet":
            if self.cwt_freqs is None:
                raise ValueError("cwt_morlet requires explicit cwt_freqs.")
            if any(b <= a for a, b in zip(self.cwt_freqs, self.cwt_freqs[1:])):
                raise ValueError("cwt_freqs must be strictly increasing.")
            if isinstance(self.cwt_n_cycles, list) and len(self.cwt_n_cycles) != len(
                self.cwt_freqs
            ):
                raise ValueError("cwt_n_cycles must have one value per cwt frequency.")
            if any(
                not any(lo <= freq <= hi for freq in self.cwt_freqs)
                for lo, hi in zip(lows, highs)
            ):
                raise ValueError("Every band must contain at least one cwt frequency.")
        elif self.cwt_freqs is not None or self.cwt_n_cycles is not None:
            raise ValueError("cwt_* options require mode='cwt_morlet'.")
        if self.pairs is not None:
            if len(set(self.pairs)) != len(self.pairs) or any(
                a == b for a, b in self.pairs
            ):
                raise ValueError("pairs must be unique, non-self channel pairs.")
        return self
