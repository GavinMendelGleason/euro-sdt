"""Orchestrate the v2 rebuild."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .db import AUDIT_DIR, V1_DB_PATH, V2_DB_PATH, connect, reset_db, table_counts
from .citations import build_citation_map
from .claims import DocCache, _finish_assertions, migrate_manifests, migrate_v1
from .corpus import build_corpus
from .entities import build_registry, write_entity_audit
from .recover import recover_claims


def log(message: str) -> None:
    print(f"[v2] {message}", flush=True)


def rebuild(fetch_missing: bool = False, skip_recover: bool = False) -> None:
    started = time.time()
    log(f"resetting {V2_DB_PATH.name}")
    db = reset_db(V2_DB_PATH)
    v1 = connect(V1_DB_PATH)

    log("building entity registry")
    v1_to_v2 = build_registry(db, v1)
    log(f"  {len(v1_to_v2)} v1 entities -> {table_counts(db)['entity']} v2 entities")

    log("building source corpus and sentence table")
    doc_by_stem = build_corpus(db, fetch_missing=fetch_missing)
    counts = table_counts(db)
    log(f"  {counts['source_document']} documents, {counts['sentence']} sentences")

    log("mapping citations to documents")
    citation_map = build_citation_map(db, v1, doc_by_stem)
    log(f"  {len(citation_map)} citations mapped")

    log("migrating v1 facts and manifests as claims")
    docs = DocCache(db)
    migrated = migrate_v1(db, v1, v1_to_v2, citation_map, docs)
    manifest_rows = migrate_manifests(db, v1_to_v2, docs)
    log(f"  {migrated} v1 fact claims, {manifest_rows} manifest evidence rows")

    if not skip_recover:
        log("recovering evidence by deterministic sentence search")
        recovered = recover_claims(db)
        log(f"  {recovered} claims recovered")

    log("grading evidence")
    db.execute("DELETE FROM rejection WHERE stage='locator'")
    _finish_assertions(db)
    write_entity_audit(db)

    counts = table_counts(db)
    log("counts: " + json.dumps(counts))
    log("grades:")
    for row in db.execute(
        "SELECT evidence_grade, status, COUNT(*) FROM assertion GROUP BY 1,2 ORDER BY 3 DESC"
    ):
        log(f"  {row[0]:>4} {row[1]:<13} {row[2]}")
    log(f"done in {time.time() - started:.1f}s")

    AUDIT_DIR.mkdir(exist_ok=True)
    (AUDIT_DIR / "pipeline_summary.json").write_text(
        json.dumps({"counts": counts, "elapsed_seconds": round(time.time() - started, 1)}, indent=2),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the v2 citation-anchored assertion layer.")
    parser.add_argument("--fetch-missing", action="store_true",
                        help="Fetch Wikipedia pages that v1 cited but did not cache.")
    parser.add_argument("--skip-recover", action="store_true",
                        help="Do not run deterministic sentence recovery.")
    args = parser.parse_args(argv)
    rebuild(fetch_missing=args.fetch_missing, skip_recover=args.skip_recover)
    return 0


if __name__ == "__main__":
    sys.exit(main())
