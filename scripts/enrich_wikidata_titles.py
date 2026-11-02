#!/usr/bin/env python3
"""Resolve exact Wikipedia titles to Wikidata and store person profile facts."""
from __future__ import annotations

import csv
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from euro_sdt.v2.db import V2_DB_PATH, connect, now, uid

WIKI = "https://en.wikipedia.org/w/api.php"
WD = "https://www.wikidata.org/w/api.php"
OUT = Path("data/corporate/wikidata_matches.csv")
UA = "euro-sdt/0.3 (research)"


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    value = re.sub(r"^(dr|prof|sir|dame|lord|ladyship)\.?\s+", "", value, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def wiki_qids(names: list[str]) -> dict[str, str]:
    out = {}
    for i in range(0, len(names), 50):
        url = WIKI + "?" + urllib.parse.urlencode(
            {"action": "query", "prop": "pageprops", "titles": "|".join(names[i:i + 50]),
             "redirects": 1, "format": "json"}
        )
        data = get(url)
        normalized = {norm(p["to"]): p["from"] for p in data.get("query", {}).get("normalized", [])}
        redirects = {norm(p["to"]): p["from"] for p in data.get("query", {}).get("redirects", [])}
        for page in data.get("query", {}).get("pages", {}).values():
            qid = page.get("pageprops", {}).get("wikibase_item")
            title = page.get("title", "")
            if qid:
                out[title] = qid
                if title in normalized:
                    out[normalized[title]] = qid
                if title in redirects:
                    out[redirects[title]] = qid
        time.sleep(2)
    return out


def wd_entities(qids: list[str]) -> dict[str, dict]:
    out = {}
    for i in range(0, len(qids), 50):
        url = WD + "?" + urllib.parse.urlencode(
            {"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
             "props": "claims|labels|descriptions", "languages": "en", "format": "json"}
        )
        out.update(get(url).get("entities", {}))
        time.sleep(0.5)
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
    return year if month == "00" else (f"{year}-{month}" if day == "00" else f"{year}-{month}-{day}")


def main() -> int:
    db = connect(V2_DB_PATH)
    db.row_factory = __import__("sqlite3").Row
    people = db.execute(
        "SELECT DISTINCT e.id, e.name FROM entity e JOIN role_tenure t ON t.person_id=e.id "
        "WHERE t.tenure_type='corporate_role' ORDER BY e.name"
    ).fetchall()
    by_norm = {norm(p["name"]): p for p in people}
    qid_by_name = wiki_qids([p["name"] for p in people])
    pairs = []
    for label, qid in qid_by_name.items():
        p = by_norm.get(norm(label))
        if p:
            pairs.append((p, qid))
    # Deduplicate by person id.
    pairs = list({p["id"]: (p, qid) for p, qid in pairs}.values())
    entities = wd_entities(sorted({qid for _, qid in pairs}))

    labels = {}
    value_ids = set()
    for _, qid in pairs:
        data = entities.get(qid, {})
        for prop in ("P27", "P69", "P106", "P108", "P39", "P1416"):
            value_ids.update(claim_ids(data, prop))
    value_ids = sorted(value_ids)
    for i in range(0, len(value_ids), 50):
        url = WD + "?" + urllib.parse.urlencode(
            {"action": "wbgetentities", "ids": "|".join(value_ids[i:i + 50]),
             "props": "labels", "languages": "en", "format": "json"}
        )
        for qid, ent in get(url).get("entities", {}).items():
            labels[qid] = (ent.get("labels", {}).get("en", {}) or {}).get("value", qid)
        time.sleep(0.5)

    out = [("person", "qid", "label", "description", "confidence")]
    profiles = 0
    for person, qid in pairs:
        data = entities.get(qid, {})
        label = (data.get("labels", {}).get("en", {}) or {}).get("value", "")
        description = (data.get("descriptions", {}).get("en", {}) or {}).get("value", "")
        out.append((person["name"], qid, label, description, "exact_title"))
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
    print(f"people={len(people)} matched={len(pairs)} profiles={profiles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
