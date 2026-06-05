# -*- coding: utf-8 -*-
"""Figure 3: the grill -> analyze -> critic three-phase skill workflow (§2.4)."""
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

fig, ax = plt.subplots(figsize=(9.4, 5.4), dpi=200)
ax.set_xlim(0, 100)
ax.set_ylim(0, 62)
ax.axis("off")


def box(x, y, w, h, fc, ec, title="", body="", t_fs=10.5, b_fs=8.6,
        tc="#10202b", dashed=False):
    style = "round,pad=0.6,rounding_size=2"
    p = FancyBboxPatch((x, y), w, h, boxstyle=style, linewidth=1.6,
                       edgecolor=ec, facecolor=fc,
                       linestyle=("--" if dashed else "-"))
    ax.add_patch(p)
    if title:
        ax.text(x + w / 2, y + h - 3.2, title, ha="center", va="center",
                fontsize=t_fs, color=ec, fontweight="bold")
    if body:
        ax.text(x + w / 2, y + (h - 6.4) / 2, body, ha="center", va="center",
                fontsize=b_fs, color=tc, linespacing=1.45)


def arrow(x1, y1, x2, y2, text="", color="#2b6cb0", fs=8.6, rad=0.0, tx=None, ty=None,
          dashed=False):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=15,
                        linewidth=1.7, color=color,
                        linestyle=("--" if dashed else "-"),
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if text:
        ax.text(tx if tx is not None else (x1 + x2) / 2,
                ty if ty is not None else (y1 + y2) / 2, text,
                ha="center", va="center", fontsize=fs, color=color)


# Phase 1: GRILL
box(2, 30, 29, 26, "#eef5fb", "#1f4e79",
    title="① 质询 GRILL",
    body="分析之前以怀疑论追问：\n· 设计与假设是否明确\n· 样本量与独立性\n· 参数依据(滤波/基线/阈值)\n· 多重比较范围与校正\n· 方法前提是否满足\n→ 显式化研究者自由度")

# Phase 2: ANALYZE
box(35.5, 36, 23, 14, "#f3f7ee", "#6b8e3d",
    title="② 分析 ANALYZE",
    body="前提澄清后\n调用 MNE-MCP 工具\n在常驻会话上执行")

# Phase 3: CRITIC (isolated subagent)
box(63, 30, 35, 26, "#fdf0f0", "#b03a3a",
    title="③ 审查 CRITIC",
    body="独立子代理 · 隔离上下文 · 中立视角\n核对常见效度陷阱：\n· 相对功率 / 成分数据\n· 双重浸取(循环分析)\n· 1/f 非周期混淆\n· 伪重复(单被试多分段)\n· 小样本正态性 · 多重比较")

arrow(31, 43, 35.5, 43, "", color="#33414e")
arrow(58.5, 43, 63, 43, "", color="#33414e")

# Verdict
box(63, 16, 35, 10, "#fff7e6", "#c08a2d",
    title="裁定  PASS / REVISE / BLOCK",
    body="PASS 通过 · REVISE 需修订 · BLOCK 阻断", t_fs=10, b_fs=8.4)
arrow(80.5, 30, 80.5, 26.2, "", color="#b03a3a")

# writeup (only PASS)
box(63, 2, 35, 10, "#eef5fb", "#1f4e79",
    title="mne-writeup",
    body="仅将 PASS 结果整理为\n规范的方法与结果文本", t_fs=10, b_fs=8.4)
arrow(80.5, 16, 80.5, 12.2, "PASS", tx=86, ty=14.1, color="#2f7d32")

# REVISE/BLOCK feedback loop back to analyze/grill
arrow(63, 18.5, 47, 36, "REVISE / BLOCK\n退回修订", tx=46, ty=27, color="#b03a3a",
      rad=-0.25, dashed=True)

ax.text(50, 59.2, "怀疑式分析技能：先质询 → 再分析 → 后审查（grill → analyze → critic）",
        ha="center", va="center", fontsize=11, color="#222", fontweight="bold")

out = os.path.join(os.path.dirname(__file__), "media", "figure3_skills.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, bbox_inches="tight", facecolor="white")
print("WROTE", out)
