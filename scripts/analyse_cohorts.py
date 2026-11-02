#!/usr/bin/env python3
"""Report pre-administration Atlanticist cohorts for commission rosters."""
from __future__ import annotations

import csv
import re
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
HARD = [
    "atlantic-council", "atlantic-councils-europe-center", "atlantic-council-eurogrowth-initiative-usa",
    "atlantic-council-of-finland-acf", "the-atlantic-council-of-finland-acf",
    "slovak-atlantic-commission", "committee-of-the-slovak-atlantic-commission", "munich-security-conference",
    "world-economic-forum", "world-economic-forum-on-the-middle-east-and-north-africa",
    "world-economic-forum-high-level-group-on-humanitarian-investing", "european-leadership-network", "globsec",
    "bilderberg-group", "bilderberg-conference", "bilderberg-meetings", "trilateral-commission",
    "the-trilateral-commission", "german-marshall-fund", "german-marshall-fund-of-the-united-states",
    "council-on-foreign-relations-cfr", "danish-delegation-to-the-nato-parliamentary-assembly",
    "international-republican-institute-iri", "international-republican-institute-iri-usa", "rand-europe",
    "center-for-european-policy-analysis-cepa",
]
CORE = ("member", "board_member", "advisory_board", "chair", "founder", "fellow")
ALIASES = {"Cathy Ashton": "catherine-ashton"}


def key(value: str | None):
    if not value:
        return None
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", value)
    return (int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0)) if m else None


def main() -> int:
    db = connect(V2_DB_PATH)
    db.row_factory = sqlite3.Row
    qh = ",".join("?" for _ in HARD)
    qc = ",".join("?" for _ in CORE)
    lines = [
        "# Pre-administration Atlanticist cohorts",
        "",
        "`pre_any` = joined before the commission start; `pre_active` = still active at that start.",
        "",
        "| Commission | Roster | All-time hard | Dated | Excluded undated | Pre-any | Pre-active |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    details = []
    for label, commission_id, path in COMMISSIONS:
        start = db.execute(
            "SELECT value FROM organisation_profile WHERE entity_id=? AND attribute='term_start'",
            (commission_id,),
        ).fetchone()["value"]
        sk = key(start)
        ids = [
            ALIASES.get(row["Name"]) or entity_id_for(db, row["Name"], "person")
            for row in csv.DictReader(open(path))
            if row.get("Name")
        ]
        ids = [x for x in ids if x]
        qs = ",".join("?" for _ in ids)
        rows = db.execute(
            f"""SELECT c.subject_id, c.start_date, c.end_date
                FROM claim c JOIN assertion a ON a.claim_id=c.id AND a.status='verified'
                WHERE c.predicate IN ({qc}) AND c.object_id IN ({qh}) AND c.subject_id IN ({qs})""",
            (*CORE, *HARD, *ids),
        ).fetchall()
        alltime = {r["subject_id"] for r in rows}
        dated = {r["subject_id"] for r in rows if r["start_date"] or r["end_date"]}
        pre_any, pre_active = set(), set()
        for r in rows:
            s, e = key(r["start_date"]), key(r["end_date"])
            if s and s < sk:
                pre_any.add(r["subject_id"])
                if e is None or e >= sk:
                    pre_active.add(r["subject_id"])
        lines.append(f"| {label} | {len(ids)} | {len(alltime)} | {len(dated)} | {len(alltime)-len(dated)} | {len(pre_any)} | {len(pre_active)} |")
        names = db.execute(
            f"""SELECT DISTINCT e.name FROM claim c JOIN assertion a ON a.claim_id=c.id AND a.status='verified'
                JOIN entity e ON e.id=c.subject_id
                WHERE c.predicate IN ({qc}) AND c.object_id IN ({qh}) AND c.subject_id IN ({qs})
                ORDER BY e.name""",
            (*CORE, *HARD, *ids),
        ).fetchall()
        details.append(f"\n## {label}\n\nAll-time: {', '.join(r['name'] for r in names) or '—'}\n")
    out = AUDIT_DIR / "cohort_coverage.md"
    out.write_text("\n".join(lines) + "\n" + "\n".join(details), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
