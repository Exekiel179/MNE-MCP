% MNE-MCP 使用介绍
% 用对话的方式做脑电 / 脑磁分析
% v0.1.0

---

# MNE-MCP 使用介绍

**MNE-MCP** 是一个 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 服务器，把开源神经电生理分析平台 **[MNE-Python](https://mne.tools/)** 接入 **Claude Code / opencode**，让你能用**自然语言对话**完成 EEG、MEG、sEEG、ECoG、fNIRS 数据的加载、预处理、ICA 去伪迹、分段、叠加平均（ERP/ERF）、时频分析、可视化与导出。

> 一句话：把"写一长串 MNE 代码"变成"和 Claude 说人话"，而且每一步的图都会画出来给你看、并解释。

---

## 1. 它是什么、为什么这样设计

MNE-Python 是纯 Python、**有状态、强可视化**的分析库——你加载一份记录后，要在它上面连续做几十步操作（滤波 → 标记坏导 → ICA → 分段 → 叠加…），而且几乎每一步都要"看图"才能决定下一步。

MNE-MCP 针对这一点设计：

- **常驻内存会话**：数据只加载一次，之后所有操作都在同一份内存对象上进行，不用反复读取几个 GB 的文件。
- **自动出图**：每个画图工具都会把结果存成 PNG 并返回路径，Claude 会**读取并解读**这张图。
- **38 个结构化工具**（含源定位 / 连接性 / 解码）+ 一个通用的 **`mne_run_code`** 工具：做不到的（BIDS、统计、beamformer…）用 `mne_run_code` 在同一个会话里写代码完成。
- **可配置默认值**：工频、默认导联、滤波带、剔除阈值等可以用 `mne-mcp configure` 一次设好。

---

## 2. 安装

环境要求：Windows / macOS / Linux，Python 3.10+。

```bash
git clone https://github.com/Exekiel179/MNE-MCP.git
cd MNE-MCP

# 安装本体 + MNE + numpy/scipy/matplotlib + scikit-learn(ICA)
pip install -e ".[ica]"

# 确认环境
mne-mcp status
```

`mne-mcp status` 会显示 MNE / scikit-learn / numpy 等版本和结果目录。看到 `MNE-Python: OK vX.Y` 就说明装好了。

---

## 3. 接入客户端（Claude Code / Codex / opencode）

### 3.1 一键注册 + 装技能（推荐）

```bash
mne-mcp setup                          # Claude Code + Codex + opencode + 技能
mne-mcp setup --clients claude,codex   # 只配置指定客户端
```

`setup` 会把 `mne` 写入各客户端配置（Claude Code 的 `~/.claude.json`、Codex 的 `~/.codex/config.toml`、
opencode 的 `~/.config/opencode/opencode.json`），改动前对已存在文件先备份，并自动安装技能。

手动配置见 [INSTALL.md](INSTALL.md#34-接入客户端claude-code--codex--opencode)（含三种客户端的配置片段）。

### 3.2 技能（随 setup 自动安装）

技能是 Claude Code 特性，让它掌握标准流程、参数约定，并自动把结果归档到 `mne_result/`；`setup` 已自动安装。

**完成后重启客户端**，`mne` 服务器与技能即可生效。

---

## 4. 配置默认参数（可选，CLI 向导）

用交互向导设置工具的默认回退值：

```bash
mne-mcp configure            # 交互式，回车保留当前值
mne-mcp configure --show     # 查看当前默认值
mne-mcp configure --reset    # 恢复内置默认
# 非交互批量设置：
mne-mcp configure --set line_freq=60 default_montage=biosemi64 reject_eeg_uv=120
```

可配置项：

| 键 | 含义 | 内置默认 |
|---|---|---|
| `line_freq` | 工频（50=中国/欧洲，60=美国） | 50 |
| `default_montage` | 默认电极导联 | standard_1020 |
| `filter_l_freq` / `filter_h_freq` | 默认高通/低通边界 (Hz) | 0.1 / 40 |
| `reject_eeg_uv` | 默认峰峰剔除阈值 (µV) | 无 |
| `ica_method` / `ica_n_components` | 默认 ICA 方法 / 成分数 | fastica / 自动 |
| `epoch_tmin` / `epoch_tmax` | 默认分段窗 (s) | -0.2 / 0.5 |
| `results_dir` / `data_dir` | 结果目录 / 数据目录 | 临时目录 / 当前目录 |
| `timeout` | 单步超时 (s) | 300 |

保存在 `~/.mne-mcp/config.json`。优先级：**环境变量 > 配置文件 > 内置默认**。对话中可用 `mne_get_config` 查看当前生效值。

---

## 5. 开始分析：直接说人话

接入后，无需记工具名，直接描述你的需求即可。例如：

```
检查一下 MNE 环境
```
```
加载 F:\data\sub-01_raw.fif，设 standard_1020 导联，画功率谱看看
```
```
对 raw 做 1–40 Hz 带通 + 50 Hz 陷波，跑 ICA，画成分图，帮我判断哪些是眼电
```
```
按 'target' 事件分段 -0.2 到 0.8 秒，叠加平均，画 ERP 和 100/200/300ms 的地形图
```

Claude 会按"加载 → 预处理 → ICA → 分段 → 叠加平均 → 画图/解读 → 归档"的顺序逐步完成，每张图都会画出来并解释。

### 没有数据？用 MNE 自带样例

```
用 mne_run_code 下载并加载 MNE 的 sample 数据集，然后画功率谱
```

（首次会下载约 1.5 GB 到 `~/mne_data`。）

---

## 6. 一次完整 ERP 流程示例

下面是一段典型对话能驱动的标准流程（你只需用自然语言提出，Claude 调用对应工具）：

1. `mne_load_raw` 加载记录 → `mne_set_montage` 设导联
2. `mne_plot_psd` 看功率谱（识别工频、坏导）
3. `mne_filter` 做 0.1–40 Hz 带通 + 50 Hz 陷波
4. `mne_mark_bad_channels` + `mne_interpolate_bads` 处理坏导
5. `mne_set_reference average` 平均参考
6. `mne_fit_ica`（建议在 ~1 Hz 高通数据上）→ `mne_plot_ica_components` 看成分 → `mne_apply_ica` 去眼电/心电
7. `mne_events_from_annotations` 或 `mne_find_events` 取事件
8. `mne_make_epochs` 分段 → `mne_average_evoked` 叠加平均
9. `mne_plot_evoked` / `mne_plot_topomap` 出图 → `mne_tfr_morlet` 时频
10. `mne_save` 保存结果

装了 `mne-analyst` 技能后，图和"等效 MNE 代码"会自动归档到工作目录的 `mne_result/`，整套分析可一键复现。

---

## 7. 关于图像

每个画图工具都会保存 PNG 并返回形如：

```
> Figure: C:\...\mne-mcp\results\psd_01.png
```

Claude 会读取这张 PNG 来判断（功率谱里的工频峰、ICA 里的眼电成分、ERP 的 N1/P2/P300 等），并用自然语言解释。

---

## 8. 超出内置工具的分析

源定位（dSPM/eLORETA）、连接性（mne-connectivity）、解码/MVPA（mne.decoding）、置换检验统计（mne.stats）、BIDS（mne-bids）、HTML 报告（mne.Report）、条件对比、特殊格式读取——都能用 **`mne_run_code`** 在同一个会话中完成。会话里已预绑定 `mne`、`np`、`pd`、`plt` 以及你加载的所有对象（`raw`、`epochs`、`evoked`、`ica` …）。

示例（让 Claude 执行）：

```
用 mne_run_code 算噪声协方差和逆算子，对 evoked 做 dSPM 源估计
```

---

## 9. 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| ICA 报错需要 scikit-learn | 服务器环境缺 sklearn | `pip install scikit-learn` 后重启 |
| 画地形图/插值报导联位置错误 | 没设导联 | 先 `mne_set_montage` |
| 剔除阈值不起作用/全被剔 | 单位写错 | 信号是伏特，100 µV 要写 `100e-6` |
| 时频报"wavelet longer than signal" | 分段太短 | 用更宽的分段窗（如 -0.5~1.5s）或提高 fmin |
| 所有 epoch 被丢弃 | 剔除阈值太严/事件码不对 | 放宽阈值；先确认真实事件码 |
| 步骤超时 | ICA/时频/大文件慢 | 调大 `MNE_MCP_TIMEOUT` 或 `mne-mcp configure` 设 timeout |

更多见仓库内 `skills/mne-analyst/references/failure-patterns.md`。

---

## 10. 工具速查（38 个）

- **状态/会话(7)**：`mne_check_status` `mne_session_info` `mne_describe` `mne_get_info` `mne_reset_session` `mne_run_code` `mne_get_config`
- **数据读取(2)**：`mne_list_files` `mne_load_raw`
- **预处理(7)**：`mne_filter` `mne_resample` `mne_crop` `mne_set_montage` `mne_set_reference` `mne_mark_bad_channels` `mne_interpolate_bads`
- **可视化(3)**：`mne_plot_psd` `mne_plot_raw` `mne_plot_sensors`
- **ICA(4)**：`mne_fit_ica` `mne_plot_ica_components` `mne_plot_ica_sources` `mne_apply_ica`
- **事件/分段/ERP(7)**：`mne_find_events` `mne_events_from_annotations` `mne_make_epochs` `mne_plot_epochs_image` `mne_average_evoked` `mne_plot_evoked` `mne_plot_topomap`
- **时频(1)**：`mne_tfr_morlet`
- **高级分析(6)**：`mne_decode` `mne_connectivity` `mne_compute_noise_cov` `mne_make_forward` `mne_apply_inverse` `mne_plot_source_estimate`
- **导出(1)**：`mne_save`

完整参数见 `TOOLS_REFERENCE.md`。高级分析需 `pip install -e ".[full]"`。

---

## 11. 资源

- 项目仓库：<https://github.com/Exekiel179/MNE-MCP>
- 快速开始：`QUICK_START.md`
- 工具参考：`TOOLS_REFERENCE.md`
- MNE-Python 官网：<https://mne.tools/>
- MCP 协议：<https://modelcontextprotocol.io>

---

*License: MIT*
