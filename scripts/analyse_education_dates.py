#!/usr/bin/env python3
"""Analyse pre-commission US-university and gating-institution attendance."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect
from euro_sdt.v2.entities import entity_id_for

COMMISSIONS = [
    ("Santer 1995–99", "santer-commission", "data/commissions/commission_santer_1995_1999.csv"),
    ("Prodi 1999–2004", "prodi-commission", "data/commissions/commission_prodi_1999_2004.csv"),
    ("Barroso I 2004–09", "barroso-i", "data/commissions/commission_barroso_i_2004_2009.csv"),
    ("Barroso II 2010–14", "barroso-ii", "data/commissions/commission_barroso_ii_2010_2014.csv"),
    ("Juncker 2014–19", "juncker-commission", "data/commissions/commission_juncker_2014_2019.csv"),
    ("VdL I 2019–24", "vdl-i-commission", "data/commissions/commission_i_2019_2024.csv"),
    ("VdL II 2024–29", "vdl-ii-commission", "data/commissions/commission_2024_2029.csv"),
]
ALIASES = {"Cathy Ashton": "catherine-ashton"}


def profile(db: sqlite3.Connection, entity_id: str, attribute: str):
    row = db.execute(
        "SELECT value FROM organisation_profile WHERE entity_id=? AND attribute=? LIMIT 1",
        (entity_id, attribute),
    ).fetchone()
    return row["value"] if row else None


def roster(db: sqlite3.Connection, path: str) -> list[str]:
    ids = []
    for row in csv.DictReader(open(path)):
        name = (row.get("Name") or "").strip()
        if not name:
            continue
        eid = ALIASES.get(name) or entity_id_for(db, name, "person")
        if eid:
            ids.append(eid)
    return ids


def main() -> int:
    db = connect(V2_DB_PATH)
    db.row_factory = sqlite3.Row
    lines = [
        "# Education by commission: pre-existing US and gating institutions",
        "",
        "Institution must have `inception_date` before the commission's `term_start`.",
        "",
        "| Commission | Roster | US university | Gating institution |",
        "|---|---:|---:|---:|",
    ]
    details = []
    for label, commission_id, path in COMMISSIONS:
        start = profile(db, commission_id, "term_start")
        ids = roster(db, path)
        us: set[str] = set()
        gating: set[str] = set()
        for row in db.execute(
            """SELECT DISTINCT c.subject_id, o.id AS institution_id, o.name
               FROM claim c JOIN assertion a ON a.claim_id=c.id AND a.status='verified'
               JOIN entity o ON o.id=c.object_id
               WHERE c.predicate='educated_at' AND c.subject_id IN ({})""".format(
                ",".join("?" for _ in ids)
            ),
            tuple(ids),
        ):
            inception = profile(db, row["institution_id"], "inception_date")
            if not inception or not start or int(inception) >= int(start[:4]):
                continue
            if profile(db, row["institution_id"], "us_university") == "true":
                us.add(row["subject_id"])
            if profile(db, row["institution_id"], "gating_institution") == "true":
                gating.add(row["subject_id"])
        lines.append(f"| {label} | {len(ids)} | {len(us)}/{len(ids)} ({100*len(us)/len(ids):.0f}%) | {len(gating)}/{len(ids)} ({100*len(gating)/len(ids):.0f}%) |")
        details.append(f"\n## {label}\n\nUS university: {len(us)}/{len(ids)}; gating institution: {len(gating)}/{len(ids)}.\n")
    out = AUDIT_DIR / "education_dates_by_commission.md"
    out.write_text("\n".join(lines) + "\n" + "\n".join(details), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
