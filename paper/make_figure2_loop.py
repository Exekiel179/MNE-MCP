# -*- coding: utf-8 -*-
"""Figure 2: persistent session + the auto-plot / AI-read closed loop (§2.2)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

for fam in ["Microsoft YaHei", "SimHei", "Source Han Sans SC", "DejaVu Sans"]:
    try:
        matplotlib.rcParams["font.sans-serif"] = [fam]
        break
    except Exception:
        continue
matplotlib.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(9.2, 5.2), dpi=200)
ax.set_xlim(0, 100)
ax.set_ylim(0, 74)
ax.axis("off")


def box(x, y, w, h, text, fc, ec="#33414e", fs=10, tc="#10202b", bold=False):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=2",
                       linewidth=1.4, edgecolor=ec, facecolor=fc)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, fontweight=("bold" if bold else "normal"))


def arrow(x1, y1, x2, y2, text="", color="#2b6cb0", fs=8.8, rad=0.0, tx=None, ty=None):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                        linewidth=1.7, color=color,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if text:
        ax.text(tx if tx is not None else (x1 + x2) / 2,
                ty if ty is not None else (y1 + y2) / 2, text,
                ha="center", va="center", fontsize=fs, color=color)


# --- Top: persistent in-memory session ---
box(4, 58, 92, 13, "", "#eef5fb", ec="#2b6cb0")
ax.text(50, 68.2, "常驻内存会话（数据加载一次，状态跨工具调用保持）", ha="center",
        va="center", fontsize=11, color="#1f4e79", fontweight="bold")
chips = ["raw", "epochs", "evoked", "ica", "power", "stc"]
cw, gap, x0, cy = 12.5, 2.0, 8, 61.5
for i, c in enumerate(chips):
    cx = x0 + i * (cw + gap)
    box(cx, cy, cw, 4.6, c, "#d6e8fb", ec="#2b6cb0", fs=10)
    if i < len(chips) - 1:
        ax.annotate("", xy=(cx + cw + gap - 0.3, cy + 2.3), xytext=(cx + cw + 0.3, cy + 2.3),
                    arrowprops=dict(arrowstyle="-|>", color="#7aa7d6", lw=1.3))

# --- Lower: the closed loop (4 nodes, clockwise) ---
N1 = (8, 30, 36, 11)    # AI calls a plotting tool
N2 = (56, 30, 36, 11)   # tool saves PNG
N3 = (56, 6, 36, 11)    # AI reads & interprets
N4 = (8, 6, 36, 11)     # decide next params
box(*N1, "① AI 调用绘图工具\n(mne_plot_psd / ica / evoked …)", "#f3f7ee", ec="#6b8e3d", fs=9.5)
box(*N2, "② 工具出图存 PNG\n(matplotlib Agg 无界面后端)", "#f3f7ee", ec="#6b8e3d", fs=9.5)
box(*N3, "③ AI 读取并解读图像\n(工频峰 / 伪迹成分 / ERP 成分)", "#fff4e0", ec="#c08a2d", fs=9.5)
box(*N4, "④ 据图判断 → 选择下一步参数\n(滤波带 / 剔除阈值 / 剔除成分)", "#fff4e0", ec="#c08a2d", fs=9.5)

arrow(44, 35.5, 56, 35.5, "保存 + 等效代码", tx=50, ty=37.6, color="#6b8e3d")
arrow(74, 30, 74, 17.2, "", color="#c08a2d", rad=0.0)
arrow(56, 11.5, 44, 11.5, "解读结论", tx=50, ty=13.6, color="#c08a2d")
arrow(26, 17.2, 26, 30, "触发下一次工具调用", tx=26.5, ty=23.5, color="#2b6cb0", rad=0.0)
ax.text(50, 23.6, "“看图—判断—调参”闭环\n由 AI 在对话中编排", ha="center", va="center",
        fontsize=9.5, color="#555", style="italic")

# session feeds the loop
arrow(50, 58, 50, 41.4, "在同一会话对象上就地操作", tx=50, ty=49.5, color="#1f4e79", rad=0.0)

out = os.path.join(os.path.dirname(__file__), "media", "figure2_loop.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, bbox_inches="tight", facecolor="white")
print("WROTE", out)
