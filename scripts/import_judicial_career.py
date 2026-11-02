#!/usr/bin/env python3
"""Import CJEU career fragments and register their official source texts."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
from euro_sdt.v2.db import PROJECT_ROOT, connect, now, sha256_text
from euro_sdt.v2.tokenizer import sentence_spans

FRAGMENTS = sorted(Path("data/cjeu/career_fragments").glob("batch_*.csv"))
FIELDS = ["person","role","organisation","start_date","end_date","start_precision","end_precision",
          "source_url","source_file","source_quote","category"]

def main() -> int:
    db = connect(); db.row_factory = __import__("sqlite3").Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS judicial_career (
        id TEXT PRIMARY KEY,
        person_id TEXT NOT NULL,
        role TEXT NOT NULL,
        organisation TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        start_precision TEXT,
        end_precision TEXT,
        category TEXT,
        source_doc_id TEXT,
        source_url TEXT,
        source_file TEXT,
        source_quote TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_judicial_career_person ON judicial_career(person_id);
    CREATE INDEX IF NOT EXISTS idx_judicial_career_category ON judicial_career(category);
    ''')
    rows=[]
    for path in FRAGMENTS:
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                rows.append({k: row.get(k,"") for k in FIELDS})
    inserted=0; docs=0; missing=[]
    doc_cache={}
    for row in rows:
        p=db.execute("SELECT id FROM entity WHERE name=? AND kind='person'",(row["person"],)).fetchone()
        if not p:
            a=db.execute("SELECT entity_id FROM entity_alias WHERE alias=?",(row["person"],)).fetchone()
            p=db.execute("SELECT id FROM entity WHERE id=?",(a["entity_id"],)).fetchone() if a else None
        if not p:
            missing.append((row["person"],"person not found")); continue
        sf=Path(row["source_file"])
        if not sf.exists():
            missing.append((row["person"],f"missing source {sf}")); continue
        text=sf.read_text(errors="replace")
        if row["source_quote"] and row["source_quote"] not in text:
            missing.append((row["person"],"quote not found")); continue
        key=(p["id"], str(sf))
        doc_id=doc_cache.get(key)
        if not doc_id:
            existing=db.execute("SELECT id FROM source_document WHERE local_path=? AND subject_id=?",(str(sf),p["id"])).fetchone()
            doc_id=existing["id"] if existing else "cjeu-career-" + hashlib.sha1(f"{p['id']}|{sf}".encode()).hexdigest()[:12]
            if not existing:
                db.execute("DELETE FROM sentence WHERE doc_id=?",(doc_id,))
                db.execute("INSERT INTO source_document (id,kind,title,url,local_path,text_sha256,char_count,sentence_count,retrieved_at,revision_id,access_date,license,subject_id,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (doc_id,"official",f"CJEU biography: {row['person']}",row["source_url"],str(sf),sha256_text(text),len(text),0,now(),None,now()[:10],"Official public document",p["id"],json.dumps({"source":"CJEU biography"},ensure_ascii=False)))
                spans=sentence_spans(text)
                db.executemany("INSERT INTO sentence (id,doc_id,ordinal,char_start,char_end,text,text_sha256) VALUES (?,?,?,?,?,?,?)",[(f"{doc_id}:{s.ordinal}",doc_id,s.ordinal,s.char_start,s.char_end,s.text,sha256_text(s.text)) for s in spans])
                db.execute("UPDATE source_document SET sentence_count=? WHERE id=?",(len(spans),doc_id)); docs+=1
            doc_cache[key]=doc_id
        cid="jc-"+hashlib.sha1("|".join([p["id"],row["role"],row["organisation"],row["start_date"],row["end_date"],row["source_quote"][:100]]).encode()).hexdigest()[:16]
        db.execute("INSERT OR REPLACE INTO judicial_career (id,person_id,role,organisation,start_date,end_date,start_precision,end_precision,category,source_doc_id,source_url,source_file,source_quote) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (cid,p["id"],row["role"],row["organisation"],row["start_date"],row["end_date"],row["start_precision"],row["end_precision"],row["category"],doc_id,row["source_url"],row["source_file"],row["source_quote"]))
        inserted+=1
    db.commit()
    print(f"rows={len(rows)} inserted={inserted} source_docs_added={docs} skipped={len(missing)}")
    for m in missing[:10]: print("SKIP",m)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
