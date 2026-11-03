#!/usr/bin/env python3
"""Chained median indices of gating-school output divided by A/B/C/total denominators."""
from __future__ import annotations
import csv, math, sqlite3, statistics
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.ticker
import matplotlib.pyplot as plt

YEARS=[1990,1995,2000,2005,2010,2015,2020,2025]
SHIFT={'College of Europe':1,'Harvard LL.M.':1,'LSE LLM':1}
COLORS={'A (Commission posts)':'#0072B2','B (bar lawyers)':'#D55E00','C (listed board seats)':'#009E73','A+B+C total':'#8B0000'}

def fetch(db,iid,prog,metric):
    op='like' if '%' in prog else '='
    return db.execute(f"select year,{metric} as v from institution_cohort where institution_id=? and programme {op} ? and {metric} is not null order by year",(iid,prog)).fetchall()

def nearest(rows, year, max_gap=1):
    best=None
    for r in rows:
        y=r['year']+SHIFT.get(r.get('name',''),0) if False else r['year']
        if abs(y-year)<=max_gap:
            if best is None or abs(y-year)<abs(best[0]-year): best=(y,r['v'])
    return best[1] if best else None

def main():
    db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
    den={int(r['year']):r for r in csv.DictReader(open('data/denominator/elite_position_denominator_5y.csv'))}
    # output series, keyed by display name; values use source year labels plus end-year shift
    raw={
      'College of Europe':fetch(db,'college-of-europe','All programmes (promotions table)','enrolled'),
      'Harvard LL.M.':fetch(db,'harvard','LL.M.','graduates'),
      'École Polytechnique':fetch(db,'ecole-polytechnique','Cycle ingénieur – voie française (concours CPGE/universitaire)','admitted'),
      'Cologne law':fetch(db,'university-of-cologne','Rechtswissenschaft (Staatsexamen / 1. Prüfung)','graduates'),
      'LSE LLM':fetch(db,'london-school-of-economics','LLM (Master of Laws)','enrolled'),
      'ENA/INSP':fetch(db,'ecole-nationale-d-administration','Formation initiale – voie générale%','enrolled'),
    }
    ox=defaultdict(dict)
    for prog in ['BCL','MJur']:
        for r in fetch(db,'university-of-oxford',prog,'graduates'): ox[r['year']][prog]=r['v']
    raw['Oxford BCL/MJur']=[{'year':y,'v':v['BCL']+v['MJur']} for y,v in ox.items() if 'BCL' in v and 'MJur' in v]
    # Shift College/Harvard/LSE and use nearest observation within one year of benchmark.
    shifted={}
    for name,rows in raw.items():
        sf=SHIFT.get(name,0)
        shifted[name]=[{'year':r['year']+sf,'v':r['v']} for r in rows]
    outs={}
    for name,rows in shifted.items():
        vals={}
        for y in YEARS:
            v=nearest(rows,y,1)
            if v is not None: vals[y]=v
        if vals: outs[name]=vals

    index={}; counts={}
    for key in ['A (Commission posts)','B (bar lawyers)','C (listed board seats)','A+B+C total']:
        col={'A (Commission posts)':'A_posts','B (bar lawyers)':'B_lawyers','C (listed board seats)':'C_seats','A+B+C total':'total'}[key]
        cur=100.0; vals={YEARS[0]:100.0}; ns={YEARS[0]:0}
        for prev,y in zip(YEARS,YEARS[1:]):
            growth=[]
            for name,o in outs.items():
                if prev in o and y in o:
                    r0=o[prev]/int(den[prev][col]); r1=o[y]/int(den[y][col])
                    growth.append(math.log(r1/r0)/5)  # annualised over 5 years
            if growth: cur*=math.exp(statistics.median(growth)*5)
            vals[y]=cur; ns[y]=len(growth)
        index[key]=vals; counts[key]=ns

    fig,ax=plt.subplots(figsize=(12,6.2))
    for key,vals in index.items():
        ax.plot(list(vals),list(vals.values()),marker='o',markersize=4,linewidth=2.1,color=COLORS[key],label=key)
    ax.axhline(100,color='#888888',linewidth=.8,linestyle='--')
    ax.set_yscale('log')
    ax.set_xlim(1988,2027); ax.set_ylim(40,400)
    ax.set_yticks([40,50,60,80,100,150,200,300,400])
    ax.set_yticklabels(['40','50','60','80','100','150','200','300','400'])
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel('Year'); ax.set_ylabel('Chained median index (1990 = 100, log scale)')
    fig.suptitle('Gating-school output divided by elite-position denominators',x=0.012,y=0.975,ha='left',fontsize=14,fontweight='bold')
    fig.text(0.012,0.925,'Each line chains the median five-year growth in institution output / denominator; institutions enter when observed in both endpoints.',ha='left',fontsize=8,color='#555')
    ax.grid(axis='y',alpha=.25); ax.legend(loc='upper left',fontsize=9,frameon=False)
    fig.tight_layout(rect=[0,0,1,0.90])
    out=Path('assets/papers/methodology/elite-school-denominator-index.png')
    fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white')
    fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig);print(out)
    csvout=Path('data/denominator/elite_school_denominator_index_5y.csv')
    with csvout.open('w',newline='') as f:
        w=csv.writer(f); w.writerow(['year','index_A','index_B','index_C','index_total','n_A','n_B','n_C','n_total'])
        for y in YEARS:
            w.writerow([y]+[round(index[k][y],2) for k in index]+[counts[k][y] for k in counts])
    print(csvout)
    for y in YEARS: print(y,{k:round(index[k][y],1) for k in index},'n',{k:counts[k][y] for k in counts})

if __name__=='__main__': main()
