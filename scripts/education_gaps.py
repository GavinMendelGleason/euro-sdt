#!/usr/bin/env python3
"""Report missing education coverage and suggested source types."""
from __future__ import annotations

import csv
import sqlite3
from collections import Counter
from pathlib import Path

from euro_sdt.v2.db import AUDIT_DIR, connect

SUGGESTIONS = {
    'commissioner': 'Commission person page; Wikipedia; official CV; declaration of interests',
    'dg': 'Commission DG CV PDF; EU Whoiswho; official CV',
    'ddg': 'Commission DG CV PDF; EU Whoiswho; official CV',
    'mep': 'European Parliament member page; national party biography; Wikipedia',
    'corporate_elite': 'Company leadership page; annual report; Wikipedia',
    'cjeu_judge': 'CURIA member biography; Wikipedia; national judicial profile',
    'cjeu_ag': 'CURIA member biography; Wikipedia; national judicial profile',
}


def main() -> int:
    db = connect()
    rows = []
    for category, suggestion in SUGGESTIONS.items():
        people = db.execute(
            "SELECT id, name FROM entity WHERE kind='person' AND status='active' AND category=? ORDER BY name",
            (category,),
        ).fetchall()
        for person in people:
            has = db.execute("""
                SELECT 1 FROM claim c JOIN assertion a ON a.claim_id=c.id
                WHERE c.subject_id=? AND a.status='verified' AND c.predicate='educated_at' LIMIT 1
            """, (person['id'],)).fetchone()
            if has:
                continue
            docs = db.execute("SELECT id, kind FROM source_document WHERE subject_id=?", (person['id'],)).fetchall()
            rows.append({
                'person_id': person['id'], 'name': person['name'], 'category': category,
                'local_docs': len(docs), 'doc_kinds': ';'.join(sorted({d['kind'] for d in docs})),
                'suggested_sources': suggestion,
            })
    AUDIT_DIR.mkdir(exist_ok=True)
    with (AUDIT_DIR / 'education_gaps.csv').open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(row['category'] for row in rows)
    lines = [
        '# Education Gaps', '',
        f'People without a verified `educated_at` claim: {len(rows)}.', '',
        '| Category | Missing | With local doc | Without local doc |',
        '|---|---:|---:|---:|',
    ]
    for category in SUGGESTIONS:
        group = [row for row in rows if row['category'] == category]
        if group:
            local = sum(1 for row in group if row['local_docs'])
            lines.append(f'| {category} | {len(group)} | {local} | {len(group)-local} |')
    lines += ['', 'Full list: `audit/education_gaps.csv`.', '']
    (AUDIT_DIR / 'education_gaps.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'wrote audit/education_gaps.csv/.md ({len(rows)} people)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
