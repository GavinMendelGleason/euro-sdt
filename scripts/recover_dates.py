#!/usr/bin/env python3
"""Recover commission terms and institution inception dates.

Writes sourced date attributes to organisation_profile:
  - commission term_start / term_end
  - institution inception_date
  - gating_institution / us_university flags

The institution set is curated to the gatekeeping and US universities that
actually appear in the commissioner education corpus.
"""
from __future__ import annotations

import argparse
import sqlite3

from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect, now, uid

COMMISSIONS = {
    "santer-commission": ("1995-01-23", "1999-03-15", "https://commission.europa.eu/about/organisation/college-commissioners_en"),
    "prodi-commission": ("1999-09-16", "2004-11-21", "https://commission.europa.eu/about/organisation/college-commissioners_en"),
    "barroso-i": ("2004-11-22", "2010-02-09", "https://commission.europa.eu/about/organisation/college-commissioners_en"),
    "barroso-ii": ("2010-02-10", "2014-10-31", "https://commission.europa.eu/about/organisation/college-commissioners_en"),
    "juncker-commission": ("2014-11-01", "2019-11-30", "https://commission.europa.eu/about/organisation/college-commissioners_en"),
    "vdl-i-commission": ("2019-12-01", "2024-11-30", "https://commission.europa.eu/about/organisation/college-commissioners_en"),
    "vdl-ii-commission": ("2024-12-01", None, "https://commission.europa.eu/about/organisation/college-commissioners_en"),
}

# entity_id: (year, source_url, gating_institution, us_university)
INSTITUTIONS = {
    "college-of-europe": (1949, "https://www.coleurope.eu/about-us/history", True, False),
    "ecole-nationale-d-administration": (1945, "https://www.wikidata.org/wiki/Q273579", True, False),
    "sciences-po": (1872, "https://www.wikidata.org/wiki/Q859363", True, False),
    "london-school-of-economics": (1895, "https://www.wikidata.org/wiki/Q174570", True, False),
    "university-of-oxford": (1096, "https://www.wikidata.org/wiki/Q34433", True, False),
    "university-of-cambridge": (1209, "https://www.wikidata.org/wiki/Q35794", True, False),
    "bocconi": (1902, "https://www.wikidata.org/wiki/Q959524", True, False),
    "insead": (1957, "https://www.wikidata.org/wiki/Q1136829", True, False),
    "georgetown-university": (1789, "https://www.wikidata.org/wiki/Q333886", True, True),
    "university-college-london": (1826, "https://www.wikidata.org/wiki/Q193196", True, False),
    "king-s-college-london": (1829, "https://www.wikidata.org/wiki/Q245247", True, False),
    "uppsala-university": (1477, "https://www.wikidata.org/wiki/Q185246", True, False),
    "university-of-vienna": (1365, "https://www.wikidata.org/wiki/Q165980", True, False),
    "sapienza-university-of-rome": (1303, "https://www.wikidata.org/wiki/Q209344", True, False),
    "hec-paris": (1881, "https://www.wikidata.org/wiki/Q273535", True, False),
    "ecole-polytechnique": (1794, "https://www.wikidata.org/wiki/Q273626", True, False),
    "harvard": (1636, "https://www.wikidata.org/wiki/Q13371", True, True),
    "yale-university": (1701, "https://www.wikidata.org/wiki/Q49112", True, True),
    "massachusetts-institute-of-technology-mit": (1861, "https://www.wikidata.org/wiki/Q49108", True, True),
    "university-of-california-berkeley": (1868, "https://www.wikidata.org/wiki/Q168756", True, True),
    "university-of-maryland-college-park": (1856, "https://www.wikidata.org/wiki/Q503415", True, True),
    "new-york-university": (1831, "https://www.wikidata.org/wiki/Q49210", True, True),
    "george-washington-university": (1821, "https://www.wikidata.org/wiki/Q432637", True, True),
    "macalester-college": (1874, "https://www.macalester.edu/about/history/", True, True),
    "rhode-island-school-of-design-risd": (1877, "https://www.risd.edu/about/history", True, True),
    "golden-gate-university-of-san-francisco": (1853, "https://www.ggu.edu/about/history/", True, True),
    "thunderbird-school-of-global-management-arizona": (1946, "https://www.wikidata.org/wiki/Q5955303", True, True),
    "university-of-chicago": (1890, "https://www.wikidata.org/wiki/Q131252", True, True),
    "university-of-southern-california": (1880, "https://www.wikidata.org/wiki/Q4614", True, True),
    "moscow-state-institute-of-international-relations": (1944, "https://mgimo.ru/about/", True, False),
    "european-university-institute": (1972, "https://www.eui.eu/about/history", True, False),
}


def put(db: sqlite3.Connection, entity_id: str, attribute: str, value: str,
        source_url: str, notes: str) -> None:
    db.execute("DELETE FROM organisation_profile WHERE entity_id=? AND attribute=?", (entity_id, attribute))
    db.execute(
        "INSERT INTO organisation_profile (id, entity_id, attribute, value, sentence_id, quote, source_url, "
        "source_date, status, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (uid("p-"), entity_id, attribute, value, None, None, source_url, now()[:10], "sourced", notes),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(V2_DB_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    db = connect(args.db)
    report = []
    for eid, (start, end, url) in COMMISSIONS.items():
        report.append((eid, "term_start", start, url))
        if end:
            report.append((eid, "term_end", end, url))
        if not args.dry_run:
            put(db, eid, "term_start", start, url, "Commission term; official College of Commissioners chronology")
            if end:
                put(db, eid, "term_end", end, url, "Commission term; official College of Commissioners chronology")
    for eid, (year, url, gating, us) in INSTITUTIONS.items():
        row = db.execute("SELECT kind FROM entity WHERE id=?", (eid,)).fetchone()
        if not row:
            report.append((eid, "MISSING_ENTITY", "", url))
            continue
        report.append((eid, "inception_date", str(year), url))
        if not args.dry_run:
            put(db, eid, "inception_date", str(year), url, "Institution inception; Wikidata/ official history")
            if gating:
                put(db, eid, "gating_institution", "true", url, "Curated gating-institution flag")
            if us:
                put(db, eid, "us_university", "true", url, "US university flag")
    if not args.dry_run:
        db.commit()
    AUDIT_DIR.mkdir(exist_ok=True)
    out = AUDIT_DIR / "date_recovery.md"
    lines = ["# Date recovery", "", "| Entity | Attribute | Value | Source |", "|---|---|---|---|"]
    for row in report:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}; {sum(1 for r in report if r[1]=='inception_date')} institution dates, "
          f"{sum(1 for r in report if r[1]=='MISSING_ENTITY')} missing entities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
