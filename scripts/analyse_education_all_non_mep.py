#!/usr/bin/env python3
"""Aggregate education by institution and job type, excluding MEPs."""
from __future__ import annotations
import csv, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_judicial_education import canon

EXTRA = {
 'harvard':'Harvard University','hec paris':'HEC Paris','insead':'INSEAD','essec business school':'ESSEC Business School',
 'bocconi':'Bocconi University','sapienza university of rome':'Sapienza University of Rome',
 'westfalische wilhelms universitat in munster':'University of Münster',
 'polytechnic university of milan':'Politecnico di Milano','university of national and world economy':'University of National and World Economy',
 'universite catholique de louvain':'UCLouvain','university of kingston upon hull':'University of Hull',
 'sciences po':'Sciences Po','georgetown university':'Georgetown University','yale university':'Yale University',
}
def canon2(org):
    return [EXTRA.get(x.strip().lower(),x) for x in canon(org)]

def main():
    import sqlite3
    db=sqlite3.connect('euro_sdt_v2.db'); db.row_factory=sqlite3.Row
    groups=[('Commissioners','commissioner'),('DGs/DDGs','dg'),('DGs/DDGs','ddg'),('Corporate elites','corporate_elite'),('Judicial','cjeu_judge'),('Judicial','cjeu_ag'),('Judicial','cjeu_gc_judge'),('Judicial','cjeu_registrar')]
    people={}; links=defaultdict(set); inst_track=defaultdict(Counter); inst_people=defaultdict(lambda: defaultdict(set)); cat_people=Counter(); cat_educated=Counter()
    for label,cat in groups:
        ids=[r[0] for r in db.execute("select id from entity where category=? and status='active'",(cat,))]
        cat_people[label]+=len(ids)
        if cat.startswith('cjeu_'):
            rows=[(r['name'],r['organisation']) for r in db.execute("""select e.name,a.organisation from judicial_affiliation a join entity e on e.id=a.person_id where a.kind='education' and e.category=?""",(cat,))]
        else:
            q=','.join('?'*len(ids))
            rows=[(r['name'],r['organisation']) for r in db.execute(f"""select e.name,o.name organisation from claim c join assertion a on a.claim_id=c.id and a.status='verified' join entity e on e.id=c.subject_id join entity o on o.id=c.object_id where c.predicate='educated_at' and c.subject_id in ({q})""",ids)] if ids else []
        for name,org in rows:
            people[name]=label
            for inst in canon2(org or ''):
                links[inst].add(name); inst_people[inst][label].add(name)
        cat_educated[label]+=len({n for n,_ in rows})
    for inst, by in inst_people.items():
        for label, ps in by.items():
            inst_track[inst][label] = len(ps)
    # dedupe group labels: DG + DDG counted as one
    cat_people['DGs/DDGs']=len({r[0] for r in db.execute("select id from entity where category in ('dg','ddg') and status='active'")})
    cat_educated['DGs/DDGs']=len({n for n,l in people.items() if l=='DGs/DDGs'})
    total=len(people); total_links=sum(len(v) for v in links.values())
    tracks=['Commissioners','DGs/DDGs','Corporate elites','Judicial']
    with open('audit/education_aggregate_non_mep.csv','w',newline='') as f:
        w=csv.writer(f); w.writerow(['institution','people','share_all']+tracks)
        for inst,ps in sorted(links.items(),key=lambda kv:(-len(kv[1]),kv[0])):
            w.writerow([inst,len(ps),round(len(ps)/total,4)]+[inst_track[inst][t] for t in tracks])
    lines=['# Education by institution and job type, excluding MEPs','',f'Educated people: **{total}**; person-institution links: **{total_links}**; distinct institutions: **{len(links)}**.','', '## Coverage','', '| Group | Population | Educated | Coverage |','|---|---:|---:|---:|']
    for t in tracks:
        lines.append(f'| {t} | {cat_people[t]} | {cat_educated[t]} | {cat_educated[t]/cat_people[t]:.1%} |')
    lines += ['', '## Aggregate top institutions','', '| Institution | People | Share | Commissioners | DGs/DDGs | Corporate | Judicial |','|---|---:|---:|---:|---:|---:|---:|']
    for inst,ps in sorted(links.items(),key=lambda kv:(-len(kv[1]),kv[0]))[:20]:
        lines.append(f'| {inst} | {len(ps)} | {len(ps)/total:.1%} | {inst_track[inst]["Commissioners"]} | {inst_track[inst]["DGs/DDGs"]} | {inst_track[inst]["Corporate elites"]} | {inst_track[inst]["Judicial"]} |')
    lines += ['', '## Top institutions by job type','']
    for t in tracks:
        lines += [f'### {t} (educated denominator {cat_educated[t]})','','| Institution | People | Share of educated |','|---|---:|---:|']
        vals=[(i,c[t]) for i,c in inst_track.items() if c[t]]
        for inst,n in sorted(vals,key=lambda x:(-x[1],x[0]))[:10]:
            lines.append(f'| {inst} | {n} | {n/cat_educated[t]:.1%} |')
        lines.append('')
    top5=set(i for i,_ in sorted(links.items(),key=lambda kv:(-len(kv[1]),kv[0]))[:5])
    covered={p for i in top5 for p in links[i]}
    lines += ['## Concentration','',f'- Top 5 institutions cover **{len(covered)}/{total}** educated people ({len(covered)/total:.1%}).',f'- Mean institutions per educated person: **{total_links/total:.2f}**.','', '## Caveats','', '- Denominator is educated people, not the full population; coverage differs greatly by track.', '- MEPs are excluded.', '- Counts are person-institution presences, not degree rows.', '- Institution names are normalized conservatively; residual variants remain in the CSV.', '- Corporate education coverage is much lower than commissioner, DG/DDG and judicial coverage.', '- This is descriptive association, not a causal effect.']
    Path('audit/education_aggregate_non_mep.md').write_text('\n'.join(lines),encoding='utf-8')
    print('people',total,'links',total_links,'institutions',len(links),'coverage',{t:(cat_educated[t],cat_people[t]) for t in tracks})
if __name__=='__main__': main()
