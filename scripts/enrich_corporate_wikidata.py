#!/usr/bin/env python3
"""Enrich corporate people with Wikidata facts via Wikipedia pageprops.

Wikidata's entity search endpoint is aggressively rate-limited, so QIDs are
resolved through Wikipedia search + pageprops, then entity data is fetched in
batches from the Wikidata API.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from euro_sdt.v2.db import V2_DB_PATH, connect, now, uid

WIKI = "https://en.wikipedia.org/w/api.php"
WD = "https://www.wikidata.org/w/api.php"
CACHE = Path("data/corporate/wikidata_cache.json")
OUT = Path("data/corporate/wikidata_matches.csv")
UA = "euro-sdt/0.3 (research)"
BUSINESS = re.compile(
    r"business|executive|chief executive|ceo|banker|entrepreneur|industrialist|manager|"
    r"company director|corporate|financier|investor|lawyer|economist|engineer|politician",
    re.I,
)


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    value = re.sub(r"^(dr|prof|sir|dame|lord|ladyship)\.?\s+", "", value, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def get_json(url: str, attempts: int = 5) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(1 + attempt)


def wiki_search(name: str) -> dict | None:
    url = WIKI + "?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": name, "srlimit": 3, "format": "json"}
    )
    results = get_json(url).get("query", {}).get("search", [])
    for r in results:
        if norm(r["title"]) == norm(name):
            return r
    return None


def wiki_qids(titles: list[str]) -> dict[str, str]:
    out = {}
    for i in range(0, len(titles), 50):
        url = WIKI + "?" + urllib.parse.urlencode(
            {"action": "query", "prop": "pageprops", "titles": "|".join(titles[i:i + 50]), "format": "json"}
        )
        data = get_json(url)
        for page in data.get("query", {}).get("pages", {}).values():
            qid = page.get("pageprops", {}).get("wikibase_item")
            if qid:
                out[page["title"]] = qid
    return out


def wd_entities(qids: list[str]) -> dict[str, dict]:
    out = {}
    for i in range(0, len(qids), 50):
        url = WD + "?" + urllib.parse.urlencode(
            {"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
             "props": "claims|labels|descriptions", "languages": "en", "format": "json"}
        )
        out.update(get_json(url).get("entities", {}))
    return out


def claim_ids(data: dict, prop: str) -> list[str]:
    out = []
    for claim in data.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            out.append(value["id"])
    return list(dict.fromkeys(out))


def birth_date(data: dict) -> str | None:
    claims = data.get("claims", {}).get("P569", [])
    if not claims:
        return None
    value = claims[0].get("mainsnak", {}).get("datavalue", {}).get("value")
    if not isinstance(value, dict):
        return None
    m = re.match(r"[+-](\d{4})-(\d{2})-(\d{2})", value.get("time", ""))
    if not m:
        return None
    year, month, day = m.groups()
    if month == "00":
        return year
    if day == "00":
        return f"{year}-{month}"
    return f"{year}-{month}-{day}"


def main() -> int:
    db = connect(V2_DB_PATH)
    db.row_factory = sqlite3.Row
    people = db.execute(
        "SELECT DISTINCT e.id, e.name FROM entity e JOIN role_tenure t ON t.person_id=e.id "
        "WHERE t.tenure_type='corporate_role' ORDER BY e.name"
    ).fetchall()
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    # Phase 1: exact Wikipedia title search.
    pending = [p for p in people if p["id"] not in cache]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(wiki_search, p["name"]): p for p in pending}
        for i, fut in enumerate(as_completed(futures), 1):
            p = futures[fut]
            try:
                r = fut.result()
                cache[p["id"]] = {"name": p["name"], "title": r["title"] if r else None}
            except Exception as exc:
                cache[p["id"]] = {"name": p["name"], "title": None, "error": str(exc)}
            if i % 25 == 0:
                CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    # Phase 2: pageprops -> QIDs.
    title_to_person = {}
    for pid, entry in cache.items():
        if entry.get("title"):
            title_to_person[entry["title"]] = pid
    qid_by_title = wiki_qids(list(title_to_person))
    for title, pid in title_to_person.items():
        cache[pid]["qid"] = qid_by_title.get(title)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    # Phase 3: fetch entity data.
    qids = sorted({entry["qid"] for entry in cache.values() if entry.get("qid")})
    entities = wd_entities(qids)
    for entry in cache.values():
        if entry.get("qid"):
            entry["data"] = entities.get(entry["qid"], {})

    # Phase 4: labels for referenced values.
    value_ids = set()
    for entry in cache.values():
        data = entry.get("data") or {}
        for prop in ("P27", "P69", "P106", "P108", "P39", "P1416"):
            value_ids.update(claim_ids(data, prop))
    labels = {}
    value_ids = sorted(value_ids)
    for i in range(0, len(value_ids), 50):
        url = WD + "?" + urllib.parse.urlencode(
            {"action": "wbgetentities", "ids": "|".join(value_ids[i:i + 50]),
             "props": "labels", "languages": "en", "format": "json"}
        )
        for qid, ent in get_json(url).get("entities", {}).items():
            labels[qid] = (ent.get("labels", {}).get("en", {}) or {}).get("value", qid)

    # Phase 5: DB + report.
    out = [("person", "qid", "label", "description", "confidence")]
    profiles = 0
    for person in people:
        entry = cache.get(person["id"], {})
        qid = entry.get("qid")
        if not qid:
            continue
        data = entry.get("data") or {}
        description = (data.get("descriptions", {}).get("en", {}) or {}).get("value", "")
        label = (data.get("labels", {}).get("en", {}) or {}).get("value", entry.get("title") or "")
        confidence = "exact_business" if BUSINESS.search(description) else "exact_title"
        out.append((person["name"], qid, label, description, confidence))
        row = db.execute("SELECT external_ids_json FROM entity WHERE id=?", (person["id"],)).fetchone()
        ext = json.loads(row[0]) if row and row[0] else {}
        ext["wikidata"] = qid
        db.execute("UPDATE entity SET external_ids_json=? WHERE id=?", (json.dumps(ext, ensure_ascii=False), person["id"]))
        attrs = [("description", description, None), ("birth_date", birth_date(data), None)]
        for prop, attribute in (("P27", "citizenship"), ("P69", "education"), ("P106", "occupation"),
                                ("P108", "employer"), ("P39", "position"), ("P1416", "member_of")):
            for vid in claim_ids(data, prop):
                attrs.append((attribute, labels.get(vid, vid), vid))
        for attribute, value, value_id in attrs:
            if not value:
                continue
            db.execute(
                "INSERT OR REPLACE INTO person_profile (id, entity_id, attribute, value, value_id, quote, "
                "status, source_url, notes, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (uid("pp-"), person["id"], attribute, value, value_id,
                 f"Wikidata {qid} {attribute}", "wikidata", f"https://www.wikidata.org/wiki/{qid}",
                 "Wikidata structured fact; QID is the provenance key", now()),
            )
            profiles += 1
    db.commit()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(out)
    matched = sum(1 for v in cache.values() if v.get("qid"))
    print(f"people={len(people)} wikipedia_titles={sum(1 for v in cache.values() if v.get('title'))} "
          f"qids={matched} profiles={profiles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
