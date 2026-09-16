# MNE 与 MNE-MCP 安装说明

更新日期：2026-09-16。本文适用于 MNE-Python 及其 Python 版 MNE-MCP，不是 MNE-CPP 的安装指南。命令默认不指定软件包版本。

版本说明：本文适用于 MNE-MCP 0.4.2，使用统一入口 `python -m mne_mcp`。从旧版本升级后需重新执行 `python -m mne_mcp setup` 更新客户端启动命令；原来只配置单个客户端的，保留相同的 `--clients` 参数。旧的 `.cli` 入口和 `mne-mcp` 快捷命令已移除。

## 12.9.1 MNE 的安装

MNE-Python 是用于 EEG、MEG、sEEG、ECoG 和 fNIRS 等神经电生理数据处理的开源 Python 软件。单独使用 MNE 不需要安装 MCP 客户端。

### 一、准备 Python 环境

Python 版本以所安装软件及其依赖的兼容要求为准，不额外设置版本上限。当前 MNE 官方最低要求为 Python 3.11；若还要使用本项目当前发布版 MNE-MCP，则同一环境需要 Python 3.12 或以上版本。较新的 Python 版本仍需验证依赖及实际分析流程，不能仅凭安装成功认定全部功能兼容。

在终端执行，而不是在 Python 的 `>>>` 窗口中执行：

```powershell
python --version
python -m pip --version
python -c "import sys; print(sys.executable)"
```

`python -m pip` 表示使用当前 Python 对应的 pip，可减少多个 Python 环境造成的安装错位。下文所有命令都应使用同一个环境。

已有可正常使用的 MNE 环境时，优先激活并复用。检查命令：

```powershell
python -c "import sys, mne; print(sys.executable); print(mne.__version__)"
```

若提示 `No module named 'mne'`，可按下文安装。若是 DLL、二进制兼容性或权限错误，应先诊断原始错误，不要直接反复重装。

没有现成环境时，可先从 [Python 官方网站](https://www.python.org/downloads/) 安装符合要求的 Python，再在自己选择的工作目录建立独立环境。以下为 Windows PowerShell 示例；`.venv` 应为新目录：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

若 PowerShell 禁止运行激活脚本，无需修改系统执行策略。将下文命令开头的 `python` 替换成 `.\.venv\Scripts\python.exe` 即可。macOS / Linux 可用 `python3 -m venv .venv` 创建环境，再执行 `source .venv/bin/activate`。

### 二、安装 MNE：三种方式任选一种

**方式一：默认在线安装**

```powershell
python -m pip install mne
```

pip 会安装 MNE 及其必要依赖，如 NumPy、SciPy 和 Matplotlib。首次安装不需要 `--upgrade`，也不需要指定版本号。已有满足要求的安装通常会被保留，并非每次执行都升级到最新版。

**方式二：国内镜像安装**

国内网络可以使用 pip。默认源较慢或超时时，可临时使用清华镜像：

```powershell
python -m pip install mne -i https://pypi.tuna.tsinghua.edu.cn/simple
```

此参数只影响本次命令，不修改全局设置。镜像可能存在同步延迟；若找不到刚发布的软件包，应核对官方源。不要通过关闭 HTTPS 校验来解决下载问题。

**方式三：本地安装包安装**

可以从 [MNE 的 PyPI 文件页面](https://pypi.org/project/mne/#files) 下载 wheel 文件。安装时使用真实文件名，例如：

```powershell
python -m pip install "D:\installers\mne-1.13.2-py3-none-any.whl"
```

这里的文件名只是本次核验版本的示例，不要求使用这一版本。单独一个 wheel 通常不包含全部依赖；缺少的依赖仍会联网下载。完全断网安装请使用本章后面的“完整离线包准备”。

### 三、验证 MNE

```powershell
python -c "import mne; print(mne.__version__); mne.sys_info()"
python -m pip check
```

第一条检查导入并显示环境信息；第二条检查已安装包的依赖声明是否冲突。未安装可选扩展不代表基础安装失败。以上检查不能代替具体分析任务的运行验证。

### 备注：可选分析依赖

高级依赖按实际任务安装，不必一次全部准备。以下命令只执行需要的项目，并使用 MNE-MCP 所在的同一个 Python 环境。

```powershell
# ICA / 机器学习解码
python -m pip install scikit-learn

# 使用 Picard ICA 算法时补充，包名不是 picard
python -m pip install python-picard

# 功能连接性分析
python -m pip install mne-connectivity

# 近红外扩展分析
python -m pip install mne-nirs

# EEGLAB / MATLAB 文件读取及 HDF5 相关读写
python -m pip install "mne[hdf5]"

# ICA 成分自动标注：选择 ONNX 推理后端
python -m pip install mne-icalabel onnxruntime

# 自动坏段检测和修复
python -m pip install autoreject

# BIDS 数据组织与读写
python -m pip install mne-bids

# 桌面三维显示，需要可用的图形环境及显卡驱动
python -m pip install pyvista pyvistaqt PySide6

# 交互式 EEG / MEG 波形浏览窗口
python -m pip install mne-qt-browser PySide6

# 特定格式导出：分别用于 EDF、BrainVision、EEGLAB
python -m pip install edfio
python -m pip install pybv
python -m pip install eeglabio
```

普通 EDF 读取不应因为上述导出备注而被误认为必须安装 edfio。其他特殊格式读取、模型权重、MRI 模板或 FreeSurfer 等外部软件，应按具体流程另外准备。安装扩展库并不意味着所有新方法都已有对应的结构化 MCP 工具。

ICLabel 的推理后端可选择 ONNX Runtime 或 PyTorch，上述命令选择前者，无需同时安装两者。已有可用 Qt 绑定的环境，应先检查并复用，避免重复安装不同 Qt 绑定。无图形界面的服务器通常不需要桌面显示组件。

这些可选包同样支持国内镜像和离线安装。例如：

```powershell
python -m pip install scikit-learn -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip install --no-index --find-links "D:\installers\wheelhouse" scikit-learn
```

安装可选依赖可能使 pip 调整关联依赖版本。重要科研环境应先保存环境记录或在独立环境验证；添加依赖后重启 MCP 客户端。

## 12.9.2 MNE-MCP 及配套技能的安装

MNE-MCP 将 MNE 分析能力接入支持 MCP 的智能体客户端。MCP 提供工具调用，配套 skill 提供分析流程、参数检查、方法学审查及结果整理指导。MNE-MCP 是轻量接口层，不会通过普通包依赖一次性安装整个科学计算栈。

### 一、安装前确认

使用上一节的同一个 Python 环境。当前发布版 MNE-MCP 要求 Python 3.12 或以上版本，不设置上限。

若已有 MNE 环境使用 Python 3.11，可保留它继续单独使用 MNE；接入当前 MNE-MCP 时应另建符合要求的环境，并在新环境中安装 MNE，不要为了接入而直接改动原有科研环境的 Python。

```powershell
python -c "import sys, mne; print(sys.executable); print(mne.__version__)"
```

本项目基础流程还会使用 pandas。缺少时补充安装：

```powershell
python -m pip install pandas
```

MNE 的基础 pip 安装会处理其必要科学依赖；不要为了安装 MCP 而用项目的开发测试锁文件覆盖现有科研环境。

### 二、安装 MNE-MCP：三种方式任选一种

**方式一：默认在线安装**

```powershell
python -m pip install mne-mcp
```

**方式二：国内镜像安装**

```powershell
python -m pip install mne-mcp -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**方式三：本地安装包安装**

从 [GitHub 最新发布页](https://github.com/Exekiel179/MNE-MCP/releases/latest) 或 [PyPI 文件页面](https://pypi.org/project/mne-mcp/#files) 下载 wheel。以下为当前发布文件名示例，后续按实际下载文件名替换：

```powershell
python -m pip install "D:\installers\mne_mcp-0.4.2-py3-none-any.whl"
```

本地 wheel 包含配套技能，但不包含全部 Python 依赖。完全离线安装需准备完整 wheelhouse，见后文。

若拿到的是发布源码压缩包，可解压并进入包含 `pyproject.toml` 的目录后执行 `python -m pip install .`。源码安装还可能需要下载构建依赖，因此不作为完全离线安装的默认方法。

### 三、注册客户端并安装配套技能

安装软件包后，还需要执行一次注册：

```powershell
python -m mne_mcp setup
```

当前发布版不指定 `--clients` 时，会为 Claude Code、Codex、PsyClaw 和 opencode 全部写入配置并安装技能，即使相应客户端尚未安装。这不会安装这些客户端软件本身。

只接入某个客户端时，改用对应命令，不需要先运行全客户端注册：

```powershell
# 以下任选一条
python -m mne_mcp setup --clients claude
python -m mne_mcp setup --clients codex
python -m mne_mcp setup --clients psyclaw
python -m mne_mcp setup --clients opencode

# 或一次指定多个客户端
python -m mne_mcp setup --clients claude,codex,psyclaw
```

`claude` 指 Claude Code，不代表自动配置 Claude Desktop 或所有 Claude 产品。其他客户端需要按各自规范配置。

setup 会绑定本次 Python 解释器的绝对路径、更新所选客户端配置、安装全部 14 个配套技能及参考文件，并测试 MCP 握手、工具发现和环境状态。已有配置和技能更新前会备份。普通 `setup` 不负责自动补装科学依赖；使用下一节的智能体安装器可以补齐缺失基础库。

默认技能位置如下，自定义环境变量可能改变实际位置：

| 客户端 | 默认技能目录 |
| --- | --- |
| Claude Code | `~/.claude/skills` |
| Codex | `~/.codex/skills`，可由 `CODEX_HOME` 改变 |
| PsyClaw | `~/.psyclaw/skills` |
| opencode | `~/.config/opencode/skills`，可由 `XDG_CONFIG_HOME` 改变 |

`~` 表示用户主目录。Claude Code 另安装方法学审查子代理；其他客户端使用相应的方法学审查技能。

### 四、重启并验证连接

重启所选客户端；PsyClaw 也可执行 `/reload`。在终端检查：

```powershell
python -m mne_mcp version
python -m mne_mcp status
python -m mne_mcp verify
```

PsyClaw 可额外检查已保存的注册记录：

```powershell
python -m mne_mcp verify --client psyclaw
```

然后在客户端向智能体发送：

> 请调用 MNE-MCP 的 mne_check_status，确认当前会话可以使用 MNE，报告实际 Python 路径、MNE 版本和缺失的可选依赖。暂时不要加载或修改我的数据。

终端握手成功与客户端当前会话可用是两项检查；应以重启后实际调用成功作为接入完成的依据。连接成功也不等于所有科学分析依赖都已安装。

### 五、使用智能体安装

该方法适用于能读取项目文档并执行本地终端命令的智能体，例如具备相应权限的 Codex、Claude Code 或 PsyClaw。普通网页聊天若无本地工具权限，不能替你安装电脑上的软件。

**一句话安装指令：**

> 请按 https://github.com/Exekiel179/MNE-MCP 的最新正式发布版 INSTALL_AGENT.md，为当前客户端安装 MNE-MCP 和全部配套技能；优先复用已有 MNE 环境，缺少 MNE 时用该环境的 pip 补齐基础依赖，完成连接测试，不要一次安装所有可选分析库。

**需要更明确控制时，可发送以下完整指令：**

```text
请帮我安装 MNE-MCP，并为当前使用的客户端安装全部配套技能。

项目：https://github.com/Exekiel179/MNE-MCP
发布入口：https://github.com/Exekiel179/MNE-MCP/releases/latest

请先获取最新正式发布版，阅读该版本的 INSTALL_AGENT.md，再执行安装：
1. 优先复用我指定的或当前已有的 MNE Python 环境，报告解释器绝对路径。
2. 若没有现成环境，在合适的工作目录创建独立虚拟环境；若 Python 本身缺失，请先说明前提，不擅自进行系统级安装。
3. 先只读预检；缺少 MNE 或基础库时，用选定解释器的 pip 补齐，不主动升级已有可正常导入的科研库。
4. 只注册当前客户端，并安装全部配套技能及参考文件；不要覆盖其他客户端设置或删除用户文件。
5. 可选分析库按实际任务安装，不要安装整套开发测试依赖。
6. 安装后执行真实 MCP 连接测试，报告版本、解释器、技能位置及错误。
7. 若需要重启客户端，明确报告“已安装，等待客户端重启”，不要提前宣称当前会话已经可用。
8. 保留现有改动，更新配置和技能前备份；不要把下载脚本直接通过管道交给 shell 执行。
```

若希望全部客户端都配置，将“只注册当前客户端”改为“注册 Claude Code、Codex、PsyClaw 和 opencode 全部四个客户端”。国内网络不佳时，可补充“pip 下载使用清华镜像，仅对本次安装生效，不修改全局配置”；GitHub 访问仍可能需要独立解决，PyPI 镜像不会代理 GitHub。

**已有本地发布源码时，可发送：**

> 请阅读 D:\installers\MNE-MCP\INSTALL_AGENT.md，并按该版本说明安装 MNE-MCP 及全部配套技能，只注册当前客户端。优先复用已有 MNE 环境；缺失基础库可以用 pip 安装，高级依赖按需补充。请先核对实际路径，不要覆盖现有文件。

上述路径需换成实际解压目录。只有 wheel 时，不应假设存在 `scripts/install.py`；智能体应按本章本地 wheel 方法安装基础库和接口包，再执行 setup 和验证。

**安装器实际执行流程说明：**

在包含 `scripts/install.py` 的发布源码目录中，可先执行只读预检，再安装。例如只配置 Codex：

```powershell
python scripts/install.py --check --json
python scripts/install.py --clients codex
```

这里的 `python` 必须是选定环境的解释器。需要显式指定路径时，PowerShell 示例为：

```powershell
& "D:\envs\mne\Scripts\python.exe" scripts/install.py --check --json --python "D:\envs\mne\Scripts\python.exe"
& "D:\envs\mne\Scripts\python.exe" scripts/install.py --python "D:\envs\mne\Scripts\python.exe" --clients codex
```

脚本会安装接口包、补齐缺失基础库、注册客户端并安装技能；脚本本身不创建虚拟环境。预检报告缺包时可以进入安装，若报告导入损坏或权限问题，应先诊断。MCP 服务启动或分析运行期间不会自动安装科学依赖。

### 备注一：完整离线包准备

“本地安装包”不等于“完整离线安装包”。完全断网时，MNE、MNE-MCP、pandas 及其全部依赖都需要提前下载。

在与目标电脑操作系统、CPU 架构和 Python 主次版本相同的联网环境中，使用符合要求的 Python 执行：

```powershell
python -m pip download --only-binary=:all: --dest "D:\installers\wheelhouse" mne pandas mne-mcp
```

国内镜像准备方式为：

```powershell
python -m pip download --only-binary=:all: --dest "D:\installers\wheelhouse" mne pandas mne-mcp -i https://pypi.tuna.tsinghua.edu.cn/simple
```

以上任选一条。若需要 ICA，可在包名列表后加上 `scikit-learn`；其他可选依赖同理。最好将本次所需包在同一条下载命令中列齐，以便 pip 一起解析依赖。`--only-binary=:all:` 会在缺少可用 wheel 时明确失败；这种情况需诊断平台兼容性或另行准备 wheel，不应将不完整目录当作完整离线包。

把整个 wheelhouse 目录复制到目标电脑，先准备好兼容的 Python 环境，再执行：

```powershell
# 安装 MNE 和 MCP 使用的基础分析库
python -m pip install --no-index --find-links "D:\installers\wheelhouse" mne pandas

# 安装 MCP 接口包
python -m pip install --no-index --find-links "D:\installers\wheelhouse" mne-mcp

# 注册全部默认客户端；只配置一个时添加 --clients
python -m mne_mcp setup
python -m mne_mcp verify
```

`--no-index` 禁止查询在线包索引；缺包时会报错，不会自动转在线下载。Python 本身、客户端软件、研究数据、模型权重和外部软件不包含在这套 wheelhouse 中，需要分别准备。严格离线部署还应确认具体分析流程不会首次联网下载模板或模型。

可让智能体离线安装：

> 请仅使用 D:\installers\wheelhouse 中的本地包，在我指定的 Python 环境中离线安装 MNE、pandas、MNE-MCP 和全部配套技能，只注册当前客户端。所有 pip 安装使用 --no-index 和 --find-links，不访问网络；缺包请报告具体缺项，不切换在线源。完成连接测试并说明是否需要重启客户端。

### 备注二：更新与故障检查

首次安装不需要 `--upgrade`。已有安装且希望更新时执行：

```powershell
python -m pip install --upgrade mne-mcp
python -m mne_mcp setup
```

原来只配置单一客户端的，更新时也应使用相同 `--clients` 参数。此流程不主动要求升级 MNE，但 pip 可能根据新包的依赖要求调整相关依赖。重要分析环境应先记录版本并验证结果复现。

出现“安装了却找不到”的问题时，先检查实际解释器：

```powershell
python -c "import sys; print(sys.executable)"
python -m pip show mne mne-mcp
python -m pip check
```

同时检查客户端 `mne_check_status` 报告的 Python 路径是否一致。不要移动或删除已注册的虚拟环境；更换环境后需要重新运行 setup。PsyClaw 项目内同 id 的 MCP 配置可能覆盖用户级配置，需要检查，不应直接删除。

### 参考与下载

- [MNE 官方安装说明](https://mne.tools/stable/install/manual_install.html)
- [MNE PyPI 下载文件](https://pypi.org/project/mne/#files)
- [MNE-MCP PyPI 下载文件](https://pypi.org/project/mne-mcp/#files)
- [MNE-MCP 最新正式发布版及本地安装包](https://github.com/Exekiel179/MNE-MCP/releases/latest)
- [本版智能体安装说明](https://github.com/Exekiel179/MNE-MCP/blob/v0.4.2/INSTALL_AGENT.md)
- [清华 PyPI 镜像使用说明](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)
- [ICLabel 安装及推理后端说明](https://mne.tools/mne-icalabel/stable/install.html)
- [pip 离线包下载说明](https://pip.pypa.io/en/stable/cli/pip_download/)
