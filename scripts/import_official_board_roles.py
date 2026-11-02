#!/usr/bin/env python3
"""Import board roles from official company governance pages.

The input CSV is a curated, source-specific extraction. Quotes are derived from
the stored source document, not typed by hand, so the deterministic locator can
check every claim.
"""
from __future__ import annotations

import csv
import hashlib
import sqlite3
from pathlib import Path

from euro_sdt.v2.claims import (
    DocCache,
    _add_evidence,
    _finish_assertions,
    _insert_claim,
    normalize_role,
)
from euro_sdt.v2.db import V2_DB_PATH, connect, now, uid
from euro_sdt.v2.entities import aliases_for, create_entity, entity_id_for

CSV_PATH = Path("data/corporate/board_roles_official_pilot.csv")
PREDICATE_FOR_KIND = {
    "chair": "chair",
    "ceo": "employed_by",
    "cfo": "employed_by",
    "board_member": "board_member",
    "advisory_board": "advisory_board",
}


def quote_for_role(text: str, company: str, person: str, role_raw: str) -> str:
    lower = text.lower()
    company_pos = lower.find(company.lower())
    if company_pos < 0:
        raise ValueError(f"company {company!r} not found in source")
    person_pos = lower.find(person.lower(), company_pos)
    if person_pos < 0:
        raise ValueError(f"person {person!r} not found after {company!r}")
    role_pos = lower.find(role_raw.lower(), person_pos + len(person))
    end = person_pos + len(person) if role_pos < 0 else role_pos + len(role_raw)
    return text[company_pos:end]


def main() -> int:
    db = connect(V2_DB_PATH)
    db.row_factory = sqlite3.Row
    docs = DocCache(db)
    rows = list(csv.DictReader(open(CSV_PATH)))
    added = 0
    for row in rows:
        company = row["company"]
        company_id = entity_id_for(db, company, "organisation")
        if not company_id:
            raise SystemExit(f"company not in frame: {company}")
        doc_id = row.get("source_id") or f"official-{company_id}"
        doc = db.execute("SELECT id, subject_id FROM source_document WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            raise SystemExit(f"missing source document {doc_id}; run add_official_source.py first")
        text = Path(db.execute("SELECT local_path FROM source_document WHERE id=?", (doc_id,)).fetchone()[0]).read_text(encoding="utf-8")
        person = row["person"]
        person_id = entity_id_for(db, person, "person")
        if not person_id:
            person_id = create_entity(db, person, "person", category="corporate_elite")
        role_kind = row["role_kind"]
        predicate = PREDICATE_FOR_KIND[role_kind]
        role = normalize_role(row["role_raw"])
        quote = quote_for_role(text, company, person, row["role_raw"])
        claim_id = _insert_claim(
            db, person_id, predicate, company_id, None, role, row["role_raw"],
            None, None, row["source_url"], "official_board_page",
        )
        _add_evidence(
            db, claim_id, doc_id, quote, None, docs,
            aliases_for(db, person_id), aliases_for(db, company_id),
            predicate, role, doc["subject_id"], person_id,
        )
        tenure_id = "rt-" + hashlib.sha1(
            "|".join([person_id, company_id, "corporate_role", row["role_raw"], row["source_url"]]).encode("utf-8")
        ).hexdigest()[:16]
        low = text.lower()
        person_pos = low.find(person.lower())
        role_pos = low.find(row["role_raw"].lower(), person_pos + len(person)) if person_pos >= 0 else -1
        if person_pos >= 0:
            compact_quote = text[person_pos: role_pos + len(row["role_raw"]) if role_pos >= 0 else person_pos + len(person)]
        else:
            compact_quote = quote[:500]
        db.execute(
            "INSERT OR REPLACE INTO role_tenure "
            "(id, person_id, organisation_id, tenure_type, role, role_raw, start_date, end_date, "
            "start_precision, end_precision, source_url, source_quote, notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tenure_id, person_id, company_id, "corporate_role", role_kind, row["role_raw"],
             None, None, "unknown", "open", row["source_url"], compact_quote,
             f"Official board/management page; role as of {row['as_of']}; start/end unknown"),
        )
        added += 1
    db.commit()
    _finish_assertions(db, preserve_adjudicated=True)
    print(f"imported {added} official board roles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
