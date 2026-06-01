# MNE-MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io)

[English](README.md) | **简体中文**

一个 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 服务器，把开源神经电生理分析平台
**[MNE-Python](https://mne.tools/)** 接入 AI 助手，用于分析 **EEG、MEG、sEEG、ECoG、fNIRS** 数据。

用自然语言描述你的分析需求——MNE-MCP 会加载记录、执行 MNE 流程（滤波、ICA、分段、ERP/ERF 叠加、
时频、以及通过代码完成的源定位等）、保存图像并解读结果。

> 可在 **Claude Code** 与 **opencode**（任意支持 MCP 的客户端）中使用。配套两个 Agent **技能**
> （`mne-analyst`、`mne-mcp-guard`），让流程更可靠、结果自动归档。

---

## 为什么要给 MNE-Python 做一个 MCP？

MNE 的分析是**有状态、强可视化**的，不同于一次性的统计批处理任务：

- 你加载一份 `Raw` 记录后，要连续做 滤波 → 重参考 → ICA → 分段 → 叠加 → 时频，每一步都会改动很大的内存对象。
  MNE-MCP 维护**一个常驻会话**，记录无需在步骤之间反复加载。
- 几乎每个决定都靠“看图”（功率谱、电极图、ICA 成分、ERP）。每个画图工具都会保存一张 AI 能读取并解读的 **PNG**。
- MNE 是庞大的纯 Python API。MNE-MCP 用 **32 个结构化工具**覆盖常见流程，并额外提供一个通用的
  **`mne_run_code`** 工具：可在同一个会话中直接执行任意 MNE/Python 代码，覆盖 MNE 的全部功能。
- 默认参数（工频、导联、滤波带、剔除阈值、ICA 设置、分段窗、目录、超时）可通过交互式
  `mne-mcp configure` 向导**由用户配置**。

---

## 环境要求

- Python 3.10+
- [MNE-Python](https://mne.tools/) ≥ 1.6（作为依赖自动安装）
- `scikit-learn`（ICA 所需，可选 extra）
- Claude Code（或任意支持 MCP 的客户端）

> 跨平台：MNE-Python 是纯 Python，分析功能在 Windows、macOS、Linux 上都可用。

---

## 快速安装

```bash
git clone https://github.com/Exekiel179/MNE-MCP.git
cd MNE-MCP

# 1. 安装（会带上 mne、numpy、scipy、matplotlib，以及 ICA 用的 scikit-learn）
pip install -e ".[ica]"

# 2. 一键注册到 Claude Code / Codex / opencode 并安装技能
mne-mcp setup

# 3. 重启你的客户端
```

或用**一键脚本**（克隆后在仓库目录运行，自动完成上面三步 + 装技能）：

```powershell
pwsh -File scripts\install.ps1     # Windows
```
```bash
bash scripts/install.sh            # macOS / Linux
```

完整步骤见 [docs/INSTALL.md](docs/INSTALL.md)；首次使用引导见 [QUICK_START.md](QUICK_START.md)。

> `mne-mcp setup` 一条命令就会把 `mne` 服务器注册到 **Claude Code、Codex、opencode**（你用到的那些）
> 并安装技能；可用 `--clients claude,codex` 缩小范围。无论哪种方式，装完都需**重启一次客户端**，
> `mne_*` 工具才会加载（MCP 在客户端启动时加载）。

---

## 配置

### 自动配置（推荐）

```bash
mne-mcp setup                          # Claude Code + Codex + opencode，并装技能
mne-mcp setup --clients claude,codex   # 只配置指定客户端
mne-mcp configure-claude               # 仅 Claude Code（setup 的子集）
```

`setup` 会把 `mne` 服务器写入各客户端配置并安装技能，改动前对已存在的文件先做带时间戳的备份：

| 客户端 | 配置文件 | 键 |
|---|---|---|
| Claude Code | `~/.claude.json` | `mcpServers.mne` |
| OpenAI Codex CLI | `~/.codex/config.toml` | `[mcp_servers.mne]` |
| opencode | `~/.config/opencode/opencode.json` | `mcp.mne` |

### 手动配置

`command` 需指向**装了本包的那个 Python**（或已在 PATH 上的 `mne-mcp`）。

**Claude Code** — `~/.claude.json`：
```json
{ "mcpServers": { "mne": { "type": "stdio", "command": "mne-mcp", "args": ["serve", "--transport", "stdio"] } } }
```

**Codex CLI** — `~/.codex/config.toml`：
```toml
[mcp_servers.mne]
command = "mne-mcp"
args = ["serve", "--transport", "stdio"]
enabled = true
```

**opencode** — `~/.config/opencode/opencode.json`：
```json
{ "mcp": { "mne": { "type": "local", "command": ["mne-mcp", "serve", "--transport", "stdio"], "enabled": true } } }
```

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
mne-mcp configure            # 交互式（回车保留当前值）
mne-mcp configure --show     # 查看当前默认值
mne-mcp configure --reset    # 恢复内置默认
mne-mcp configure --set line_freq=60 default_montage=biosemi64 reject_eeg_uv=120   # 非交互
```

默认值保存在 `~/.mne-mcp/config.json`（可用 `MNE_MCP_CONFIG` 改路径）。优先级：**环境变量 > 配置文件 > 内置默认**。
对话中用 `mne_get_config` 工具查看当前生效配置。修改后重启 MCP 服务生效。

### 安装技能

`mne-mcp setup` 会自动安装技能。如需手动：

```cmd
set SKILLS_DIR=%USERPROFILE%\.claude\skills
xcopy /E /I skills\mne-analyst    "%SKILLS_DIR%\mne-analyst"
xcopy /E /I skills\mne-mcp-guard  "%SKILLS_DIR%\mne-mcp-guard"
```

安装后重启客户端。（技能是 Claude Code 的特性；Codex / opencode 直接用 MCP 服务器。）

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

## 可用工具（32 个）

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

### 时频 (1)
`mne_tfr_morlet`

### 导出 (1)
`mne_save`

源定位、连接性、解码、BIDS、自定义统计等结构化工具未覆盖的内容，都可在同一个会话中通过
**`mne_run_code`** 完成。完整参数见 [TOOLS_REFERENCE.zh-CN.md](TOOLS_REFERENCE.zh-CN.md)。

---

## 开发

```bash
# 编译检查
python -m compileall src/mne_mcp

# 运行测试
pytest

# CLI 命令
mne-mcp status            # 检查环境
mne-mcp setup-info        # 打印配置片段
mne-mcp configure         # 设置分析默认值
mne-mcp setup             # 注册到 Claude Code / Codex / opencode + 装技能
mne-mcp configure-claude  # 仅 Claude Code
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
