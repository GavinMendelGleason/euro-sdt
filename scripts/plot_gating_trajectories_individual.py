#!/usr/bin/env python3
"""Individual gating-institution output graphs, 1990--2025."""
from __future__ import annotations
import re
import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SERIES = [
    ("ena-insp", "ENA / INSP", "ecole-nationale-d-administration", [("Formation initiale – voie générale%", "Initial training")], "enrolled", "Enrolled students"),
    ("ecole-polytechnique", "École Polytechnique", "ecole-polytechnique", [("Cycle ingénieur – voie française (concours CPGE/universitaire)", "French cycle"), ("Cycle ingénieur – voie internationale (concours)", "International cycle")], "admitted", "Entrants/admitted"),
    ("harvard", "Harvard LL.M.", "harvard", [("LL.M.", "LL.M.")], "graduates", "Degrees conferred"),
    ("oxford", "Oxford BCL / MJur", "university-of-oxford", [("BCL", "BCL"), ("MJur", "MJur")], "graduates", "Candidates examined"),
    ("cologne", "Cologne law", "university-of-cologne", [("Rechtswissenschaft (Staatsexamen / 1. Prüfung)", "Law")], "graduates", "First-examination graduates"),
    ("lse", "LSE LLM", "london-school-of-economics", [("LLM (Master of Laws)", "LLM")], "enrolled", "Enrolled students"),
    ("college-of-europe", "College of Europe", "college-of-europe", [("All programmes (promotions table)", "All programmes")], "enrolled", "Matriculated students"),
]
COLORS = ["#0072B2", "#E69F00", "#D55E00", "#CC79A7"]

def rows(db, iid, programme, metric):
    if "%" in programme:
        return db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme like ? and {metric} is not null order by year",(iid, programme)).fetchall()
    return db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme=? and {metric} is not null order by year",(iid, programme)).fetchall()

def main():
    db=sqlite3.connect('euro_sdt_v2.db'); db.row_factory=sqlite3.Row
    outdir=Path('assets/papers/methodology/gating-trajectories'); outdir.mkdir(parents=True, exist_ok=True)
    for slug,title,iid,programmes,metric,ylabel in SERIES:
        fig, ax=plt.subplots(figsize=(10,3.8))
        first=None
        for j,(prog,label) in enumerate(programmes):
            rr=rows(db,iid,prog,metric)
            if not rr: continue
            xs=[r['year'] for r in rr]; ys=[r['value'] for r in rr]
            first=min(xs) if first is None else min(first,min(xs))
            ax.plot(xs,ys,marker='o',markersize=4,linewidth=1.8,color=COLORS[j],label=label if len(programmes)>1 else None)
        ax.set_title(title,loc='left',fontsize=13,fontweight='bold')
        ax.set_ylabel(ylabel,fontsize=9)
        xmin=max(1948, (min(xs) if first is None else first)-2)
        ax.set_xlim(xmin,2025.5)
        ax.set_xticks(range((int(xmin)//5)*5,2026,5))
        ax.tick_params(labelsize=8)
        ax.grid(axis='y',alpha=.25)
        if len(programmes)>1: ax.legend(fontsize=8,frameon=False)
        if first and first>1990:
            ax.axvspan(1990,first,color='#999999',alpha=.08)
            ax.text(0.02,0.82,f'Annual series begins {first}',transform=ax.transAxes,fontsize=8,color='#555')
            if max(xs)-min(xs)+1 > len(xs):
                ax.text(0.02,0.74,'Some years not reported',transform=ax.transAxes,fontsize=8,color='#777')
        fig.tight_layout()
        fig.savefig(outdir/f'{slug}.png',dpi=180,bbox_inches='tight',facecolor='white')
        fig.savefig(outdir/f'{slug}.svg',bbox_inches='tight',facecolor='white')
        plt.close(fig)
        print(outdir/f'{slug}.png')

if __name__=='__main__': main()
