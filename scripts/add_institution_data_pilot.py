#!/usr/bin/env python3
"""Add the first exact institution cohort and position-opening records."""
from __future__ import annotations
import sqlite3
from euro_sdt.v2.db import connect

COHORTS=[
 ('coe-2024-all','college-of-europe','All programmes',2024,None,None,496,None,
  'https://www.coleurope.eu/sites/default/files/uploads/news/Rector%20Mogherini%20-%202020-2025%20Mandate%20Report.pdf',
  'sources/official/college-of-europe-2020-2025-mandate-report.txt',
  '2024-25 enrolment record; graduates not stated'),
 ('insp-2025-fi-a','ecole-nationale-d-administration','Formation initiale, promotion 2025-2027 A',2025,None,61,61,None,
  'https://www.insp.gouv.fr/files/files/institut/donnees-ressources/rapport-activite/rapport_activite_insp_2024_light.pdf',
  'sources/official/insp-activity-report-2024.txt',
  '61 students admitted to promotion 2025-2027 A; graduates not yet observed'),
]
POSITIONS=[
 ('cjeu-2024-openings-cj','CJEU Court of Justice','european-court-of-justice','Judges',2024,6,
  'https://curia.europa.eu/site/upload/docs/application/pdf/2024-10/cp240174en.pdf',
  'Six new Judges appointed on 7 October 2024; renewals excluded'),
 ('cjeu-2024-openings-ag','CJEU Court of Justice','european-court-of-justice','Advocates General',2024,3,
  'https://curia.europa.eu/site/upload/docs/application/pdf/2024-10/cp240174en.pdf',
  'Three new Advocates General appointed on 7 October 2024; renewals excluded'),
 ('cjeu-2024-openings-gc','CJEU General Court','general-court-of-the-european-union','Judges',2024,2,
  'https://curia.europa.eu/site/upload/docs/application/pdf/2024-10/cp240174en.pdf',
  'Two new General Court Judges appointed on 7 October 2024'),
]
def main():
 db=connect();db.row_factory=sqlite3.Row
 for cid,iid,prog,year,app,adm,enr,grad,url,sf,notes in COHORTS:
  db.execute("insert or replace into institution_cohort (id,institution_id,programme,year,applicants,admitted,enrolled,graduates,source_url,source_file,notes) values (?,?,?,?,?,?,?,?,?,?,?)",(cid,iid,prog,year,app,adm,enr,grad,url,sf,notes))
 for pid,track,org,role,year,op,url,notes in POSITIONS:
  db.execute("insert or replace into position_census (id,track,organisation_id,role,year,stock,openings,source_url,source_file,notes) values (?,?,?,?,?,?,?,?,?,?)",(pid,track,org,role,year,None,op,url,'sources/official/cjeu-cp240174-2024.pdf',notes))
 db.commit();print('cohorts',len(COHORTS),'position rows',len(POSITIONS))
if __name__=='__main__': main()
