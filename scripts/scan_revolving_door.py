#!/usr/bin/env python3
"""Scan Corporate Europe Observatory's RevolvingDoorWatch for DG/DDG cases."""
from __future__ import annotations

import argparse
import csv
import re
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect

BASE = "https://corporateeurope.org/en/revolvingdoorwatch"
UA = {"User-Agent": "euro-sdt/0.2 (research)"}
EMPLOYER_CLASS = {
    "Jean-Paul Mingasson": ("European", "business association"),
    "Robert Madelin": ("European", "consultancy"),
    "Hervé Jouanjean": ("European", "law"),
    "Peter Faross": ("European", "business association/consultancy"),
    "Joao Pacheco": ("Mixed", "consultancy/think tank"),
    "Jörgen Holmquist": ("European", "lobby/consultancy"),
    "Mogens Peter Carl": ("European", "lobby/consultancy"),
    "Michel Petite": ("European", "law"),
}


def page_rows(page: int) -> list[list[str]]:
    url = BASE if page == 0 else f"{BASE}?page={page}"
    html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(cells) >= 6:
            rows.append(cells)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(V2_DB_PATH))
    parser.add_argument("--out", type=Path, default=AUDIT_DIR / "revolving_door_dg")
    args = parser.parse_args()
    db = connect(args.db)
    db.row_factory = __import__("sqlite3").Row
    people = {r["name"]: r["category"] for r in db.execute("SELECT name, category FROM entity WHERE kind='person' AND status='active'")}
    all_rows = []
    for page in range(0, 20):
        rows = page_rows(page)
        if not rows or any(row == all_rows[-1] for row in rows if all_rows):
            if not rows:
                break
        all_rows.extend(rows)
        if len(rows) < 50:
            break
    filtered = []
    # Additional named case from ALTER-EU, "Block the revolving door" (2011), Annexe 1.
    extra = [{
        "name": "Jean-Paul Mingasson", "policy_area": "Enterprise",
        "former": "Director-General, DG Enterprise and Industry",
        "new": "BusinessEurope, General adviser", "date": "2004",
        "employer_region": "European", "employer_type": "business association",
        "in_graph": "Jean-Paul Mingasson" in people,
        "source": "ALTER-EU 2011, Annexe 1",
    }]
    filtered.extend(extra)
    seen = {tuple((r["name"], r["former"], r["new"], r["date"])) for r in filtered}
    for row in all_rows:
        key = tuple(row[:4])
        if key in seen:
            continue
        seen.add(key)
        former = row[2].lower()
        if "european parliament" in former or "principal adviser to the director-general" in former:
            continue
        if re.search(r"director[- ]general|director general|deputy director[- ]general", row[2], re.I):
            name = row[0].split(" UK")[0].split(" France")[0].split(" Germany")[0].split(" Portugal")[0].split(" Sweden")[0].split(" Britain")[0].split(" Denmark")[0].split(" Netherlands")[0]
            region, kind = EMPLOYER_CLASS.get(name, ("Unknown", "corporate/lobby/consultancy"))
            filtered.append({
                "name": row[0], "policy_area": row[1], "former": row[2],
                "new": row[3], "date": row[4], "employer_region": region,
                "employer_type": kind, "in_graph": row[0] in people,
                "source": "RevolvingDoorWatch",
            })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(filtered[0].keys()) if filtered else [])
        writer.writeheader(); writer.writerows(filtered)
    lines = [
        "# Revolving-door cases involving Directors-General or Deputy Directors-General",
        "",
        f"Sources: {BASE}; ALTER-EU, Block the revolving door (2011); European Ombudsman SI/5/2024/KR. Cases found: {len(filtered)}.",
        "",
        "| Name | Policy | Former role | New employer | Employer region | Employer type | Date | In graph? | Source |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in filtered:
        lines.append(f"| {r['name']} | {r['policy_area']} | {r['former']} | {r['new']} | {r['employer_region']} | {r['employer_type']} | {r['date']} | {'yes' if r['in_graph'] else 'no'} | {r['source']} |")
    lines += [
        "",
        "## Additional source",
        "",
        "European Ombudsman SI/5/2024/KR reports a former DG Competition director who joined **Paul Weiss**, a US law firm, in 2024. The official note anonymises the individual but confirms the move and the Commission's post-service restrictions.",
    ]
    args.out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}.csv/.md ({len(filtered)} DG/DDG cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
