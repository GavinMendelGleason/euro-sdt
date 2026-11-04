#!/usr/bin/env python3
"""Aggregate cutoff>=5 output divided by Commission + judicial positions by year."""
from __future__ import annotations
import csv, sqlite3, statistics
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Current six output series, using their existing metric (not a harmonised degree total)
db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
def fetch(i,p,m):
 op='like' if '%' in p else '='
 return db.execute(f"select year,{m} as v from institution_cohort where institution_id=? and programme {op} ? and {m} is not null order by year",(i,p)).fetchall()
current={
 'College of Europe':fetch('college-of-europe','All programmes (promotions table)','enrolled'),
 'Harvard LL.M.':fetch('harvard','LL.M.','graduates'),
 'ENA/INSP':fetch('ecole-nationale-d-administration','Formation initiale – voie générale%','enrolled'),
 'Oxford BCL/MJur':fetch('university-of-oxford','BCL','graduates'),
 'LSE LLM':fetch('london-school-of-economics','LLM (Master of Laws)','enrolled'),
 'Cologne law':fetch('university-of-cologne','Rechtswissenschaft (Staatsexamen / 1. Prüfung)','graduates'),
}
# Oxford total BCL+MJur
ox=defaultdict(dict)
for p in ['BCL','MJur']:
 for r in fetch('university-of-oxford',p,'graduates'): ox[r['year']][p]=r['v']
current['Oxford BCL/MJur']=[{'year':y,'v':v['BCL']+v['MJur']} for y,v in ox.items() if 'BCL' in v and 'MJur' in v]
# Add current outputs by year
by=defaultdict(float); contrib=defaultdict(set); metrics={}
for name,rs in current.items():
 for r in rs:
  if 2000<=r['year']<=2025:
   by[r['year']]+=r['v']; contrib[r['year']].add(name); metrics[name]='current mixed'
# cutoff5 partial outputs; exclude HESA qualifiers to avoid double counting Cambridge degree series
for r in csv.DictReader(open('data/analysis/gating_cutoff5_outputs.csv')):
 if r['metric']=='HE qualifiers (all levels)': continue
 y=int(r['year'])
 if 2000<=y<=2025:
  by[y]+=float(r['value']); contrib[y].add(r['institution'])

# Commission posts from 5y panel, interpolate yearly
panel={int(r['year']):int(r['A_posts']) for r in csv.DictReader(open('data/denominator/elite_position_denominator_5y.csv'))}
years=sorted(panel)
def interp(y):
 for a,b in zip(years,years[1:]):
  if a<=y<=b: return panel[a]+(panel[b]-panel[a])*(y-a)/(b-a)
 return panel[years[-1]]
JUD=92
out=[]
for y in sorted(by):
 den=interp(y)+JUD
 out.append({'year':y,'aggregate_output':round(by[y],1),'contributing_institutions':len(contrib[y]),'commission_posts':round(interp(y),1),'judicial_positions':JUD,'denominator':round(den,1),'output_per_1000_positions':round(1000*by[y]/den,2)})
p=Path('data/analysis/gating_cutoff5_output_per_position.csv');p.parent.mkdir(exist_ok=True)
with p.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
fig,ax=plt.subplots(figsize=(9,5.2))
ax.plot([r['year'] for r in out],[r['output_per_1000_positions'] for r in out],marker='o',markersize=3,linewidth=2,color='#0072B2')
for r in out:
 if r['year'] in (2000,2005,2010,2015,2020,2025):
  ax.annotate(f"n={r['contributing_institutions']}",xy=(r['year'],r['output_per_1000_positions']),xytext=(4,5),textcoords='offset points',fontsize=7)
ax.set_xlabel('Year');ax.set_ylabel('Aggregate output per 1,000 Commission + judicial positions')
fig.suptitle('Cutoff ≥5: aggregate output / Commission + judiciary positions',x=0.012,y=0.985,ha='left',fontsize=13,fontweight='bold')
fig.text(0.012,0.925,'Numerator: sum of available institutional output; measures differ. denominator: Commission posts (interpolated) + 92 judicial positions (constant).',ha='left',fontsize=7.5,color='#555')
ax.grid(axis='y',alpha=.25)
fig.tight_layout(rect=[0,0,1,0.88])
img=Path('assets/papers/methodology/gating-cutoff5-output-per-position.png')
fig.savefig(img,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(img.with_suffix('.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
print(p);print(img);print(out[:3]);print(out[-3:])
