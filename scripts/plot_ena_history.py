#!/usr/bin/env python3
"""ENA/INSP: all located historical observations, with metric labels."""
from __future__ import annotations
import csv, sqlite3
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def main():
    db=sqlite3.connect('euro_sdt_v2.db'); db.row_factory=sqlite3.Row
    places=list(csv.DictReader(open('data/institutions/ena_places_offered.csv')))
    enrolled=[(r['year'],r['enrolled']) for r in db.execute("select year,enrolled from institution_cohort where institution_id='ecole-nationale-d-administration' and enrolled is not null order by year")]
    admitted=[(r['year'],r['admitted']) for r in db.execute("select year,admitted from institution_cohort where institution_id='ecole-nationale-d-administration' and admitted is not null and programme like 'ENA historical admitted%' order by year")]
    graduates=[(r['year'],r['graduates']) for r in db.execute("select year,graduates from institution_cohort where institution_id='ecole-nationale-d-administration' and graduates is not null and programme like 'ENA historical graduates%' order by year")]
    # add the explicit 1993/2000/2001/2014/2016 rows if present by their metrics above

    fig,ax=plt.subplots(figsize=(11,4.8))
    ax.plot([int(r['year']) for r in places],[int(r['places_offered']) for r in places],color='#777777',linewidth=1.6,linestyle='--',marker='s',markersize=3,label='Places offered (not output)')
    recent=[(int(y),int(v)) for y,v in enrolled if int(y)>=2019]
    early=[(int(y),int(v)) for y,v in enrolled if int(y)<2019]
    ax.plot([y for y,_ in recent],[v for _,v in recent],color='#0072B2',linewidth=2,marker='o',markersize=4,label='Enrolled, initial training (2019–25)')
    ax.scatter([y for y,_ in early],[v for _,v in early],color='#0072B2',marker='o',s=40,zorder=3,label='Enrolled, 2014')
    ax.scatter([int(y) for y,_ in admitted],[int(v) for _,v in admitted],color='#D55E00',marker='D',s=35,zorder=3,label='Admitted/cohort, observed')
    ax.scatter([int(y) for y,_ in graduates],[int(v) for _,v in graduates],color='#009E73',marker='^',s=45,zorder=3,label='Graduates, observed')
    ax.set_xlim(1990,2026); ax.set_ylim(0,125)
    ax.set_xlabel('Year'); ax.set_ylabel('People / places')
    fig.suptitle('ENA / INSP: all located annual observations',x=0.012,y=0.975,ha='left',fontsize=13,fontweight='bold')
    fig.text(0.012,0.925,'Metrics differ: places offered, admitted cohort, enrolled students, graduates. Points are not a single continuous series.',ha='left',fontsize=8,color='#555')
    ax.grid(axis='y',alpha=.25)
    ax.legend(loc='center left',bbox_to_anchor=(1.01,0.5),fontsize=8,frameon=False)
    fig.tight_layout(rect=[0,0,1,0.90])
    out=Path('assets/papers/methodology/ena-insp-history.png')
    fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white')
    fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig); print(out)
    print('enrolled',enrolled); print('admitted',admitted); print('graduates',graduates)

if __name__=='__main__': main()
