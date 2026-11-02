#!/usr/bin/env python3
"""Merge collected board-role fragments and register their official sources."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from euro_sdt.v2.db import PROJECT_ROOT, connect, now, sha256_text
from euro_sdt.v2.entities import entity_id_for
from euro_sdt.v2.tokenizer import sentence_spans

MAIN = Path("data/corporate/board_roles_official_pilot.csv")
FRAGMENTS = sorted(Path("data/corporate/fragments").glob("batch_*.csv"))
FIELDS = ["company", "person", "role_kind", "role_raw", "as_of", "source_url", "source_id", "source_file"]


def main() -> int:
    rows = []
    for path in [MAIN] + FRAGMENTS:
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if not row.get("source_file"):
                    row["source_file"] = ""
                rows.append({key: row.get(key, "") for key in FIELDS})
    # Stable de-duplication: identical company/person/role/source is one row.
    seen = set()
    merged = []
    for row in rows:
        key = (row["company"], row["person"], row["role_raw"], row["source_id"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    with MAIN.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(merged)

    db = connect()
    db.row_factory = __import__("sqlite3").Row
    docs = {}
    added_docs = 0
    for row in merged:
        source_id = row["source_id"]
        source_file = row["source_file"]
        if not source_id or not source_file:
            continue
        if source_id in docs:
            continue
        path = Path(source_file)
        if not path.exists():
            print(f"missing source file: {source_file}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace").replace("\u00a0", " ").replace("\u202f", " ")
        company_id = entity_id_for(db, row["company"], "organisation")
        if not company_id:
            print(f"missing company: {row['company']}")
            continue
        exists = db.execute("SELECT 1 FROM source_document WHERE id=?", (source_id,)).fetchone()
        if exists:
            docs[source_id] = source_id
            continue
        db.execute("DELETE FROM sentence WHERE doc_id=?", (source_id,))
        db.execute(
            "INSERT INTO source_document (id, kind, title, url, local_path, text_sha256, char_count, "
            "sentence_count, retrieved_at, revision_id, access_date, license, subject_id, metadata_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (source_id, "official", source_id, row["source_url"], source_file,
             sha256_text(text), len(text), 0, now(), None, now()[:10],
             "Official public document", company_id,
             json.dumps({"url": row["source_url"], "company": row["company"]}, ensure_ascii=False)),
        )
        spans = sentence_spans(text)
        db.executemany(
            "INSERT INTO sentence (id, doc_id, ordinal, char_start, char_end, text, text_sha256) VALUES (?,?,?,?,?,?,?)",
            [(f"{source_id}:{s.ordinal}", source_id, s.ordinal, s.char_start, s.char_end, s.text, sha256_text(s.text))
             for s in spans],
        )
        db.execute("UPDATE source_document SET sentence_count=? WHERE id=?", (len(spans), source_id))
        docs[source_id] = source_id
        added_docs += 1
    db.commit()
    print(f"merged rows={len(merged)} from {len(FRAGMENTS)} fragments; source docs added={added_docs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
