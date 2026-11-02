#!/usr/bin/env python3
"""Attach biography source file/quote to institution-linked 2024 intake rows."""
from __future__ import annotations
import sqlite3
from euro_sdt.v2.db import connect
PATTERNS={
 'leiden-university':'Leiden',
 'london-school-of-economics':'London School',
 'insead':'INSEAD',
 'stockholm-university':'Stockholm',
 'ecole-nationale-d-administration':'administration',
 'university-of-copenhagen':'Copenhagen',
 'aarhus-university':'Aarhus',
 'university-of-malta':'Malta',
 'university-of-cambridge':'Cambridge',
 'universite-catholique-de-louvain':'Louvain',
 'universita-degli-studi-di-firenze-university-of-florence-italy':'Firenze',
 'vilnius-university':'Vilnius',
 'hec-paris':'HEC',
 'universite-de-paris-ii-assas':'Assas',
 'university-of-oxford':'Oxford',
 'college-of-europe':'College of Europe',
 'university-of-paris-sud':'Paris-Sud',
}
def main():
 db=connect();db.row_factory=sqlite3.Row
 rows=db.execute("select id,person_id,institution_id from role_intake where institution_id is not null").fetchall()
 updated=0; missing=[]
 for r in rows:
  pat=PATTERNS.get(r['institution_id'])
  if not pat: missing.append((r['institution_id'],'pattern')); continue
  aff=db.execute("""select a.source_file,a.source_url,a.source_quote from judicial_affiliation a join entity e on e.id=a.person_id
   where a.kind='education' and e.id=? and a.organisation like ? order by length(a.source_file) limit 1""",(r['person_id'],'%'+pat+'%')).fetchone()
  if not aff: missing.append((r['institution_id'],'affiliation')); continue
  db.execute("update role_intake set source_doc_id=null,source_file=?,source_url=?,source_quote=? where id=?",(aff['source_file'],aff['source_url'],aff['source_quote'],r['id']))
  updated+=1
 db.commit();print('updated',updated,'missing',len(missing));print(missing[:10])
if __name__=='__main__': main()
