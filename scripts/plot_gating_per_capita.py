#!/usr/bin/env python3
"""Gating-institution output per 100,000 EU/EC population, 1960-2025."""
from __future__ import annotations
import csv, sqlite3
from collections import defaultdict
from statistics import mean
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000"]
ENLARGEMENTS = [(1973,"1973"),(1981,"1981"),(1986,"1986"),(1995,"1995"),(2004,"2004"),(2007,"2007"),(2013,"2013"),(2020,"2020")]

def fetch(db, iid, programme, metric):
    if "%" in programme:
        return db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme like ? and {metric} is not null order by year",(iid,programme)).fetchall()
    return db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme=? and {metric} is not null order by year",(iid,programme)).fetchall()

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

    fig, ax=plt.subplots(figsize=(12,6.2))
    rates_by_year=defaultdict(list)
    for color,(name,pts) in zip(COLORS,series.items()):
        raw=sorted((y,v) for y,v in pts if y in pop)
        if not raw: continue
        vals=dict(raw); ys=list(range(raw[0][0],raw[-1][0]+1))
        xs=ys; rates=[None if vals.get(y) is None else vals[y]/pop[y]*100000 for y in ys]
        for y,r in zip(xs,rates):
            if r is not None: rates_by_year[y].append(r)
        ax.plot(xs,rates,marker='o',markersize=3.5,linewidth=1.9,color=color,label=name)
    avg_years=sorted(y for y,v in rates_by_year.items() if len(v)>=2)
    ax.plot(avg_years,[mean(rates_by_year[y]) for y in avg_years],color='#333333',linewidth=2.6,linestyle='--',label='Mean of available series')
    for y,label in ENLARGEMENTS:
        ax.axvline(y,color='#999999',linewidth=.6,linestyle=':',alpha=.7)
        ax.text(y,0.120,label,rotation=90,fontsize=6,color='#777',ha='right',va='top')
    ax.set_xlim(1959,2026)
    ax.set_ylim(0,0.125)
    ax.set_xlabel('Year')
    ax.set_ylabel('Output per 100,000 EU/EC population')
    fig.suptitle('Gating institutions: output per 100,000 EU/EC population',x=0.012,y=0.975,ha='left',fontsize=14,fontweight='bold')
    fig.text(0.012,0.925,'Denominator = population of member states at each date; EU-6 in 1960, with enlargements applied at accession and the UK removed in 2020. Mean line = unweighted mean of series available in that year (at least two).',ha='left',fontsize=8.5,color='#555')
    ax.grid(axis='y',alpha=.25)
    ax.legend(loc='upper left',fontsize=8,frameon=False)
    fig.tight_layout(rect=[0,0,1,0.90])
    out=Path('assets/papers/methodology/gating-trajectories-per-capita.png')
    fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white')
    fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig);print(out)

if __name__=='__main__': main()
