#!/usr/bin/env python3
"""Rebuild, extract, repair, adjudicate, and render the v2 layer."""
from __future__ import annotations

import sqlite3
import time

from euro_sdt.v2.adjudicate import adjudicate
from euro_sdt.v2.audit_v2 import audit
from euro_sdt.v2.claims import _finish_assertions
from euro_sdt.v2.db import connect
from euro_sdt.v2.extract import extract
from euro_sdt.v2.graph import build_graph
from euro_sdt.v2.pipeline import rebuild
from euro_sdt.v2.repair import recompute_role_flags, resolve_literal_objects
from euro_sdt.v2.report import generate_report
from euro_sdt.v2.wiki import generate_wiki


def main() -> int:
    started = time.time()
    rebuild()
    db = connect()

    print("[finalize] extraction (cached chunks are reused)")
    print(extract(db, ("commissioner",), limit=150, workers=6))

    print("[finalize] repairs")
    print("literal objects:", resolve_literal_objects(db))
    print("role flags:", recompute_role_flags(db))
    db.execute("DELETE FROM rejection WHERE stage='locator'")
    _finish_assertions(db, preserve_adjudicated=True)

    print("[finalize] adjudication")
    print(adjudicate(db, workers=6))

    db.execute("DELETE FROM rejection WHERE rowid NOT IN (SELECT MIN(rowid) FROM rejection GROUP BY claim_id, stage)")
    db.commit()
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    print("[finalize] rendering")
    metrics = build_graph(db)
    counts = generate_wiki(db)
    report = audit(db)
    generate_report(db)
    print("graph:", metrics["all_verified"]["nodes"], "nodes,", metrics["all_verified"]["edges"], "edges")
    print("wiki:", counts)
    print("assertions:", report["assertions_by_status"])
    print(f"elapsed: {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
