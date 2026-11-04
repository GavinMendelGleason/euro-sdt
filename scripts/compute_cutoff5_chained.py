#!/usr/bin/env python3
"""Harmonised chained median index: cutoff>=5 output per Commission+judicial position."""
from __future__ import annotations
import csv, math, sqlite3, statistics
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
def fetch(i,p,m):
 op='like' if '%' in p else '='
 return db.execute(f"select year,{m} as v from institution_cohort where institution_id=? and programme {op} ? and {m} is not null order by year",(i,p)).fetchall()
# current output series
current={
 'College of Europe':fetch('college-of-europe','All programmes (promotions table)','enrolled'),
 'Harvard LL.M.':fetch('harvard','LL.M.','graduates'),
 'ENA/INSP':fetch('ecole-nationale-d-administration','Formation initiale – voie générale%','enrolled'),
 'LSE LLM':fetch('london-school-of-economics','LLM (Master of Laws)','enrolled'),
 'Cologne law':fetch('university-of-cologne','Rechtswissenschaft (Staatsexamen / 1. Prüfung)','graduates'),
}
ox=defaultdict(dict)
for p in ['BCL','MJur']:
 for r in fetch('university-of-oxford',p,'graduates'): ox[r['year']][p]=r['v']
current['Oxford BCL/MJur']=[{'year':y,'v':v['BCL']+v['MJur']} for y,v in ox.items() if 'BCL' in v and 'MJur' in v]
series={n:{r['year']:r['v'] for r in rs} for n,rs in current.items()}
for r in csv.DictReader(open('data/analysis/gating_cutoff5_outputs.csv')):
 if r['metric']=='HE qualifiers (all levels)': continue
 series.setdefault(r['institution'],{})[int(r['year'])]=float(r['value'])
# denominator
panel={int(r['year']):int(r['A_posts']) for r in csv.DictReader(open('data/denominator/elite_position_denominator_5y.csv'))}
py=sorted(panel)
def ap(y):
 for a,b in zip(py,py[1:]):
  if a<=y<=b: return panel[a]+(panel[b]-panel[a])*(y-a)/(b-a)
 return panel[py[-1]]
jud={int(r['year']):int(r['judicial_positions']) for r in csv.DictReader(open('data/denominator/judicial_positions_annual.csv'))}
den={y:ap(y)+jud[y] for y in range(2000,2026)}
rate={n:{y:v/den[y] for y,v in obs.items() if 2000<=y<=2025} for n,obs in series.items()}
growth=defaultdict(list)
for obs in rate.values():
 ys=sorted(obs)
 for a,b in zip(ys,ys[1:]):
  g=math.log(obs[b]/obs[a])/(b-a)
  for y in range(a+1,b+1): growth[y].append(g)
idx={2000:100.0}; cur=100
rows=[]
for y in range(2000,2026):
 if growth[y]: cur*=math.exp(statistics.median(growth[y]))
 idx[y]=cur
 rows.append({'year':y,'index':round(cur,2),'n_growth_series':len(growth[y]),'n_output_series':sum(1 for obs in rate.values() if y in obs)})
p=Path('data/analysis/gating_cutoff5_chained_harmonised.csv')
with p.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
fig,ax=plt.subplots(figsize=(9,5.2))
ax.plot([r['year'] for r in rows],[r['index'] for r in rows],marker='o',markersize=3,linewidth=2,color='#0072B2')
ax.axhline(100,color='#888888',linestyle='--',linewidth=.8)
for r in rows:
 if r['year'] in (2000,2005,2010,2015,2020,2025):
  ax.annotate(f"n={r['n_growth_series']}",xy=(r['year'],r['index']),xytext=(4,5),textcoords='offset points',fontsize=7)
ax.set_xlabel('Year');ax.set_ylabel('Chained median index (2000 = 100)')
fig.suptitle('Cutoff ≥5: harmonised output per Commission + judicial position',x=0.012,y=0.985,ha='left',fontsize=13,fontweight='bold')
fig.text(0.012,0.925,'Each institution’s own output measure is divided by positions; annual growth is interpolated and the median is chained. 2000 = 100.',ha='left',fontsize=7.5,color='#555')
ax.grid(axis='y',alpha=.25)
fig.tight_layout(rect=[0,0,1,0.88])
img=Path('assets/papers/methodology/gating-cutoff5-chained-harmonised.png')
fig.savefig(img,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(img.with_suffix('.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
print(p);print(img);print(rows[0],rows[-1])
