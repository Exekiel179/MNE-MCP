# -*- coding: utf-8 -*-
"""Generate Figure 1: MNE-MCP architecture & data-flow diagram."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# Try a Chinese-capable font; fall back gracefully.
for fam in ["Microsoft YaHei", "SimHei", "Source Han Sans SC", "DejaVu Sans"]:
    try:
        matplotlib.rcParams["font.sans-serif"] = [fam]
        break
    except Exception:
        continue
matplotlib.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(9.2, 4.6), dpi=200)
ax.set_xlim(0, 100)
ax.set_ylim(0, 60)
ax.axis("off")

def box(x, y, w, h, text, fc, ec="#33414e", fs=10, tc="#10202b"):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=2",
                       linewidth=1.4, edgecolor=ec, facecolor=fc)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, wrap=True)

def arrow(x1, y1, x2, y2, text="", color="#2b6cb0", fs=8.5, rad=0.0, tx=None, ty=None):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                        linewidth=1.6, color=color,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if text:
        ax.text(tx if tx is not None else (x1 + x2) / 2,
                ty if ty is not None else (y1 + y2) / 2 + 2.2,
                text, ha="center", va="center", fontsize=fs, color=color)

# Left: user + Claude Code (MCP host)
box(2, 36, 26, 12, "用户（自然语言）\nUser · natural language", "#e8f1fb", fs=10)
box(2, 12, 26, 16, "Claude Code / opencode\n（MCP 宿主）\n读取并解读 PNG", "#d6e8fb", fs=10)

# Right: MNE-MCP server
box(56, 8, 40, 44, "", "#f3f7ee", ec="#6b8e3d")
ax.text(76, 48.5, "MNE-MCP 服务器（FastMCP）", ha="center", va="center",
        fontsize=11, color="#3f5a1f", fontweight="bold")
box(60, 35.5, 32, 9, "常驻会话 Session\nraw · epochs · evoked · ica …", "#eaf3da", fs=9)
box(60, 24.5, 32, 8.5, "operations · 调用 MNE-Python", "#eaf3da", fs=9)
box(60, 13.5, 32, 8.5, "figures · 出图存 PNG（Agg）", "#eaf3da", fs=9)

# Bottom: results
box(56, -0.5, 40, 6.5, "results/*.png  +  等效 MNE 代码", "#fff4e0", ec="#c08a2d", fs=9.5)

# Arrows
arrow(15, 36, 15, 28.2, "")  # user -> claude
arrow(28.5, 22, 55.5, 30, "调用 38 个工具 / run_code", tx=42, ty=33, rad=0.08)
arrow(55.5, 24, 28.5, 18, "返回 Markdown + 图路径", tx=42, ty=12.5, rad=0.08, color="#6b8e3d")
arrow(76, 13.0, 76, 6.2, "")  # server -> results
arrow(56, 3, 28.5, 14.5, "读取 PNG 解读", tx=40, ty=6.0, rad=-0.18, color="#c08a2d")

out = os.path.join(os.path.dirname(__file__), "media", "figure1_architecture.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, bbox_inches="tight", facecolor="white")
print("WROTE", out)
