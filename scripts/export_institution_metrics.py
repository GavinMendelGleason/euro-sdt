#!/usr/bin/env python3
"""Export observed institution metrics; production and openings remain null until collected."""
from __future__ import annotations
import csv
from pathlib import Path
from euro_sdt.v2.db import connect
COUNTS={
 'college-of-europe': {'Commissioners':3,'DGs/DDGs':8,'Corporate elites':0,'Judicial':7},
 'harvard': {'Commissioners':6,'DGs/DDGs':2,'Corporate elites':0,'Judicial':6},
 'university-of-cambridge': {'Commissioners':2,'DGs/DDGs':3,'Corporate elites':0,'Judicial':5},
 'ecole-nationale-d-administration': {'Commissioners':3,'DGs/DDGs':0,'Corporate elites':1,'Judicial':6},
 'london-school-of-economics': {'Commissioners':4,'DGs/DDGs':1,'Corporate elites':1,'Judicial':2},
 'universite-catholique-de-louvain': {'Commissioners':1,'DGs/DDGs':2,'Corporate elites':1,'Judicial':4},
 'university-of-oxford': {'Commissioners':3,'DGs/DDGs':1,'Corporate elites':2,'Judicial':2},
 'vilnius-university': {'Commissioners':3,'DGs/DDGs':0,'Corporate elites':0,'Judicial':4},
 'ecole-polytechnique': {'Commissioners':0,'DGs/DDGs':0,'Corporate elites':7,'Judicial':0},
 'university-of-cologne': {'Commissioners':2,'DGs/DDGs':0,'Corporate elites':1,'Judicial':3},
}
def main():
 db=connect(); db.row_factory=__import__('sqlite3').Row
 for iid, tracks in COUNTS.items():
  for track,n in tracks.items():
   db.execute("insert or replace into institution_metric (institution_id,track,observed_alumni,observed_role_holders,production,openings,placement_rate,overproduction_ratio,source_status) values (?,?,?,?,?,?,?,?,?)",(iid,track,n,n,None,None,None,None,'observed_only'))
 db.commit()
 out=Path('graph/institution_metrics.csv'); out.parent.mkdir(exist_ok=True)
 with out.open('w',newline='') as f:
  w=csv.writer(f); w.writerow(['institution_id','institution_name','track','observed_alumni','observed_role_holders','production','openings','placement_rate','overproduction_ratio','source_status'])
  for r in db.execute("""select m.*,e.name from institution_metric m join entity e on e.id=m.institution_id order by e.name,m.track"""):
   w.writerow([r['institution_id'],r['name'],r['track'],r['observed_alumni'],r['observed_role_holders'],r['production'],r['openings'],r['placement_rate'],r['overproduction_ratio'],r['source_status']])
 print('metrics',db.execute('select count(*) from institution_metric').fetchone()[0])
if __name__=='__main__': main()
