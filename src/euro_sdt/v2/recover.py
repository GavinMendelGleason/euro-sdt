"""Recover evidence for claims that v1 recorded without a usable quote.

This is a deterministic sentence search, not generation. A sentence is used only
when it contains the subject and the object (or the subject's own CV/document
and the object), and it is stored verbatim with its sentence ID. Every recovered
row is marked so it can be filtered in analysis.
"""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict

from .db import now, uid
from .entities import aliases_for
from .locate import alias_in_text
from .tokenizer import normalize_text
from .claims import PREDICATE_KEYWORDS, _evidence_id, _literal_aliases

RECOVERABLE = {
    "served_on_commission", "from_country", "nominated_by", "held_portfolio",
    "educated_at", "member", "board_member", "chair", "advisory_board",
    "employed_by", "founder", "fellow", "attendee", "affiliated_with",
    "held_position", "post_mandate_occupation", "studied_field", "held_degree",
}


def _sentence_rows(db: sqlite3.Connection, doc_id: str):
    return db.execute(
        "SELECT id, ordinal, char_start, char_end, text FROM sentence WHERE doc_id=? ORDER BY ordinal",
        (doc_id,),
    ).fetchall()


def _object_aliases(db: sqlite3.Connection, claim: sqlite3.Row) -> tuple[str, ...]:
    if claim["object_id"]:
        return aliases_for(db, claim["object_id"])
    return _literal_aliases(claim["object_literal"])


def _candidate_docs(db: sqlite3.Connection, claim: sqlite3.Row) -> list[str]:
    docs: list[str] = []
    seen: set[str] = set()

    def add(rows):
        for row in rows:
            if row[0] not in seen:
                seen.add(row[0])
                docs.append(row[0])

    add(db.execute("SELECT id FROM source_document WHERE subject_id=?", (claim["subject_id"],)).fetchall())
    if claim["object_id"]:
        add(db.execute("SELECT id FROM source_document WHERE subject_id=?", (claim["object_id"],)).fetchall())
        # Commission / organisation pages are often titled by the object name.
        name = db.execute("SELECT name FROM entity WHERE id=?", (claim["object_id"],)).fetchone()
        if name:
            token = normalize_text(name[0]).split()[0] if name[0] else ""
            if token:
                add(db.execute(
                    "SELECT id FROM source_document WHERE kind='wikipedia' AND lower(title) LIKE ? LIMIT 8",
                    (f"%{normalize_text(name[0])}%",),
                ).fetchall())
    return docs


def recover_claims(db: sqlite3.Connection, max_claims: int | None = None) -> int:
    claims = db.execute(
        "SELECT c.* FROM claim c WHERE c.predicate IN ({}) AND NOT EXISTS ("
        "  SELECT 1 FROM evidence e WHERE e.claim_id=c.id AND e.locator_status='located'"
        ") ORDER BY c.predicate, c.subject_id".format(",".join("?" for _ in RECOVERABLE)),
        tuple(sorted(RECOVERABLE)),
    ).fetchall()
    if max_claims:
        claims = claims[:max_claims]

    alias_cache: dict[str, tuple[str, ...]] = {}
    doc_cache: dict[str, list] = {}
    recovered = 0

    for claim in claims:
        subject_aliases = alias_cache.setdefault(claim["subject_id"], aliases_for(db, claim["subject_id"]))
        object_aliases = alias_cache.setdefault(
            claim["object_id"] or f"lit:{claim['object_literal']}",
            _object_aliases(db, claim),
        )
        role_words = PREDICATE_KEYWORDS.get(claim["predicate"], ())
        if claim["role"] and claim["role"] in PREDICATE_KEYWORDS:
            role_words = tuple(set(role_words) | set(PREDICATE_KEYWORDS[claim["role"]]))
        best = None  # (score, doc_id, sentence, flags)
        for doc_id in _candidate_docs(db, claim):
            if doc_id not in doc_cache:
                doc_cache[doc_id] = _sentence_rows(db, doc_id)
            subject_row = db.execute("SELECT subject_id, kind FROM source_document WHERE id=?", (doc_id,)).fetchone()
            doc_subject = subject_row["subject_id"] if subject_row else None
            doc_kind = subject_row["kind"] if subject_row else None
            if claim["predicate"] == "served_on_commission" and doc_kind == "revolving_door":
                continue
            for sentence in doc_cache[doc_id]:
                text = sentence["text"]
                if len(text) > 1200:
                    continue
                norm = normalize_text(text)
                if claim["predicate"] == "post_mandate_occupation" and doc_kind == "revolving_door":
                    if not any(word in norm for word in ("authoris", "approved", "decision")):
                        continue
                subj = alias_in_text(text, subject_aliases)
                obj = alias_in_text(text, object_aliases) if object_aliases else False
                role = any(word in norm for word in role_words) if role_words else False
                doc_ok = bool(doc_subject and doc_subject == claim["subject_id"])
                if subj and obj and role:
                    score = 100
                elif subj and obj:
                    score = 80
                elif doc_ok and obj and role:
                    score = 90
                elif doc_ok and obj:
                    score = 72
                elif subj and role and claim["predicate"] in ("served_on_commission",):
                    score = 60
                else:
                    continue
                score -= min(20, len(text) // 100)
                if doc_kind == "revolving_door":
                    score -= 15
                elif doc_kind == "entity_md":
                    score -= 25
                elif doc_kind == "org_site":
                    score -= 5
                if best is None or score > best[0]:
                    best = (score, doc_id, sentence, subj, obj, role, doc_ok)

        if not best or best[0] < 55:
            continue
        score, doc_id, sentence, subj, obj, role, doc_ok = best
        claim_id = claim["id"]
        # Replace the unusable evidence with the recovered sentence.
        db.execute("DELETE FROM evidence WHERE claim_id=?", (claim_id,))
        db.execute(
            "INSERT OR REPLACE INTO evidence (id, claim_id, doc_id, sentence_start_id, sentence_end_id, "
            "char_start, char_end, quote, locator_status, matched_chars, subject_mentioned, "
            "object_mentioned, role_mentioned, subject_context, notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                _evidence_id(claim_id, doc_id, sentence["text"]), claim_id, doc_id,
                sentence["id"], sentence["id"], sentence["char_start"], sentence["char_end"],
                sentence["text"], "located", len(sentence["text"]),
                int(subj), int(obj), int(role), "span" if subj else ("document" if doc_ok else "none"),
                f"recovered_sentence_search score={score}",
            ),
        )
        recovered += 1

    db.commit()
    return recovered
