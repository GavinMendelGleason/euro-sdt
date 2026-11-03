#!/usr/bin/env python3
"""Population-adjusted institutional series with superimposed chained index."""
from __future__ import annotations
import csv, math, sqlite3, statistics
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000"]
YEAR_SHIFT = {'College of Europe': 1, 'Harvard LL.M.': 1, 'LSE LLM': 1}
ENLARGEMENTS = [(1973,"1973"),(1981,"1981"),(1986,"1986"),(1995,"1995"),(2004,"2004"),(2007,"2007"),(2013,"2013"),(2020,"2020")]

def fetch(db, iid, programme, metric):
    op='like' if '%' in programme else '='
    return db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme {op} ? and {metric} is not null order by year",(iid,programme)).fetchall()

def main():
    db=sqlite3.connect('euro_sdt_v2.db'); db.row_factory=sqlite3.Row
    pop={int(r['year']):int(r['population']) for r in csv.DictReader(open('data/institutions/eu_population.csv'))}
    series={}
    series['College of Europe']=[(r['year'],r['value']) for r in fetch(db,'college-of-europe','All programmes (promotions table)','enrolled')]
    series['Harvard LL.M.']=[(r['year'],r['value']) for r in fetch(db,'harvard','LL.M.','graduates')]
    series['École Polytechnique']=[(r['year'],r['value']) for r in fetch(db,'ecole-polytechnique','Cycle ingénieur – voie française (concours CPGE/universitaire)','admitted')]
    ox=defaultdict(dict)
    for prog in ['BCL','MJur']:
        for r in fetch(db,'university-of-oxford',prog,'graduates'):
            ox[r['year']][prog]=r['value']
    series['Oxford BCL/MJur']=[(y,v['BCL']+v['MJur']) for y,v in sorted(ox.items()) if 'BCL' in v and 'MJur' in v]
    series['Cologne law']=[(r['year'],r['value']) for r in fetch(db,'university-of-cologne','Rechtswissenschaft (Staatsexamen / 1. Prüfung)','graduates')]
    series['LSE LLM']=[(r['year'],r['value']) for r in fetch(db,'london-school-of-economics','LLM (Master of Laws)','enrolled')]
    series['ENA/INSP']=[(r['year'],r['value']) for r in fetch(db,'ecole-nationale-d-administration','Formation initiale – voie générale%','enrolled')]

    rates={}
    for name,pts in series.items():
        shift=YEAR_SHIFT.get(name,0)
        rates[name]={y+shift:v/pop[y+shift]*100000 for y,v in pts if y+shift in pop}

    first=min(min(r) for r in rates.values()); last=max(max(r) for r in rates.values())
    index={first:100.0}; cur=100.0
    for y in range(first+1,last+1):
        growth=[]
        for obs in rates.values():
            earlier=[yy for yy in obs if yy<y]
            if not earlier or y not in obs: continue
            prev=max(earlier); gap=y-prev
            if gap>0: growth.append(math.log(obs[y]/obs[prev])/gap)
        if growth: cur*=math.exp(statistics.median(growth))
        index[y]=cur

    fig, ax=plt.subplots(figsize=(12,6.4))
    lines=[]; labels=[]
    for color,(name,pts) in zip(COLORS,series.items()):
        shift=YEAR_SHIFT.get(name,0)
        raw=sorted((y+shift,v) for y,v in pts if y+shift in pop)
        if not raw: continue
        vals=dict(raw); ys=list(range(raw[0][0],raw[-1][0]+1))
        rr=[None if vals.get(y) is None else vals[y]/pop[y]*100000 for y in ys]
        ln,=ax.plot(ys,rr,marker='o',markersize=3,linewidth=1.8,color=color,label=name)
        lines.append(ln); labels.append(name)
    ax.set_xlim(first-1,last+1)
    ax.set_ylim(0,0.125)
    ax.set_xlabel('Year')
    ax.set_ylabel('Output per 100,000 EU/EC population')
    ax.grid(axis='y',alpha=.22)

    ax2=ax.twinx()
    ln,=ax2.plot(sorted(index),[index[y] for y in sorted(index)],color='#8B0000',linewidth=3.0,label='Chained median index (1960 = 100)  [right axis]')
    ax2.set_ylabel('Chained index (1960 = 100)',color='#8B0000')
    ax2.tick_params(axis='y',colors='#8B0000')
    ax2.set_ylim(60,340)
    lines.append(ln); labels.append('Chained median index (1960 = 100)  [right axis]')
    for y,label in ENLARGEMENTS:
        ax.axvline(y,color='#999999',linewidth=.6,linestyle=':',alpha=.7)
        ax.text(y,0.121,label,rotation=90,fontsize=6,color='#777',ha='right',va='top')
    fig.suptitle('Gating institutions: population-adjusted output and chained index',x=0.012,y=0.975,ha='left',fontsize=14,fontweight='bold')
    fig.text(0.012,0.925,'Per-capita lines use EU/EC member-state population; the black-red index chains median annual log growth across observed pairs, 1960 = 100.',ha='left',fontsize=8.5,color='#555')
    ax.legend(lines,labels,loc='upper left',fontsize=8,frameon=False)
    fig.tight_layout(rect=[0,0,1,0.90])
    out=Path('assets/papers/methodology/gating-trajectories-combined.png')
    fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white')
    fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig);print(out);print({y:round(index[y],1) for y in [1960,1980,2000,2020,2025]})

if __name__=='__main__': main()
