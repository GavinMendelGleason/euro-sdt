"""Render a verified-only wiki from euro_sdt_v2.db."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from .db import WIKI_V2_DIR, now
from .graph import NETWORK_PREDICATES, OCCUPATIONAL_PREDICATES, EDUCATION_PREDICATES, INSTITUTIONAL_PREDICATES

PREDICATE_LABEL = {
    "member": "Membership",
    "board_member": "Board / trustee",
    "advisory_board": "Advisory board",
    "chair": "Chair / president",
    "employed_by": "Employment",
    "founder": "Founder",
    "fellow": "Fellowship",
    "attendee": "Attendance",
    "affiliated_with": "Affiliation",
    "educated_at": "Education",
    "studied_field": "Field of study",
    "held_degree": "Degree",
    "served_on_commission": "Commission service",
    "held_portfolio": "Portfolio",
    "from_country": "Country",
    "nominated_by": "Nominated by",
    "post_mandate_occupation": "Post-mandate occupation",
    "held_position": "Position",
}

PREDICATE_PRIORITY = {
    "board_member": 0, "advisory_board": 1, "chair": 2, "founder": 3,
    "fellow": 4, "member": 5, "affiliated_with": 6, "attendee": 7,
    "served_on_commission": 0, "held_portfolio": 1, "nominated_by": 2,
    "from_country": 3, "educated_at": 0, "studied_field": 1, "held_degree": 2,
    "employed_by": 0, "held_position": 1, "post_mandate_occupation": 2,
}
GRADE_RANK = {"A": 0, "B": 1, "C": 2}


def _best_row(rows):
    return sorted(
        rows,
        key=lambda row: (
            GRADE_RANK.get(row["evidence_grade"], 3),
            0 if (row["role"] or row["role_raw"]) else 1,
            len(row["quote"] or ""),
        ),
    )[0]


def _roles(rows, object_name: str) -> list[str]:
    values = []
    for row in rows:
        role = (row["role"] or row["role_raw"] or "").strip()
        if role and role.lower() not in {object_name.lower(), "member", "affiliated_with"}:
            values.append(role)
    # Preserve order, remove case duplicates.
    seen = set()
    out = []
    for role in values:
        key = role.lower()
        if key not in seen:
            seen.add(key)
            out.append(role)
    return out


ORDER = [
    "served_on_commission", "held_portfolio", "nominated_by", "from_country",
    "educated_at", "studied_field", "held_degree",
    "member", "board_member", "advisory_board", "chair", "founder", "fellow",
    "affiliated_with", "attendee",
    "employed_by", "held_position", "post_mandate_occupation",
]


def _safe(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _wl(path: str, label: str) -> str:
    """Obsidian wikilink, so the graph view recognises the edge."""
    clean = _safe(label).replace("|", "-").replace("]", "")
    return f"[[{path}|{clean}]]"


def _quote(text: str, limit: int = 600) -> str:
    text = _safe(text)
    if len(text) > limit:
        text = text[:limit].rstrip() + " […]"
    return text.replace('"', '\\"')


def _frontmatter(fields: dict) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _entity_row(db: sqlite3.Connection, entity_id: str):
    return db.execute("SELECT * FROM entity WHERE id=?", (entity_id,)).fetchone()


def _assertions_for_subject(db: sqlite3.Connection, entity_id: str):
    return db.execute("""
        SELECT a.claim_id, a.evidence_grade, c.predicate, c.object_id, c.object_literal,
               c.role, c.role_raw, c.start_date, c.end_date,
               COALESCE(o.name, c.object_literal) AS object_name,
               e.quote, e.doc_id, d.title AS doc_title, d.url AS doc_url
        FROM assertion a
        JOIN claim c ON c.id = a.claim_id
        LEFT JOIN entity o ON o.id = c.object_id AND o.status='active'
        LEFT JOIN evidence e ON e.claim_id = c.id AND e.locator_status = 'located'
        LEFT JOIN source_document d ON d.id = e.doc_id
        WHERE a.status = 'verified' AND c.subject_id = ?
          AND (c.object_id IS NULL OR o.id IS NOT NULL)
        ORDER BY c.predicate, object_name
    """, (entity_id,)).fetchall()


def _assertions_for_object(db: sqlite3.Connection, entity_id: str):
    return db.execute("""
        SELECT a.claim_id, a.evidence_grade, c.predicate, c.subject_id, c.role, c.role_raw,
               c.start_date, c.end_date, s.name AS subject_name,
               e.quote, e.doc_id, d.title AS doc_title
        FROM assertion a
        JOIN claim c ON c.id = a.claim_id
        JOIN entity s ON s.id = c.subject_id
        LEFT JOIN evidence e ON e.claim_id = c.id AND e.locator_status = 'located'
        LEFT JOIN source_document d ON d.id = e.doc_id
        WHERE a.status = 'verified' AND c.object_id = ? AND s.status='active'
        ORDER BY s.name, c.predicate
    """, (entity_id,)).fetchall()


def person_page(db: sqlite3.Connection, entity_id: str) -> str:
    ent = _entity_row(db, entity_id)
    if not ent:
        return ""
    rows = _assertions_for_subject(db, entity_id)
    tags = ["person", "verified"]
    if ent["category"]:
        tags.append(str(ent["category"]).replace("_", "-"))
    fm = _frontmatter({"id": entity_id, "title": ent["name"], "type": "person",
                       "category": ent["category"] or "", "country": ent["country"] or "",
                       "tags": tags, "generated": now()[:10]})
    lines = [fm, f"# {ent['name']}", ""]
    meta = [str(ent["category"]).replace("_", " ").title() if ent["category"] else "Person"]
    if ent["country"]:
        meta.append(str(ent["country"]))
    lines.append(" · ".join(meta))
    lines.append("")
    lines.append(f"*Verified assertions: {len(rows)}*")
    lines.append("")
    by_object: dict[str, list] = defaultdict(list)
    for row in rows:
        key = row["object_name"] or row["object_literal"] or row["predicate"]
        by_object[key].append(row)
    sectioned: dict[str, list] = defaultdict(list)
    for key, group in by_object.items():
        predicate = min(group, key=lambda row: PREDICATE_PRIORITY.get(row["predicate"], 99))["predicate"]
        sectioned[predicate].append((key, group))
    for predicate in ORDER:
        if predicate not in sectioned:
            continue
        lines.append(f"## {PREDICATE_LABEL.get(predicate, predicate)}")
        lines.append("")
        for key, group in sorted(sectioned[predicate], key=lambda item: item[0].lower()):
            best = _best_row(group)
            obj = key
            if best["object_id"]:
                kind_row = db.execute("SELECT kind FROM entity WHERE id=?", (best["object_id"],)).fetchone()
                kind = kind_row["kind"] if kind_row else "organisation"
                subdir = "commissions" if kind == "commission" else "organisations"
                obj = _wl(f"{subdir}/{best['object_id']}", key)
            roles = _roles(group, key)
            role_text = "; ".join(roles)
            dates = ""
            if best["start_date"] or best["end_date"]:
                dates = f" ({best['start_date'] or ''}–{best['end_date'] or ''})".replace("–)", ")")
            lines.append(f"- {obj}{(' — ' + role_text) if role_text else ''}{dates}  ")
            if best["quote"]:
                lines.append(f'  > "{_quote(best["quote"])}"')
            if best["doc_id"]:
                lines.append(f"  > Source: {_wl('sources/' + best['doc_id'], best['doc_title'])} · grade {best['evidence_grade']}")
            lines.append("")
    return "\n".join(lines)


def organisation_page(db: sqlite3.Connection, entity_id: str) -> str:
    ent = _entity_row(db, entity_id)
    if not ent:
        return ""
    rows = _assertions_for_object(db, entity_id)
    profile = db.execute(
        "SELECT attribute, value, status, quote, source_url FROM organisation_profile "
        "WHERE entity_id=? AND status IN ('manual_seed','sourced') ORDER BY attribute",
        (entity_id,),
    ).fetchall()
    tags = ["organisation", "verified"]
    if ent["category"]:
        tags.append(str(ent["category"]).replace("_", "-"))
    fm = _frontmatter({"id": entity_id, "title": ent["name"], "type": "organisation",
                       "category": ent["category"] or "", "tags": tags, "generated": now()[:10]})
    lines = [fm, f"# {ent['name']}", ""]
    lines.append(f"*Verified member assertions: {len({r['subject_id'] for r in rows})} people*")
    lines.append("")
    if profile:
        lines.append("## Profile")
        lines.append("")
        for item in profile:
            label = item["attribute"].replace("_", " ").title()
            lines.append(f"- **{label}:** {item['value']}  ")
            if item["status"] == "manual_seed":
                lines.append("  *Manual research seed; not yet tied to a primary-source sentence.*")
        lines.append("")
    if rows:
        lines.append("## Members and roles")
        lines.append("")
        by_person: dict[str, list] = defaultdict(list)
        for row in rows:
            by_person[row["subject_name"]].append(row)
        for name, group in sorted(by_person.items(), key=lambda item: item[0].lower()):
            best = _best_row(group)
            roles = _roles(group, ent["name"])
            role_text = "; ".join(roles)
            dates = f" ({best['start_date'] or ''}–{best['end_date'] or ''})".replace("–)", ")") if (best["start_date"] or best["end_date"]) else ""
            lines.append(f"- {_wl('people/' + best['subject_id'], name)}{(' — ' + role_text) if role_text else ''}{dates}  ")
            if best["quote"]:
                lines.append(f"  > \"{_quote(best['quote'], 400)}\"")
            if best["doc_id"]:
                lines.append(f"  > Source: {_wl('sources/' + best['doc_id'], best['doc_title'])} · grade {best['evidence_grade']}")
        lines.append("")
    return "\n".join(lines)


def source_page(db: sqlite3.Connection, doc_id: str) -> str:
    doc = db.execute("SELECT * FROM source_document WHERE id=?", (doc_id,)).fetchone()
    if not doc:
        return ""
    rows = db.execute("""
        SELECT DISTINCT a.claim_id, a.evidence_grade, c.subject_id, c.predicate, c.object_id,
               c.object_literal, s.name AS subject_name, COALESCE(o.name, c.object_literal) AS object_name,
               e.quote
        FROM evidence e
        JOIN claim c ON c.id = e.claim_id
        JOIN assertion a ON a.claim_id = c.id
        JOIN entity s ON s.id = c.subject_id
        LEFT JOIN entity o ON o.id = c.object_id
        WHERE e.doc_id = ? AND a.status = 'verified'
        ORDER BY s.name, c.predicate
    """, (doc_id,)).fetchall()
    fm = _frontmatter({"id": doc_id, "title": doc["title"], "type": "source",
                       "tags": ["source"], "generated": now()[:10]})
    lines = [fm, f"# {doc['title']}", ""]
    lines.append(f"- Kind: `{doc['kind']}`")
    if doc["url"]:
        lines.append(f"- URL: {doc['url']}")
    lines.append(f"- Local path: `{doc['local_path']}`")
    lines.append(f"- SHA-256: `{doc['text_sha256']}`")
    lines.append(f"- Sentences: {doc['sentence_count']}")
    if doc["revision_id"]:
        lines.append(f"- Revision: {doc['revision_id']}")
    lines.append("")
    lines.append(f"## Verified claims citing this document ({len(rows)})")
    lines.append("")
    for row in rows:
        obj = row["object_name"] or ""
        lines.append(f"- {_wl('people/' + row['subject_id'], row['subject_name'])} — {row['predicate']} — {obj}")
        if row["quote"]:
            lines.append(f"  > \"{_quote(row['quote'], 400)}\"")
    return "\n".join(lines)


def commission_page(db: sqlite3.Connection, entity_id: str) -> str:
    ent = _entity_row(db, entity_id)
    if not ent:
        return ""
    rows = _assertions_for_object(db, entity_id)
    fm = _frontmatter({"id": entity_id, "title": ent["name"], "type": "commission",
                       "tags": ["commission", "verified"], "generated": now()[:10]})
    lines = [fm, f"# {ent['name']}", "", f"*Verified members: {len({r['subject_id'] for r in rows})}*", ""]
    for row in rows:
        lines.append(f"- {_wl('people/' + row['subject_id'], row['subject_name'])}")
        if row["quote"]:
            lines.append(f"  > \"{_quote(row['quote'], 400)}\"")
        if row["doc_id"]:
            lines.append(f"  > Source: {_wl('sources/' + row['doc_id'], row['doc_title'])} · grade {row['evidence_grade']}")
    return "\n".join(lines)


def generate_wiki(db: sqlite3.Connection, output_dir: Path = WIKI_V2_DIR) -> dict[str, int]:
    (output_dir / "people").mkdir(parents=True, exist_ok=True)
    (output_dir / "organisations").mkdir(parents=True, exist_ok=True)
    (output_dir / "commissions").mkdir(parents=True, exist_ok=True)
    (output_dir / "sources").mkdir(parents=True, exist_ok=True)
    for old in output_dir.rglob("*.md"):
        old.unlink()

    active = db.execute("""
        SELECT DISTINCT e.id, e.kind FROM entity e
        WHERE e.status='active' AND (
          EXISTS (SELECT 1 FROM claim c JOIN assertion a ON a.claim_id=c.id
                  WHERE c.subject_id=e.id AND a.status='verified')
          OR EXISTS (SELECT 1 FROM claim c JOIN assertion a ON a.claim_id=c.id
                     WHERE c.object_id=e.id AND a.status='verified')
        )
    """).fetchall()
    counts = Counter()
    for row in active:
        if row["kind"] == "person":
            page = person_page(db, row["id"])
            path = output_dir / "people" / f"{row['id']}.md"
            counts["people"] += 1
        elif row["kind"] in ("organisation", "institution"):
            page = organisation_page(db, row["id"])
            path = output_dir / "organisations" / f"{row['id']}.md"
            counts["organisations"] += 1
        elif row["kind"] == "commission":
            page = commission_page(db, row["id"])
            path = output_dir / "commissions" / f"{row['id']}.md"
            counts["commissions"] += 1
        else:
            continue
        if page:
            path.write_text(page, encoding="utf-8")

    docs = db.execute("""
        SELECT DISTINCT s.id FROM source_document s
        JOIN evidence e ON e.doc_id=s.id
        JOIN assertion a ON a.claim_id=e.claim_id
        WHERE a.status='verified'
    """).fetchall()
    for row in docs:
        page = source_page(db, row["id"])
        if page:
            (output_dir / "sources" / f"{row['id']}.md").write_text(page, encoding="utf-8")
            counts["sources"] += 1

    _index(db, output_dir)
    _start_here(output_dir)
    _citations(db, output_dir)
    _stats(db, output_dir)
    return dict(counts)


def _index(db: sqlite3.Connection, output_dir: Path) -> None:
    counts = db.execute("SELECT status, COUNT(*) FROM assertion GROUP BY 1").fetchall()
    summary = ", ".join(f"{status}: {n}" for status, n in counts)
    (output_dir / "index.md").write_text(
        _frontmatter({"id": "index", "title": "Euro-SDT v2", "type": "index", "tags": ["index"]})
        + "\n\n# Euro-SDT v2\n\n"
        + "Verified-only citation-anchored elite graph.\n\n"
        + f"Assertions: {summary}\n\n"
        + "- [[stats|Statistics]]\n- [[citations|Citations]]\n",
        encoding="utf-8",
    )


def _start_here(output_dir: Path) -> None:
    text = """---
id: start-here
title: Start Here
type: index
tags: [index]
---

# Start Here

This vault is the verified-only Euro-SDT wiki.

## Open the graph

Press **Ctrl+G** (or **Cmd+G** on macOS), or open the command palette and run
**Graph view: Open graph view**. Close any Canvas tab first.

If the graph looks empty:

1. Open the graph view's filter panel.
2. Clear the search box.
3. Turn **Orphans** on.
4. Make sure the vault is `wiki_v2`, not a subfolder or a new vault.

The Obsidian graph is a **page-link** view. The typed person–organisation graph
with edge classes, grades, quotes, and source locators is in `graph/`:

- `graph/graph.graphml` — Gephi / Cytoscape
- `graph/edges.csv` — analysis
- `graph/graph_overview.png` — static overview

## Browse

- [[index|Index]]
- [[stats|Statistics]]
- [[citations|Citations]]
"""
    (output_dir / "Start Here.md").write_text(text, encoding="utf-8")


def _citations(db: sqlite3.Connection, output_dir: Path) -> None:
    rows = db.execute("""
        SELECT s.id, s.title, s.kind, s.url, COUNT(DISTINCT a.claim_id) AS claims
        FROM source_document s
        LEFT JOIN evidence e ON e.doc_id=s.id
        LEFT JOIN assertion a ON a.claim_id=e.claim_id AND a.status='verified'
        GROUP BY s.id ORDER BY claims DESC, s.title
    """).fetchall()
    lines = [_frontmatter({"id": "citations", "title": "Citations", "type": "index", "tags": ["citations"]}),
             "# Citations", "", "| Source | Kind | Verified claims |", "|---|---|---:|"]
    for row in rows:
        lines.append(f"| {_wl('sources/' + row['id'], row['title'])} | {row['kind']} | {row['claims']} |")
    (output_dir / "citations.md").write_text("\n".join(lines), encoding="utf-8")


def _stats(db: sqlite3.Connection, output_dir: Path) -> None:
    grades = db.execute("SELECT evidence_grade, status, COUNT(*) FROM assertion GROUP BY 1,2 ORDER BY 1,2").fetchall()
    preds = db.execute("""
        SELECT c.predicate, a.status, COUNT(*) FROM assertion a JOIN claim c ON c.id=a.claim_id
        GROUP BY 1,2 ORDER BY 1,2
    """).fetchall()
    cats = db.execute("""
        SELECT s.category, COUNT(DISTINCT c.id) AS claims,
               SUM(CASE WHEN a.status='verified' THEN 1 ELSE 0 END) AS verified
        FROM claim c JOIN entity s ON s.id=c.subject_id JOIN assertion a ON a.claim_id=c.id
        WHERE s.kind='person' GROUP BY 1 ORDER BY 2 DESC
    """).fetchall()
    sources = db.execute("SELECT kind, COUNT(*) FROM source_document GROUP BY 1 ORDER BY 2 DESC").fetchall()
    lines = [_frontmatter({"id": "stats", "title": "v2 Statistics", "type": "stats", "tags": ["stats"]}),
             "# v2 Statistics", "",
             "## Assertions by grade and status", "",
             "| Grade | Status | Count |", "|---|---|---:|"]
    for grade, status, n in grades:
        lines.append(f"| {grade} | {status} | {n} |")
    lines += ["", "## Predicate coverage", "", "| Predicate | Status | Count |", "|---|---|---:|"]
    for pred, status, n in preds:
        lines.append(f"| {pred} | {status} | {n} |")
    lines += ["", "## Person categories", "", "| Category | Claims | Verified |", "|---|---:|---:|"]
    for cat, claims, verified in cats:
        lines.append(f"| {cat or '(none)'} | {claims} | {verified} |")
    lines += ["", "## Source documents", "", "| Kind | Documents |", "|---|---:|"]
    for kind, n in sources:
        lines.append(f"| {kind} | {n} |")
    (output_dir / "stats.md").write_text("\n".join(lines), encoding="utf-8")
