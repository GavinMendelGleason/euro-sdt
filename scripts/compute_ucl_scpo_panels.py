#!/usr/bin/env python3
"""UCLouvain 2001-2020 seven panel and Sciences Po 2015-2020 eight panel."""
import csv,sqlite3
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

base={int(r['year']):r for r in csv.DictReader(open('data/analysis/gating_balanced_2001_more_europe.csv'))}
deg=list(csv.DictReader(open('data/institutions/degrees_awarded.csv')))
ucl={int(r['year']):int(r['degrees']) for r in deg if r['institution_id']=='uclouvain'}
scpo={int(r['year']):int(r['degrees']) for r in deg if r['institution_id']=='sciences-po'}
panel={int(r['year']):int(r['A_posts']) for r in csv.DictReader(open('data/denominator/elite_position_denominator_5y.csv'))}
jud={int(r['year']):int(r['judicial_positions']) for r in csv.DictReader(open('data/denominator/judicial_positions_annual.csv'))}
py=sorted(panel)
def ap(y):
 for a,b in zip(py,py[1:]):
  if a<=y<=b:return panel[a]+(panel[b]-panel[a])*(y-a)/(b-a)
 return panel[py[-1]]
def make(years,extras,cols,out,title,sub):
 rows=[]
 for y in years:
  vals=[int(base[y][c]) for c in cols]+[e[y] for e in extras]
  den=ap(y)+jud[y]
  rows.append({'year':y,'aggregate_output':sum(vals),'n_institutions':len(vals),'per_1000_positions':round(1000*sum(vals)/den,2)})
 p=Path(out+'.csv');
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 fig,ax=plt.subplots(figsize=(9,5.2));ax.plot([r['year'] for r in rows],[r['per_1000_positions'] for r in rows],color='#0072B2',marker='o',markersize=3,linewidth=2)
 ax.set_xlabel('Year');ax.set_ylabel('Aggregate output per 1,000 Commission + judicial positions')
 fig.suptitle(title,x=0.012,y=0.985,ha='left',fontsize=13,fontweight='bold');fig.text(0.012,0.925,sub,ha='left',fontsize=7.5,color='#555')
 ax.grid(axis='y',alpha=.25);fig.tight_layout(rect=[0,0,1,0.88])
 img=Path(out+'.png');fig.savefig(img,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(img.with_suffix('.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
 print(p,img,rows[0],rows[-1])
make(range(2001,2021),[ucl],['College','Harvard','Stockholm','Georgetown','Bocconi','LUISS'],'data/analysis/gating_balanced_2001_2020_uclouvain','Seven-institution panel with UCLouvain, 2001–2020','College, Harvard, Stockholm, Georgetown, Bocconi, LUISS, UCLouvain; fixed n=7.')
make(range(2015,2021),[ucl,scpo],['College','Harvard','Stockholm','Georgetown','Bocconi','LUISS'],'data/analysis/gating_balanced_2015_2020_sciencespo','Eight-institution panel with Sciences Po, 2015–2020','College, Harvard, Stockholm, Georgetown, Bocconi, LUISS, UCLouvain, Sciences Po; fixed n=8.')
