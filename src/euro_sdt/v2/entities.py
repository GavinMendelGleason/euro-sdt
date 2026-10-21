"""Entity registry for v2.

The v1 database split persons into `name` and `mep-name` nodes, used two slug
functions, and never merged aliases. This module builds one registry from the
v1 entities, the hand-curated dedup map, and the CSVs that carry external IDs.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from .db import PROJECT_ROOT, now, normalize_name, org_merge_key, slugify

ORG_KINDS = {"organisation", "institution", "university", "commission"}
_ORG_KEY_CACHE: dict[int, dict[str, str]] = {}


CATEGORY_PRIORITY = {
    "commissioner": 100,
    "dg": 90,
    "ddg": 85,
    "corporate_elite": 80,
    "cjeu_judge": 75,
    "cjeu_ag": 74,
    "mep_sdt": 50,
    "mep": 50,
}

JUNK_PATTERNS = [
    r"\bin (19|20)\d{2}\b",
    r"^(show|hide|read|edit|career|biography|early life|personal life|other activities)\b",
    r"^(member|president|chairman|chair|director|board member|ceo|vice[- ]president)\b",
    r"\b(award|medal|decoration|order of|grand cross|knight|commander)\b",
    r"^(alumni|the alumni|unknown|various|several|multiple)\b",
    r"\b(not specified|not mentioned|unclear|none listed)\b",
]


def is_junk_name(name: str) -> bool:
    low = (name or "").strip().lower()
    if len(low) < 2 or len(low) > 160:
        return True
    return any(re.search(pattern, low) for pattern in JUNK_PATTERNS)


def _load_dedup_aliases() -> dict[str, list[str]]:
    path = PROJECT_ROOT / "manifests" / "_dedup.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    merged = data.get("auto_merged", {})
    aliases: dict[str, list[str]] = {}
    for canonical, variants in merged.items():
        aliases.setdefault(canonical, [])
        for variant in variants:
            if variant != canonical and variant not in aliases[canonical]:
                aliases[canonical].append(variant)
    return aliases


def _load_external_ids() -> dict[str, dict[str, str]]:
    """name-normalised -> {wikidata: QID}."""
    out: dict[str, dict[str, str]] = {}
    sources = [
        (PROJECT_ROOT / "data" / "meps_2024_2029.csv", "Name", "wikidata_id"),
        (PROJECT_ROOT / "data" / "commissions" / "commission_2024_2029.csv", "Name", "wikidata_id"),
        (PROJECT_ROOT / "data" / "cjeu" / "cjeu_members_list.csv", "Name", "wikidata_id"),
        (PROJECT_ROOT / "data" / "officials" / "commission_senior_officials.csv", "name", "wikidata_id"),
    ]
    for path, name_col, qid_col in sources:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh):
                name = (row.get(name_col) or "").strip()
                qid = (row.get(qid_col) or "").strip()
                if name and re.fullmatch(r"Q\d+", qid):
                    out.setdefault(normalize_name(name), {})["wikidata"] = qid
    return out


def _choose_canonical(rows: list[sqlite3.Row]) -> sqlite3.Row:
    def score(row: sqlite3.Row) -> tuple:
        category = (row["category"] or "").strip()
        return (
            CATEGORY_PRIORITY.get(category, 0),
            0 if str(row["id"]).startswith("mep-") else 1,
            -len(row["name"] or ""),
            row["id"],
        )

    return sorted(rows, key=score, reverse=True)[0]


def build_registry(db: sqlite3.Connection, v1: sqlite3.Connection) -> dict[str, str]:
    """Populate entity/entity_alias and return v1_id -> v2_id."""
    dedup = _load_dedup_aliases()
    external = _load_external_ids()
    v1_rows = v1.execute("SELECT id, name, type, category, country FROM entity").fetchall()

    groups: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
    for row in v1_rows:
        kind = (row["type"] or "organisation").strip()
        name_key = org_merge_key(row["name"] or row["id"]) if kind in ORG_KINDS else normalize_name(row["name"] or row["id"])
        groups[(kind, name_key)].append(row)

    v1_to_v2: dict[str, str] = {}
    used_ids: dict[str, str] = {}
    merged_groups = []
    quarantined = []

    for (kind, _norm), rows in groups.items():
        canonical = _choose_canonical(rows)
        base_id = slugify(canonical["name"] or canonical["id"])
        if not base_id:
            base_id = slugify(canonical["id"])
        entity_id = base_id
        suffix = 2
        while entity_id in used_ids:
            entity_id = f"{base_id}-{suffix}"
            suffix += 1
        used_ids[entity_id] = normalize_name(canonical["name"])
        category = canonical["category"]
        if category == "mep_sdt":
            category = "mep"
        ext = dict(external.get(normalize_name(canonical["name"]), {}))
        v1_categories = sorted({r["category"] for r in rows if r["category"]})
        meta = {"v1_ids": [r["id"] for r in rows], "v1_categories": v1_categories}
        status = "quarantined" if is_junk_name(canonical["name"]) else "active"
        if len(rows) > 1:
            merged_groups.append({
                "kind": kind,
                "canonical_id": entity_id,
                "canonical_name": canonical["name"],
                "merged": [{"id": r["id"], "name": r["name"], "category": r["category"]} for r in rows],
            })
        if status == "quarantined":
            quarantined.append({"id": entity_id, "name": canonical["name"], "kind": kind})
        db.execute(
            "INSERT OR REPLACE INTO entity (id, kind, name, category, country, external_ids_json, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                entity_id,
                kind,
                canonical["name"],
                category,
                canonical["country"],
                json.dumps({**ext, **meta}, ensure_ascii=False),
                status,
                now(),
            ),
        )
        for row in rows:
            v1_to_v2[row["id"]] = entity_id
            for alias in {row["name"], row["id"]}:
                if alias:
                    db.execute(
                        "INSERT OR IGNORE INTO entity_alias (entity_id, alias, source) VALUES (?,?,?)",
                        (entity_id, alias, "v1"),
                    )
            variants = dedup.get(row["name"], [])
            for variant in variants:
                db.execute(
                    "INSERT OR IGNORE INTO entity_alias (entity_id, alias, source) VALUES (?,?,?)",
                    (entity_id, variant, "dedup"),
                )
        # Acronyms in parentheses become aliases.
        name = canonical["name"] or ""
        for acronym in re.findall(r"\(([A-Z][A-Z0-9&.-]{1,12})\)", name):
            db.execute(
                "INSERT OR IGNORE INTO entity_alias (entity_id, alias, source) VALUES (?,?,?)",
                (entity_id, acronym, "acronym"),
            )

    db.commit()
    _ORG_KEY_CACHE.clear()
    import json as _json
    from .db import AUDIT_DIR
    AUDIT_DIR.mkdir(exist_ok=True)
    (AUDIT_DIR / "entity_merge.json").write_text(
        _json.dumps({"merged_groups": merged_groups, "quarantined": quarantined}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return v1_to_v2


def _org_key_index(db: sqlite3.Connection) -> dict[str, str]:
    key = id(db)
    if key in _ORG_KEY_CACHE:
        return _ORG_KEY_CACHE[key]
    index: dict[str, str] = {}
    for row in db.execute(
        "SELECT e.id, e.name, a.alias FROM entity e LEFT JOIN entity_alias a ON a.entity_id=e.id "
        "WHERE e.status='active' AND e.kind IN ('organisation','institution','university','commission')"
    ):
        for value in (row["name"], row["alias"]):
            if value:
                index.setdefault(org_merge_key(value), row["id"])
    _ORG_KEY_CACHE[key] = index
    return index


def entity_id_for(db: sqlite3.Connection, name: str, kind: str = "organisation") -> str | None:
    if not name:
        return None
    norm = normalize_name(name)
    row = db.execute(
        "SELECT e.id FROM entity e JOIN entity_alias a ON a.entity_id=e.id "
        "WHERE e.kind=? AND lower(a.alias)=lower(?) ORDER BY e.status='active' DESC LIMIT 1",
        (kind, name),
    ).fetchone()
    if row:
        return row[0]
    row = db.execute(
        "SELECT id FROM entity WHERE kind=? AND lower(name)=lower(?) LIMIT 1",
        (kind, name),
    ).fetchone()
    if row:
        return row[0]
    # Try a normalised alias match.
    for candidate in db.execute("SELECT entity_id, alias FROM entity_alias WHERE entity_id IN (SELECT id FROM entity WHERE kind=?)", (kind,)):
        if normalize_name(candidate["alias"]) == norm:
            return candidate["entity_id"]
    if kind in ORG_KINDS:
        found = _org_key_index(db).get(org_merge_key(name))
        if found:
            return found
    return None


def create_entity(db: sqlite3.Connection, name: str, kind: str, category: str | None = None,
                  country: str | None = None) -> str:
    base_id = slugify(name) or "entity"
    entity_id = base_id
    i = 2
    while db.execute("SELECT 1 FROM entity WHERE id=?", (entity_id,)).fetchone():
        entity_id = f"{base_id}-{i}"
        i += 1
    db.execute(
        "INSERT INTO entity (id, kind, name, category, country, external_ids_json, status, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (entity_id, kind, name, category, country, "{}", "quarantined" if is_junk_name(name) else "active", now()),
    )
    db.execute(
        "INSERT OR IGNORE INTO entity_alias (entity_id, alias, source) VALUES (?,?,?)",
        (entity_id, name, "created"),
    )
    cache = _ORG_KEY_CACHE.get(id(db))
    if cache is not None:
        cache.setdefault(org_merge_key(name), entity_id)
    return entity_id


def resolve_or_create(db: sqlite3.Connection, name: str, kind: str,
                      category: str | None = None, country: str | None = None) -> str:
    found = entity_id_for(db, name, kind)
    if found:
        return found
    return create_entity(db, name, kind, category=category, country=country)


def write_entity_audit(db: sqlite3.Connection) -> dict:
    """Reconstruct merge/quarantine audit from the v2 registry."""
    import json as _json
    from .db import AUDIT_DIR
    groups = []
    for row in db.execute("SELECT id, name, kind, category, status, external_ids_json FROM entity"):
        meta = _json.loads(row["external_ids_json"] or "{}")
        v1_ids = meta.get("v1_ids", [])
        if len(v1_ids) > 1:
            groups.append({
                "kind": row["kind"], "canonical_id": row["id"], "canonical_name": row["name"],
                "merged": [{"id": vid} for vid in v1_ids],
            })
    quarantined = [
        {"id": row["id"], "name": row["name"], "kind": row["kind"]}
        for row in db.execute("SELECT id, name, kind FROM entity WHERE status='quarantined'")
    ]
    AUDIT_DIR.mkdir(exist_ok=True)
    payload = {"merged_groups": groups, "quarantined": quarantined}
    (AUDIT_DIR / "entity_merge.json").write_text(_json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def aliases_for(db: sqlite3.Connection, entity_id: str) -> tuple[str, ...]:
    rows = db.execute(
        "SELECT alias FROM entity_alias WHERE entity_id=? AND length(alias) >= 2", (entity_id,)
    ).fetchall()
    name = db.execute("SELECT name FROM entity WHERE id=?", (entity_id,)).fetchone()
    values = {row[0] for row in rows}
    if name:
        values.add(name[0])
    return tuple(sorted(values, key=len, reverse=True))
