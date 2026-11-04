#!/usr/bin/env python3
"""Share of elite groups with education at a core gating institution."""
from __future__ import annotations
import csv, sqlite3
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CORE = {
 'College of Europe': ['college of europe'],
 'Harvard University': ['harvard'],
 'University of Cambridge': ['cambridge'],
 'ENA/INSP': ["ecole nationale d'administration", 'école nationale d’administration', 'ena'],
 'LSE': ['london school of economics', 'lse'],
 'UCLouvain': ['uclouvain', 'catholique de louvain'],
 'University of Oxford': ['oxford'],
 'Vilnius University': ['vilnius'],
 'École Polytechnique': ['polytechnique'],
 'University of Cologne': ['cologne'],
}
BOC = 'Bocconi'
def which(org):
    s=(org or '').lower()
    for label,keys in CORE.items():
        if any(k in s for k in keys): return label
    if 'bocconi' in s: return BOC
    return None

def main():
    db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
    groups={
      'Commission heads':['commissioner'],
      'Commission + DGs/DDGs':['commissioner','dg','ddg'],
      'Judiciary':['cjeu_judge','cjeu_ag','cjeu_gc_judge','cjeu_registrar'],
    }
    out=[]; chart=[]
    for label,cats in groups.items():
        ids={r['id'] for r in db.execute("select id from entity where status='active' and category in (%s)"%','.join('?'*len(cats)),cats)}
        if label=='Judiciary':
            rows=db.execute("select person_id as subject_id, organisation as org from judicial_affiliation where kind='education'").fetchall()
        else:
            q=','.join('?'*len(ids))
            rows=db.execute(f"select c.subject_id,o.name org from claim c join assertion a on a.claim_id=c.id and a.status='verified' join entity o on o.id=c.object_id where c.predicate='educated_at' and c.subject_id in ({q})",list(ids)).fetchall()
        people=defaultdict(set)
        for r in rows:
            if r['subject_id'] in ids:
                g=which(r['org'])
                if g: people[r['subject_id']].add(g)
        core=sum(1 for v in people.values() if any(g!=BOC for g in v))
        incl=sum(1 for v in people.values() if v)
        out.append([label,len(ids),core,round(100*core/len(ids),2),incl,round(100*incl/len(ids),2)])
        chart.append((label,len(ids),core,incl))
    p=Path('data/analysis/gating_share_by_group.csv'); p.parent.mkdir(exist_ok=True)
    with p.open('w',newline='') as f:
        w=csv.writer(f); w.writerow(['group','denominator','core_count','core_pct','incl_bocconi_count','incl_bocconi_pct']); w.writerows(out)
    labels=[x[0] for x in chart]; x=range(len(labels)); width=.36
    fig,ax=plt.subplots(figsize=(9,5.2))
    core=[x[2] for x in chart]; incl=[x[3] for x in chart]; den=[x[1] for x in chart]
    ax.bar([i-width/2 for i in x],[100*c/d for c,d in zip(core,den)],width,color='#0072B2',label='Core gating set (10)')
    ax.bar([i+width/2 for i in x],[100*c/d for c,d in zip(incl,den)],width,color='#D55E00',label='Including Bocconi (11)')
    for i,(c,n,d) in enumerate(zip(core,incl,den)):
        ax.text(i-width/2,100*c/d+.6,f'{c}/{d}\n{100*c/d:.1f}%',ha='center',va='bottom',fontsize=8,color='#0072B2')
        ax.text(i+width/2,100*n/d+.6,f'{n}/{d}\n{100*n/d:.1f}%',ha='center',va='bottom',fontsize=8,color='#D55E00')
    ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    ax.set_ylim(0,42); ax.set_ylabel('Percent of group')
    fig.suptitle('Share with education at a gating institution',x=0.012,y=0.975,ha='left',fontsize=14,fontweight='bold')
    fig.text(0.012,0.90,'Denominator = all people in the group; education coverage is uneven.\nCounts are unique people with at least one verified education link.',ha='left',fontsize=8,color='#555')
    ax.grid(axis='y',alpha=.25); ax.legend(frameon=False,fontsize=8,loc='upper left')
    fig.tight_layout(rect=[0,0,1,0.86])
    outp=Path('assets/papers/methodology/gating-share-by-group.png')
    fig.savefig(outp,dpi=200,bbox_inches='tight',facecolor='white'); fig.savefig(outp.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig); print(p);print(outp);print(out)

if __name__=='__main__': main()
