#!/usr/bin/env python3
"""Balanced 5-institution aggregate output per Commission+judicial positions, 2010-2024."""
import csv, sqlite3
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
def fetch(i,p,m):
 op='like' if '%' in p else '='
 return db.execute(f"select year,{m} as v from institution_cohort where institution_id=? and programme {op} ? and {m} is not null order by year",(i,p)).fetchall()
series={
 'College of Europe':{r['year']:r['v'] for r in fetch('college-of-europe','All programmes (promotions table)','enrolled')},
 'Harvard LL.M.':{r['year']:r['v'] for r in fetch('harvard','LL.M.','graduates')},
 'Cologne law':{r['year']:r['v'] for r in fetch('university-of-cologne','Rechtswissenschaft (Staatsexamen / 1. Prüfung)','graduates')},
}
for r in csv.DictReader(open('data/analysis/gating_cutoff5_outputs.csv')):
 if r['institution'] in ('stockholm-university','university-of-tartu') and r['metric']!='HE qualifiers (all levels)':
  series.setdefault(r['institution'],{})[int(r['year'])]=float(r['value'])
panel={int(r['year']):int(r['A_posts']) for r in csv.DictReader(open('data/denominator/elite_position_denominator_5y.csv'))}
jud={int(r['year']):int(r['judicial_positions']) for r in csv.DictReader(open('data/denominator/judicial_positions_annual.csv'))}
py=sorted(panel)
def ap(y):
 for a,b in zip(py,py[1:]):
  if a<=y<=b:return panel[a]+(panel[b]-panel[a])*(y-a)/(b-a)
 return panel[py[-1]]
rows=[]
for y in range(2010,2025):
 vals=[obs.get(y) for obs in series.values()]
 if any(v is None for v in vals): raise SystemExit(f'missing {y}')
 den=ap(y)+jud[y]
 rows.append({'year':y,'aggregate_output':sum(vals),'n_institutions':len(vals),'commission_posts':round(ap(y),1),'judicial_positions':jud[y],'denominator':round(den,1),'output_per_1000_positions':round(1000*sum(vals)/den,2)})
p=Path('data/analysis/gating_cutoff5_balanced_output_per_position.csv')
with p.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
fig,ax=plt.subplots(figsize=(9,5.2))
ax.plot([r['year'] for r in rows],[r['output_per_1000_positions'] for r in rows],marker='o',markersize=3,linewidth=2,color='#0072B2')
ax.set_xlabel('Year');ax.set_ylabel('Aggregate output per 1,000 Commission + judicial positions')
fig.suptitle('Balanced 5-institution aggregate output per position',x=0.012,y=0.985,ha='left',fontsize=13,fontweight='bold')
fig.text(0.012,0.925,'College of Europe, Harvard, Cologne, Stockholm and Tartu; fixed panel, 2010–2024. Measures still differ.',ha='left',fontsize=7.5,color='#555')
ax.grid(axis='y',alpha=.25)
fig.tight_layout(rect=[0,0,1,0.88])
img=Path('assets/papers/methodology/gating-cutoff5-balanced-per-position.png')
fig.savefig(img,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(img.with_suffix('.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
print(p);print(img);print(rows[0],rows[-1])
