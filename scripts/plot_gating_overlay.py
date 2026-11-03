#!/usr/bin/env python3
"""Single indexed overlay of gating-institution output trajectories."""
from __future__ import annotations
import sqlite3
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000"]

def fetch(db, iid, programme, metric):
    if "%" in programme:
        return db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme like ? and {metric} is not null order by year",(iid,programme)).fetchall()
    return db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme=? and {metric} is not null order by year",(iid,programme)).fetchall()

def main():
    db=sqlite3.connect('euro_sdt_v2.db'); db.row_factory=sqlite3.Row
    series={}
    series['College of Europe'] = [(r['year'],r['value']) for r in fetch(db,'college-of-europe','All programmes (promotions table)','enrolled')]
    series['Harvard LL.M.'] = [(r['year'],r['value']) for r in fetch(db,'harvard','LL.M.','graduates')]
    series['École Polytechnique'] = [(r['year'],r['value']) for r in fetch(db,'ecole-polytechnique','Cycle ingénieur – voie française (concours CPGE/universitaire)','admitted')]
    # Oxford total candidates examined = BCL + MJur, years with both
    ox=defaultdict(dict)
    for prog in ['BCL','MJur']:
        for r in fetch(db,'university-of-oxford',prog,'graduates'):
            ox[r['year']][prog]=r['value']
    series['Oxford BCL/MJur'] = [(y,v['BCL']+v['MJur']) for y,v in sorted(ox.items()) if 'BCL' in v and 'MJur' in v]
    series['Cologne law'] = [(r['year'],r['value']) for r in fetch(db,'university-of-cologne','Rechtswissenschaft (Staatsexamen / 1. Prüfung)','graduates')]
    series['LSE LLM'] = [(r['year'],r['value']) for r in fetch(db,'london-school-of-economics','LLM (Master of Laws)','enrolled')]
    series['ENA/INSP'] = [(r['year'],r['value']) for r in fetch(db,'ecole-nationale-d-administration','Formation initiale – voie générale%','enrolled')]

    fig, ax=plt.subplots(figsize=(12,6.2))
    for color,(name,pts) in zip(COLORS,series.items()):
        pts=sorted(pts)
        if not pts: continue
        base=pts[0][1]
        ax.plot([y for y,_ in pts],[v/base*100 for _,v in pts],marker='o',markersize=3.5,linewidth=1.9,color=color,label=f'{name} ({pts[0][0]} = 100)')
    ax.axhline(100,color='#888888',linewidth=.8,linestyle='--')
    ax.set_yscale('log')
    ax.set_xlim(1948,2026)
    ax.set_ylim(40,1600)
    ax.set_yticks([50,100,200,400,800,1600])
    ax.set_yticklabels(['50','100','200','400','800','1600'])
    ax.set_xlabel('Year')
    ax.set_ylabel('Indexed output (first observation = 100, log scale)')
    fig.suptitle('Gating institutions: indexed output trajectories',x=0.012,y=0.975,ha='left',fontsize=14,fontweight='bold')
    fig.text(0.012,0.925,'Each series is indexed to its own first observation; the lines show relative change, not common raw units.',ha='left',fontsize=9,color='#555')
    ax.grid(axis='y',which='major',alpha=.25)
    ax.legend(loc='upper left',fontsize=8,frameon=False)
    fig.tight_layout(rect=[0,0,1,0.90])
    out=Path('assets/papers/methodology/gating-trajectories-overlay.png')
    fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white')
    fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig);print(out)

if __name__=='__main__': main()
