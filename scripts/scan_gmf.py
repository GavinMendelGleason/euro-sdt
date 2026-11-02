#!/usr/bin/env python3
"""Search for German Marshall Fund connections in local sources and official pages.

Read-only. The local pass scans every stored sentence for GMF aliases. The URL
pass fetches official GMF pages, matches their text against active person
entities, and reports candidates with the existing graph status.
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect
from euro_sdt.v2.entities import aliases_for

GMF_IDS = ("german-marshall-fund", "german-marshall-fund-of-the-united-states")
TASK_IDS = (
    "transatlantic-task-force-of-the-german-marshall-fund-and-the-bundeskanzler-helmut-schmidt-stiftung-bkhs",
    "transatlantic-task-force-of-the-german-marshall-fund-and-the-federal-chancellor-helmut-schmidt-foundation-bkhs",
)
TARGET_CATEGORIES = ("commissioner", "dg", "ddg", "cjeu_judge", "cjeu_ag")
ALIASES = ("German Marshall Fund", "German Marshall Fund of the United States", "GMF", "GMFUS", "Marshall Fund")

DEFAULT_URLS = (
    "https://www.gmfus.org/news/german-marshall-fund-and-bundeskanzler-helmut-schmidt-stiftung-launch-transatlantic-task-force",
    "https://www.gmfus.org/news/gmf-launches-transatlantic-task-force",
)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; euro-sdt)"})
    html = urllib.request.urlopen(req, timeout=60).read()
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def existing_claims(db: sqlite3.Connection) -> dict[str, list[dict]]:
    rows = db.execute("""
        SELECT e.id AS person_id, e.name, e.category, c.predicate,
               coalesce(o.name, c.object_literal) AS object, c.role_raw,
               a.status, a.evidence_grade
        FROM claim c
        JOIN assertion a ON a.claim_id=c.id
        JOIN entity e ON e.id=c.subject_id
        LEFT JOIN entity o ON o.id=c.object_id
        WHERE c.object_id IN ({}) OR c.object_id IN ({})
    """.format(",".join("?" for _ in GMF_IDS), ",".join("?" for _ in TASK_IDS)),
        (*GMF_IDS, *TASK_IDS)).fetchall()
    out: dict[str, list[dict]] = {}
    for row in rows:
        out.setdefault(row["person_id"], []).append(dict(row))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(V2_DB_PATH))
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--out", type=Path, default=AUDIT_DIR / "gmf_connections")
    args = parser.parse_args()
    db = connect(args.db)
    db.row_factory = sqlite3.Row
    claims = existing_claims(db)

    # Local corpus pass.
    local = []
    for row in db.execute("""
        SELECT e.id AS person_id, e.name, e.category, d.id AS doc_id, d.title,
               d.url, s.ordinal, s.text
        FROM sentence s
        JOIN source_document d ON d.id=s.doc_id
        JOIN entity e ON e.id=d.subject_id
        WHERE lower(s.text) LIKE '%german marshall%'
           OR lower(s.text) LIKE '%marshall fund%'
           OR lower(s.text) LIKE '%gmf%'
        ORDER BY e.category, e.name, s.ordinal
    """):
        local.append({
            "source": "local",
            "person": row["name"], "person_id": row["person_id"], "category": row["category"],
            "url": row["url"] or "", "doc_id": row["doc_id"], "sentence": row["ordinal"],
            "matched": "", "snippet": row["text"].replace("\n", " "),
            "target_scope": row["category"] in TARGET_CATEGORIES,
            "existing": "; ".join(
                f"{c['predicate']}={c['object']} ({c['status']})"
                for c in claims.get(row["person_id"], [])
            ),
        })

    # Official page pass.
    candidates = []
    people = db.execute(
        "SELECT id, name, category FROM entity WHERE kind='person' AND status='active' "
        "ORDER BY category, name"
    ).fetchall()
    for url in (args.url or DEFAULT_URLS):
        try:
            text = fetch_text(url)
        except Exception as exc:
            print(f"fetch failed: {url}: {exc}")
            continue
        for person in people:
            aliases = [a for a in aliases_for(db, person["id"]) if len(a) >= 6 and " " in a]
            hit = next((a for a in aliases if re.search(rf"(?<!\w){re.escape(a)}(?!\w)", text, re.I)), None)
            if not hit:
                continue
            idx = text.lower().find(hit.lower())
            snippet = text[max(0, idx - 180): idx + 300].replace("\n", " ")
            candidates.append({
                "source": "web",
                "person": person["name"], "person_id": person["id"], "category": person["category"],
                "url": url, "doc_id": "", "sentence": "",
                "matched": hit, "snippet": snippet,
                "target_scope": person["category"] in TARGET_CATEGORIES,
                "existing": "; ".join(
                    f"{c['predicate']}={c['object']} ({c['status']})"
                    for c in claims.get(person["id"], [])
                ),
            })

    rows = local + candidates
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    lines = ["# German Marshall Fund connections", "", f"Rows: {len(rows)}", ""]
    lines += ["## Local corpus", ""]
    for r in local:
        lines.append(f"- **{r['person']}** ({r['category']}) — `{r['doc_id']}:{r['sentence']}`")
        lines.append(f"  > {r['snippet'][:500]}")
        if r["existing"]:
            lines.append(f"  Existing claims: {r['existing']}")
    lines += ["", "## Official-page candidates", ""]
    for r in candidates:
        scope = "" if r["target_scope"] else " — outside target scope"
        lines.append(f"- **{r['person']}** ({r['category']}{scope}) — {r['url']}")
        lines.append(f"  > {r['snippet'][:500]}")
        if r["existing"]:
            lines.append(f"  Existing claims: {r['existing']}")
    args.out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}.csv/.md ({len(local)} local, {len(candidates)} web)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
