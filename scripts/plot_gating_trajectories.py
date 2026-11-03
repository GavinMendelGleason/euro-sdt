#!/usr/bin/env python3
"""Small-multiple lines of available gating-institution output series."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SERIES = [
    ("ENA / INSP", "ecole-nationale-d-administration", ["Formation initiale – voie générale%"], "enrolled", "Initial-training enrolment"),
    ("École Polytechnique", "ecole-polytechnique", ["Cycle ingénieur – voie française (concours CPGE/universitaire)", "Cycle ingénieur – voie internationale (concours)"], "enrolled", "Engineering-cycle enrolment"),
    ("Harvard LL.M.", "harvard", ["LL.M."], "graduates", "LL.M. degrees conferred"),
    ("Oxford BCL / MJur", "university-of-oxford", ["BCL", "MJur"], "enrolled", "Master's law enrolment"),
    ("Cologne law", "university-of-cologne", ["Rechtswissenschaft (Staatsexamen / 1. Prüfung)"], "graduates", "First-examination graduates"),
    ("LSE LLM", "london-school-of-economics", ["LLM (Master of Laws)"], "enrolled", "LLM enrolment"),
]
COLORS = ["#0072B2", "#E69F00", "#D55E00", "#CC79A7", "#009E73", "#56B4E9"]

def main():
    db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
    fig, axes=plt.subplots(3, 3, figsize=(12, 7.5), sharex=False)
    axes=axes.ravel()
    for ax,(title,iid,programmes,metric,ylabel) in zip(axes,SERIES):
        for j,prog in enumerate(programmes):
            rows=db.execute("select year,value from institution_cohort where institution_id=? and programme=? and value is not null and year is not null order by year",(iid,prog)).fetchall() if False else []
            if '%' in prog:
                rows=db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme like ? and {metric} is not null order by year",(iid,prog)).fetchall()
            else:
                rows=db.execute(f"select year,{metric} as value from institution_cohort where institution_id=? and programme=? and {metric} is not null order by year",(iid,prog)).fetchall()
            if rows:
                ax.plot([r['year'] for r in rows],[r['value'] for r in rows], marker='o', color=COLORS[j], linewidth=1.8, markersize=4, label=prog if len(programmes)>1 else None)
        ax.set_title(title, fontsize=10, loc='left')
        ax.set_ylabel(ylabel, fontsize=8)
        ax.tick_params(labelsize=8)
        ax.grid(axis='y', alpha=.25)
        if len(programmes)>1:
            ax.legend(fontsize=7, frameon=False)
        ax.set_xlim(2018.5, 2025.5)
    # College panel: no common annual series
    ax=axes[6]; ax.set_title('College of Europe', fontsize=10, loc='left')
    ax.text(.5,.55,'No annual graduate series',ha='center',va='center',fontsize=10,transform=ax.transAxes)
    ax.text(.5,.42,'2019 Natolin and 2024 all-College\nare not comparable points',ha='center',va='center',fontsize=8,transform=ax.transAxes,color='#555')
    ax.set_xticks([]); ax.set_yticks([]); ax.set_frame_on(False)
    axes[7].axis('off'); axes[8].axis('off')
    fig.suptitle('Available gating-institution output series, 2019–2025\nEach panel uses its own reported measure; no common scale', fontsize=12, x=.02, ha='left')
    fig.tight_layout(rect=[0,0,1,.92])
    out=Path('assets/papers/methodology/gating-trajectories.png')
    fig.savefig(out,dpi=180,bbox_inches='tight',facecolor='white')
    fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig);print(out)
if __name__=='__main__': main()
