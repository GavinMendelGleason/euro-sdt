#!/usr/bin/env python3
"""Import historical DG/DDG post-service roles into role_tenure.

The role interval is the source of truth; current/former is derived from
start/end dates rather than stored as a status.
"""
from __future__ import annotations

import csv
import hashlib
import re
import sqlite3
from pathlib import Path

from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect, uid
from euro_sdt.v2.entities import create_entity, entity_id_for, entity_id_for
from euro_sdt.v2.claims import _insert_claim, _add_evidence, _finish_assertions

ART16 = {
    "Karl-Friedrich Falkenberg": ("2017-06-30", "https://commission.europa.eu/document/download/a81c34b5-7b26-4cb8-8a80-507888bc4f18_en"),
    "Jonathan Faull": ("2016-12-31", "https://commission.europa.eu/document/download/a81c34b5-7b26-4cb8-8a80-507888bc4f18_en"),
    "Klaus-Dieter Borchardt": ("2020-09-30", "https://commission.europa.eu/document/download/668f20e5-35d7-4203-921c-4f2afdd0d4e7_en"),
    "Carles Esteva Mosso": ("2021-04-30", "https://commission.europa.eu/document/download/668f20e5-35d7-4203-921c-4f2afdd0d4e7_en"),
    "Cecilio Madero Villarejo": ("2020-09-30", "https://commission.europa.eu/document/download/668f20e5-35d7-4203-921c-4f2afdd0d4e7_en"),
    "Michael Koehler": ("2024-01-31", "https://commission.europa.eu/document/download/ca839f72-fd27-44d6-b5e9-4dbda7981769_en"),
}
MONTHS = {m: i for i, m in enumerate("January February March April May June July August September October November December".split(), 1)}

def norm_date(value: str):
    value = value.strip()
    m = re.match(r"([A-Za-z]+)\s+(\d{4})", value)
    if m:
        key = m.group(1)[:3].title()
        full = next((k for k in MONTHS if k.startswith(key)), None)
        if full:
            return f"{m.group(2)}-{MONTHS[full]:02d}", "month"
    m = re.match(r"(\d{4})", value)
    if m:
        return m.group(1), "year"
    return value or None, "unknown"

def rid(*parts: object) -> str:
    return "rt-" + hashlib.sha1("|".join(str(x) for x in parts).encode()).hexdigest()[:16]

SOURCES = {
    "RevolvingDoorWatch": "https://corporateeurope.org/en/revolvingdoorwatch",
    "ALTER-EU 2011, Annexe 1": "https://www.corporateeurope.org/sites/default/files/publications/20111116_aeu-revolving_1.pdf",
}
CLEAN = re.compile(r"\s+(UK|France|Germany|Portugal|Sweden|Denmark|Netherlands|Britain)$")


def employer_for(row: dict) -> tuple[str, str, str, str]:
    # canonical id suffix, display name, region, type
    mapping = {
        "Jean-Paul Mingasson": ("businesseurope", "BusinessEurope", "European", "business association"),
        "Carles Esteva Mosso": ("latham-watkins", "Latham & Watkins", "US", "law"),
        "Cecilio Madero Villarejo": ("clifford-chance", "Clifford Chance", "European", "law"),
        "Klaus-Dieter Borchardt": ("oxford-institute-energy-studies", "Oxford Institute for Energy Studies", "European", "academic"),
        "Michael Koehler": ("koehler-advisory-boards", "Koehler advisory boards", "Mixed", "non-profit advisory boards"),
        "Robert Madelin": ("madelin-innovation", "Madelin Innovation", "European", "consultancy"),
        "Hervé Jouanjean": ("fidal", "Fidal", "European", "law"),
        "Peter Faross": ("ueapme", "UEAPME", "European", "business association/consultancy"),
        "Joao Pacheco": ("pacheco-consulting", "JSPacheco / Allen F. Johnson / Farm Europe", "Mixed", "consultancy/think tank"),
        "Jörgen Holmquist": ("interel", "Interel", "European", "lobby/consultancy"),
        "Mogens Peter Carl": ("kreab", "Kreab Gavin Anderson", "European", "lobby/consultancy"),
        "Michel Petite": ("clifford-chance", "Clifford Chance", "European", "law"),
        "Karl-Friedrich Falkenberg": ("european-aluminium", "European Aluminium", "European", "business association"),
        "Jonathan Faull": ("faull-consulting", "Faull Consulting / Brunswick Group / Caisse de dépôt", "Mixed", "consultancy/lobby/finance"),
    }
    return mapping[CLEAN.sub("", row["name"]).strip()]


def main() -> int:
    db = connect(V2_DB_PATH)
    db.row_factory = sqlite3.Row
    rows = list(csv.DictReader(open(AUDIT_DIR / "revolving_door_dg.csv")))
    created_people = created_orgs = tenures = 0
    for row in rows:
        name = CLEAN.sub("", row["name"]).strip()
        is_ddg = "deputy" in row["former"].lower()
        category = "ddg" if is_ddg else "dg"
        person = entity_id_for(db, name, "person")
        if not person:
            person = create_entity(db, name, "person", category=category)
            db.execute("UPDATE entity SET status='historical' WHERE id=?", (person,))
            created_people += 1
        eid, org_name, region, sector = employer_for(row)
        org = entity_id_for(db, org_name, "organisation")
        if not org:
            org = create_entity(db, org_name, "organisation", category=sector)
            created_orgs += 1
        for attr, value in (("employer_region", region), ("employer_sector", sector)):
            db.execute("DELETE FROM organisation_profile WHERE entity_id=? AND attribute=?", (org, attr))
            db.execute("INSERT INTO organisation_profile (id, entity_id, attribute, value, status, notes) VALUES (?,?,?,?,?,?)",
                       (uid("p-"), org, attr, value, "sourced", "Imported role_tenure employer classification"))
        source_url = SOURCES.get(row["source"], ART16.get(name, ("", ""))[1] if name in ART16 else row["source"])
        # post-service tenure
        start, precision = norm_date(row["date"])
        db.execute("INSERT OR REPLACE INTO role_tenure (id, person_id, organisation_id, tenure_type, role, role_raw, start_date, end_date, start_precision, end_precision, source_url, source_quote, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (rid(person, org, "post_service", start, row["new"]), person, org, "post_service", "post_service", row["new"], start, None, precision, "open", source_url, row["new"], row["source"]))
        tenures += 1
        # service tenure end, where the report dates it
        if name in ART16:
            service_end = ART16[name][0]
            db.execute("INSERT OR REPLACE INTO role_tenure (id, person_id, organisation_id, tenure_type, role, role_raw, start_date, end_date, start_precision, end_precision, source_url, source_quote, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (rid(person, "european-commission", "service", service_end, row["former"]), person, "european-commission", "service", "dg" if not is_ddg else "ddg", row["former"], None, service_end, "unknown", "day", source_url, row["former"], "End date from Article 16 report"))
    db.commit()
    print(f"people={created_people} orgs={created_orgs} tenures={tenures}")
    print("role_tenure rows:", db.execute("SELECT COUNT(*) FROM role_tenure").fetchone()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
