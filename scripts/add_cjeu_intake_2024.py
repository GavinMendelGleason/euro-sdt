#!/usr/bin/env python3
"""Record 2024 CJEU intake events; position/institution linkage is a later step."""
from __future__ import annotations
import hashlib, sqlite3
from euro_sdt.v2.db import connect
PEOPLE={
 'Bernardus (Ben) Maria Polycarpus Smulders':'Court of Justice judges',
 'Massimo Condinanzi':'Court of Justice judges',
 'Fredrik Schalin':'Court of Justice judges',
 'Stéphane Gervasoni':'Court of Justice judges',
 'Niels Fenger':'Court of Justice judges',
 'Ramona Frendo':'Court of Justice judges',
 'Dean Spielmann':'Advocates General',
 'Andrea Biondi':'Advocates General',
 'Rimvydas Norkus':'Advocates General',
 'Hervé Cassagnabère':'General Court judges',
 'Raphaël Meyer':'General Court judges',
}
def main():
 db=connect();db.row_factory=sqlite3.Row
 for name,track in PEOPLE.items():
  p=db.execute("select id from entity where name=? and kind='person'",(name,)).fetchone()
  if not p: print('missing person',name); continue
  rid='ri-'+hashlib.sha1(f'{p[0]}|{track}|2024'.encode()).hexdigest()[:16]
  db.execute("insert or replace into role_intake (id,person_id,institution_id,position_id,track,intake_year,source_doc_id,source_quote,notes) values (?,?,?,?,?,?,?,?,?)",(rid,p[0],None,None,track,2024,'official-cjeu-cp240174-2024','Appointed with effect from 7 October 2024','CURIA Press Release 174/24; position and institution linkage pending'))
 db.commit();print('intake rows',db.execute('select count(*) from role_intake').fetchone()[0])
if __name__=='__main__': main()
