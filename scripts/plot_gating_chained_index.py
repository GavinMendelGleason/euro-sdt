#!/usr/bin/env python3
"""Chained index of gating-institution output per 100,000 EU/EC population."""
from __future__ import annotations
import csv, math, sqlite3, statistics
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

YEAR_SHIFT = {'College of Europe': 1, 'Harvard LL.M.': 1, 'LSE LLM': 1}
ENLARGEMENTS = [(1973,"1973"),(1981,"1981"),(1986,"1986"),(1995,"1995"),(2004,"2004"),(2007,"2007"),(2013,"2013"),(2020,"2020")]

def fetch(db, iid, programme, metric):
    op = 'like' if '%' in programme else '='
    return db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme {op} ? and {metric} is not null order by year",(iid,programme)).fetchall()

def main():
    db=sqlite3.connect('euro_sdt_v2.db'); db.row_factory=sqlite3.Row
    pop={int(r['year']):int(r['population']) for r in csv.DictReader(open('data/institutions/eu_population.csv'))}
    series={}
    series['College of Europe'] = [(r['year'],r['value']) for r in fetch(db,'college-of-europe','All programmes (promotions table)','enrolled')]
    series['Harvard LL.M.'] = [(r['year'],r['value']) for r in fetch(db,'harvard','LL.M.','graduates')]
    series['École Polytechnique'] = [(r['year'],r['value']) for r in fetch(db,'ecole-polytechnique','Cycle ingénieur – voie française (concours CPGE/universitaire)','admitted')]
    ox=defaultdict(dict)
    for prog in ['BCL','MJur']:
        for r in fetch(db,'university-of-oxford',prog,'graduates'):
            ox[r['year']][prog]=r['value']
    series['Oxford BCL/MJur'] = [(y,v['BCL']+v['MJur']) for y,v in sorted(ox.items()) if 'BCL' in v and 'MJur' in v]
    series['Cologne law'] = [(r['year'],r['value']) for r in fetch(db,'university-of-cologne','Rechtswissenschaft (Staatsexamen / 1. Prüfung)','graduates')]
    series['LSE LLM'] = [(r['year'],r['value']) for r in fetch(db,'london-school-of-economics','LLM (Master of Laws)','enrolled')]
    series['ENA/INSP'] = [(r['year'],r['value']) for r in fetch(db,'ecole-nationale-d-administration','Formation initiale – voie générale%','enrolled')]

    rates={}
    for name,pts in series.items():
        shift=YEAR_SHIFT.get(name,0)
        rates[name]={y+shift:v/pop[y+shift]*100000 for y,v in pts if y+shift in pop}

    first=min(min(r) for r in rates.values())
    last=max(max(r) for r in rates.values())
    growth_by_year=defaultdict(list)
    for obs in rates.values():
        ys=sorted(obs)
        for p,y in zip(ys,ys[1:]):
            gap=y-p
            if gap<=0: continue
            g=math.log(obs[y]/obs[p])/gap
            for yy in range(p+1,y+1): growth_by_year[yy].append(g)
    values={first:100.0}; n_pairs={first:0}; current=100.0
    for y in range(first+1,last+1):
        growth=growth_by_year[y]
        if growth: current*=math.exp(statistics.median(growth))
        values[y]=current; n_pairs[y]=len(growth)

    fig, ax=plt.subplots(figsize=(12,6.2))
    ys=sorted(values)
    ax.plot(ys,[values[y] for y in ys],color='#222222',linewidth=2.8,label='Chained median index (1960 = 100)')
    ax.axhline(100,color='#888888',linewidth=.8,linestyle='--')
    for y,label in ENLARGEMENTS:
        ax.axvline(y,color='#999999',linewidth=.6,linestyle=':',alpha=.7)
        ax.text(y,0.97,label,transform=ax.get_xaxis_transform(),rotation=90,fontsize=6,color='#777',ha='right',va='top')
    ax.set_xlim(first-1,last+1)
    ax.set_xlabel('Year')
    ax.set_ylabel('Chained index of output per 100,000 EU/EC population (1960 = 100)')
    fig.suptitle('Gating institutions: chained per-capita index',x=0.012,y=0.975,ha='left',fontsize=14,fontweight='bold')
    fig.text(0.012,0.925,'Median annual log growth across observed intervals, distributed across missing years; no level jump when a series enters or leaves.',ha='left',fontsize=8.5,color='#555')
    ax.grid(axis='y',alpha=.25)
    ax.legend(loc='upper left',fontsize=9,frameon=False)
    fig.tight_layout(rect=[0,0,1,0.90])
    out=Path('assets/papers/methodology/gating-trajectories-chained-index.png')
    fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white')
    fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig)
    print(out)
    print('index', {y:round(values[y],1) for y in [1960,1970,1980,1990,2000,2010,2020,2025] if y in values})
    print('n_pairs', {y:n_pairs[y] for y in [1960,1983,2002,2010,2019,2024,2025] if y in n_pairs})

if __name__=='__main__': main()
