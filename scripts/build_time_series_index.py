#!/usr/bin/env python3
"""Build the catalogue of institution time series."""
from __future__ import annotations
import csv, re, sqlite3
from collections import defaultdict
from pathlib import Path

METRICS = ['applicants', 'admitted', 'enrolled', 'graduates']
CHART = {
    'college-of-europe': 'assets/papers/methodology/gating-trajectories/college-of-europe.png',
    'harvard': 'assets/papers/methodology/gating-trajectories/harvard.png',
    'ecole-polytechnique': 'assets/papers/methodology/gating-trajectories/ecole-polytechnique.png',
    'university-of-oxford': 'assets/papers/methodology/gating-trajectories/oxford.png',
    'university-of-cologne': 'assets/papers/methodology/gating-trajectories/cologne.png',
    'london-school-of-economics': 'assets/papers/methodology/gating-trajectories/lse.png',
    'ecole-nationale-d-administration': 'assets/papers/methodology/gating-trajectories/ena-insp.png',
}

def main():
    db=sqlite3.connect('euro_sdt_v2.db'); db.row_factory=sqlite3.Row
    rows=[]
    groups=db.execute("select distinct institution_id, programme from institution_cohort order by institution_id, programme").fetchall()
    for g in groups:
        iid,prog=g['institution_id'],g['programme']
        for metric in METRICS:
            q=f"select year,source_url,notes from institution_cohort where institution_id=? and programme=? and {metric} is not null order by year"
            obs=db.execute(q,(iid,prog)).fetchall()
            if not obs: continue
            years=[r['year'] for r in obs]
            sources=sorted({r['source_url'] for r in obs if r['source_url']})
            sid=f"{iid}::{re.sub(r'[^a-z0-9]+','-',prog.lower()).strip('-')}::{metric}"
            rows.append({
                'series_id': sid, 'institution_id': iid, 'programme': prog, 'metric': metric,
                'first_year': min(years), 'last_year': max(years), 'n_obs': len(obs),
                'has_gaps': 'yes' if max(years)-min(years)+1 > len(obs) else 'no',
                'storage': 'euro_sdt_v2.db:institution_cohort',
                'chart': CHART.get(iid,''),
                'source_urls': '; '.join(sources),
                'notes': obs[0]['notes'] or '',
            })
    # Degree/qualifier CSV series
    degree_rows=list(csv.DictReader(open('data/institutions/degrees_awarded.csv')))
    degree_groups=defaultdict(list)
    for r in degree_rows:
        degree_groups[(r['institution_id'],r['programme'],r['metric'])].append(r)
    for (iid,prog,metric),rr in sorted(degree_groups.items()):
        years=[int(x['year']) for x in rr]
        rows.append({
            'series_id':f"{iid}::{re.sub(r'[^a-z0-9]+','-',prog.lower()).strip('-')}::{re.sub(r'[^a-z0-9]+','-',metric.lower()).strip('-')}",
            'institution_id':iid,'programme':prog,'metric':metric,
            'first_year':min(years),'last_year':max(years),'n_obs':len(rr),
            'has_gaps':'yes' if max(years)-min(years)+1>len(rr) else 'no',
            'storage':'data/institutions/degrees_awarded.csv','chart':'',
            'source_urls':'; '.join(sorted({x['source_url'] for x in rr if x['source_url']})),
            'notes':'Degree/qualifier series; see audit/degrees_awarded_sources.md'
        })
    # CSV-only series
    places=list(csv.DictReader(open('data/institutions/ena_places_offered.csv')))
    rows.append({
        'series_id':'ecole-nationale-d-administration::places-offered::places_offered',
        'institution_id':'ecole-nationale-d-administration','programme':'Entrance concours','metric':'places_offered',
        'first_year':min(int(r['year']) for r in places),'last_year':max(int(r['year']) for r in places),'n_obs':len(places),
        'has_gaps':'no','storage':'data/institutions/ena_places_offered.csv','chart':'assets/papers/methodology/ena-insp-history.png',
        'source_urls':'; '.join(sorted({r['source_url'] for r in places})),'notes':'Places offered, not output.'
    })
    pop=list(csv.DictReader(open('data/institutions/eu_population.csv')))
    rows.append({
        'series_id':'eu-ec-population::member-states::population',
        'institution_id':'EU/EC','programme':'Member states at each date','metric':'population',
        'first_year':min(int(r['year']) for r in pop),'last_year':max(int(r['year']) for r in pop),'n_obs':len(pop),
        'has_gaps':'no','storage':'data/institutions/eu_population.csv','chart':'assets/papers/methodology/gating-trajectories-combined.png',
        'source_urls':'https://data.worldbank.org/indicator/SP.POP.TOTL','notes':'Sum of member states at each date; membership recorded in file.'
    })
    out=Path('data/institutions/time_series_index.csv')
    fields=['series_id','institution_id','programme','metric','first_year','last_year','n_obs','has_gaps','storage','chart','source_urls','notes']
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); rows.sort(key=lambda r:(r['institution_id'],r['programme'],r['metric'])); w.writerows(rows)
    print(out, len(rows))

if __name__=='__main__': main()
