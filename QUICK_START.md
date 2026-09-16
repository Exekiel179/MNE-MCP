# MNE-MCP 快速开始 / Quick Start

让 Claude Code 用对话的方式帮你做 EEG/MEG 分析。

## 1. 安装 / Install

先激活已有 Python 3.12+ MNE 环境，执行：

```bash
python -m pip install mne-mcp
python -m mne_mcp setup
```

默认注册 Claude Code、Codex、PsyClaw 和 opencode。只安装 PsyClaw 接入时加 `--clients psyclaw`。
完成后重启客户端，PsyClaw 也可 `/reload`。
MNE 科学计算栈由用户管理；setup 安装全部 14 个技能及参考文件。
setup 自动测试 MCP 连接和状态；可用 `python -m mne_mcp verify --client psyclaw` 复检。

## 2.5 配置默认参数（可选）/ Configure defaults

用交互向导设置默认值（工频、默认导联、滤波带、剔除阈值、ICA 方法/成分数、分段窗、目录、超时）：

```bash
python -m mne_mcp configure            # 交互式，回车保留当前值
python -m mne_mcp configure --show     # 查看当前默认值
python -m mne_mcp configure --set line_freq=60 default_montage=biosemi64 reject_eeg_uv=120   # 非交互
```

保存在 `~/.mne-mcp/config.json`。优先级：环境变量 > 配置文件 > 内置默认。设置后重启 MCP 服务生效；
对话中可用 `mne_get_config` 查看当前生效的默认值。

## 3. 第一次对话 / First session

直接用自然语言，例如：

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

Claude 会：加载 → 预处理 → ICA → 分段 → 叠加平均 → 画图（每张图存成 PNG 并解读）→ 归档到
`mne_result/`。

## 4. 没有数据？用 MNE 自带样例 / No data? Use MNE's sample set

```
用 mne_run_code 下载并加载 MNE 的 sample 数据集，然后画功率谱
```
（首次会下载约 1.5 GB 到 ~/mne_data。）

## 5. 超出内置工具的分析 / Beyond the built-in tools

源定位、连接性、解码(MVPA)、置换检验统计、BIDS、Report —— 都能通过 `mne_run_code` 在同一个会话里完成。
参考 `skills/mne-analyst/references/mne-pipelines.md`。

## 常见问题 / Troubleshooting

- **ICA 报错需要 scikit-learn** → 在 MCP 使用的同一环境补齐 scikit-learn，然后重启客户端。
- **地形图/插值报导联位置错误** → 先 `mne_set_montage`。
- **阈值单位** → 信号是伏特，100 µV 要写 `100e-6`。
- **慢/超时** → 在配置里调大 `MNE_MCP_TIMEOUT`（秒）。

详见 `README.md` 与 `TOOLS_REFERENCE.md`。
