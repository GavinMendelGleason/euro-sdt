#!/usr/bin/env python3
"""Analyse judicial education by institution and job type."""
from __future__ import annotations
import csv, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from euro_sdt.v2.db import connect

COUNTRIES = r'(?:Slovenia|Malta|Estonia|France|Croatia|Slovakia|Sweden|Lithuania|Finland|Denmark|Romania|Austria|Greece|Hungary|Belgium|Poland|Spain|Italy|Germany|United Kingdom|UK|Ireland|Netherlands|Portugal|Czech Republic|Czechia|Bulgaria|Latvia|Luxembourg|Cyprus|Norway|Switzerland|United States|USA|Canada|Australia|Tunisia|Tunis)'
ALIAS = {
 'universita degli studi di firenze':'University of Florence','university of florence':'University of Florence',
 'panepistimio athinon':'National and Kapodistrian University of Athens','ethniko kai kapodistriako panepistimio athinon':'National and Kapodistrian University of Athens','national and kapodistrian university of athens':'National and Kapodistrian University of Athens',
 'universite libre de bruxelles':'Université libre de Bruxelles','free university of brussels':'Université libre de Bruxelles',
 'catholic university of louvain':'UCLouvain','universite catholique de louvain':'UCLouvain','university of louvain':'UCLouvain','catholic university of leuven':'UCLouvain','uclouvain':'UCLouvain',
 'fitzwilliam college university of cambridge':'University of Cambridge',"king s college of the university of cambridge":'University of Cambridge','university of cambridge':'University of Cambridge',
 'universite paris ii':'Université Paris II Panthéon-Assas','university paris 2 pantheon assas':'Université Paris II Panthéon-Assas','university of paris pantheon assas':'Université Paris II Panthéon-Assas','university of law economics and social sciences of university paris 2 pantheon assas':'Université Paris II Panthéon-Assas','pantheon assas university':'Université Paris II Panthéon-Assas','university of paris ii':'Université Paris II Panthéon-Assas',
 'paris 1 pantheon sorbonne university':'Université Paris 1 Panthéon-Sorbonne','universite paris 1 pantheon sorbonne':'Université Paris 1 Panthéon-Sorbonne','university of paris i pantheon sorbonne':'Université Paris 1 Panthéon-Sorbonne',
 'ecole nationale de la magistrature':'École nationale de la magistrature','national school for the judiciary bordeaux':'École nationale de la magistrature',
 'national school of administration':'École nationale d’administration','ecole nationale d administration':'École nationale d’administration',
 'universitat bonn':'University of Bonn','rhenish friedrich wilhelm university of bonn':'University of Bonn','university of bonn':'University of Bonn',
 'tartu ulikool':'University of Tartu','university of tartu':'University of Tartu','vilniaus universitetas':'Vilnius University','university of vilnius':'Vilnius University',
 'mykolo romerio universitetas':'Mykolas Romeris University','mykolas romeris university':'Mykolas Romeris University',
 'london school of economics and political science':'London School of Economics','london school of economics':'London School of Economics','university college london':'University College London',
 'college of europe':'College of Europe','college of europe in bruges':'College of Europe','college of europe bruges':'College of Europe',
 'harvard university':'Harvard University','harvard law school':'Harvard University','university of stockholm':'Stockholm University','stockholm university':'Stockholm University',
 'university of utrecht':'Utrecht University','utrecht university':'Utrecht University','university of leiden':'Leiden University','leiden university':'Leiden University',
 'vienna university':'University of Vienna','university of vienna':'University of Vienna','cologne':'University of Cologne','university of cologne':'University of Cologne',
 'jean monnet faculty of the paris sud university':'University of Paris-Sud','universite paris sud saclay':'University of Paris-Sud','university of paris sud':'University of Paris-Sud',
 'university of silesia':'University of Silesia in Katowice','university of silesia in katowice':'University of Silesia in Katowice',
 'university of ljubljana':'University of Ljubljana','university of malta':'University of Malta','university of zagreb':'University of Zagreb',
 'comenius university in bratislava':'Comenius University Bratislava','comenius university bratislava':'Comenius University Bratislava','comenius university':'Comenius University Bratislava',
 'university of helsinki':'University of Helsinki','university of copenhagen':'University of Copenhagen','university of bucharest':'University of Bucharest','university of graz':'University of Graz',
 'eotvos lorand university':'Eötvös Loránd University','eotvos lorand university budapest':'Eötvös Loránd University','university of strasbourg':'University of Strasbourg','aristotle university of thessaloniki':'Aristotle University of Thessaloniki',
 'charles university':'Charles University','charles university in prague':'Charles University','jagiellonian university of krakow':'Jagiellonian University','jagiellonian university':'Jagiellonian University',
 'university of coimbra':'University of Coimbra','university of poitiers':'University of Poitiers','university college dublin':'University College Dublin','comillas pontifical university':'Comillas Pontifical University','saarland university':'Saarland University',
 'university of leicester':'University of Leicester','university of michigan':'University of Michigan','university of oxford':'University of Oxford','university of latvia':'University of Latvia','aarhus university':'Aarhus University','lund university':'Lund University','university of szeged':'University of Szeged',
}

def norm(s: str) -> str:
    s=s.replace('\xa0',' ').replace('’',"'").replace('‘',"'").replace('–','-')
    return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip()

def canon(org: str) -> list[str]:
    out=[]
    for part in [x.strip() for x in re.split(r';',org) if x.strip()]:
        m=re.search(r'\(([^()]*(?:University|College|School|Institute|Academy|Universit|Universidad)[^()]*)\)',part)
        if m: part=m.group(1)
        part=re.sub(r'\s*\([^()]*\)\s*$','',part)
        part=re.sub(r',\s*'+COUNTRIES+r'\s*$','',part,flags=re.I)
        n=norm(part)
        if not n or n in {'germany','france','italy','spain','united kingdom','belgium','netherlands','portugal','greece','poland','romania','sweden','finland','denmark','austria','ireland','malta','croatia','slovenia','estonia','latvia','lithuania','luxembourg','cyprus','hungary','slovakia','czech republic','bulgaria'}:
            continue
        out.append(ALIAS.get(n,part.strip()))
    return out

def main() -> int:
    db=connect(); db.row_factory=__import__('sqlite3').Row
    rows=db.execute("""select e.name,e.category,a.organisation from judicial_affiliation a join entity e on e.id=a.person_id
    where a.kind='education' and e.category in ('cjeu_judge','cjeu_ag','cjeu_gc_judge','cjeu_registrar')""").fetchall()
    track={'cjeu_judge':'CJ judge','cjeu_ag':'AG','cjeu_gc_judge':'GC judge','cjeu_registrar':'Registrar'}
    people_by={}; track_by=defaultdict(Counter); all_people=set()
    for r in rows:
        all_people.add(r['name'])
        for inst in canon(r['organisation']):
            people_by.setdefault(inst,set()).add(r['name']); track_by[inst][track[r['category']]]+=1
    # Person-institution track counts: one per person per institution.
    inst_track=defaultdict(Counter)
    for inst,people in people_by.items():
        for p in people:
            cat=db.execute("select category from entity where name=? and kind='person'",(p,)).fetchone()
            if cat: inst_track[inst][track[cat[0]]]+=1
    denom=Counter()
    for p in all_people:
        c=db.execute("select category from entity where name=? and kind='person'",(p,)).fetchone()
        if c: denom[track[c[0]]]+=1
    total_people=len(all_people); total_links=sum(len(v) for v in people_by.values())
    out=Path('audit/judicial_education_institutions.csv')
    with out.open('w',newline='') as f:
        w=csv.writer(f); w.writerow(['institution','people','share_all','cj_judge','ag','gc_judge','registrar','top_track'])
        for inst,people in sorted(people_by.items(), key=lambda kv:(-len(kv[1]),kv[0])):
            tr=inst_track[inst]
            w.writerow([inst,len(people),round(len(people)/total_people,4),tr['CJ judge'],tr['AG'],tr['GC judge'],tr['Registrar'],tr.most_common(1)[0][0] if tr else ''])
    # Markdown summary
    lines=['# Judicial education by institution','',f'People with at least one education row: **{total_people}**.',f'Person-institution links: **{total_links}**; mean institutions per person: **{total_links/total_people:.2f}**.','', '## Aggregate top institutions','', '| Institution | People | Share | CJ judge | AG | GC judge |','|---|---:|---:|---:|---:|---:|']
    for inst,people in sorted(people_by.items(), key=lambda kv:(-len(kv[1]),kv[0]))[:15]:
        tr=inst_track[inst]; lines.append(f'| {inst} | {len(people)} | {len(people)/total_people:.1%} | {tr["CJ judge"]} | {tr["AG"]} | {tr["GC judge"]} |')
    lines += ['', '## By job type','']
    for label in ['CJ judge','AG','GC judge']:
        lines += [f'### {label} (denominator {denom[label]})','','| Institution | People in track | Share of track |','|---|---:|---:|']
        vals=[(inst,tr[label]) for inst,tr in inst_track.items() if tr[label]>0]
        for inst,n in sorted(vals,key=lambda x:(-x[1],x[0]))[:10]:
            lines.append(f'| {inst} | {n} | {n/denom[label]:.1%} |')
        lines.append('')
    top5=set(inst for inst,_ in sorted(people_by.items(),key=lambda kv:(-len(kv[1]),kv[0]))[:5])
    lines += ['', '## Overrepresentation by job type','', 'Location quotient = (share of track with institution) / (share of all people with institution); only institutions with at least two people in the track.','']
    for label in ['CJ judge','AG','GC judge']:
        lines += [f'### {label}','','| Institution | Track N | All N | Location quotient |','|---|---:|---:|---:|']
        vals=[]
        for inst,tr in inst_track.items():
            if tr[label] >= 2:
                vals.append((inst,tr[label],len(people_by[inst]),(tr[label]/denom[label])/(len(people_by[inst])/total_people)))
        for inst,n,alln,lq in sorted(vals,key=lambda x:(-x[3],-x[1],x[0]))[:10]:
            lines.append(f'| {inst} | {n} | {alln} | {lq:.2f} |')
        lines.append('')
    covered={p for inst in top5 for p in people_by[inst]}
    lines += ['## Concentration','',f'- Top 5 institutions cover **{len(covered)}/{total_people}** people ({len(covered)/total_people:.1%}).',f'- Distinct institutions: **{len(people_by)}**.',f'- Mean institutions per person: **{total_links/total_people:.2f}**.','', '## Caveats','', '- Counts are person-institution presences, not degree rows; a person with two degrees from one institution counts once.', '- Multiple institutions can appear in one biography sentence; strings were split on semicolons and normalized.', '- Institution names were canonicalized conservatively; residual variants remain in the CSV.', '- This is descriptive association, not a causal effect of institution on job type.', '- Registrar is included in the aggregate but excluded from the three job-type tables.']
    Path('audit/judicial_education_analysis.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'people={total_people} links={total_links} institutions={len(people_by)} denom={dict(denom)}')
    return 0
if __name__=='__main__': raise SystemExit(main())
