# MNE MCP Tools Reference

All tools operate on the **persistent session**. Names default sensibly (`raw`, `events`, `epochs`,
`evoked`, `ica`, `power`) so a simple linear pipeline needs few explicit names.

## Status & session
| Tool | Purpose | Key args |
|---|---|---|
| `mne_check_status` | Verify MNE / sklearn / dirs. Call first. | — |
| `mne_session_info` | List all loaded objects with one-line summaries. | — |
| `mne_describe` | Detailed summary of one object. | `name` |
| `mne_get_info` | Full channel list + measurement info. | `name` |
| `mne_reset_session` | Clear everything (irreversible). | — |
| `mne_run_code` | Run arbitrary MNE/Python in the session. Returns stdout, last-expression value, and any figures. | `code` |
| `mne_get_config` | Show user-configured defaults (line freq, montage, filter band, reject, ICA, epoch window). Set via `mne-mcp configure`. | — |

## Data IO
| Tool | Purpose | Key args |
|---|---|---|
| `mne_list_files` | Find neuro data files under a directory. | `directory`, `pattern` |
| `mne_load_raw` | Load a recording (auto-detect format). | `path`, `name=raw`, `preload=true` |

## Preprocessing (in-place on the named object)
| Tool | Purpose | Key args |
|---|---|---|
| `mne_filter` | Band-pass / notch. | `name`, `l_freq`, `h_freq`, `notch`, `picks` |
| `mne_resample` | Change sampling rate. | `name`, `sfreq` |
| `mne_crop` | Keep [tmin, tmax] seconds. | `name`, `tmin`, `tmax` |
| `mne_set_montage` | Set electrode positions. | `name`, `montage=standard_1020` |
| `mne_set_reference` | EEG reference: `average`, `REST`, or `"TP9,TP10"`. | `name`, `ref_channels` |
| `mne_mark_bad_channels` | Flag bad channels (comma list). | `name`, `bads`, `replace` |
| `mne_interpolate_bads` | Spline-interpolate bads (needs montage). | `name`, `reset_bads` |

## Visualization (each returns a PNG path → read it)
| Tool | Purpose | Key args |
|---|---|---|
| `mne_plot_psd` | Power spectral density. | `name`, `fmin`, `fmax`, `picks` |
| `mne_plot_raw` | Signal traces. | `name`, `start`, `duration`, `n_channels` |
| `mne_plot_sensors` | Electrode/sensor layout. | `name`, `kind` (`topomap`/`3d`) |

## ICA
| Tool | Purpose | Key args |
|---|---|---|
| `mne_fit_ica` | Fit ICA (needs sklearn). | `name`, `n_components`, `method`, `ica_name` |
| `mne_plot_ica_components` | Component topographies. | `ica_name` |
| `mne_plot_ica_sources` | Component time courses. | `ica_name`, `inst_name` |
| `mne_apply_ica` | Remove components in place. | `ica_name`, `inst_name`, `exclude="0,3"` |

## Events / Epochs / ERP
| Tool | Purpose | Key args |
|---|---|---|
| `mne_find_events` | Events from a stim channel. | `raw_name`, `stim_channel`, `events_name` |
| `mne_events_from_annotations` | Events from annotations. | `raw_name`, `events_name` |
| `mne_make_epochs` | Segment around events. | `raw_name`, `events_name`, `event_id`, `tmin`, `tmax`, `baseline`, `reject_eeg`, `epochs_name` |
| `mne_plot_epochs_image` | ERP-image heatmap. | `name`, `picks` |
| `mne_average_evoked` | Average epochs → evoked. | `epochs_name`, `condition`, `evoked_name` |
| `mne_plot_evoked` | `joint` / `topo` / `butterfly`. | `name`, `style` |
| `mne_plot_topomap` | Scalp maps at times. | `name`, `times="0.1,0.2"` |

## Time-frequency & export
| Tool | Purpose | Key args |
|---|---|---|
| `mne_tfr_morlet` | Morlet TF power + plot. | `epochs_name`, `fmin`, `fmax`, `n_freqs`, `tfr_name` |
| `mne_save` | Save object (`*_raw.fif` / `*-epo.fif` / `*-ave.fif`). | `name`, `path`, `overwrite` |

## When to use `mne_run_code` instead
Source localization, connectivity (`mne-connectivity`), decoding (`mne.decoding`), permutation
statistics (`mne.stats`), BIDS (`mne-bids`), `mne.Report`, condition contrasts, custom montages,
reading uncommon formats, and any parameter not exposed by a structured tool.
