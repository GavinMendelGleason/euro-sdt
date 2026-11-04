#!/usr/bin/env python3
"""College of Europe alone vs the composite gating-institution index."""
import csv, math, sqlite3, statistics
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def fetch(db,i,p,m):
 op='like' if '%' in p else '='
 return db.execute(f"select year,{m} as v from institution_cohort where institution_id=? and programme {op} ? and {m} is not null order by year",(i,p)).fetchall()

def main():
 db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
 pop={int(r['year']):int(r['population']) for r in csv.DictReader(open('data/institutions/eu_population.csv'))}
 series={'College of Europe':fetch(db,'college-of-europe','All programmes (promotions table)','enrolled'),'Harvard LL.M.':fetch(db,'harvard','LL.M.','graduates'),'École Polytechnique':fetch(db,'ecole-polytechnique','Cycle ingénieur – voie française (concours CPGE/universitaire)','admitted'),'Cologne law':fetch(db,'university-of-cologne','Rechtswissenschaft (Staatsexamen / 1. Prüfung)','graduates'),'LSE LLM':fetch(db,'london-school-of-economics','LLM (Master of Laws)','enrolled'),'ENA/INSP':fetch(db,'ecole-nationale-d-administration','Formation initiale – voie générale%','enrolled')}
 ox=defaultdict(dict)
 for p in ['BCL','MJur']:
  for r in fetch(db,'university-of-oxford',p,'graduates'): ox[r['year']][p]=r['v']
 series['Oxford BCL/MJur']=[{'year':y,'v':v['BCL']+v['MJur']} for y,v in ox.items() if 'BCL' in v and 'MJur' in v]
 shift={'College of Europe':1,'Harvard LL.M.':1,'LSE LLM':1}
 rates={}
 for n,rs in series.items():
  sf=shift.get(n,0); rates[n]={r['year']+sf:r['v']/pop[r['year']+sf]*100000 for r in rs if r['year']+sf in pop}
 def chain(rr):
  first=min(min(o) for o in rr.values()); last=max(max(o) for o in rr.values()); gb=defaultdict(list)
  for obs in rr.values():
   ys=sorted(obs)
   for a,b in zip(ys,ys[1:]):
    g=math.log(obs[b]/obs[a])/(b-a)
    for y in range(a+1,b+1): gb[y].append(g)
  idx={first:100};cur=100
  for y in range(first+1,last+1):
   if gb[y]: cur*=math.exp(statistics.median(gb[y]))
   idx[y]=cur
  return idx
 comp=chain(rates); col=chain({'College of Europe':rates['College of Europe']})
 fig,ax=plt.subplots(figsize=(9,5.2))
 ax.plot(sorted(col),[col[y] for y in sorted(col)],color='#0072B2',linewidth=2.3,marker='o',markersize=3,label='College of Europe alone')
 ax.plot(sorted(comp),[comp[y] for y in sorted(comp)],color='#333333',linewidth=2.3,marker='o',markersize=3,label='Composite gating index')
 ax.axhline(100,color='#888888',linewidth=.8,linestyle='--')
 ax.set_xlim(1960,2026); ax.set_ylim(60,520)
 ax.set_ylabel('Chained index (1960 = 100)'); ax.set_xlabel('Year')
 fig.suptitle('Is the College of Europe a good proxy for the composite?',x=0.012,y=0.975,ha='left',fontsize=14,fontweight='bold')
 fig.text(0.012,0.91,'Both series use EU/EC population and interpolated chained growth; the College-only line is matriculation, not degrees.',ha='left',fontsize=8,color='#555')
 ax.grid(axis='y',alpha=.25); ax.legend(frameon=False,fontsize=9)
 fig.tight_layout(rect=[0,0,1,0.86])
 out=Path('assets/papers/methodology/college-vs-composite-proxy.png')
 fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
 plt.close(fig);print(out);print('college2025',round(col[max(col)],1),'composite2025',round(comp[max(comp)],1))

if __name__=='__main__': main()
