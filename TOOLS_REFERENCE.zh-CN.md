# MNE-MCP 工具参考

解码及解码组检验新增：数值证据、方法、解释边界、缺失信息及待审 Results 段落。
这不等于设计审查通过，也不会自动补造置信区间或引文。
参见[科学解释输出规范](skills/mne-writeup/references/evidence-to-claims.md)。
滤波在执行前检查全部截止/陷波频率；裁剪、重采样检查范围和数值。
REST 重参考须通过 `mne_run_code` 显式提供前向模型。

[English](TOOLS_REFERENCE.md) | **简体中文**

40 个工具，全部基于**常驻会话**：已加载的对象（`raw`、`epochs`、`evoked`、`ica` …）在多次调用之间保持在内存中。
画图工具会保存 PNG 并返回路径，读取该 PNG 即可查看；工具结果还会附带等效 MNE 代码（```python``` 代码块）。

许多工具在你**省略参数**时会回退到**用户可配置的默认值**（工频、导联、滤波带、剔除阈值、ICA 设置、分段窗）——
用 `python -m mne_mcp configure` 设置，用 `mne_get_config` 查看。

---

## 状态与会话

### `mne_check_status`
显示 MNE / scikit-learn / numpy / scipy / matplotlib / pandas 版本及运行目录。**请先调用它。**
同时报告执行状态 `busy` / `idle`。超时不代表后台计算停止；忙碌时拒绝其他会话操作。
恢复空闲后先检查对象，不能盲目重试会原地修改数据的步骤。

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
显示工具回退使用的默认参数。用 `python -m mne_mcp configure` 修改。

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
推荐使用 JSON：`event_id={"target":1,"standard":2}`、`baseline=[null,0]`；`baseline=null` 关闭基线。
新增 `reject` / `flat`（通道类型到 SI 阈值的字典）、`picks`（类型、名称列表或索引列表）、
`detrend=null|0|1`、`reject_by_annotation=true`、`event_repeated="error"|"drop"|"merge"`。
`reject={}` 显式关闭配置中的剔除阈值，省略则使用默认值；不能与 `reject_eeg` 同时设置。

### `mne_plot_epochs_image(name="epochs", picks=None)` · ERP 图（试次 × 时间热图）。
### `mne_average_evoked(epochs_name="epochs", condition=None, evoked_name="evoked")` · ERP/ERF。
### `mne_plot_evoked(name="evoked", style="joint")` · `joint` / `topo` / `butterfly`。
### `mne_plot_topomap(name="evoked", times="auto")` · `auto` / `peaks` / `"0.1,0.2,0.3"`。

---

## 时频与导出

### `mne_compute_tfr(params)`
可配置 Morlet / multitaper 功率和可选 ITC。`params` 必填 `freqs`（递增的 Hz 数组）。
可选参数：`epochs_name="epochs"`、`method="morlet"`、`n_cycles=7`（标量或逐频率数组）、
`time_bandwidth=null`（仅 multitaper）、`picks=null`、`average=true`、`return_itc=false`、
`decim=1`、`baseline=null`、`baseline_mode="mean"`、`tfr_name="power"`、`itc_name="itc"`、`plot=true`。
ITC 要求 `average=true`。基线归一化作用于保存的功率，不作用于 ITC；不要重复归一化。
`average=false` 保留逐试次功率，绘图时才做显示用平均。`decim` 是变换后的抽点，可能混叠。
不修改输入 epochs；输出名称可能替换同名结果。[完整 JSON 示例](skills/mne-analyst/references/structured-analysis.md)。

### `mne_tfr_morlet(epochs_name="epochs", fmin=4, fmax=40, n_freqs=20, tfr_name="power")`
Morlet 小波时频功率（`n_cycles=freqs/2`）并绘图。分段需足够长以容纳最低频率的小波。

### `mne_save(name, path, overwrite=True)`
命名规则：Raw → `*_raw.fif`，Epochs → `*-epo.fif`，Evoked → `*-ave.fif`。

---

## 高级分析（唯一安装器已包含依赖）

### `mne_decode(epochs_name="epochs", cond_a, cond_b, scoring="roc_auc", cv=5, name="decoding")`
二分类解码，在每个训练折内拟合标准化与逻辑回归。`method="sliding"`（默认）返回
`(时间,)`；`method="generalizing"` 返回 `(训练时间, 测试时间)`，可生成热图。
支持 `cv_strategy="stratified"|"stratified_group"|"leave_one_group_out"`、`groups`、
`picks`、`shuffle=false`、`random_state=97`、`plot=true`。分组标签必须对应条件筛选前的全部保留试次。
`tmin/tmax` 在副本上裁剪时间窗；分类器支持 `C=1.0`、`class_weight=null|"balanced"`、`max_iter=1000`。
保存均值得分、`name_folds` 逐折得分、`name_details` 分组/类别/时间轴诊断。
参考线不是显著性阈值，交叉验证折不能作为独立被试。需要 scikit-learn。
参见[参数示例与结果语义](skills/mne-decoding/references/structured-decoding.md)。

### `mne_decoding_group_test(params)`
对独立被试的平均解码曲线/泛化矩阵做组水平符号翻转检验，不能把交叉验证折当被试。
必填 `score_names`、唯一 `subject_ids`、`independent_subjects=true`、明确的 `null_value`。
支持 ROC AUC / balanced accuracy；要求时间网格与方法一致。
`correction="max_t"` 为双侧逐点 FWER 校正；`"cluster"` 为簇质量校正，邻接覆盖时间或训练/测试双轴。
可设 `tail`、`n_permutations`、`seed`、`alpha`、`threshold`（成簇 t 阈值，不是 p 值）、`name`、`plot`。
保存统计量、校正 p 值或簇级 p 值、掩码、平均效应及零分布。簇范围不能解释为精确显著时间点。
要求被试效应独立且在零假设下对称；不等同于单被试标签置换或总体可解码比例推断。
参见[设计边界与示例](skills/mne-decoding/references/group-inference.md)。

### `mne_connectivity(epochs_name="epochs", method="coh", fmin=8, fmax=13, con_name="con")`
单频段连接性，保留旧版全矩阵存储；改为有序通道对热图，不再无条件对称化。
默认排除坏导和非数据通道。需要 mne-connectivity 和至少两个保留试次。

### `mne_compute_connectivity(params)`
双变量多频段连接性。支持 `method`、`mode="multitaper"|"fourier"|"cwt_morlet"`、
`fmin/fmax`（标量或匹配数组）、`faverage`、`picks`、`pairs`（有序通道名称对）、
`tmin/tmax`、`mt_bandwidth/mt_adaptive/mt_low_bias`、`cwt_freqs/cwt_n_cycles`、
`block_size`、`plot`、`epochs_name/con_name`。不兼容的谱估计参数会明确报错。
存储形状为 `(连接对, 频率或频段[, 时间])`，保留符号与复数信息；热图只显示前 30 对，
复数显示幅值，Morlet 显示时间平均，不推断未计算的反向连接。
Granger、多变量和 PAC 仍通过 `mne_run_code`。参见[参数示例与结果语义](skills/mne-connectivity/references/structured-connectivity.md)。

### `mne_compute_noise_cov(name="epochs", tmax=0.0, cov_name="noise_cov")`
从分段基线算噪声协方差——构建逆算子的前置。

### `mne_make_forward(name="evoked", fwd_name="fwd")`
基于 fsaverage 模板头的 EEG 前向模型（首次会下载 fsaverage）。需 nibabel。

### `mne_apply_inverse(evoked_name="evoked", fwd_name="fwd", cov_name="noise_cov", method="dSPM", snr=3.0, stc_name="stc")`
估计皮层源（`dSPM`/`MNE`/`sLORETA`/`eLORETA`）；存 stc 并报告峰值时间。

### `mne_plot_source_estimate(stc_name="stc", hemi="both", time=None)`
把源估计渲染成皮层激活图 PNG（需 PyVista 离屏渲染）。

---

## 上面没有？
BIDS、自定义统计、beamformer（LCMV/DICS）、autoreject、条件对比、冷门格式 → 用 **`mne_run_code`**。
recipes 见 `skills/mne-analyst/references/mne-pipelines.md`。
