# MNE-MCP

独立的 C++ 预览版见 [MNE-CPP MCP 安装与能力说明](packages/mne-cpp-mcp/README.md)。
现已提供原生运行库安装、客户端注册和配套 skill 安装入口；目前只支持 FIFF 检查，不能替代本文的 MNE-Python 分析后端。

[![CI](https://github.com/Exekiel179/MNE-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/Exekiel179/MNE-MCP/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io)

[English](README.md) | **简体中文**

一个 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 服务器，把开源神经电生理分析平台
**[MNE-Python](https://mne.tools/)** 接入 AI 助手，用于分析 **EEG、MEG、sEEG、ECoG、fNIRS** 数据。

用自然语言描述你的分析需求——MNE-MCP 会加载记录、执行 MNE 流程（滤波、ICA、分段、ERP/ERF 叠加、
时频、以及通过代码完成的源定位等）、保存图像并解读结果。

> 可在 **Claude Code**、**Codex**、**PsyClaw** 与 **opencode** 中使用。配套一组 Agent **技能**
> ——`mne-analyst`、`mne-mcp-guard`，以及一套"先怀疑、后审查"的**分析技能套件**
> （`mne-methodology-critic` + 各分析大类的专用技能），让流程更可靠、结果自动归档。

---

## 为什么要给 MNE-Python 做一个 MCP？

MNE 的分析是**有状态、强可视化**的，不同于一次性的统计批处理任务：

- 你加载一份 `Raw` 记录后，要连续做 滤波 → 重参考 → ICA → 分段 → 叠加 → 时频，每一步都会改动很大的内存对象。
  MNE-MCP 维护**一个常驻会话**，记录无需在步骤之间反复加载。
- 几乎每个决定都靠“看图”（功率谱、电极图、ICA 成分、ERP）。每个画图工具都会保存一张 AI 能读取并解读的 **PNG**。
- MNE 提供庞大的 Python API。MNE-MCP 用 **41 个结构化工具**覆盖常见流程**和高级分析**（源定位、连接性、
  解码），并额外提供一个通用的 **`mne_run_code`** 工具：可在同一个会话中直接执行任意 MNE/Python 代码，
  覆盖 MNE 的全部功能。
- 默认参数（工频、导联、滤波带、剔除阈值、ICA 设置、分段窗、目录、超时）可通过交互式
  `python -m mne_mcp configure` 向导**由用户配置**。

---

## 环境要求

- Python **3.12+**（不设包版本上限；完整测试基线为 3.12）
- Git
- Claude Code、Codex、PsyClaw、opencode 或其他支持 MCP 的客户端

> 跨平台：MNE-Python 是纯 Python，分析功能在 Windows、macOS、Linux 上都可用。

---

## 安装

### 让智能体安装

把下面这句话发给有终端权限的智能体：

> 按 https://github.com/Exekiel179/MNE-MCP/blob/v0.4.1/INSTALL_AGENT.md 安装 MNE-MCP 和全部配套技能，复用我的 MNE 环境，配置到当前客户端并验证。

智能体会检查已有环境、安装轻量接口、注册当前客户端和全部 14 个技能。
如果选定环境尚未安装 MNE 或基础分析库，安装器会自动用 pip 补齐并验证。首次安装后需要重启客户端。
环境检查与验证步骤见 [安装指南](INSTALL_AGENT.md)。

### 手动安装

先激活已有的 Python 3.12+ MNE 环境，执行：

```bash
python -m pip install mne-mcp
python -m mne_mcp setup
```

下载入口：[最新发布页](https://github.com/Exekiel179/MNE-MCP/releases/latest)。
下载源码压缩包后，解压并在该目录使用 `python -m pip install .`。
不加参数默认注册全部四个客户端并安装配套技能。只接入 PsyClaw 时使用
`python -m mne_mcp setup --clients psyclaw`；也支持 `claude`、`codex`、`opencode`，多个用逗号分隔。
完成后重启客户端，PsyClaw 也可执行 `/reload`。
本包只安装通信与配置依赖，不安装或升级 MNE 科学计算栈。详见 [安装说明](docs/INSTALL.md)。

## 配置

更新包使用 `python -m pip install --upgrade mne-mcp`，随后在同一 MNE 环境重新执行 setup，更新客户端和技能。配置绑定当前 Python 的绝对路径。
已有配置和技能更新前会备份。

### PsyClaw 连接验证

自动写入 `~/.psyclaw/mcp/mne.json`，将全部 14 个技能及参考文件安装到
`~/.psyclaw/skills`。setup 会测试真实 MCP 握手、工具发现及 `mne_check_status`，
并再次测试保存的 PsyClaw 配置。之后可单独复检，不修改注册：

```bash
python -m mne_mcp verify --client psyclaw
```

`connected` 表示通信成功，`mne_available` 表示 MNE 可用，两者分开报告。
执行 `/reload` 后，让 PsyClaw 列出 `mne` 服务工具并调用 `mne_check_status`。
项目内 `.psyclaw/mcp/*.json` 中相同 id 的配置优先于用户配置；解释器不符时先检查这里。
setup 的独立连接测试通过，不代表已打开的聊天已经重新加载。

### 环境变量（可选 `.env`）

```ini
MNE_MCP_TIMEOUT=300          # 单步超时（秒）；ICA / 时频 / 大文件可调大
MNE_MCP_RESULTS_DIR=...      # 图像与导出对象的保存目录
MNE_MCP_DATA_DIR=...         # mne_list_files 默认扫描的目录
```

### 配置分析默认值（交互向导）

设置工具在你省略参数时回退使用的默认值——工频（50/60 Hz）、默认导联、滤波带、EEG 剔除阈值、
ICA 方法/成分数、分段窗、目录与超时：

```bash
python -m mne_mcp configure            # 交互式（回车保留当前值）
python -m mne_mcp configure --show     # 查看当前默认值
python -m mne_mcp configure --reset    # 恢复内置默认
python -m mne_mcp configure --set line_freq=60 default_montage=biosemi64 reject_eeg_uv=120   # 非交互
```

默认值保存在 `~/.mne-mcp/config.json`（可用 `MNE_MCP_CONFIG` 改路径）。优先级：**环境变量 > 配置文件 > 内置默认**。
对话中用 `mne_get_config` 工具查看当前生效配置。修改后重启 MCP 服务生效。

### 技能

setup 会向所选客户端安装全部 14 个技能及其参考文件。Claude 同时安装方法学审查子代理；
其他客户端使用方法学审查技能。更新本包后重新执行 setup 即可更新技能。

---

## 使用

直接描述你的需求即可：

```
加载 sub-01_raw.fif，看一下功率谱
```
```
对 raw 做 1–40 Hz 带通、50 Hz 陷波，然后跑 ICA 去眼电
```
```
按 'target' 事件分段，-0.2 到 0.8 秒，叠加平均，并画出 100/200/300 ms 的 ERP 地形图
```

AI 将会：
1. 检查能力（`mne_check_status`）
2. 把记录加载进常驻会话
3. 一步步执行流程，并以 PNG 形式展示图像
4. 用自然语言解读每个结果
5. 把图像与等效 MNE 代码归档到 `mne_result/`

---

## 输出

每个画图工具都会把 PNG 保存到结果目录并返回其路径：

```
> Figure: `C:\...\mne-mcp\results\psd_01.png`
```

装了 `mne-analyst` 技能后，结果与生成它们的确切 MNE 代码会归档到工作目录的 `mne_result/`（带序号），
使分析完全可复现。

---

## 可用工具（41 个）

### 状态与会话 (7)
`mne_check_status` · `mne_session_info` · `mne_describe` · `mne_get_info` ·
`mne_reset_session` · `mne_run_code` · `mne_get_config`

### 数据读取 (2)
`mne_list_files` · `mne_load_raw`

### 预处理 (7)
`mne_filter` · `mne_resample` · `mne_crop` · `mne_set_montage` ·
`mne_set_reference` · `mne_mark_bad_channels` · `mne_interpolate_bads`

### 可视化 (3)
`mne_plot_psd` · `mne_plot_raw` · `mne_plot_sensors`

### ICA (4)
`mne_fit_ica` · `mne_plot_ica_components` · `mne_plot_ica_sources` · `mne_apply_ica`

### 事件 / 分段 / ERP (7)
`mne_find_events` · `mne_events_from_annotations` · `mne_make_epochs` ·
`mne_plot_epochs_image` · `mne_average_evoked` · `mne_plot_evoked` · `mne_plot_topomap`

### 时频 (2)
`mne_compute_tfr`（Morlet / multitaper、自定义周期、ITC、逐试次功率、基线）· `mne_tfr_morlet`

### 高级分析 (8)
`mne_decode`（解码/MVPA）· `mne_connectivity` · `mne_compute_connectivity`（多频段、通道对、谱估计）· `mne_compute_noise_cov` ·
`mne_make_forward`（源模型）· `mne_apply_inverse`（源定位）· `mne_plot_source_estimate`

`mne_decoding_group_test` 提供被试层面的 max-T / cluster 多重比较校正。
解码报告区分数值证据、方法、解释、局限和待审稿件草稿。
通用代码执行不等于所有 MNE API 都已有结构化校验与科学流程覆盖。

### 导出 (1)
`mne_save`

仍未覆盖的（BIDS、自定义统计、beamformer、autoreject 等）都可在同一个会话中通过 **`mne_run_code`** 完成。
完整参数见 [TOOLS_REFERENCE.zh-CN.md](TOOLS_REFERENCE.zh-CN.md)。高级分析依赖由用户按需准备，调用对应功能时检查。

## 开发

```bash
python -m compileall src/mne_mcp

# 运行测试
pytest

# CLI 命令
python -m mne_mcp status            # 检查环境
python -m mne_mcp setup-info        # 打印配置片段
python -m mne_mcp configure         # 设置分析默认值
python -m mne_mcp setup --clients codex # 注册到 Codex + 装技能
```

---

## 文档

- **项目介绍**：[docs/INTRODUCTION.md](docs/INTRODUCTION.md) · [.docx](docs/INTRODUCTION.docx)
- **安装说明**：[docs/INSTALL.md](docs/INSTALL.md) · [.docx](docs/INSTALL.docx)
- **使用介绍**：[docs/USAGE.md](docs/USAGE.md) · [.docx](docs/USAGE.docx)
- **快速开始**：[QUICK_START.md](QUICK_START.md)
- **工具参考**：[TOOLS_REFERENCE.zh-CN.md](TOOLS_REFERENCE.zh-CN.md)

---

## 许可证

MIT —— 见 [LICENSE](LICENSE)

## 链接

- **MNE-Python**：https://mne.tools/
- **MCP 协议**：https://modelcontextprotocol.io
