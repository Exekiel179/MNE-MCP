# -*- coding: utf-8 -*-
"""Figure 5: gallery of the real motor-imagery case study (§3.4).
Panels are the actual MNE-MCP archived outputs (mne_result/) for PhysioNet
eegbci S001, runs 4/8/12 (left vs right fist motor imagery). Sources live in
media/casestudy/ so the composite regenerates from in-repo files.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

for fam in ["Microsoft YaHei", "SimHei", "Source Han Sans SC", "DejaVu Sans"]:
    try:
        matplotlib.rcParams["font.sans-serif"] = [fam]
        break
    except Exception:
        continue
matplotlib.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(__file__)
CS = os.path.join(HERE, "media", "casestudy")

panels = [
    ("01_psd_raw.png", "(a) 原始 PSD：可见 ~10 Hz mu 与 60 Hz 工频峰"),
    ("04_psd_filtered.png", "(b) 滤波(1–40 Hz)+陷波(60 Hz)+平均参考后"),
    ("05_ica_components.png", "(c) ICA 成分地形（IC0 = 额部眨眼，已剔除）"),
    ("08_evoked_left_joint.png", "(d) 左手想象诱发响应：线索瞬态峰 ~0.29 s"),
    ("10_erp_image_C3.png", "(e) C3 单试次 ERP 图像（试次 × 时间）"),
    ("13_csp_patterns.png", "(f) CSP 空间模式：聚焦双侧感觉运动区"),
]

fig, axes = plt.subplots(2, 3, figsize=(10.2, 6.4), dpi=200)
for ax, (fn, cap) in zip(axes.ravel(), panels):
    img = mpimg.imread(os.path.join(CS, fn))
    ax.imshow(img)
    ax.set_title(cap, fontsize=9.2, color="#222", pad=4)
    ax.axis("off")

fig.suptitle("运动想象 EEG 案例（PhysioNet eegbci S001）经 MNE-MCP 的端到端产物",
             fontsize=11.5, fontweight="bold", y=0.995)
fig.tight_layout(rect=[0, 0, 1, 0.97])
out = os.path.join(CS, "..", "figure5_casestudy.png")
fig.savefig(out, bbox_inches="tight", facecolor="white")
print("WROTE", os.path.normpath(out))
