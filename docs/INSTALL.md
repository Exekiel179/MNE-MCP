% MNE-MCP 安装说明
% 从零到能在 Claude Code 里对话分析脑电
% v0.1.0

---

# MNE-MCP 安装说明

本文档手把手讲清楚 **MNE-MCP** 的安装、接入 Claude Code、配置与排错。读完照做即可用对话方式做 EEG/MEG 分析。

> 只想最快跑起来？看 [QUICK_START.md](../QUICK_START.md)；想了解项目本身看 [INTRODUCTION.md](INTRODUCTION.md)。

---

## 1. 系统要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows 10/11、macOS、Linux 均可 |
| Python | **3.10 或更高**（建议 3.11 / 3.12） |
| 磁盘 | 约 1–2 GB（MNE + numpy/scipy/matplotlib/scikit-learn 等依赖） |
| 网络 | 安装依赖时需要联网（可用国内镜像加速） |
| 客户端 | Claude Code（或其他支持 MCP 的客户端，如 opencode） |

> MNE-Python 是纯 Python 库，所以分析功能 **三大平台通用**，不像某些商业软件只限 Windows。

---

## 2. 准备工作

### 2.1 安装 Python 3.10+

检查是否已安装：

```bash
python --version
```

若低于 3.10 或未安装，到 <https://www.python.org/downloads/> 下载安装。Windows 安装时请勾选 **“Add Python to PATH”**。

### 2.2 安装 Claude Code

按官方说明安装 Claude Code（CLI / 桌面端 / IDE 扩展均可）。本说明以 Claude Code 为例；opencode 见 [3.4](#34-接入-opencode)。

### 2.3（可选）安装 git

用 `git clone` 获取代码更方便；没有 git 也可以直接下载 zip。

---

## 3. 安装步骤

> **最快：一键脚本。** 克隆仓库后，在仓库目录运行一条命令即可完成全部安装（建环境、装依赖、验证、注册
> Claude Code、装技能）：
>
> ```powershell
> pwsh -File scripts\install.ps1        # Windows
> ```
> ```bash
> bash scripts/install.sh               # macOS / Linux
> ```
> 国内加速：PowerShell 加 `-Mirror`，bash 用 `MIRROR=1 bash scripts/install.sh`。脚本**幂等**，可重复运行；
> 加 `-SkipConfigure` / `SKIP_CONFIGURE=1` 可只装不配置；用 `-Clients` / `CLIENTS=` 指定客户端。
> 脚本会调用 `mne-mcp setup`，把服务器注册到 **Claude Code / Codex / opencode** 并安装技能。
>
> 装完需**重启一次**客户端，`mne_*` 工具才会加载（MCP 在客户端启动时加载，无法在同一会话内省略）。
> 下面是逐步手动安装。

### 3.1 获取代码

```bash
git clone https://github.com/Exekiel179/MNE-MCP.git
cd MNE-MCP
```

或在 GitHub 页面点 **Code → Download ZIP**，解压后进入该目录。

### 3.2 安装本体（三种方式，选一种）

> 强烈建议装在**独立虚拟环境**里，避免污染系统 Python。`".[ica]"` 这个 extra 会一并装上 ICA 需要的 scikit-learn。

#### 方式 A：venv + pip（最通用）

Windows (PowerShell)：
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[ica]"
```

macOS / Linux：
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[ica]"
```

#### 方式 B：uv（更快，推荐熟练用户）

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -e ".[ica]"   # Windows
# macOS/Linux: uv pip install --python .venv/bin/python -e ".[ica]"
```

#### 方式 C：conda

```bash
conda create -n mne-mcp python=3.12 -y
conda activate mne-mcp
pip install -e ".[ica]"
```

> **国内加速**：`pip install -e ".[ica]" -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 3.3 验证安装

```bash
mne-mcp status
```

应看到类似：

```
=== MNE MCP Capability Status ===
MNE-Python   : OK v1.12.1
scikit-learn : OK v1.8.0
numpy        : 2.x  | scipy : 1.x
matplotlib   : 3.x  | pandas : 2.x/3.x
Results dir  : ...\mne-mcp\results
Timeout      : 300s
```

只要 `MNE-Python : OK` 就说明本体装好了。

---

## 3.4 接入客户端（Claude Code / Codex / opencode）

### 自动（推荐）

**在你安装本体的那个环境里**（venv 已激活、或用该 venv 的 `mne-mcp`）运行一条命令，即可注册到三种客户端并装好技能：

```bash
mne-mcp setup                          # Claude Code + Codex + opencode + 技能
mne-mcp setup --clients claude,codex   # 只配置指定客户端
```

它会把 `mne` 写入各客户端配置（已存在的文件先备份），并把启动命令指向**当前 Python**，所以一定能找到你装的包：

| 客户端 | 配置文件 | 键 |
|---|---|---|
| Claude Code | `~/.claude.json` | `mcpServers.mne` |
| OpenAI Codex CLI | `~/.codex/config.toml` | `[mcp_servers.mne]` |
| opencode | `~/.config/opencode/opencode.json` | `mcp.mne` |

> ⚠️ 关键点：注册的启动命令取决于“运行 setup 时用的是哪个 Python”。务必先激活装好包的虚拟环境再运行，
> 否则可能指到没有 mne-mcp 的解释器。

### 手动

`command` 指向**装了本包的那个 Python**（venv 内的 `python.exe`，最常见的踩坑点），或已在 PATH 上的 `mne-mcp`。

**Claude Code** — `~/.claude.json`：
```json
{ "mcpServers": { "mne": { "type": "stdio", "command": "C:\\path\\to\\.venv\\Scripts\\python.exe", "args": ["-m","mne_mcp.cli","serve","--transport","stdio"], "env": { "MNE_MCP_TIMEOUT": "300" } } } }
```

**Codex CLI** — `~/.codex/config.toml`：
```toml
[mcp_servers.mne]
command = "C:\\path\\to\\.venv\\Scripts\\python.exe"
args = ["-m", "mne_mcp.cli", "serve", "--transport", "stdio"]
env = { MNE_MCP_TIMEOUT = "300" }
enabled = true
```

**opencode** — `~/.config/opencode/opencode.json`：
```json
{ "mcp": { "mne": { "type": "local", "command": ["C:\\path\\to\\.venv\\Scripts\\python.exe","-m","mne_mcp.cli","serve","--transport","stdio"], "enabled": true } } }
```

---

## 4. 安装技能（Skills）

> `mne-mcp setup` 已自动安装技能，本节是手动方式。技能是 **Claude Code** 的特性（让它掌握标准流程、
> 参数约定，并把结果归档到 `mne_result/`）；Codex / opencode 直接用 MCP 服务器，不需要技能。

Windows (cmd)：
```cmd
set SKILLS_DIR=%USERPROFILE%\.claude\skills
xcopy /E /I skills\mne-analyst    "%SKILLS_DIR%\mne-analyst"
xcopy /E /I skills\mne-mcp-guard  "%SKILLS_DIR%\mne-mcp-guard"
```

macOS / Linux：
```bash
mkdir -p ~/.claude/skills
cp -r skills/mne-analyst   ~/.claude/skills/
cp -r skills/mne-mcp-guard ~/.claude/skills/
```

---

## 5. 配置默认参数（可选）

用交互向导设置工具默认值（工频、默认导联、滤波带、剔除阈值、ICA、分段窗、目录、超时）：

```bash
mne-mcp configure            # 交互式，回车保留当前值
mne-mcp configure --show     # 查看
mne-mcp configure --reset    # 恢复默认
mne-mcp configure --set line_freq=60 default_montage=biosemi64 reject_eeg_uv=120
```

保存在 `~/.mne-mcp/config.json`。优先级：环境变量 > 配置文件 > 内置默认。

---

## 6. 重启并测试

1. **重启 Claude Code**（让它重新加载 MCP 配置与技能）。
2. 在对话里输入：

```
检查一下 MNE 环境
```

Claude 应调用 `mne_check_status` 并返回版本信息——看到即表示接入成功。

没有数据？让它加载 MNE 自带样例：

```
用 mne_run_code 下载并加载 MNE 的 sample 数据集，然后画功率谱
```

---

## 7. 升级

```bash
cd MNE-MCP
git pull
pip install -e ".[ica]"     # 在原虚拟环境里重新安装（editable 模式通常无需重装，但依赖有更新时需要）
```

升级后重启 Claude Code。

---

## 8. 卸载

1. 从 `~/.claude.json` 的 `mcpServers` 中删除 `"mne"` 项（或恢复安装时生成的 `.backup` 备份）。
2. 删除技能目录：`~/.claude/skills/mne-analyst`、`~/.claude/skills/mne-mcp-guard`。
3. 删除虚拟环境目录 `.venv`（以及可选的 `~/.mne-mcp/config.json`）。
4. 重启 Claude Code。

---

## 9. 安装常见问题

| 问题 | 原因 / 解决 |
|---|---|
| `pip install` 装 mne 很慢或失败 | 用镜像：`-i https://pypi.tuna.tsinghua.edu.cn/simple`；确保网络可达 PyPI |
| 命令找不到 `mne-mcp` | 虚拟环境没激活，或没装上。先激活 `.venv`，或在配置里用 Python 绝对路径 `-m mne_mcp.cli` |
| Claude Code 里看不到 `mne` 工具 | 没重启；或 `command` 指向了错误的 Python。重启 Claude Code，核对 `command` 路径 |
| ICA 报“requires scikit-learn” | 安装时漏了 extra。重装：`pip install -e ".[ica]"` |
| Windows PowerShell 无法激活 venv | 执行策略限制：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 后重试 |
| `setup` 注册后仍连不上 | 确认是用“装了包的那个 Python”运行的 setup；必要时改用手动配置指定 Python 绝对路径 |
| 步骤超时（大文件 / ICA / 时频） | 调大 `MNE_MCP_TIMEOUT`（秒），或 `mne-mcp configure` 设 `timeout` |

更多分析阶段的报错见仓库 `skills/mne-analyst/references/failure-patterns.md`。

---

## 10. 各平台命令对照

| 操作 | Windows (PowerShell) | macOS / Linux |
|---|---|---|
| 建虚拟环境 | `python -m venv .venv` | `python3 -m venv .venv` |
| 激活 | `.\.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| 安装 | `pip install -e ".[ica]"` | `pip install -e ".[ica]"` |
| 装技能 | `xcopy /E /I skills\... "%USERPROFILE%\.claude\skills\..."` | `cp -r skills/... ~/.claude/skills/` |

---

*License: MIT ·  仓库：<https://github.com/Exekiel179/MNE-MCP>*
