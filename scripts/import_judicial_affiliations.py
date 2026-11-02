#!/usr/bin/env python3
"""Import CJEU education, memberships, fellowships, awards and post-CJEU roles."""
from __future__ import annotations
import csv, hashlib, sqlite3
from pathlib import Path
from euro_sdt.v2.db import connect, now
FIELDS=["person","kind","organisation","role","start_date","end_date","start_precision","end_precision","source_url","source_file","source_quote","notes"]
FRAGMENTS=sorted(Path("data/cjeu/enrichment_fragments").glob("batch_*.csv"))
def main():
 db=connect(); db.row_factory=sqlite3.Row
 db.executescript('''CREATE TABLE IF NOT EXISTS judicial_affiliation (id TEXT PRIMARY KEY, person_id TEXT NOT NULL, kind TEXT NOT NULL, organisation TEXT, role TEXT, start_date TEXT, end_date TEXT, start_precision TEXT, end_precision TEXT, source_url TEXT, source_file TEXT, source_quote TEXT, notes TEXT); CREATE INDEX IF NOT EXISTS idx_judicial_affiliation_person ON judicial_affiliation(person_id); CREATE INDEX IF NOT EXISTS idx_judicial_affiliation_kind ON judicial_affiliation(kind);''')
 rows=[]; skipped=[]
 for p in FRAGMENTS:
  with p.open(newline="",encoding="utf-8") as f:
   for r in csv.DictReader(f): rows.append({k:r.get(k,"") for k in FIELDS})
 inserted=0
 for r in rows:
  person=db.execute("SELECT id FROM entity WHERE name=? AND kind='person'",(r["person"],)).fetchone()
  if not person: skipped.append((r["person"],"person")); continue
  sf=Path(r["source_file"])
  if not sf.exists(): skipped.append((r["person"],"file")); continue
  text=sf.read_text(errors="replace")
  if r["source_quote"] not in text: skipped.append((r["person"],"quote")); continue
  rid="ja-"+hashlib.sha1("|".join([person[0],r["kind"],r["organisation"],r["role"],r["start_date"],r["source_quote"][:100]]).encode()).hexdigest()[:16]
  db.execute("INSERT OR REPLACE INTO judicial_affiliation (id,person_id,kind,organisation,role,start_date,end_date,start_precision,end_precision,source_url,source_file,source_quote,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,person[0],r["kind"],r["organisation"],r["role"],r["start_date"],r["end_date"],r["start_precision"],r["end_precision"],r["source_url"],r["source_file"],r["source_quote"],r["notes"]))
  inserted+=1
 db.commit();print(f"rows={len(rows)} inserted={inserted} skipped={len(skipped)}")
 for s in skipped[:10]: print("SKIP",s)
 return 0
if __name__=="__main__": raise SystemExit(main())
