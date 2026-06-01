# MNE-MCP 工具参考

[English](TOOLS_REFERENCE.md) | **简体中文**

32 个工具，全部基于**常驻会话**：已加载的对象（`raw`、`epochs`、`evoked`、`ica` …）在多次调用之间保持在内存中。
画图工具会保存 PNG 并返回路径，读取该 PNG 即可查看；工具结果还会附带等效 MNE 代码（```python``` 代码块）。

许多工具在你**省略参数**时会回退到**用户可配置的默认值**（工频、导联、滤波带、剔除阈值、ICA 设置、分段窗）——
用 `mne-mcp configure` 设置，用 `mne_get_config` 查看。

---

## 状态与会话

### `mne_check_status`
显示 MNE / scikit-learn / numpy / scipy / matplotlib / pandas 版本及运行目录。**请先调用它。**

### `mne_session_info`
列出会话中每个对象及其一行摘要（类型、通道数、采样率等）。

### `mne_describe(name)`
某个对象的详细摘要：通道、通道类型、采样率、滤波带、坏导、导联、时长。

### `mne_get_info(name)`
完整的逐通道清单（名称、类型、是否坏导）及测量信息。

### `mne_reset_session`
清空所有对象与图像。不可撤销。

### `mne_run_code(code)`
在会话中执行 Python/MNE 代码。预绑定：`mne`、`np`、`pd`、`plt`，以及所有已加载对象。
类似 notebook：末尾表达式的值会返回；捕获 stdout；matplotlib 图像保存为 PNG。
下面没列到的、以及一切未覆盖的功能都靠它。

### `mne_get_config`
显示工具回退使用的默认参数。用 `mne-mcp configure` 修改。

---

## 数据读取

### `mne_list_files(directory=None, pattern=None)`
列出某目录下的神经数据文件（`.fif .edf .bdf .gdf .vhdr .set .cnt .egi .mff .ds .snirf …`）。
默认用 `MNE_MCP_DATA_DIR` 或当前目录；`pattern` 为 glob 通配。（会自动跳过 `.venv`、`site-packages`、`.git` 等噪声目录。）

### `mne_load_raw(path, name="raw", preload=True)`
加载一份记录，按扩展名自动识别格式（带备选读取器）。超大文件可用 `preload=False`（惰性加载，之后再 `mne_crop`）。

---

## 预处理 —— 原地修改 `name`

### `mne_filter(name="raw", l_freq=None, h_freq=None, notch=None, picks=None)`
`l_freq`=高通边界，`h_freq`=低通边界，`notch`=工频（50/60）。例如 ERP：`0.1, 40, 50`。
（三者都省略时，使用配置的默认滤波带。）

### `mne_resample(name, sfreq)` · 降采样（尽量在分段后做以保留事件）。
### `mne_crop(name, tmin=0, tmax=None)` · 保留某个时间窗。
### `mne_set_montage(name, montage=None)` · 设电极位置（`standard_1020`、`standard_1005`、`biosemi64`、`GSN-HydroCel-128` …）；省略时用配置默认导联。
### `mne_set_reference(name, ref_channels="average")` · `average`、`REST` 或 `"TP9,TP10"`。
### `mne_mark_bad_channels(name, bads, replace=False)` · `bads="Fp1,T7"`。
### `mne_interpolate_bads(name, reset_bads=True)` · 样条插值坏导（需先设导联）。

---

## 可视化 —— 返回 PNG 路径

### `mne_plot_psd(name, fmin=0, fmax=None, picks=None)` · 功率谱（找工频/坏导）。
### `mne_plot_raw(name, start=0, duration=20, n_channels=20)` · 信号波形。
### `mne_plot_sensors(name, kind="topomap", show_names=True)` · 电极布局（`topomap`/`3d`）。

---

## ICA —— 去伪迹

### `mne_fit_ica(name="raw", n_components=None, method=None, ica_name="ica", random_state=97)`
拟合 ICA（需 scikit-learn）。`n_components`：int、float（方差比例，如 `0.99`）或 null。
`method`：`fastica` / `infomax` / `picard`（省略时用配置默认）。**建议在约 1 Hz 高通的数据上拟合。**

### `mne_plot_ica_components(ica_name="ica")` · 成分头皮分布图。
### `mne_plot_ica_sources(ica_name="ica", inst_name="raw")` · 成分时间序列。
### `mne_apply_ica(ica_name, inst_name, exclude=None)` · 原地去除成分；`exclude="0,3"`。

---

## 事件 / 分段 / ERP

### `mne_find_events(raw_name="raw", stim_channel=None, events_name="events")` · 从触发通道取事件。
### `mne_events_from_annotations(raw_name="raw", events_name="events")` · 从注释取事件（EDF/BrainVision/EEGLAB）。
### `mne_make_epochs(raw_name, events_name, event_id=None, tmin=None, tmax=None, baseline="default", reject_eeg=None, epochs_name="epochs")`
`event_id="target:1,standard:2"` 命名/筛选条件；`baseline="default"` = `(None,0)`；
`reject_eeg=100e-6` = 峰峰 100 µV 剔除阈值（单位伏特）。`tmin/tmax` 省略时用配置默认分段窗。

### `mne_plot_epochs_image(name="epochs", picks=None)` · ERP 图（试次 × 时间热图）。
### `mne_average_evoked(epochs_name="epochs", condition=None, evoked_name="evoked")` · ERP/ERF。
### `mne_plot_evoked(name="evoked", style="joint")` · `joint` / `topo` / `butterfly`。
### `mne_plot_topomap(name="evoked", times="auto")` · `auto` / `peaks` / `"0.1,0.2,0.3"`。

---

## 时频与导出

### `mne_tfr_morlet(epochs_name="epochs", fmin=4, fmax=40, n_freqs=20, tfr_name="power")`
Morlet 小波时频功率（`n_cycles=freqs/2`）并绘图。分段需足够长以容纳最低频率的小波。

### `mne_save(name, path, overwrite=True)`
命名规则：Raw → `*_raw.fif`，Epochs → `*-epo.fif`，Evoked → `*-ave.fif`。

---

## 上面没有？
源定位、连接性、解码、统计、BIDS、Report、条件对比、冷门格式 → 用 **`mne_run_code`**。
recipes 见 `skills/mne-analyst/references/mne-pipelines.md`。
