#!/usr/bin/env python3
"""Six-institution balanced panel with Bocconi and LUISS, 2001-2024."""
import csv, sqlite3
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
def fetch(i,p,m):
 op='like' if '%' in p else '='
 return db.execute(f"select year,{m} as v from institution_cohort where institution_id=? and programme {op} ? and {m} is not null order by year",(i,p)).fetchall()
col={r['year']:r['v'] for r in fetch('college-of-europe','All programmes (promotions table)','enrolled')}
har={r['year']:r['v'] for r in fetch('harvard','LL.M.','graduates')}
# Stockholm and Georgetown from 1990 panel CSV
old={int(r['year']):r for r in csv.DictReader(open('data/analysis/gating_balanced_1990_panel.csv'))}
boc=dict(zip(range(2001,2025),[2144,2210,2468,4591,4422,3391,4063,4221,3597,4047,4083,4267,4226,4377,4370,4618,4505,4524,4717,4780,4741,4681,4801,5025]))
luiss=dict(zip(range(2001,2025),[844,826,876,1425,1516,1222,1205,1596,1732,2054,2062,2125,2240,2325,2131,2332,2394,2612,2747,3060,3202,3090,3282,3226]))
panel={int(r['year']):int(r['A_posts']) for r in csv.DictReader(open('data/denominator/elite_position_denominator_5y.csv'))}
jud={int(r['year']):int(r['judicial_positions']) for r in csv.DictReader(open('data/denominator/judicial_positions_annual.csv'))}
py=sorted(panel)
def ap(y):
 for a,b in zip(py,py[1:]):
  if a<=y<=b:return panel[a]+(panel[b]-panel[a])*(y-a)/(b-a)
 return panel[py[-1]]
rows=[]
for y in range(2001,2025):
 vals=[col[y],har[y],int(old[y]['Stockholm']),int(old[y]['Georgetown']),boc[y],luiss[y]]
 den=ap(y)+jud[y]
 rows.append({'year':y,'College':vals[0],'Harvard':vals[1],'Stockholm':vals[2],'Georgetown':vals[3],'Bocconi':vals[4],'LUISS':vals[5],'aggregate_output':sum(vals),'commission_posts':round(ap(y),1),'judicial_positions':jud[y],'per_1000_positions':round(1000*sum(vals)/den,2)})
p=Path('data/analysis/gating_balanced_2001_more_europe.csv')
with p.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
fig,ax=plt.subplots(figsize=(9,5.2))
ax.plot([r['year'] for r in rows],[r['per_1000_positions'] for r in rows],color='#0072B2',marker='o',markersize=3,linewidth=2)
ax.set_xlabel('Year');ax.set_ylabel('Aggregate output per 1,000 Commission + judicial positions')
fig.suptitle('Balanced six-institution output per position, 2001–2024',x=0.012,y=0.985,ha='left',fontsize=13,fontweight='bold')
fig.text(0.012,0.925,'College of Europe, Harvard, Stockholm, Georgetown, Bocconi and LUISS; fixed n=6. Output measures still differ.',ha='left',fontsize=7.5,color='#555')
ax.grid(axis='y',alpha=.25);fig.tight_layout(rect=[0,0,1,0.88])
img=Path('assets/papers/methodology/gating-balanced-2001-more-europe.png')
fig.savefig(img,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(img.with_suffix('.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
print(p);print(img);print(rows[0],rows[-1])
