#!/usr/bin/env python3
"""Recover start/end dates for existing membership claims from their evidence.

Only writes a date when the evidence sentence explicitly states one. No
imputation: unstated dates remain NULL.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect, sha256_text
from euro_sdt.v2.extract import _call

CACHE_PATH = AUDIT_DIR / "llm_affiliation_dates_cache.json"
MODEL = "deepseek-chat"
HARD = [
    "atlantic-council", "atlantic-councils-europe-center", "atlantic-council-eurogrowth-initiative-usa",
    "atlantic-council-of-finland-acf", "the-atlantic-council-of-finland-acf",
    "slovak-atlantic-commission", "committee-of-the-slovak-atlantic-commission",
    "munich-security-conference", "world-economic-forum", "world-economic-forum-on-the-middle-east-and-north-africa",
    "world-economic-forum-high-level-group-on-humanitarian-investing", "european-leadership-network",
    "globsec", "bilderberg-group", "bilderberg-conference", "bilderberg-meetings",
    "trilateral-commission", "the-trilateral-commission", "german-marshall-fund",
    "german-marshall-fund-of-the-united-states", "council-on-foreign-relations-cfr",
    "danish-delegation-to-the-nato-parliamentary-assembly", "international-republican-institute-iri",
    "international-republican-institute-iri-usa", "rand-europe", "center-for-european-policy-analysis-cepa",
]
CORE = ("member", "board_member", "advisory_board", "chair", "founder", "fellow")


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_cache(cache: dict) -> None:
    AUDIT_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def clean(value):
    if value is None:
        return None
    m = re.search(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?", str(value))
    if not m:
        return None
    return "-".join(x for x in m.groups() if x)


def prompt(subject: str, role: str, organisation: str, quote: str) -> str:
    return f"""Read this evidence sentence about {subject}'s relationship with {organisation}.

Role: {role}
Evidence: {quote}

Return the relationship start and end dates ONLY if the evidence explicitly states them.
Use YYYY, YYYY-MM, or YYYY-MM-DD. If no date is stated, return null. Do not infer or use outside knowledge.

Return JSON array only:
[{{"start_date": null, "end_date": null}}]"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(V2_DB_PATH))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    db = connect(args.db)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """SELECT c.id, c.start_date, c.end_date, c.role_raw, e.name AS subject, o.name AS object,
                  ev.quote
           FROM claim c JOIN assertion a ON a.claim_id=c.id AND a.status='verified'
           JOIN entity e ON e.id=c.subject_id JOIN entity o ON o.id=c.object_id
           JOIN evidence ev ON ev.claim_id=c.id AND ev.locator_status='located'
           WHERE c.predicate IN ({}) AND c.object_id IN ({})
             AND c.start_date IS NULL AND c.end_date IS NULL
           GROUP BY c.id""".format(",".join("?" for _ in CORE), ",".join("?" for _ in HARD)),
        (*CORE, *HARD),
    ).fetchall()
    print("claims without dates:", len(rows))
    cache = load_cache()
    tasks = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for r in rows:
            p = prompt(r["subject"], r["role_raw"] or "", r["object"], r["quote"])
            key = f"{MODEL}|{sha256_text(p)}"
            if key not in cache:
                tasks[pool.submit(_call, p, MODEL, False)] = (r["id"], key)
        errors = 0
        for future in as_completed(tasks):
            cid, key = tasks[future]
            try:
                result = future.result()
                if isinstance(result, dict):
                    cache[key] = result
                elif isinstance(result, list) and result and isinstance(result[0], dict):
                    cache[key] = result[0]
                else:
                    cache[key] = {}
            except Exception:
                errors += 1
    save_cache(cache)
    updated = 0
    for r in rows:
        p = prompt(r["subject"], r["role_raw"] or "", r["object"], r["quote"])
        result = cache.get(f"{MODEL}|{sha256_text(p)}", {})
        start, end = clean(result.get("start_date")), clean(result.get("end_date"))
        if start or end:
            updated += 1
            print(r["subject"], "→", r["object"], start, end)
            if not args.dry_run:
                db.execute("UPDATE claim SET start_date=?, end_date=? WHERE id=?",
                           (start, end, r["id"]))
    if not args.dry_run:
        db.commit()
    print("updated:", updated, "errors:", errors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
