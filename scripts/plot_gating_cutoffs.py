#!/usr/bin/env python3
"""Cutoff membership and output coverage charts."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows=list(csv.DictReader(open('data/analysis/gating_cutoff_membership.csv')))
rows.sort(key=lambda r:int(r['mentions']), reverse=True)
# membership chart top 25
sub=rows[:25]
fig,ax=plt.subplots(figsize=(9,7))
colors=['#0072B2' if r['current_output']!='none' else '#D55E00' for r in sub]
ax.barh(range(len(sub)),[int(r['mentions']) for r in sub],color=colors)
ax.set_yticks(range(len(sub))); ax.set_yticklabels([r['institution'] for r in sub],fontsize=8)
ax.invert_yaxis(); ax.set_xlabel('Commission + DG/DDG + Judiciary mentions')
for cut in (5,4,3): ax.axvline(cut,color='#555',linestyle='--',linewidth=.8)
fig.suptitle('Cutoff membership by elite-position mentions',x=0.012,y=0.985,ha='left',fontsize=13,fontweight='bold')
fig.text(0.012,0.945,'Blue: current output series exists. Orange: missing output. Dashed lines: cutoffs 5, 4, 3.',ha='left',fontsize=8,color='#555')
ax.grid(axis='x',alpha=.2)
fig.tight_layout(rect=[0,0,1,0.90])
out=Path('assets/papers/methodology/gating-cutoff-membership.png')
fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)

# coverage chart
fig,ax=plt.subplots(figsize=(8,4.8))
cuts=[5,4,3]
covered=[]; missing=[]; pct=[]
for c in cuts:
 sel=[r for r in rows if int(r['mentions'])>=c]
 cov=sum(1 for r in sel if r['current_output']!='none'); mis=len(sel)-cov
 covered.append(cov); missing.append(mis); pct.append(100*sum(int(r['mentions']) for r in sel if r['current_output']!='none')/sum(int(r['mentions']) for r in sel))
x=range(len(cuts))
ax.bar(x,covered,color='#0072B2',label='With output series')
ax.bar(x,missing,bottom=covered,color='#D55E00',label='Missing output')
for i,(c,m,p) in enumerate(zip(covered,missing,pct)):
 ax.text(i,c+m+1,f'{c} covered / {m} missing\n{p:.1f}% of mentions covered',ha='center',va='bottom',fontsize=8)
ax.set_xticks(list(x)); ax.set_xticklabels([f'≥{c}' for c in cuts]); ax.set_ylabel('Institutions')
ax.set_ylim(0,48); ax.legend(frameon=False,fontsize=8)
fig.suptitle('Output-data coverage of cutoff sets',x=0.012,y=0.985,ha='left',fontsize=13,fontweight='bold')
fig.text(0.012,0.925,'Cutoff by total mentions in Commission + DG/DDG + Judiciary.',ha='left',fontsize=8,color='#555')
ax.grid(axis='y',alpha=.2)
fig.tight_layout(rect=[0,0,1,0.88])
out2=Path('assets/papers/methodology/gating-cutoff-coverage.png')
fig.savefig(out2,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(out2.with_suffix('.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
print(out);print(out2)
