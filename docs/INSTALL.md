# MNE-MCP 安装说明

## 独立 C++ 预览版

MNE-CPP MCP 不依赖 MNE-Python。在源码仓库的 Python 3.12+ 环境执行：

```bash
python -m pip install ./packages/mne-cpp-mcp
mne-cpp-mcp setup --data-dir "D:/research/data"
```

将数据路径替换为已存在且授权读取的绝对目录，这是唯一必需参数。
仅检测到一个客户端时自动选择；检测到多个或没有时，再加 `--clients codex`、
`--clients claude` 或 `--clients opencode`。只配置选定客户端并安装配套 skill。
命令不在 PATH 时可用 `python -m mne_cpp_mcp setup --data-dir "D:/research/data"`。
完成后重启客户端。
Windows x86_64 可自动下载并校验官方原生 ZIP（含 Qt），不改系统 PATH。
默认复用或安装原生库，不必加 `--install-native`；已有原生程序可用 `--bin-dir`
或 `MNE_CPP_BIN_DIR` 指定。加 `--check` 只预检不写入。
C++ 包尚未发布到 PyPI，目前仅支持 FIFF 只读检查，不支持完整分析。
详见 [C++ 安装指南](../packages/mne-cpp-mcp/README.md)和
[智能体安装约定](../packages/mne-cpp-mcp/INSTALL_AGENT.md)。

## Python 版

MNE-MCP 是轻量接口层，随包提供 14 个分析技能及参考文件，不将科学计算栈声明为包依赖。
智能体安装器会自动用选定解释器的 pip 补齐缺失的 MNE 和基础分析库，再验证；已有库不主动升级。
可选高级分析库仍按需准备。--check 保持只读，权限或二进制错误不会触发自动重装。
最低版本及完整测试基线是 Python 3.12，不设 Python 版本上限。
3.13、3.14 等新版本不会仅因版本号被拒绝；依赖和实际分析流程仍需验证。
先激活你已经安装好 MNE 的环境。

## 安装与接入

智能体安装入口见 [INSTALL_AGENT.md](../INSTALL_AGENT.md)。用户可以直接让智能体按该文件执行。
脚本支持 --check --json 只读预检、--python 指定已有环境、--clients 指定当前客户端。
Python 版未指定客户端时，默认注册 Claude Code、Codex、PsyClaw 和 opencode 并安装各自技能。
只接入一个客户端时，明确使用 --clients psyclaw（或 claude、codex、opencode）。

在已有 Python 3.12+ MNE 环境执行：

```bash
python -c "import sys, mne; print(sys.executable, mne.__version__)"
python -m pip install mne-mcp
mne-mcp setup
```

下载入口：[最新发布页](https://github.com/Exekiel179/MNE-MCP/releases/latest)。
也可以从发布页下载源码包，解压后在包含 pyproject.toml 的目录执行
`python -m pip install .`。请使用与下载版本配套的安装说明。
选择 claude、codex、psyclaw、opencode，多个客户端用逗号分隔。setup 绑定当前 Python
的绝对路径，不依赖客户端的 PATH。安装完成后重启所选客户端。

scripts/install.py 复用选定解释器，自动补齐缺失基础库，不创建新环境。
requirements.lock 仅供开发/测试重建参考环境，普通用户不要用它覆盖现有科研环境。

## 技能安装

setup 自动安装完整技能套件和所有 references 文件：

| 客户端 | 技能目录 |
|---|---|
| Claude Code | ~/.claude/skills |
| Codex | $CODEX_HOME/skills，默认 ~/.codex/skills |
| PsyClaw | ~/.psyclaw/skills |
| opencode | $XDG_CONFIG_HOME/opencode/skills，默认 ~/.config/opencode/skills |

Claude 另安装方法学审查子代理；其他客户端使用 mne-methodology-critic 技能。
已有技能会先备份到技能目录旁的 mne-mcp-backups，再合并更新；用户额外文件保留。
客户端配置也有带时间戳的备份。只更新 MCP 配置时可使用 --no-skills。
缺少随包技能时 setup 报错，不静默宣称完整安装。

PsyClaw 自动注册文件为 `~/.psyclaw/mcp/mne.json`，不是 Claude 的 mcpServers 格式。
setup 会启用该服务；保留其他配置字段，更新前备份。完成后执行 `/reload` 或重启。
项目内 `.psyclaw/mcp/*.json` 中同 id 配置会覆盖用户级注册，不会被安装器删除。

## 科学计算依赖

基本分析会使用 mne、numpy、scipy、matplotlib、pandas。
ICA/解码需要 scikit-learn；连接性需要 mne-connectivity；
自动剔除需要 autoreject；BIDS 需要 mne-bids；源定位/渲染可能需要 nibabel、pyvista。
基础库可由安装器补齐，高级库由用户按实际需求在同一环境准备。MCP 服务运行期间不安装包。

缺少某个可选库不会阻止其他功能。先检查实际 import 错误：
缺包、二进制不兼容和配置文件权限错误需要不同处理，不要反复重装 MNE-MCP。

## 更新与验证

更新执行 `python -m pip install --upgrade mne-mcp`，再运行 setup 更新客户端和技能。
用 `mne-mcp status` 或客户端的 `mne_check_status` 检查环境。
setup 自动执行真实 MCP 握手、工具发现及状态调用，再验证写入的 PsyClaw 配置。
使用 `mne-mcp verify --client psyclaw` 可复检已保存的命令而不修改配置。
connected 为真不等于科学依赖齐备，另检查 mne_available。
在 PsyClaw 内通过 psyclaw_mcp 列出 mne 工具，再调用 mne_check_status，才代表当前会话接入成功。
出现错误时核对服务实际解释器；环境修改后重启客户端。
保留用户原有 MNE 偏好，不自动改写或隔离全局 MNE 配置。
