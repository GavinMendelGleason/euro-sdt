"""Post-build repairs that do not require a full rebuild."""

from __future__ import annotations

import sqlite3

from .claims import PREDICATE_KEYWORDS, _keyword_present
from .db import normalize_name
from .entities import entity_id_for
from .tokenizer import normalize_text

ROLE_REPAIR_PREDICATES = {"held_portfolio", "nominated_by", "from_country", "held_position", "post_mandate_occupation"}


def resolve_literal_objects(db: sqlite3.Connection) -> int:
    """Turn a literal that is an entity ID into an object reference.

    If the resolved claim already exists, merge the duplicate: move its
    evidence to the surviving claim and delete the duplicate.
    """
    rows = db.execute(
        "SELECT id, subject_id, predicate, role, object_literal FROM claim "
        "WHERE object_id IS NULL AND object_literal IS NOT NULL"
    ).fetchall()
    fixed = 0
    for row in rows:
        literal = row["object_literal"]
        found = db.execute("SELECT id FROM entity WHERE id=?", (literal,)).fetchone()
        if not found:
            found_id = entity_id_for(db, literal, "organisation")
            found = (found_id,) if found_id else None
        if not found:
            continue
        entity_id = found[0]
        existing = db.execute(
            "SELECT id FROM claim WHERE subject_id=? AND predicate=? AND object_id=? AND COALESCE(role,'')=COALESCE(?,'')",
            (row["subject_id"], row["predicate"], entity_id, row["role"]),
        ).fetchone()
        if existing:
            target = existing[0]
            if _claim_rank(db, row["id"]) < _claim_rank(db, target):
                # The literal claim is stronger: keep it and retire the target.
                _move_evidence(db, target, row["id"])
                db.execute("DELETE FROM adjudication WHERE claim_id=?", (target,))
                db.execute("DELETE FROM rejection WHERE claim_id=?", (target,))
                db.execute("DELETE FROM assertion WHERE claim_id=?", (target,))
                db.execute("DELETE FROM claim WHERE id=?", (target,))
                db.execute("UPDATE claim SET object_id=?, object_literal=NULL WHERE id=?", (entity_id, row["id"]))
            else:
                _move_evidence(db, row["id"], target)
                db.execute("DELETE FROM adjudication WHERE claim_id=?", (row["id"],))
                db.execute("DELETE FROM rejection WHERE claim_id=?", (row["id"],))
                db.execute("DELETE FROM assertion WHERE claim_id=?", (row["id"],))
                db.execute("DELETE FROM claim WHERE id=?", (row["id"],))
        else:
            db.execute("UPDATE claim SET object_id=?, object_literal=NULL WHERE id=?", (entity_id, row["id"]))
        fixed += 1
    db.commit()
    return fixed


def _claim_rank(db: sqlite3.Connection, claim_id: str) -> tuple:
    row = db.execute("SELECT status, evidence_grade FROM assertion WHERE claim_id=?", (claim_id,)).fetchone()
    if not row:
        return (3, 3)
    status_rank = {"verified": 0, "needs_review": 1, "rejected": 2}.get(row[0], 3)
    grade_rank = {"A": 0, "B": 1, "C": 2, "none": 3}.get(row[1], 3)
    return (status_rank, grade_rank)


def _move_evidence(db: sqlite3.Connection, source: str, target: str) -> None:
    rows = db.execute("SELECT * FROM evidence WHERE claim_id=?", (source,)).fetchall()
    for evidence in rows:
        try:
            db.execute("UPDATE evidence SET claim_id=? WHERE id=?", (target, evidence["id"]))
        except sqlite3.IntegrityError:
            # Copy with a deterministic new ID so the quote is not lost.
            new_id = "e-" + __import__("hashlib").sha1(
                f"{target}|{evidence['doc_id']}|{evidence['quote']}|{evidence['id']}".encode()
            ).hexdigest()[:16]
            db.execute(
                "INSERT OR IGNORE INTO evidence (id, claim_id, doc_id, sentence_start_id, sentence_end_id, "
                "char_start, char_end, quote, locator_status, matched_chars, subject_mentioned, "
                "object_mentioned, role_mentioned, subject_context, notes) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (new_id, target, evidence["doc_id"], evidence["sentence_start_id"], evidence["sentence_end_id"],
                 evidence["char_start"], evidence["char_end"], evidence["quote"], evidence["locator_status"],
                 evidence["matched_chars"], evidence["subject_mentioned"], evidence["object_mentioned"],
                 evidence["role_mentioned"], evidence["subject_context"], evidence["notes"]),
            )
            db.execute("DELETE FROM evidence WHERE id=?", (evidence["id"],))
    db.execute("DELETE FROM evidence WHERE claim_id=?", (source,))


def reject_party_group_mismatches(db: sqlite3.Connection) -> int:
    """A quote about the EPP parliamentary group is not a claim about the party."""
    rows = db.execute("""
        SELECT a.claim_id, a.status FROM assertion a
        JOIN claim c ON c.id=a.claim_id
        JOIN entity o ON o.id=c.object_id
        JOIN evidence e ON e.claim_id=c.id AND e.locator_status='located'
        WHERE lower(o.name) IN ('european people''s party', 'european peoples party')
          AND lower(e.quote) LIKE '%party group%'
    """).fetchall()
    for row in rows:
        if row["status"] == "verified":
            db.execute(
                "UPDATE assertion SET status='rejected', reason=?, adjudicator='deterministic', adjudicated_at=datetime('now') "
                "WHERE claim_id=?",
                ("quote names the parliamentary group, not the party", row["claim_id"]),
            )
            db.execute(
                "INSERT OR IGNORE INTO rejection (id, claim_id, stage, reason, created_at) "
                "VALUES (?,?,?,?,datetime('now'))",
                ("r-" + __import__("hashlib").sha1(f"{row['claim_id']}|party_group".encode()).hexdigest()[:16],
                 row["claim_id"], "party_group_guard", "quote names the parliamentary group, not the party"),
            )
    db.commit()
    return len(rows)


def recompute_role_flags(db: sqlite3.Connection) -> int:
    """Recompute role mention with word-boundary keyword matching."""
    rows = db.execute("""
        SELECT e.id, e.sentence_start_id, e.sentence_end_id, e.quote,
               c.predicate, c.role
        FROM evidence e JOIN claim c ON c.id = e.claim_id
        WHERE e.locator_status='located' AND c.predicate IN ({})
    """.format(",".join("?" for _ in ROLE_REPAIR_PREDICATES)), tuple(sorted(ROLE_REPAIR_PREDICATES))).fetchall()
    updated = 0
    for row in rows:
        text = row["quote"] or ""
        if row["sentence_start_id"] and row["sentence_end_id"]:
            start_doc, start_ord = row["sentence_start_id"].rsplit(":", 1)
            end_doc, end_ord = row["sentence_end_id"].rsplit(":", 1)
            if start_doc == end_doc:
                sentences = db.execute(
                    "SELECT text FROM sentence WHERE doc_id=? AND ordinal BETWEEN ? AND ? ORDER BY ordinal",
                    (start_doc, int(start_ord), int(end_ord)),
                ).fetchall()
                if sentences:
                    text = " ".join(s["text"] for s in sentences)
        words = PREDICATE_KEYWORDS.get(row["predicate"], ())
        if row["role"] and row["role"] in PREDICATE_KEYWORDS:
            words = tuple(set(words) | set(PREDICATE_KEYWORDS[row["role"]]))
        norm = normalize_text(text)
        present = int(any(_keyword_present(norm, word) for word in words)) if words else 1
        db.execute("UPDATE evidence SET role_mentioned=? WHERE id=?", (present, row["id"]))
        updated += 1
    db.commit()
    return updated
