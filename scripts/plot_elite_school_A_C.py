#!/usr/bin/env python3
"""Paper figure: A and C denominator indices only."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows=list(csv.DictReader(open('data/denominator/elite_school_denominator_index_5y.csv')))
years=[int(r['year']) for r in rows]
A=[float(r['index_A']) for r in rows]
C=[float(r['index_C']) for r in rows]

fig, ax=plt.subplots(figsize=(9,5.2))
ax.plot(years,A,color='#0072B2',marker='o',markersize=4,linewidth=2.2,label='A: all included gating institutions / Commission posts')
ax.plot(years,C,color='#009E73',marker='o',markersize=4,linewidth=2.2,label='B: all included gating institutions / listed-board seats')
ax.axhline(100,color='#999999',linewidth=.8,linestyle='--')
ax.annotate(f'{A[-1]:.0f}',xy=(years[-1],A[-1]),xytext=(-28,-14),textcoords='offset points',color='#0072B2',fontsize=9)
ax.annotate(f'{C[-1]:.0f}',xy=(years[-1],C[-1]),xytext=(-28,8),textcoords='offset points',color='#009E73',fontsize=9)
ax.set_xlim(1988,2027); ax.set_ylim(70,220)
ax.set_xticks([1990,1995,2000,2005,2010,2015,2020,2025])
ax.set_yticks([70,80,100,120,140,160,180,200,220])
ax.set_xlabel('Year')
ax.set_ylabel('Chained median index (1990 = 100)')
fig.suptitle('Gating-institution programme output per Commission post and board seat',x=0.012,y=0.985,ha='left',fontsize=14,fontweight='bold')
fig.text(0.012,0.915,'Median chained output across programme measures from all included gating institutions (College of Europe, Harvard, Polytechnique, Oxford, Cologne, LSE, ENA/INSP), divided by each denominator.',ha='left',fontsize=8,color='#555')
ax.grid(axis='y',alpha=.25)
ax.legend(loc='upper left',fontsize=9,frameon=False)
fig.tight_layout(rect=[0,0,1,0.86])
out=Path('assets/papers/methodology/elite-school-denominator-A-B.png')
fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white')
fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
plt.close(fig);print(out)
