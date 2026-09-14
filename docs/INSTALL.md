# MNE-MCP 安装说明

MNE-MCP 是轻量接口层，随包提供 14 个分析技能及参考文件，不将科学计算栈声明为包依赖。
智能体安装器会自动用选定解释器的 pip 补齐缺失的 MNE 和基础分析库，再验证；已有库不主动升级。
可选高级分析库仍按需准备。--check 保持只读，权限或二进制错误不会触发自动重装。
当前测试基线是 Python 3.12。先激活你已经安装好 MNE 的环境。

## 安装与接入

智能体安装入口见 [INSTALL_AGENT.md](../INSTALL_AGENT.md)。用户可以直接让智能体按该文件执行。
脚本支持 --check --json 只读预检、--python 指定已有环境、--clients 指定当前客户端。
未指定客户端时，只会自动选择唯一检测到的客户端；多个或没有候选时会明确报错。

在已有 Python 3.12 MNE 环境执行：

```bash
python -c "import sys, mne; print(sys.executable, mne.__version__)"
python -m pip install "mne-mcp==0.4.0"
python -m mne_mcp.cli setup --clients codex
```

下载入口：[v0.4.0 发布页](https://github.com/Exekiel179/MNE-MCP/releases/tag/v0.4.0)。
也可以从发布页下载源码包，解压后在包含 pyproject.toml 的目录执行
`python -m pip install .`。不要把旧版本安装说明与 0.4.0 混用。
选择 claude、codex、opencode，多个客户端用逗号分隔。setup 绑定当前 Python
的绝对路径，不依赖客户端的 PATH。安装完成后重启所选客户端。

scripts/install.py 复用选定解释器，自动补齐缺失基础库，不创建新环境。
requirements.lock 仅供开发/测试重建参考环境，普通用户不要用它覆盖现有科研环境。

## 技能安装

setup 自动安装完整技能套件和所有 references 文件：

| 客户端 | 技能目录 |
|---|---|
| Claude Code | ~/.claude/skills |
| Codex | $CODEX_HOME/skills，默认 ~/.codex/skills |
| opencode | $XDG_CONFIG_HOME/opencode/skills，默认 ~/.config/opencode/skills |

Claude 另安装方法学审查子代理；其他客户端使用 mne-methodology-critic 技能。
已有技能会先备份到技能目录旁的 mne-mcp-backups，再合并更新；用户额外文件保留。
客户端配置也有带时间戳的备份。只更新 MCP 配置时可使用 --no-skills。
缺少随包技能时 setup 报错，不静默宣称完整安装。

## 科学计算依赖

基本分析会使用 mne、numpy、scipy、matplotlib、pandas。
ICA/解码需要 scikit-learn；连接性需要 mne-connectivity；
自动剔除需要 autoreject；BIDS 需要 mne-bids；源定位/渲染可能需要 nibabel、pyvista。
基础库可由安装器补齐，高级库由用户按实际需求在同一环境准备。MCP 服务运行期间不安装包。

缺少某个可选库不会阻止其他功能。先检查实际 import 错误：
缺包、二进制不兼容和配置文件权限错误需要不同处理，不要反复重装 MNE-MCP。

## 更新与验证

更新到此版本执行 `python -m pip install "mne-mcp==0.4.0"`，再运行 setup 更新客户端和技能。
用 python -m mne_mcp.cli status 或客户端的 mne_check_status 检查环境。
出现错误时核对服务实际解释器；环境修改后重启客户端。
保留用户原有 MNE 偏好，不自动改写或隔离全局 MNE 配置。
