# MNE Pipelines & Conventions

Reference for the `mne-analyst` skill. Parameters assume the MNE MCP tools; the `run_code` recipes
run in the persistent session where `mne`, `np`, `pd`, `plt`, and your loaded objects are pre-bound.

## Units & conventions (memorize)

| Quantity | Unit in MNE | Example |
|---|---|---|
| EEG / EOG | volts | 100 µV → `100e-6` |
| MEG mag | tesla | `4e-12` |
| MEG grad | T/m | `4000e-13` |
| Time | seconds | `tmin=-0.2` |
| Frequency | Hz | `l_freq=1.0` |
| Rejection (`reject`) | dict of peak-to-peak in SI | `{"eeg": 100e-6}` |

- Filtering: `l_freq` = high-pass edge (removes slow drift), `h_freq` = low-pass edge (removes
  high-freq noise). Either can be null.
- Line noise: `notch=50` (China/EU) or `notch=60` (US).
- Montage required before `plot_topomap`, ICA `plot_components`, and `interpolate_bads`.

## Standard EEG preprocessing (ERP)

1. `mne_load_raw path=sub-01_raw.fif`
2. `mne_set_montage montage=standard_1020`  (or the cap's actual montage)
3. `mne_plot_psd fmin=1 fmax=80` → **read PNG**: spot 50/60 Hz line noise, bad channels
4. `mne_filter l_freq=0.1 h_freq=40 notch=50`
5. `mne_mark_bad_channels bads=Fp1,T7` (from inspection) → `mne_interpolate_bads`
6. `mne_set_reference ref_channels=average`
7. ICA (see below)
8. `mne_events_from_annotations` *or* `mne_find_events stim_channel=STI 014`
9. `mne_make_epochs event_id="target:1,standard:2" tmin=-0.2 tmax=0.8 baseline=default reject_eeg=100e-6`
10. `mne_average_evoked condition=target` (repeat per condition)
11. `mne_plot_evoked style=joint` and `mne_plot_topomap times="0.1,0.2,0.3"`
12. `mne_save name=evoked path=sub-01-ave.fif`

## ICA artifact removal (the careful way)

ICA is unstable on slow drifts, so **fit on ~1 Hz high-passed data**, then apply to the
analysis-filtered data:

```
# raw is already 0.1–40 Hz for ERP. Make a 1 Hz copy for ICA:
mne_run_code code="raw_ica = raw.copy().filter(1.0, None); raw_ica"
mne_fit_ica name=raw_ica n_components=0.99 method=fastica ica_name=ica
mne_plot_ica_components ica_name=ica     # read PNG → identify eye/heart comps
mne_plot_ica_sources ica_name=ica inst_name=raw_ica
mne_apply_ica ica_name=ica inst_name=raw exclude="0,3"   # apply to the ERP raw
```

Tip: `ica.find_bads_eog` / `find_bads_ecg` auto-detect artifact comps via `mne_run_code` when EOG/ECG
channels exist:
```
mne_run_code code="eog_idx, scores = ica.find_bads_eog(raw); ica.exclude = eog_idx; eog_idx"
```

## Time-frequency (Morlet)

TFR wavelets need **long enough epochs**. With `n_cycles = freqs/2`, the wavelet spans ~constant time;
make the epoch window wider than an ERP window (e.g. `tmin=-0.5 tmax=1.5`) and avoid very low
frequencies on short epochs.

```
mne_make_epochs ... tmin=-0.5 tmax=1.5 epochs_name=epochs_tfr
mne_tfr_morlet epochs_name=epochs_tfr fmin=4 fmax=40 n_freqs=20 tfr_name=power
```
Baseline-correct power for display via `mne_run_code`:
```
mne_run_code code="power.plot(baseline=(-0.5,0), mode='logratio', combine='mean')"
```

## run_code recipes (beyond the structured tools)

**Sample data (for demos, no local file):**
```
mne_run_code code="import os; p=mne.datasets.sample.data_path(); raw=mne.io.read_raw_fif(os.path.join(p,'MEG','sample','sample_audvis_raw.fif'), preload=True); raw"
```

**Compare conditions:**
```
mne_run_code code="mne.viz.plot_compare_evokeds({'target':ev_t,'standard':ev_s}, picks='Cz', show=False)"
```

**Source localization (dSPM, requires forward + noise cov):**
```
mne_run_code code="cov = mne.compute_covariance(epochs, tmax=0.); inv = mne.minimum_norm.make_inverse_operator(evoked.info, fwd, cov); stc = mne.minimum_norm.apply_inverse(evoked, inv, lambda2=1/9., method='dSPM'); stc"
```

**Cluster-based permutation stats:**
```
mne_run_code code="from mne.stats import permutation_cluster_1samp_test; T,clusters,p,_ = permutation_cluster_1samp_test(X); p"
```

**Decoding (MVPA):**
```
mne_run_code code="from mne.decoding import SlidingEstimator, cross_val_multiscore; from sklearn.linear_model import LogisticRegression; from sklearn.pipeline import make_pipeline; from sklearn.preprocessing import StandardScaler; clf=make_pipeline(StandardScaler(), LogisticRegression()); sl=SlidingEstimator(clf, scoring='roc_auc'); scores=cross_val_multiscore(sl, epochs.get_data(), epochs.events[:,2], cv=5).mean(0); scores.shape"
```

**BIDS (needs `pip install mne-bids`):**
```
mne_run_code code="from mne_bids import BIDSPath, read_raw_bids; bp=BIDSPath(subject='01', task='rest', root='/data/bids'); raw=read_raw_bids(bp); raw"
```

**HTML report:**
```
mne_run_code code="rep=mne.Report(title='Analysis'); rep.add_evokeds(evoked); rep.save('report.html', overwrite=True, open_browser=False)"
```
