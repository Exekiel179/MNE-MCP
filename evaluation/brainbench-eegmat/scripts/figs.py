import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.titlesize':10,'axes.titleweight':'bold','axes.titlelocation':'left'})
C={'Python':'#8c8c8c','MNE MCP':'#2b6cb0','MNE MCP + skills':'#dd6b20'}
conds=list(C)
# ---------- Figure 2
fig,ax=plt.subplots(1,3,figsize=(7.2,2.7),gridspec_kw={'width_ratios':[1.15,1,1]})
a=ax[0]
labs=['MNE MCP − Python\n(tool layer)','+ skills − MNE MCP\n(skill layer)','+ skills − Python\n(both)']
est=[2.14,-1.71,0.43]; lo=[0.60,-3.35,-1.69]; hi=[3.93,-0.42,2.57]
cols=[C['MNE MCP'],C['MNE MCP + skills'],'#555']
y=np.arange(3)[::-1]
for i in range(3):
    a.plot([lo[i],hi[i]],[y[i]]*2,color=cols[i],lw=2)
    a.plot(est[i],y[i],'o',color=cols[i],ms=7)
    (a.text(hi[i]+0.25,y[i],f'{est[i]:+.2f}',va='center',fontsize=8) if est[i]>0 else a.text(lo[i]-0.25,y[i],f'{est[i]:+.2f}'.replace('-','−'),va='center',ha='right',fontsize=8))
a.axvline(0,color='k',lw=0.8,ls='--')
a.set_yticks(y); a.set_yticklabels(labs,fontsize=8); a.set_xlim(-7.5,5.4)
a.set_xlabel('Paired score difference (points)\nwith task-family cluster 95% CI'); a.set_title('A  Layer effects')
b=ax[1]
lv=['1.0\n(40)','1.5\n(86)','2.0\n(55)']
M={'Python':[97.50,93.72,77.27],'MNE MCP':[97.50,97.05,79.09],'MNE MCP + skills':[97.50,95.97,75.14]}
x=np.arange(3); w=0.26
for k,c in enumerate(conds):
    b.bar(x+(k-1)*w,M[c],w,color=C[c],label=c)
b.set_ylim(70,100); b.set_xticks(x); b.set_xticklabels(lv,fontsize=8); b.set_xlabel('Difficulty level (tasks)'); b.set_ylabel('Mean score'); b.set_title('B  By difficulty')
c=ax[2]
tok=[66582,127745,329597]; tm=[129.6,145.1,256.8]
c.bar(np.arange(3),np.array(tok)/1000,color=[C[k] for k in conds])
for i,v in enumerate(tok): c.text(i,v/1000+6,f'{v/1000:.0f}k',ha='center',fontsize=8)
for i,v in enumerate(tm): c.text(i,12,f'{v:.0f} s',ha='center',fontsize=7.5,color='white')
c.set_xticks(range(3)); c.set_xticklabels(['Python','MCP','MCP +\nskills'],fontsize=8); c.set_ylabel('Tokens per full-score task (k)'); c.set_title('C  Cost'); c.set_ylim(0,370)
h,l=b.get_legend_handles_labels(); fig.legend(h,l,loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(0.5,-0.04))
fig.tight_layout(rect=(0,0.07,1,1)); fig.savefig('fig2_en.png',dpi=300,bbox_inches='tight')
# ---------- Figure 3
fig=plt.figure(figsize=(7.2,4.6)); gs=fig.add_gridspec(2,2,height_ratios=[1,1.15],hspace=0.75,wspace=0.95)
a=fig.add_subplot(gs[0,:])
parts=['Session, loading & info','Structured analysis tools','mne_run_code']
pc=['#cbd5e0','#2c7a7b','#2b6cb0']
data={'MNE MCP':[503,27,345],'MNE MCP + skills':[514,2,583]}
for i,(k,v) in enumerate(data.items()):
    left=0
    for j,val in enumerate(v):
        a.barh(i,val,left=left,color=pc[j],label=parts[j] if i==0 else None,height=0.55)
        a.text(left+val/2,i,str(val) if val>40 else '',ha='center',va='center',fontsize=8,color='white' if j else 'black')
        left+=val
    a.text(left+10,i,f'{sum(v)} calls · run_code {v[2]/sum(v)*100:.1f}%',va='center',fontsize=8)
    if v[1]<40: a.annotate(str(v[1]),xy=(v[0]+v[1]/2,i+0.28),xytext=(v[0]+v[1]/2,i+0.45),ha='center',fontsize=7.5,color=pc[1],arrowprops=dict(arrowstyle='-',color=pc[1],lw=0.6))
a.set_yticks([0,1]); a.set_yticklabels(list(data)); a.invert_yaxis(); a.set_xlim(0,1400); a.set_xlabel('MCP tool calls over 181 tasks')
a.legend(loc='upper center',ncol=3,frameon=False,fontsize=8,bbox_to_anchor=(0.5,-0.32)); a.set_title('A  Composition of MCP calls')
b=fig.add_subplot(gs[1,0])
beh=['Read skill files','Read review skill','Review run in code','Wrote review files','Unrequested sensitivity\nanalysis']
val=[181,179,113,108,24]
b.barh(range(5),val,color=C['MNE MCP + skills']); b.invert_yaxis()
for i,v in enumerate(val): b.text(v+3,i,str(v),va='center',fontsize=8)
b.set_yticks(range(5)); b.set_yticklabels(beh,fontsize=8); b.set_xlim(0,215); b.set_xlabel('Tasks (of 181), skills condition'); b.set_title('B  Skill-driven behaviour')
c=fig.add_subplot(gs[1,1])
src=['Welch window\n(2 s skill example)','Other numerical','Interpretation','Missing item','Timeout']
t_up=[0,3,5,0,0]; t_dn=[0,1,1,0,0]; s_up=[0,0,1,0,0]; s_dn=[6,0,2,1,1]
yy=np.arange(5); hh=0.36
c.barh(yy-hh/2,t_up,hh,color=C['MNE MCP'],label='MCP vs Python'); c.barh(yy-hh/2,[-v for v in t_dn],hh,color=C['MNE MCP'])
c.barh(yy+hh/2,s_up,hh,color=C['MNE MCP + skills'],label='Skills vs MCP'); c.barh(yy+hh/2,[-v for v in s_dn],hh,color=C['MNE MCP + skills'])
c.axvline(0,color='k',lw=0.8); c.invert_yaxis(); c.set_yticks(yy); c.set_yticklabels(src,fontsize=8); c.set_xlim(-7,6.5)
c.set_xticks([-6,-4,-2,0,2,4,6]); c.set_xticklabels(['6','4','2','0','2','4','6'])
c.set_xlabel('← tasks declined     tasks improved →'); c.legend(frameon=False,fontsize=8,loc='upper center',handlelength=1.2,ncol=2,bbox_to_anchor=(0.5,-0.3)); c.set_title('C  Sources of score differences')
fig.savefig('fig3_en.png',dpi=300,bbox_inches='tight')
