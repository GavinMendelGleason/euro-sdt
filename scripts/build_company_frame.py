#!/usr/bin/env python3
"""Build the company_frame layer from the existing transnational company list.

This does not claim the frame is exhaustive. It records the current inclusion
rule and metadata so the sample can be audited and replaced by a defined index.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect, uid
from euro_sdt.v2.entities import create_entity, entity_id_for

CSV_PATH = Path("data/corporate/transnational_companies.csv")
FRAME = "legacy_transnational_53"
RULE = "Curated large European transnational companies; sector-balanced by hand; not an index census"


def main() -> int:
    db = connect(V2_DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS company_frame (
        id TEXT PRIMARY KEY,
        company_id TEXT NOT NULL,
        frame_name TEXT NOT NULL,
        selection_rule TEXT NOT NULL,
        snapshot_year INTEGER,
        sector TEXT,
        headquarters TEXT,
        market_cap_bn REAL,
        eu_countries TEXT,
        source_url TEXT,
        notes TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_company_frame_company ON company_frame(company_id);
    CREATE INDEX IF NOT EXISTS idx_company_frame_name ON company_frame(frame_name);
    ''')
    rows = list(csv.DictReader(open(CSV_PATH)))
    added = created = 0
    for row in rows:
        company = entity_id_for(db, row["company"], "organisation")
        if not company:
            company = create_entity(db, row["company"], "organisation", category=row["sector"])
            created += 1
        company_id = company
        try:
            cap = float(row["market_cap_bn"]) if row["market_cap_bn"].strip() else None
        except ValueError:
            cap = None
        db.execute("DELETE FROM company_frame WHERE company_id=? AND frame_name=?", (company_id, FRAME))
        db.execute(
            "INSERT INTO company_frame (id, company_id, frame_name, selection_rule, snapshot_year, sector, "
            "headquarters, market_cap_bn, eu_countries, source_url, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (uid("cf-"), company_id, FRAME, RULE, None, row["sector"], row["headquarters"], cap,
             row["eu_countries"], "", "Legacy curated list; needs replacement by an explicit index/selection rule"),
        )
        added += 1
    db.commit()
    out = AUDIT_DIR / "company_frame.md"
    counts = {}
    for row in rows:
        counts[row["sector"]] = counts.get(row["sector"], 0) + 1
    lines = [
        "# Company frame",
        "",
        f"Frame: `{FRAME}`",
        f"Selection rule: {RULE}",
        f"Companies: {added}",
        "",
        "| Sector | Companies |",
        "|---|---:|",
    ]
    for k, v in sorted(counts.items(), key=lambda item: -item[1]):
        lines.append(f"| {k} | {v} |")
    lines += ["", "This frame is not exhaustive. Replace it with an explicit index or top-N rule before computing rates."]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"frame rows={added}, new companies={created}; wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
