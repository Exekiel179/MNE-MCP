# MNE-MCP

[![CI](https://github.com/Exekiel179/MNE-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/Exekiel179/MNE-MCP/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io)

[English](README.md) | **简体中文**

一个 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 服务器，把开源神经电生理分析平台
**[MNE-Python](https://mne.tools/)** 接入 AI 助手，用于分析 **EEG、MEG、sEEG、ECoG、fNIRS** 数据。

用自然语言描述你的分析需求——MNE-MCP 会加载记录、执行 MNE 流程（滤波、ICA、分段、ERP/ERF 叠加、
时频、以及通过代码完成的源定位等）、保存图像并解读结果。

> 可在 **Claude Code** 与 **opencode**（任意支持 MCP 的客户端）中使用。配套一组 Agent **技能**
> ——`mne-analyst`、`mne-mcp-guard`，以及一套"先怀疑、后审查"的**分析技能套件**
> （`mne-methodology-critic` + 各分析大类的专用技能），让流程更可靠、结果自动归档。

---

## 为什么要给 MNE-Python 做一个 MCP？

MNE 的分析是**有状态、强可视化**的，不同于一次性的统计批处理任务：

- 你加载一份 `Raw` 记录后，要连续做 滤波 → 重参考 → ICA → 分段 → 叠加 → 时频，每一步都会改动很大的内存对象。
  MNE-MCP 维护**一个常驻会话**，记录无需在步骤之间反复加载。
- 几乎每个决定都靠“看图”（功率谱、电极图、ICA 成分、ERP）。每个画图工具都会保存一张 AI 能读取并解读的 **PNG**。
- MNE 是庞大的纯 Python API。MNE-MCP 用 **38 个结构化工具**覆盖常见流程**和高级分析**（源定位、连接性、
  解码），并额外提供一个通用的 **`mne_run_code`** 工具：可在同一个会话中直接执行任意 MNE/Python 代码，
  覆盖 MNE 的全部功能。
- 默认参数（工频、导联、滤波带、剔除阈值、ICA 设置、分段窗、目录、超时）可通过交互式
  `mne-mcp configure` 向导**由用户配置**。

---

## 环境要求

- Python 3.10+
- [MNE-Python](https://mne.tools/) ≥ 1.6 —— **按需安装**（见[默认轻量 —— 按需后端](#默认轻量--按需后端)）；想预装可用 `mne-mcp[analysis]`
- `scikit-learn`（ICA 所需，在 `ica` / `full` extra 中，或用 `mne-mcp install-backend`）
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

### 用 `uvx` / `pipx` 运行（标准 MCP 方式，推荐）

`mne-mcp` 已[发布到 PyPI](https://pypi.org/project/mne-mcp/)，最通用的方式是标准 MCP 启动器——无需克隆、无需
`setup`。在客户端配置里加入（Claude Code 为 `~/.claude.json`，Claude Desktop 为 `claude_desktop_config.json`）：

```json
{ "mcpServers": { "mne": { "command": "uvx", "args": ["--from", "mne-mcp[ica]", "mne-mcp", "serve", "--transport", "stdio"] } } }
```

`uvx`（来自 [uv](https://docs.astral.sh/uv/)）会按需拉取并运行 `mne-mcp`。`[ica]` 附加项会带上 scikit-learn，
让 ICA 开箱即用；换成 **`mne-mcp[full]`** 可再获得高级工具（源定位、连接性、解码、BIDS）。由于 MNE 依赖较重，
**持久安装**通常比每次临时解析更快：

```bash
pipx install "mne-mcp[ica]"        # 或：uv tool install "mne-mcp[ica]"（高级工具用 [full]）
```

随后把配置里的 `command` 指向 `mne-mcp`、`args: ["serve", "--transport", "stdio"]`。上面的源码安装
仍是开发者路径。

> **技能已随包发布（自 0.2.2 起）。** PyPI 包内自带技能套件与 `mne-methodology-critic` 子代理，因此
> 多跑一条命令即可装上——`mne-mcp setup`（在 `pipx` / `uv tool install` 之后）或 `uvx mne-mcp setup`，
> 无需克隆仓库。

### 默认轻量 —— 按需后端

自 **0.3.0** 起，包本身极小：直接 `pip install mne-mcp` / `pipx install mne-mcp` 只会装上 MCP 协议层
（`mcp`、`fastmcp`、`pydantic`、`python-dotenv`），几秒装完。庞大的科学栈（MNE-Python + numpy/scipy/
matplotlib/pandas，以及 ICA 用的 scikit-learn）会在**第一次真正需要分析时按需安装**：

- 在对话里直接提需求即可——当某个工具报告"后端缺失"时，调用 **`mne_install_backend`** 工具
  （`mne_check_status` 也会提示）。它会 `pip install` 到服务器**自己那个环境**，并且**无需重启客户端**就能用。
- 在终端里：`mne-mcp install-backend`（加 `--profile full` 可装源定位 / 连接性 / 解码 / BIDS）。

```bash
pipx install mne-mcp            # 极小、瞬间装好
mne-mcp install-backend        # 准备好了再装 MNE + ICA（或让工具自己装）
```

想一次装全？改用 extra：**`mne-mcp[analysis]`**（MNE 核心）、**`[ica]`**（+ scikit-learn）、
**`[full]`**（+ 高级工具）。对于临时的 `uvx` 运行，请在配置里固定 extra（如上的 `--from mne-mcp[ica]`），
因为 `uvx` 环境每次运行后即丢弃，按需安装不会保留。

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

`mne-mcp setup` 会自动安装全部技能。如需手动，把 `skills/` 下每个文件夹拷到技能目录——套件包括
`mne-analyst`、`mne-mcp-guard`、`mne-methodology-critic`，以及各分析大类技能（`mne-preprocess`、
`mne-artifacts`、`mne-erp`、`mne-spectral`、`mne-timefreq`、`mne-connectivity`、`mne-source`、
`mne-decoding`、`mne-stats`、`mne-advanced`），以及写作技能（`mne-writeup`）：

```cmd
set SKILLS_DIR=%USERPROFILE%\.claude\skills
for %S in (mne-analyst mne-mcp-guard mne-methodology-critic mne-preprocess mne-artifacts mne-erp mne-spectral mne-timefreq mne-connectivity mne-source mne-decoding mne-stats mne-advanced mne-writeup) do xcopy /E /I skills\%S "%SKILLS_DIR%\%S"
```

> `mne-mcp setup` 还会把 `mne-methodology-critic` **子代理（subagent）**安装到 `~/.claude/agents/`
> （各技能的 Phase 3 会在隔离上下文中调用它）。手动安装时把 `agents\mne-methodology-critic.md` 拷过去即可。

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

## 可用工具（38 个）

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

### 高级分析 (6)
`mne_decode`（解码/MVPA）· `mne_connectivity`（连接性）· `mne_compute_noise_cov` ·
`mne_make_forward`（源模型）· `mne_apply_inverse`（源定位）· `mne_plot_source_estimate`

### 导出 (1)
`mne_save`

仍未覆盖的（BIDS、自定义统计、beamformer、autoreject 等）都可在同一个会话中通过 **`mne_run_code`** 完成。
完整参数见 [TOOLS_REFERENCE.zh-CN.md](TOOLS_REFERENCE.zh-CN.md)。高级工具需要 `[full]` 额外依赖
（`pip install -e ".[full]"`）。

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
