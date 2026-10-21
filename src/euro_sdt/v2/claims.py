"""Migrate v1 facts and manifests into v2 claims, then grade evidence.

A claim is only a candidate. The deterministic locator decides whether its
quote exists; the flags decide whether the quote establishes subject, object and
role. Only grade A/B claims become verified assertions.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from .db import PROJECT_ROOT, normalize_name, now, slugify, uid
from .entities import aliases_for, entity_id_for, resolve_or_create
from .locate import DocumentIndex, alias_in_text
from .tokenizer import normalize_text, sentence_spans

PREDICATE_KEYWORDS = {
    "educated_at": ("graduat", "studied", "study", "degree", "diploma", "university", "school", "institute", "college", "educated", "phd", "doctor"),
    "served_on_commission": ("commission", "commissioner"),
    "member": ("member", "membership", "joined", "part of"),
    "board_member": ("board", "trustee", "supervisory", "director"),
    "advisory_board": ("advisory", "advisor"),
    "chair": ("chair", "chairman", "chairwoman", "president", "presiding"),
    "employed_by": ("ceo", "chief", "executive", "manager", "director", "head of", "worked", "works", "employed", "chairman"),
    "founder": ("found", "co-found", "founded"),
    "fellow": ("fellow",),
    "attendee": ("attend", "participat", "speaker", "guest"),
    "affiliated_with": ("member", "affiliated", "board", "trustee", "advisor", "chair", "president", "founder", "fellow"),
    "held_portfolio": ("commissioner", "portfolio", "president", "vice-president"),
    "post_mandate_occupation": (),
    "held_position": (),
    "from_country": ("born", "nationality", "citizen", "native", "comes from"),
    "nominated_by": ("nominat", "nominee", "appointed by", "proposed by", "put forward", "commission"),
    "held_portfolio": ("commissioner", "portfolio", "commission", "responsible for", "president", "vice-president"),
    "post_mandate_occupation": ("authoris", "approved", "occupation", "post-mandate", "after leaving", "decision"),
    "held_position": ("director", "head", "chief", "deputy", "secretary", "president", "manager"),
    "held_degree": ("phd", "doctor", "master", "bachelor", "degree", "diploma"),
    "studied_field": ("studied", "degree", "field", "major"),
    "works_at": ("works", "worked", "employed", "director", "head"),
}

ROLE_STRICT = {
    "chair", "board_member", "advisory_board", "employed_by", "founder",
    "fellow", "attendee", "from_country", "nominated_by", "held_portfolio",
    "held_position", "served_on_commission", "post_mandate_occupation",
}

ROLE_PATTERNS = [
    ("advisory_board", r"advisory|advisor"),
    ("board_member", r"board|trustee|supervisory|director"),
    ("chair", r"chair|president|presiding"),
    ("founder", r"founder|co-founder|founded"),
    ("fellow", r"fellow"),
    ("attendee", r"attend|particip|guest|speaker"),
    ("employed_by", r"ceo|chief|executive|manager|head of|director general|works at|worked at|employed"),
    ("member", r"member|membership"),
]


def normalize_role(raw: str | None) -> str | None:
    if not raw:
        return None
    low = raw.strip().lower()
    if len(low) > 80 or low.startswith(("http", "www")):
        return None
    for role, pattern in ROLE_PATTERNS:
        if re.search(pattern, low):
            return role
    return "affiliated_with"


def predicate_for_role(role: str | None) -> str:
    return role or "affiliated_with"


def _claim_key(subject_id: str, predicate: str, object_id: str | None,
               object_literal: str | None, role: str | None) -> str:
    key = "|".join([subject_id, predicate, object_id or "", object_literal or "", role or ""])
    return "c-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _evidence_id(claim_id: str, doc_id: str, quote: str) -> str:
    key = "|".join([claim_id, doc_id, quote[:200]])
    return "e-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _rejection_id(claim_id: str, stage: str) -> str:
    return "r-" + hashlib.sha1(f"{claim_id}|{stage}".encode("utf-8")).hexdigest()[:16]


def _predicate_keywords(predicate: str, role: str | None) -> tuple[str, ...]:
    words = PREDICATE_KEYWORDS.get(predicate, ())
    if role and role in PREDICATE_KEYWORDS:
        words = tuple(set(words) | set(PREDICATE_KEYWORDS[role]))
    return words


ISO_TO_COUNTRY = {
    "AUT": "Austria", "BEL": "Belgium", "BGR": "Bulgaria", "CYP": "Cyprus",
    "CZE": "Czechia", "DEU": "Germany", "DNK": "Denmark", "ESP": "Spain",
    "EST": "Estonia", "FIN": "Finland", "FRA": "France", "GBR": "United Kingdom",
    "GRC": "Greece", "HRV": "Croatia", "HUN": "Hungary", "IRL": "Ireland",
    "ITA": "Italy", "LTU": "Lithuania", "LUX": "Luxembourg", "LVA": "Latvia",
    "MLT": "Malta", "NLD": "Netherlands", "POL": "Poland", "PRT": "Portugal",
    "ROU": "Romania", "SVK": "Slovakia", "SVN": "Slovenia", "SWE": "Sweden",
}


def _keyword_present(text: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _literal_aliases(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    values = {value}
    if value in ISO_TO_COUNTRY:
        values.add(ISO_TO_COUNTRY[value])
    if "-" in value and " " not in value:
        values.add(value.replace("-", " "))
    if "→" in value:
        values.update(part.strip() for part in value.split("→") if part.strip())
    return tuple(values)


class DocCache:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.cache: dict[str, DocumentIndex] = {}

    def get(self, doc_id: str | None) -> DocumentIndex | None:
        if not doc_id:
            return None
        if doc_id not in self.cache:
            row = self.db.execute("SELECT local_path FROM source_document WHERE id=?", (doc_id,)).fetchone()
            if not row:
                return None
            path = PROJECT_ROOT / row["local_path"]
            text = path.read_text(encoding="utf-8", errors="replace")
            sentences = sentence_spans(text)
            self.cache[doc_id] = DocumentIndex(text, sentences)
        return self.cache[doc_id]


def _grade(locator_status: str, subject_context: str, object_mentioned: int,
           role_mentioned: int) -> tuple[str, str]:
    if locator_status != "located":
        return "none", "quote could not be located in the cited document"
    if subject_context == "none":
        return "C", "subject is not identifiable in the quoted span"
    if not object_mentioned:
        return "C", "object is not mentioned in the quoted span"
    if role_mentioned:
        return "A", "quote locates; subject, object and role are present"
    return "B", "quote locates; subject and object are present; role is implicit"


def _insert_claim(db: sqlite3.Connection, subject_id: str, predicate: str,
                  object_id: str | None, object_literal: str | None,
                  role: str | None, role_raw: str | None, start_date: str | None,
                  end_date: str | None, source_hint: str | None, extractor: str,
                  run_id: str | None = None) -> str:
    claim_id = _claim_key(subject_id, predicate, object_id, object_literal, role)
    db.execute(
        "INSERT OR IGNORE INTO claim (id, subject_id, predicate, object_id, object_literal, role, role_raw, "
        "start_date, end_date, source_hint, extractor, extractor_run, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (claim_id, subject_id, predicate, object_id, object_literal, role, role_raw,
         start_date, end_date, source_hint, extractor, run_id, now()),
    )
    return claim_id


def _add_evidence(db: sqlite3.Connection, claim_id: str, doc_id: str | None,
                  quote: str, hint_ordinal: int | None, docs: DocCache,
                  subject_aliases: tuple[str, ...], object_aliases: tuple[str, ...],
                  predicate: str, role: str | None, doc_subject_id: str | None,
                  claim_subject_id: str) -> None:
    if not doc_id:
        db.execute(
            "INSERT OR IGNORE INTO rejection (id, claim_id, stage, reason, created_at) VALUES (?,?,?,?,?)",
            (_rejection_id(claim_id, "source_resolution"), claim_id, "source_resolution",
             "citation could not be mapped to a local source document", now()),
        )
        return
    index = docs.get(doc_id)
    if not index:
        db.execute(
            "INSERT OR IGNORE INTO rejection (id, claim_id, stage, reason, created_at) VALUES (?,?,?,?,?)",
            (_rejection_id(claim_id, "source_resolution"), claim_id, "source_resolution",
             f"source document text is not available: {doc_id}", now()),
        )
        return
    location = index.locate(quote, hint_ordinal, subject_aliases)
    if location.status != "located":
        db.execute(
            "INSERT OR IGNORE INTO evidence (id, claim_id, doc_id, quote, locator_status, notes) "
            "VALUES (?,?,?,?,?,?)",
            (_evidence_id(claim_id, doc_id, quote), claim_id, doc_id, quote, location.status,
             "quote not found by deterministic locator"),
        )
        return
    assert location.sentence_start_ordinal is not None
    assert location.sentence_end_ordinal is not None
    span = index.span_text(location.sentence_start_ordinal, location.sentence_end_ordinal)
    subject_in_span = alias_in_text(span, subject_aliases)
    object_in_span = alias_in_text(span, object_aliases) if object_aliases else False
    role_tokens = _predicate_keywords(predicate, role)
    span_norm = normalize_text(span)
    role_in_span = any(_keyword_present(span_norm, token) for token in role_tokens) if role_tokens else True
    if subject_in_span:
        subject_context = "span"
    elif doc_subject_id and doc_subject_id == claim_subject_id:
        subject_context = "document"
    else:
        subject_context = "none"
    sentence_start = f"{doc_id}:{location.sentence_start_ordinal}"
    sentence_end = f"{doc_id}:{location.sentence_end_ordinal}"
    db.execute(
        "INSERT OR IGNORE INTO evidence (id, claim_id, doc_id, sentence_start_id, sentence_end_id, "
        "char_start, char_end, quote, locator_status, matched_chars, subject_mentioned, "
        "object_mentioned, role_mentioned, subject_context, notes) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (_evidence_id(claim_id, doc_id, quote), claim_id, doc_id, sentence_start, sentence_end,
         location.char_start, location.char_end, quote, location.status, location.matched_chars,
         int(subject_in_span), int(object_in_span), int(role_in_span), subject_context,
         "matched a truncated prefix" if location.matched_prefix else None),
    )


def _finish_assertions(db: sqlite3.Connection, preserve_adjudicated: bool = False) -> None:
    rows = db.execute(
        "SELECT c.id, c.predicate, c.role, "
        "  SUM(CASE WHEN e.locator_status='located' THEN 1 ELSE 0 END) AS n_sources, "
        "  MIN(CASE WHEN e.locator_status='located' THEN "
        "    CASE WHEN e.subject_context!='none' AND e.object_mentioned=1 AND e.role_mentioned=1 THEN 0 "
        "         WHEN e.subject_context!='none' AND e.object_mentioned=1 THEN 1 "
        "         WHEN e.subject_context!='none' OR e.object_mentioned=1 THEN 2 ELSE 3 END "
        "    ELSE 4 END) AS best "
        "FROM claim c LEFT JOIN evidence e ON e.claim_id=c.id GROUP BY c.id"
    ).fetchall()
    for row in rows:
        if preserve_adjudicated:
            existing = db.execute("SELECT adjudicator FROM assertion WHERE claim_id=?", (row["id"],)).fetchone()
            if existing and existing[0] and (existing[0].startswith("llm:") or existing[0] == "human"):
                continue
        best = row["best"]
        n_sources = row["n_sources"] or 0
        if best == 0:
            grade, status, reason = "A", "verified", "quote locates; subject, object and role present"
        elif best == 1:
            if row["predicate"] in ROLE_STRICT:
                grade, status, reason = "C", "needs_review", "quote locates; role or nomination wording is missing"
            else:
                grade, status, reason = "B", "verified", "quote locates; subject and object present"
        elif best == 2:
            grade, status, reason = "C", "needs_review", "quote locates but subject or object is missing"
        else:
            grade, status, reason = "none", "rejected", "no locatable quote supporting the claim"
        db.execute(
            "INSERT OR REPLACE INTO assertion (id, claim_id, status, evidence_grade, n_sources, reason, "
            "adjudicator, adjudicated_at) VALUES (?,?,?,?,?,?,?,?)",
            ("a-" + row["id"][2:], row["id"], status, grade, n_sources, reason, "deterministic", now()),
        )
        if status == "rejected":
            db.execute(
                "INSERT OR IGNORE INTO rejection (id, claim_id, stage, reason, created_at) VALUES (?,?,?,?,?)",
                (_rejection_id(row["id"], "locator"), row["id"], "locator", reason, now()),
            )
    db.commit()


def migrate_v1(db: sqlite3.Connection, v1: sqlite3.Connection, v1_to_v2: dict[str, str],
               citation_map: dict[str, str], docs: DocCache) -> int:
    facts = v1.execute(
        "SELECT f.id, f.entity_id, f.predicate, f.object, f.object_type, f.qualifier, "
        "f.start_date, f.end_date, p.quote_text, p.phrase_index, p.citation_id "
        "FROM fact f LEFT JOIN provenance p ON p.fact_id=f.id"
    ).fetchall()
    alias_cache: dict[str, tuple[str, ...]] = {}
    count = 0

    def aliases(entity_id: str | None) -> tuple[str, ...]:
        if not entity_id:
            return ()
        if entity_id not in alias_cache:
            alias_cache[entity_id] = aliases_for(db, entity_id)
        return alias_cache[entity_id]

    for fact in facts:
        subject_id = v1_to_v2.get(fact["entity_id"])
        if not subject_id:
            continue
        predicate = fact["predicate"]
        obj = fact["object"]
        role_raw = fact["qualifier"]
        if predicate in ("classified_as", "funding_notes", "has_description"):
            obj_id = None
            if fact["object_type"] in ("entity", "entity_id"):
                obj_id = v1_to_v2.get(obj)
            entity = subject_id
            attribute = {"classified_as": "org_type", "funding_notes": "funding", "has_description": "description"}[predicate]
            source_status = "manual_seed" if fact["citation_id"] in ("cit-orgs-classified", "cit-atlanticist-comparison") else "unverified"
            db.execute(
                "INSERT OR IGNORE INTO organisation_profile (id, entity_id, attribute, value, quote, status, notes) "
                "VALUES (?,?,?,?,?,?,?)",
                (uid("p-"), entity, attribute, obj, fact["quote_text"], source_status,
                 f"migrated from v1 fact {fact['id']}"),
            )
            continue
        object_id = None
        object_literal = None
        kind_for_object = {
            "educated_at": "institution",
            "served_on_commission": "commission",
            "affiliated_with": "organisation",
            "member_of": "organisation",
            "works_at": "organisation",
            "held_position": "organisation",
        }.get(predicate, "organisation")
        # A literal that is actually a known entity slug is still an entity.
        object_id = v1_to_v2.get(obj)
        if not object_id:
            object_id = entity_id_for(db, obj, kind_for_object)
        if not object_id and fact["object_type"] in ("entity", "entity_id"):
            object_id = entity_id_for(db, obj, "organisation")
            if not object_id and predicate == "educated_at":
                object_id = resolve_or_create(db, obj, "institution", category="institution")
            if not object_id and predicate == "served_on_commission":
                object_id = resolve_or_create(db, obj, "commission", category="commission")
        if not object_id:
            object_literal = obj

        if predicate in ("affiliated_with", "member_of", "works_at"):
            role = normalize_role(role_raw) if predicate == "affiliated_with" else "member"
            if predicate == "member_of" and role_raw and normalize_name(role_raw) == normalize_name(obj):
                role = "member"
            predicate = "employed_by" if predicate == "works_at" else predicate_for_role(role)
        else:
            role = None
            if predicate == "works_at":
                predicate = "employed_by"

        claim_id = _insert_claim(
            db, subject_id, predicate, object_id, object_literal, role, role_raw,
            fact["start_date"], fact["end_date"],
            fact["citation_id"], "v1_fact",
        )
        quote = fact["quote_text"]
        if quote is None:
            db.execute(
                "INSERT OR IGNORE INTO rejection (id, claim_id, stage, reason, created_at) VALUES (?,?,?,?,?)",
                (_rejection_id(claim_id, "migration"), claim_id, "migration", "v1 fact has no provenance row", now()),
            )
            continue
        doc_id = citation_map.get(fact["citation_id"])
        doc_subject = None
        if doc_id:
            row = db.execute("SELECT subject_id FROM source_document WHERE id=?", (doc_id,)).fetchone()
            doc_subject = row["subject_id"] if row else None
        _add_evidence(
            db, claim_id, doc_id, quote, fact["phrase_index"], docs,
            aliases(subject_id), aliases(object_id) or _literal_aliases(object_literal),
            predicate, role, doc_subject, subject_id,
        )
        count += 1
    db.commit()
    return count


def migrate_manifests(db: sqlite3.Connection, v1_to_v2: dict[str, str], docs: DocCache) -> int:
    manifest_dir = PROJECT_ROOT / "manifests"
    count = 0
    alias_cache: dict[str, tuple[str, ...]] = {}
    for path in sorted(manifest_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") != "ok":
            continue
        slug = data.get("slug") or path.stem
        name = data.get("name") or slug.replace("-", " ").title()
        subject_id = v1_to_v2.get(slug) or entity_id_for(db, name, "person")
        if not subject_id:
            continue
        # Prefer the Wikipedia document dedicated to this person.
        doc_row = db.execute(
            "SELECT id, subject_id FROM source_document WHERE kind='wikipedia' AND subject_id=? "
            "ORDER BY char_count DESC LIMIT 1", (subject_id,)
        ).fetchone()
        if not doc_row:
            doc_row = db.execute(
                "SELECT id, subject_id FROM source_document WHERE kind='wikipedia' AND id=?",
                (f"wikipedia-{slug}",)
            ).fetchone()
        doc_id = doc_row["id"] if doc_row else None
        doc_subject = doc_row["subject_id"] if doc_row else subject_id
        for org in data.get("orgs", []):
            raw_org = (org.get("organisation") or "").strip()
            if not raw_org:
                continue
            object_id = resolve_or_create(db, raw_org, "organisation")
            role_raw = org.get("role")
            role = normalize_role(role_raw)
            predicate = predicate_for_role(role)
            claim_id = _insert_claim(
                db, subject_id, predicate, object_id, None, role, role_raw,
                None, None, f"manifest:{path.name}", "v1_manifest",
            )
            quote = org.get("evidence") or ""
            subject_aliases = alias_cache.setdefault(subject_id, aliases_for(db, subject_id))
            object_aliases = alias_cache.setdefault(object_id, aliases_for(db, object_id))
            _add_evidence(
                db, claim_id, doc_id, quote, org.get("phrase"), docs,
                subject_aliases, object_aliases, predicate, role, doc_subject, subject_id,
            )
            count += 1
    db.commit()
    return count
