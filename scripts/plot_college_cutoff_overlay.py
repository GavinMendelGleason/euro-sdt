#!/usr/bin/env python3
"""College-of-Europe-only chained index superimposed on cutoff>=5 index."""
import csv, math, sqlite3
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
rows=db.execute("select year,enrolled from institution_cohort where institution_id='college-of-europe' and programme='All programmes (promotions table)' and enrolled is not null order by year").fetchall()
col={r['year']:r['enrolled'] for r in rows if 2000<=r['year']<=2024}
panel={int(r['year']):int(r['A_posts']) for r in csv.DictReader(open('data/denominator/elite_position_denominator_5y.csv'))}
py=sorted(panel)
def ap(y):
 for a,b in zip(py,py[1:]):
  if a<=y<=b: return panel[a]+(panel[b]-panel[a])*(y-a)/(b-a)
 return panel[py[-1]]
rate={y:v/(ap(y)+92) for y,v in col.items()}
ys=sorted(rate); idx={2000:100.0}; cur=100
for a,b in zip(ys,ys[1:]):
 g=math.log(rate[b]/rate[a])/(b-a)
 for y in range(a+1,b+1):
  cur*=math.exp(g); idx[y]=cur
comp={int(r['year']):float(r['index']) for r in csv.DictReader(open('data/analysis/gating_cutoff5_chained_harmonised.csv'))}
fig,ax=plt.subplots(figsize=(9,5.2))
ax.plot(sorted(idx),[idx[y] for y in sorted(idx)],color='#0072B2',marker='o',markersize=3,linewidth=2.2,label='College of Europe only')
ax.plot(sorted(comp),[comp[y] for y in sorted(comp)],color='#333333',marker='o',markersize=3,linewidth=2.2,label='Cutoff ≥5 composite')
ax.axhline(100,color='#999999',linestyle='--',linewidth=.8)
for series,name,color in [(idx,'College',"#0072B2"),(comp,'Composite','#333333')]:
 y=max(series); ax.annotate(f'{series[y]:.1f}',xy=(y,series[y]),xytext=(-35,6),textcoords='offset points',fontsize=8,color=color)
ax.set_xlim(1999,2026); ax.set_ylim(80,320)
ax.set_xlabel('Year'); ax.set_ylabel('Chained median index (2000 = 100)')
fig.suptitle('College of Europe vs the cutoff ≥5 composite',x=0.012,y=0.985,ha='left',fontsize=13,fontweight='bold')
fig.text(0.012,0.925,'Both divide output by Commission posts + 92 judicial positions; College uses enrolment, composite uses available output measures.',ha='left',fontsize=7.5,color='#555')
ax.grid(axis='y',alpha=.25); ax.legend(frameon=False,fontsize=9)
fig.tight_layout(rect=[0,0,1,0.88])
out=Path('assets/papers/methodology/college-vs-cutoff5-index.png')
fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
print(out);print('college2024',round(idx[max(idx)],1),'composite2024',round(comp[2024],1))
