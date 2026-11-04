#!/usr/bin/env python3
"""Simple bar chart: share with core gating-institution education."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows=list(csv.DictReader(open('data/analysis/gating_share_by_group.csv')))
labels=[r['group'] for r in rows]
vals=[float(r['core_pct']) for r in rows]
counts=[f"{r['core_count']}/{r['denominator']}" for r in rows]

fig,ax=plt.subplots(figsize=(8,4.8))
bars=ax.bar(labels,vals,color=['#0072B2','#009E73','#D55E00'],width=.6)
for b,v,c in zip(bars,vals,counts):
    ax.text(b.get_x()+b.get_width()/2,v+1,f'{c}\n{round(v+1e-9,1):.1f}%',ha='center',va='bottom',fontsize=9)
ax.set_ylim(0,40); ax.set_ylabel('Percent of group')
fig.suptitle('Share educated at a core gating institution',x=0.012,y=0.975,ha='left',fontsize=14,fontweight='bold')
fig.text(0.012,0.91,'Core set = 10 institutions in Table 1. Denominator = all people in the group.',ha='left',fontsize=8,color='#555')
ax.grid(axis='y',alpha=.25)
fig.tight_layout(rect=[0,0,1,0.86])
out=Path('assets/papers/methodology/gating-share-simple.png')
fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white')
fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
plt.close(fig);print(out)
