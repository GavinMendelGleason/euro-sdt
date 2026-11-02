#!/usr/bin/env python3
"""Link 2024 CJEU intake events to their documented education institutions."""
from __future__ import annotations
import hashlib
from euro_sdt.v2.db import connect
LINKS={
 'Bernardus (Ben) Maria Polycarpus Smulders':['leiden-university','london-school-of-economics','insead'],
 'Fredrik Schalin':['stockholm-university'],
 'Stéphane Gervasoni':['ecole-nationale-d-administration'],
 'Niels Fenger':['university-of-copenhagen','aarhus-university'],
 'Ramona Frendo':['university-of-malta','university-of-cambridge'],
 'Dean Spielmann':['universite-catholique-de-louvain','university-of-cambridge'],
 'Andrea Biondi':['universita-degli-studi-di-firenze-university-of-florence-italy'],
 'Rimvydas Norkus':['vilnius-university'],
 'Hervé Cassagnabère':['ecole-nationale-d-administration','hec-paris'],
 'Raphaël Meyer':['universite-de-paris-ii-assas','university-of-oxford','college-of-europe','university-of-paris-sud'],
}
def main():
 db=connect();db.row_factory=__import__('sqlite3').Row
 n=0
 for name,iids in LINKS.items():
  p=db.execute("select id from entity where name=? and kind='person'",(name,)).fetchone()
  if not p: print('missing person',name); continue
  track=db.execute("select track from role_intake where person_id=?",(p[0],)).fetchone()
  if not track: print('missing intake',name); continue
  for iid in iids:
   if not db.execute("select 1 from entity where id=?",(iid,)).fetchone(): print('missing institution',iid); continue
   rid='ri-inst-'+hashlib.sha1(f'{p[0]}|{iid}|2024'.encode()).hexdigest()[:16]
   db.execute("insert or replace into role_intake (id,person_id,institution_id,position_id,track,intake_year,source_doc_id,source_quote,notes) values (?,?,?,?,?,?,?,?,?)",(rid,p[0],iid,None,track[0],2024,'official-cjeu-cp240174-2024','Education affiliations from the official CURIA biography; intake date from Press Release 174/24','Institution-linked intake row'))
   n+=1
 db.commit();print('institution links',n)
if __name__=='__main__': main()
