import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
plt.rcParams.update({'font.family': 'Liberation Sans', 'font.size': 7.5})

INK = '#1f2933'; GREY = '#7b8794'; LIGHT = '#f5f7fa'
BLUE = '#2b6cb0'; BLUE_L = '#e6eef8'; TEAL = '#2c7a7b'; TEAL_L = '#e3f1f1'
ORANGE = '#dd6b20'; ORANGE_L = '#fcefe5'

fig = plt.figure(figsize=(7.2, 4.9))
axA = fig.add_axes([0.0, 0.33, 1.0, 0.67]); axA.set_xlim(0, 100); axA.set_ylim(0, 60); axA.axis('off')
axB = fig.add_axes([0.0, 0.0, 1.0, 0.31]); axB.set_xlim(0, 100); axB.set_ylim(0, 28); axB.axis('off')

def box(ax, x, y, w, h, fc, ec, lw=0.9, ls='-', r=0.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0,rounding_size={r}', fc=fc, ec=ec, lw=lw, ls=ls))
def title(ax, x, y, t, c=INK, s=8.2):
    ax.text(x, y, t, ha='center', va='center', fontsize=s, fontweight='bold', color=c)
def body(ax, x, y, t, c=INK, s=7, ha='center'):
    ax.text(x, y, t, ha=ha, va='center', fontsize=s, color=c, linespacing=1.35)
def arrow(ax, p, q, c=GREY, rad=0.0, lw=1.0, both=False):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle='<|-|>' if both else '-|>', mutation_scale=8,
                                 color=c, lw=lw, connectionstyle=f'arc3,rad={rad}', shrinkA=0, shrinkB=0))
def step(ax, x, y, n):
    ax.add_patch(plt.Circle((x, y), 1.35, fc=INK, ec='none'))
    ax.text(x, y, str(n), ha='center', va='center', color='white', fontsize=6.5, fontweight='bold')

# ---------------- Panel A
axA.text(0.8, 58.6, 'A', fontsize=10, fontweight='bold', va='center')
# side regions
axA.add_patch(Rectangle((2, 0.6), 27, 54.4, fc='none', ec=GREY, lw=0.8, ls=(0, (3, 2))))
axA.text(15.5, 53.2, 'Agent side', ha='center', va='center', fontsize=7, color=GREY, style='italic')
axA.add_patch(Rectangle((34, 0.6), 64, 54.4, fc='none', ec=GREY, lw=0.8, ls=(0, (3, 2))))
axA.text(66, 53.2, 'MNE-MCP server (one process)', ha='center', va='center', fontsize=7, color=GREY, style='italic')

# agent
box(axA, 4.5, 27, 22, 23, LIGHT, INK)
title(axA, 15.5, 46.5, 'Coding agent (MCP host)')
body(axA, 15.5, 37, 'LLM policy\nselects the next operation\nand its arguments from the\nrequest, prior observations\nand loaded knowledge')
box(axA, 4.5, 5, 22, 17, ORANGE_L, ORANGE)
title(axA, 15.5, 18.6, 'Knowledge', ORANGE)
body(axA, 15.5, 11.5, '14 domain skills\nworkflows, conventions,\nmethodological review')
arrow(axA, (15.5, 22), (15.5, 27), c=ORANGE)
axA.text(16.6, 24.5, 'context', fontsize=6.5, color=ORANGE, va='center')

# actions
box(axA, 37, 27, 27, 23, BLUE_L, BLUE)
title(axA, 50.5, 46.5, 'Actions', BLUE)
body(axA, 50.5, 41.6, '40 structured tools  +  mne_run_code')
axA.plot([39, 62], [38.8, 38.8], color=BLUE, lw=0.5, alpha=0.6)
body(axA, 50.5, 33.4, 'Schema validation of arguments\nPreconditions on session state\nSingle execution lock')
# operations
box(axA, 37, 5, 27, 17, LIGHT, INK)
title(axA, 50.5, 18.6, 'MNE-Python operations')
body(axA, 50.5, 11.5, 'filtering · ICA · epochs · ERP\nPSD · TFR · connectivity\ndecoding · source estimation')
arrow(axA, (50.5, 27), (50.5, 22), c=BLUE)
axA.text(51.6, 24.5, 'execute', fontsize=6.5, color=BLUE, va='center')

# state
box(axA, 69, 27, 27, 23, TEAL_L, TEAL)
title(axA, 82.5, 46.5, 'State', TEAL)
body(axA, 82.5, 37.2, 'Persistent session of named objects\nraw · epochs · evoked · TFR\nconnectivity · decoding results\nwith processing history')
# observation
box(axA, 69, 5, 27, 17, TEAL_L, TEAL, ls=(0, (4, 1.5)))
title(axA, 82.5, 18.6, 'Observation', TEAL)
body(axA, 82.5, 11.5, 'object summary · figures\nequivalent Python code\n(record of the analysis path)')
arrow(axA, (64, 13.5), (69, 13.5), c=GREY)
arrow(axA, (64, 36), (69, 36), c=TEAL, both=True)
axA.text(66.5, 38.2, 'read/\nwrite', fontsize=6.2, color=TEAL, ha='center', va='bottom', linespacing=1.1)

# main loop arrows
arrow(axA, (26.5, 42), (37, 42), c=INK, lw=1.1)
axA.text(31.75, 44.2, 'tool call', fontsize=6.5, ha='center', va='bottom')
axA.plot([82.5, 82.5, 32, 32], [5, 3.4, 3.4, 31], color=INK, lw=1.1)
arrow(axA, (32, 31), (26.5, 31), c=INK, lw=1.1)
axA.text(57, 3.4, 'observation returned to the agent', fontsize=6.5, ha='center', va='center',
         bbox=dict(fc='white', ec='none', pad=0.6))
step(axA, 31.75, 39.8, 1); step(axA, 48, 24.5, 2); step(axA, 66.5, 33.5, 3); step(axA, 66.5, 11.2, 4); step(axA, 32, 17, 5)

# ---------------- Panel B
axB.text(0.8, 26.5, 'B', fontsize=10, fontweight='bold', va='center')
cols = ['Code execution', 'Structured tools\n(actions)', 'Persistent session\n(state, observation)', 'Domain skills\n(knowledge)']
ccol = [INK, BLUE, TEAL, ORANGE]
rows = [('Python', [1, 0, 0, 0]), ('MNE MCP', [1, 1, 1, 0]), ('MNE MCP + skills', [1, 1, 1, 1])]
xs = [36, 52, 68, 84]
for x, c, col in zip(xs, cols, ccol):
    axB.text(x, 23.2, c, ha='center', va='center', fontsize=7, color=col, fontweight='bold', linespacing=1.15)
axB.plot([4, 96], [19.6, 19.6], color=INK, lw=0.7)
for i, (name, v) in enumerate(rows):
    y = 15.5 - i * 5.2
    axB.text(5, y, name, ha='left', va='center', fontsize=7.5, fontweight='bold')
    for x, on, col in zip(xs, v, ccol):
        axB.scatter([x], [y], s=70, c=[col if on else 'white'], edgecolors=[col if on else GREY], linewidths=0.9, zorder=3)
axB.plot([4, 96], [2.6, 2.6], color=INK, lw=0.7)
axB.text(96, 0.8, 'Contrast 1: MNE MCP − Python (actions and state added together)    Contrast 2: + skills − MNE MCP (knowledge only)',
         ha='right', va='center', fontsize=6.3, color=GREY)

fig.savefig('fig1_en.png', dpi=300, bbox_inches='tight', facecolor='white')
fig.savefig('fig1_en.pdf', bbox_inches='tight', facecolor='white')
