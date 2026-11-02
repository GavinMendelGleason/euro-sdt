#!/usr/bin/env python3
"""Seed institution profiles and the first position census without inventing production data."""
from __future__ import annotations
import sqlite3
from euro_sdt.v2.db import connect, now
from euro_sdt.v2.entities import create_entity

PROFILES = {
 'college-of-europe': 'College of Europe',
 'harvard': 'Harvard University',
 'university-of-cambridge': 'University of Cambridge',
 'ecole-nationale-d-administration': "École nationale d'administration",
 'london-school-of-economics': 'London School of Economics',
 'universite-catholique-de-louvain': 'UCLouvain',
 'university-of-oxford': 'University of Oxford',
 'vilnius-university': 'Vilnius University',
 'ecole-polytechnique': 'École Polytechnique',
 'university-of-cologne': 'University of Cologne',
}
POSITIONS = [
 ('cjeu-court-judges','CJEU Court of Justice','european-court-of-justice','Judges',2026,27,'https://curia.europa.eu/site/jcms/d2_5093/en/the-court-of-justice','Official composition: 27 Judges'),
 ('cjeu-court-ags','CJEU Court of Justice','european-court-of-justice','Advocates General',2026,11,'https://curia.europa.eu/site/jcms/d2_5093/en/the-court-of-justice','Official composition: 11 Advocates General'),
 ('cjeu-general-court-judges','CJEU General Court','general-court-of-the-european-union','Judges',2026,53,'https://curia.europa.eu/site/jcms/qua1_6250/en/members-of-the-general-court','Rendered roster lists 53; official prose states 54'),
 ('cjeu-registrar','CJEU Court of Justice','european-court-of-justice','Registrar',2026,1,'https://curia.europa.eu/site/jcms/d2_5096/en/court-of-justice','One Registrar'),
 ('commission-college','European Commission','european-commission','Commissioners',2026,27,'https://commission.europa.eu/about/organisation/college-commissioners_en','College of Commissioners'),
 ('commission-dg-ddg','European Commission','european-commission','Directors-General and Deputy Directors-General',2026,85,'internal:role_tenure','Count from the active DG/DDG frame; not an official establishment table'),
]
def main():
 db=connect(); db.row_factory=sqlite3.Row
 for eid,name in PROFILES.items():
  if not db.execute("select 1 from entity where id=?",(eid,)).fetchone():
   print('missing institution',eid,name); continue
  db.execute("insert or replace into institution_profile (institution_id,institution_type,country,founded,selectivity,source_url,status,notes) values (?,?,?,?,?,?,?,?)",(eid,'university',None,None,None,None,'provisional','Seeded from graph entity; no admissions yet'))
 # ensure General Court entity
 gc=db.execute("select id from entity where name='General Court of the European Union'").fetchone()
 if not gc: gc_id=create_entity(db,'General Court of the European Union','organisation',category='court')
 else: gc_id=gc[0]
 for pid,track,org,role,year,stock,url,notes in POSITIONS:
  if org=='general-court-of-the-european-union': org=gc_id
  db.execute("insert or replace into position_census (id,track,organisation_id,role,year,stock,openings,source_url,source_file,notes) values (?,?,?,?,?,?,?,?,?,?)",(pid,track,org,role,year,stock,None,url,None,notes))
 db.commit();print('profiles',len(PROFILES),'positions',len(POSITIONS))
if __name__=='__main__': main()
