#!/usr/bin/env python3
"""Import programme cohorts and annual CJEU openings."""
from __future__ import annotations
import csv, hashlib, sqlite3
from pathlib import Path
COHORTS=sorted(Path('data/institutions/cohort_fragments').glob('batch_*.csv'))
POSITIONS=sorted(Path('data/institutions/position_fragments').glob('batch_*.csv'))
def num(v):
 v=(v or '').strip()
 return int(v) if v else None
def main():
 db=sqlite3.connect('euro_sdt_v2.db');db.row_factory=sqlite3.Row
 cohort_fields=['institution_id','programme','year','applicants','admitted','enrolled','graduates','source_url','source_file','notes']
 pos_fields=['track','organisation_id','role','year','openings','source_url','source_file','notes']
 # Replace only pilot cohort/openings rows; keep stock rows.
 db.execute('delete from institution_cohort'); db.execute('delete from position_census where openings is not null')
 inserted=0; skipped=[]
 for p in COHORTS:
  for r in csv.DictReader(p.open()):
   iid=r['institution_id']; sf=Path(r['source_file'])
   if not db.execute('select 1 from entity where id=?',(iid,)).fetchone(): skipped.append((iid,'institution')); continue
   if not sf.exists(): skipped.append((iid,'source file')); continue
   cid='ic-'+hashlib.sha1('|'.join([iid,r['programme'],r['year'],r['source_quote'] if 'source_quote' in r else r['notes']]).encode()).hexdigest()[:16]
   db.execute('insert or replace into institution_cohort (id,institution_id,programme,year,applicants,admitted,enrolled,graduates,source_url,source_file,notes) values (?,?,?,?,?,?,?,?,?,?,?)',(cid,iid,r['programme'],int(r['year']),num(r['applicants']),num(r['admitted']),num(r['enrolled']),num(r['graduates']),r['source_url'],r['source_file'],r['notes'])); inserted+=1
 posins=0
 for p in POSITIONS:
  for r in csv.DictReader(p.open()):
   oid=r['organisation_id']; sf=Path(r['source_file'])
   if not db.execute('select 1 from entity where id=?',(oid,)).fetchone(): skipped.append((oid,'organisation')); continue
   if not sf.exists(): skipped.append((oid,'source file')); continue
   pid='pc-'+hashlib.sha1('|'.join([r['track'],oid,r['role'],r['year'],r['openings'],r['notes'][:100]]).encode()).hexdigest()[:16]
   db.execute('insert or replace into position_census (id,track,organisation_id,role,year,stock,openings,source_url,source_file,notes) values (?,?,?,?,?,?,?,?,?,?)',(pid,r['track'],oid,r['role'],int(r['year']),None,num(r['openings']),r['source_url'],r['source_file'],r['notes'])); posins+=1
 db.commit();print('cohorts',inserted,'positions',posins,'skipped',len(skipped));print('skips',skipped[:10])
if __name__=='__main__': main()
