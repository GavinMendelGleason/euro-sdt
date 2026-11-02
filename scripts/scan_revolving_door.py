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
    "Carles Esteva Mosso": ("US", "law"),
    "Cecilio Madero Villarejo": ("European", "law"),
    "Klaus-Dieter Borchardt": ("European", "academic"),
    "Michael Koehler": ("Mixed", "non-profit advisory boards"),
    "Karl-Friedrich Falkenberg": ("European", "business association"),
    "Jonathan Faull": ("Mixed", "consultancy/lobby/finance"),
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
    extra = [
        {
            "name": "Jean-Paul Mingasson", "policy_area": "Enterprise",
            "former": "Director-General, DG Enterprise and Industry",
            "new": "BusinessEurope, General adviser", "date": "2004",
            "employer_region": "European", "employer_type": "business association",
            "in_graph": "Jean-Paul Mingasson" in people,
            "source": "ALTER-EU 2011, Annexe 1",
        },
        {
            "name": "Carles Esteva Mosso", "policy_area": "Competition",
            "former": "Deputy Director-General, DG COMP",
            "new": "Latham & Watkins LLP, Partner", "date": "2021",
            "employer_region": "US", "employer_type": "law",
            "in_graph": "Carles Esteva Mosso" in people,
            "source": "Commission Article 16 annual report 2022",
        },
        {
            "name": "Cecilio Madero Villarejo", "policy_area": "Competition",
            "former": "Deputy Director-General, DG COMP",
            "new": "Clifford Chance LLP, Of Counsel", "date": "2020",
            "employer_region": "European", "employer_type": "law",
            "in_graph": "Cecilio Madero Villarejo" in people,
            "source": "Commission Article 16 annual report 2022",
        },
        {
            "name": "Klaus-Dieter Borchardt", "policy_area": "Energy",
            "former": "Deputy Director-General, DG ENER",
            "new": "Oxford Institute for Energy Studies, Senior Visiting Research Fellow", "date": "2021",
            "employer_region": "European", "employer_type": "academic",
            "in_graph": "Klaus-Dieter Borchardt" in people,
            "source": "Commission Article 16 annual report 2022",
        },
        {
            "name": "Michael Koehler", "policy_area": "Humanitarian Aid",
            "former": "Deputy Director-General, DG ECHO",
            "new": "Positive Agenda, Polisync, Candid Foundation, Deutsche Welthungerhilfe, advisory boards", "date": "2024",
            "employer_region": "Mixed", "employer_type": "non-profit advisory boards",
            "in_graph": "Michael Koehler" in people,
            "source": "Commission Article 16 annual report 2025",
        },
        {
            "name": "Karl-Friedrich Falkenberg", "policy_area": "Environment",
            "former": "Director-General, DG ENV",
            "new": "European Aluminium, independent advisory board on sustainability", "date": "2017",
            "employer_region": "European", "employer_type": "business association",
            "in_graph": "Karl-Friedrich Falkenberg" in people,
            "source": "Commission Article 16 annual report 2018",
        },
        {
            "name": "Jonathan Faull", "policy_area": "Financial services / Secretariat-General",
            "former": "Director-General, DG FISMA and Secretariat-General",
            "new": "Faull Consulting; Brunswick Group (Chair, Public Affairs Europe); Caisse de dépôt et placement du Québec", "date": "2016",
            "employer_region": "Mixed", "employer_type": "consultancy/lobby/finance",
            "in_graph": "Jonathan Faull" in people,
            "source": "Commission Article 16 annual report 2018",
        },
    ]
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
        "",
        "Commission Article 16 annual reports also document named DDG moves to Latham & Watkins (US) and Clifford Chance (UK), plus an academic and non-profit role.",
        "",
        "Official-report coverage: English PDFs for 2018–2025 were searched for `Director-General` / `Deputy Director-General`. DG/DDG cases were found in 2018 (Falkenberg, Faull), 2022 (Borchardt, Esteva Mosso, Madero Villarejo), and 2025 (Koehler); no DG/DDG hits were found in 2019–2021, 2023, or 2024. This is a keyword-assisted review, not a line-by-line audit of every case section.",
    ]
    args.out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}.csv/.md ({len(filtered)} DG/DDG cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
