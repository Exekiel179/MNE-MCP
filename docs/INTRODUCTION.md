% MNE-MCP 项目介绍
% 用对话驱动 MNE-Python 的神经电生理分析
% v0.1.0

---

# MNE-MCP 项目介绍

## 一句话

**MNE-MCP** 把开源神经电生理分析平台 **MNE-Python** 接入 **Claude Code / opencode**，让你用**自然语言对话**完成 EEG、MEG、sEEG、ECoG、fNIRS 数据的预处理、ICA 去伪迹、分段、ERP/ERF 叠加、时频、可视化与导出——每一步都自动出图并由 AI 解读。

---

## 1. 背景

- **MNE-Python** 是把 MNE-C 迁移到 Python 后逐步发展起来的开源平台，如今已是 EEG/MEG/iEEG/fNIRS 分析的国际主流工具，广泛用于认知神经科学、临床脑科学和脑机接口研究。它流程完整（预处理、ICA、时频、源定位、统计），与 NumPy/Pandas/Scikit-learn 深度兼容，可视化强，支持 BIDS 与机器学习——开源透明、可复现性高。
- **MCP（Model Context Protocol）** 是让 AI 助手安全调用外部工具/数据的开放协议。
- **MNE-MCP = MNE-Python × MCP**：把 MNE 的能力包装成 AI 能直接调用的工具，于是“做分析”从“写一长串代码”变成“和 Claude 说人话”。

---

## 2. 它解决什么问题

MNE 很强，但门槛不低：

- API 庞大，一个完整流程要写几十行、几十步代码；
- 分析是**强交互的**——几乎每一步都要先“看图”（功率谱、ICA 成分、ERP 地形图）才能决定参数；
- 新手要记大量约定（单位是伏特、ICA 前要高通、地形图前要设导联……）容易踩坑。

MNE-MCP 让这些都能在对话里完成：你描述意图，AI 调用合适的工具、把图画出来、读图解读、并按最佳实践帮你避坑。

---

## 3. 核心设计理念

MNE 的分析是**有状态、强可视化**的，这决定了 MNE-MCP 与“无状态批处理型”工具（如统计软件）截然不同的设计：

1. **常驻内存会话** — 数据只加载一次，之后滤波 → 标坏导 → ICA → 分段 → 叠加…… 全部在同一份内存对象上连续操作，不必反复读取数 GB 的文件。
2. **自动出图 + AI 读图** — 每个画图工具都把结果存成 PNG 并返回路径，AI 会**读取并解读**（识别工频峰、眼电成分、N1/P2/P300 等）。
3. **结构化工具 + 通用补充工具** — 38 个专用工具覆盖常见流程**与高级分析**（源定位、连接性、解码）；其余（BIDS、统计、beamformer……）可用 `mne_run_code` 在同一个会话中直接写代码完成。
4. **可配置默认值** — 工频、默认导联、滤波带、剔除阈值等可用 `mne-mcp configure` 一次设好，省略参数时自动套用。

---

## 4. 工作原理

```
   你（自然语言）
        │
        ▼
  ┌─────────────┐   调用 38 个工具 / run_code   ┌──────────────────────────┐
  │ Claude Code │ ───────────────────────────▶ │  MNE-MCP 服务器 (FastMCP) │
  │ / opencode  │ ◀─────────────────────────── │  · 持久 Session(内存对象) │
  └─────────────┘   返回 Markdown + 图路径      │  · 调用 MNE-Python        │
        ▲                                       │  · 出图存 PNG             │
        │ 读取 PNG 解读                          └──────────────┬───────────┘
        │                                                       ▼
   results/*.png  ◀──────────────────────────────────  raw / epochs / evoked / ica …
```

- 服务器进程内**只有一个会话**，持有命名的 MNE 对象（`raw`、`epochs`、`evoked`、`ica`…），跨工具调用保持。
- 工具是薄封装，真正干活的是 MNE-Python；每步还会返回“等效 MNE 代码”，便于复现与归档。
- 所有执行被串行化（锁保护），避免并发时 matplotlib 全局状态与会话被打架。

---

## 5. 能力总览（38 个工具，9 类）

| 类别 | 工具 |
|---|---|
| 状态/会话 (7) | `mne_check_status` `mne_session_info` `mne_describe` `mne_get_info` `mne_reset_session` `mne_run_code` `mne_get_config` |
| 数据读取 (2) | `mne_list_files` `mne_load_raw` |
| 预处理 (7) | `mne_filter` `mne_resample` `mne_crop` `mne_set_montage` `mne_set_reference` `mne_mark_bad_channels` `mne_interpolate_bads` |
| 可视化 (3) | `mne_plot_psd` `mne_plot_raw` `mne_plot_sensors` |
| ICA (4) | `mne_fit_ica` `mne_plot_ica_components` `mne_plot_ica_sources` `mne_apply_ica` |
| 事件/分段/ERP (7) | `mne_find_events` `mne_events_from_annotations` `mne_make_epochs` `mne_plot_epochs_image` `mne_average_evoked` `mne_plot_evoked` `mne_plot_topomap` |
| 时频 (1) | `mne_tfr_morlet` |
| 高级分析 (6) | `mne_decode` `mne_connectivity` `mne_compute_noise_cov` `mne_make_forward` `mne_apply_inverse` `mne_plot_source_estimate` |
| 导出 (1) | `mne_save` |

> 高级分析（解码/连接性/源定位）需安装 `[full]` 额外依赖：`pip install -e ".[full]"`。

支持读取的格式：FIF、EDF、BDF、BrainVision(.vhdr)、EEGLAB(.set)、CNT、EGI/.mff、CTF(.ds)、SNIRF 等。

---

## 6. 一个典型 ERP 流程

> 你只需用自然语言提出，AI 自动编排下列步骤：

加载记录 → 设导联 → 看功率谱 → 0.1–40 Hz 带通 + 50 Hz 陷波 → 处理坏导 → 平均参考 → ICA（在 ~1 Hz 高通数据上拟合）→ 看成分图 → 去眼电/心电 → 取事件 → 分段 → 叠加平均 → 画 ERP / 地形图 → 时频 → 保存。

装了 `mne-analyst` 技能后，图与等效代码会自动归档到工作目录 `mne_result/`，整套分析可一键复现。

---

## 7. 适用场景

- **认知神经科学**：ERP/ERF、时频、试次级分析。
- **临床脑科学**：EEG 预处理与可视化、报告。
- **脑机接口（BCI）**：快速预处理与特征探索，配合 `mne.decoding` 做解码。
- **教学**：把“怎么做 EEG 分析”变成可对话、可看图的互动过程。
- **可复现研究**：每步留有等效代码与归档，便于复算与共享。

---

## 8. 定位（与其他方式相比）

- **相比直接写 MNE 代码**：省去查 API、记参数、反复贴代码看图的循环；AI 按最佳实践编排并解读，新手也能跑通完整流程，专家则用 `mne_run_code` 不受限。
- **相比商业脑电软件**：开源透明、跨平台、可复现、可扩展，且天然嵌入 AI 对话工作流。

---

## 9. 配套技能

- **`mne-analyst`** — 标准流程、参数约定、图像解读指引、结果归档（`mne_result/`），含 `references/`（流程、工具、失败模式）。
- **`mne-mcp-guard`** — 防错执行：单位（伏特 vs 微伏）、导联前置、ICA 高通、时频窗长、空 epoch、超时等常见坑的预防与诊断。

---

## 10. 技术栈与兼容性

- Python 3.10+；MNE-Python ≥ 1.6；NumPy / SciPy / Matplotlib / pandas；scikit-learn（ICA）。
- 服务器基于 FastMCP（stdio 传输）；matplotlib 用无界面 Agg 后端。
- Windows / macOS / Linux 通用；Claude Code 与 opencode 等 MCP 客户端均可接入。

---

## 11. 项目结构

```
MNE-MCP/
├─ src/mne_mcp/
│  ├─ server.py        # 38 个 MCP 工具定义（薄封装）
│  ├─ operations.py    # 真正的 MNE 操作实现
│  ├─ kernel.py        # 持久会话 + run_code 执行 + 图像捕获
│  ├─ figures.py       # matplotlib 无界面捕获为 PNG
│  ├─ summaries.py     # MNE 对象的可读摘要
│  ├─ config.py        # 配置/能力检测/可配置默认值
│  ├─ wizard.py        # mne-mcp configure 交互向导
│  ├─ claude_config.py # 自动写入 Claude Code 配置
│  └─ cli.py           # 命令行入口
├─ skills/             # mne-analyst / mne-mcp-guard
├─ tests/              # 单元测试 + 端到端冒烟流程
└─ docs/               # 使用介绍 / 安装说明 / 项目介绍
```

---

## 12. 质量保证

- 31 个单元测试（配置、Claude 配置合并、内核、操作、配置向导）。
- 1 套端到端冒烟流程（合成 EEG，21 项校验：加载→预处理→ICA→分段→叠加→时频→导出）。
- 通过真实 MCP 客户端验证 38 个工具的调用与持久会话。

---

## 13. 路线图（设想）

- 源定位/连接性/解码的**专用结构化工具**（目前经 `mne_run_code` 完成）。
- BIDS（mne-bids）与 `mne.Report` 一键化。
- GitHub Actions CI 自动跑测试。
- 对话内可写配置工具（`mne_set_config`）。

---

## 14. 许可证与链接

- 许可证：**MIT**
- 仓库：<https://github.com/Exekiel179/MNE-MCP>
- 安装说明：[INSTALL.md](INSTALL.md) ·  使用介绍：[USAGE.md](USAGE.md) ·  工具参考：[../TOOLS_REFERENCE.md](../TOOLS_REFERENCE.md)
- MNE-Python：<https://mne.tools/> ·  MCP 协议：<https://modelcontextprotocol.io>

> 致谢 MNE-Python 与 MCP 社区。MNE-MCP 是独立项目，与 MNE-Python 官方无隶属关系。
