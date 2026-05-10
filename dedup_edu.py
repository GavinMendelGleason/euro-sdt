"""
dedup_edu.py — Deduplicate educational institution entities using the same
string similarity + LLM judge approach as extract_orgs.py.

Reads all institution entities from euro_sdt.db, groups duplicates,
saves audit trail to manifests/_edu_dedup.json, and merges fact targets.

Usage:
    .venv/bin/python dedup_edu.py [--dry-run]
"""
import sqlite3, json, os, re, difflib, urllib.request, urllib.parse, time
from collections import defaultdict

API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DB = 'euro_sdt.db'
MANIFEST_DIR = 'manifests'

SKIP_NAMES = {
    '(none explicitly named)', '(none)', 'unknown', 'n/a',
    'secondary school', 'high school', 'gymnasium', 'lyceum', 'lycée',
    'primary school', 'secondary education', 'secondary studies',
}

def slugify(t):
    return re.sub(r'[^a-z0-9]+', '-', t.lower().strip()).strip('-')


def call_llm(prompt, max_tokens=80):
    if not API_KEY: return None
    payload = json.dumps({
        'model': 'deepseek-v4-pro',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.0,
    }).encode()
    req = urllib.request.Request('https://api.deepseek.com/v1/chat/completions',
        data=payload, headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'})
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=45)
            return json.loads(resp.read())['choices'][0]['message']['content'].strip()
        except Exception as e:
            if attempt < 2: time.sleep(2 * (attempt + 1))
    return None


def get_institutions(db_path):
    """Get all institution names from educated_at facts, with usage counts."""
    db = sqlite3.connect(db_path)
    names = []
    for r in db.execute("""
        SELECT TRIM(obj.name), COUNT(DISTINCT f.entity_id) as n_people, obj.id
        FROM fact f JOIN entity obj ON obj.id = f.object
        WHERE f.predicate = 'educated_at'
        GROUP BY obj.name ORDER BY n_people DESC
    """):
        name, count, eid = r
        if name.lower().strip() in SKIP_NAMES:
            continue
        if len(name) < 3:
            continue
        names.append({'name': name, 'count': count, 'entity_id': eid})
    db.close()
    return names


def extract_context(db_path, institution_names):
    """Get a representative educated_at fact for each institution for evidence."""
    db = sqlite3.connect(db_path)
    context = {}
    for inst in institution_names:
        name = inst['name']
        row = db.execute("""
            SELECT e.name, p.quote_text FROM fact f
            JOIN entity e ON e.id = f.entity_id
            JOIN provenance p ON p.fact_id = f.id
            JOIN entity obj ON obj.id = f.object
            WHERE f.predicate = 'educated_at' AND obj.name = ?
            LIMIT 3
        """, [name]).fetchall()
        if row:
            context[name] = [
                {'person': r[0], 'evidence': (r[1] or '')[:300]}
                for r in row
            ]
        else:
            # Fallback: just get the person names
            people = db.execute("""
                SELECT e.name FROM fact f
                JOIN entity e ON e.id = f.entity_id
                WHERE f.predicate = 'educated_at' AND f.object = (
                    SELECT id FROM entity WHERE name = ? LIMIT 1
                ) LIMIT 3
            """, [name]).fetchall()
            context[name] = [{'person': r[0], 'evidence': f'Attended {name}'} for r in people]
    db.close()
    return context


def deduplicate(institutions, edu_context, auto_threshold=0.95, llm_min=0.30, max_llm=100):
    """Two-pass dedup: auto-merge + LLM judge."""
    raw_names = [inst['name'] for inst in institutions]
    raw_list = sorted(raw_names)

    # Pass 1: auto-merge
    clusters = {}
    canonicals = {}
    for raw in raw_list:
        raw_lower = raw.lower().strip()
        matched = False
        for canonical in list(canonicals.keys()):
            if difflib.SequenceMatcher(None, raw_lower, canonical.lower()).ratio() >= auto_threshold:
                clusters[raw] = canonical
                canonicals[canonical].append(raw)
                matched = True
                break
        if not matched:
            clusters[raw] = raw
            canonicals[raw] = [raw]

    print(f"  Pass 1 (auto-merge >= {auto_threshold}): {len(raw_names)} raw → {len(canonicals)} clusters")

    # Pass 2: LLM judge
    raw_by_cluster = defaultdict(list)
    for raw in raw_list:
        raw_by_cluster[clusters.get(raw, raw)].append(raw)
    canonical_list = sorted(raw_by_cluster.keys(), key=lambda c: -len(raw_by_cluster[c]))

    candidates = []
    seen_pairs = set()
    for ci in range(len(canonical_list)):
        c1 = canonical_list[ci]
        reps1 = sorted(raw_by_cluster[c1], key=len)[:3]
        for cj in range(ci + 1, len(canonical_list)):
            c2 = canonical_list[cj]
            reps2 = sorted(raw_by_cluster[c2], key=len)[:3]
            best_ratio = 0
            best_pair = None
            for r1 in reps1:
                for r2 in reps2:
                    ratio = difflib.SequenceMatcher(None, r1.lower(), r2.lower()).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_pair = (r1, r2)
            if llm_min <= best_ratio < auto_threshold and best_pair:
                pk = tuple(sorted(best_pair))
                if pk not in seen_pairs:
                    seen_pairs.add(pk)
                    candidates.append((best_ratio, best_pair[0], best_pair[1], c1, c2))

    candidates.sort(key=lambda x: -x[0])
    print(f"  Pass 2 candidates: {len(candidates)} borderline pairs")

    if len(candidates) > max_llm:
        print(f"    Limiting to {max_llm} LLM calls")
        candidates = candidates[:max_llm]

    llm_log = []
    resolved_merged = 0
    resolved_separate = 0

    for idx, (ratio, r1, r2, c1, c2) in enumerate(candidates):
        ctx1 = edu_context.get(r1, [])
        ctx2 = edu_context.get(r2, [])

        evidence1 = '\n'.join(
            f'  [{i+1}] {c.get("person","?")} — "{c.get("evidence","")[:200]}"'
            for i, c in enumerate(ctx1[:2])
        ) or f'  (no evidence for {r1})'

        evidence2 = '\n'.join(
            f'  [{i+1}] {c.get("person","?")} — "{c.get("evidence","")[:200]}"'
            for i, c in enumerate(ctx2[:2])
        ) or f'  (no evidence for {r2})'

        prompt = f"""Are these two educational institution names referring to the SAME institution or DIFFERENT institutions?

Institution A: "{r1}"
Context A:
{evidence1}

Institution B: "{r2}"
Context B:
{evidence2}

Consider:
- Acronyms (LSE = London School of Economics, ENA = École nationale d'administration)
- Language variants (Université Libre de Bruxelles = Free University of Brussels = ULB)
- College vs university (Balliol College is part of Oxford University — but these are DIFFERENT entities)
- Merged universities (University of Manchester = Victoria University of Manchester after merger)
- Different campuses (University of California, Berkeley ≠ University of California, Los Angeles)

Reply with exactly one word: SAME or DIFFERENT
Then a one-line reason.
Example: SAME
LSE is the standard acronym for London School of Economics"""

        resp = call_llm(prompt, max_tokens=100)
        if not resp:
            continue

        lines = resp.strip().split('\n')
        verdict = lines[0].strip().upper()
        reason = lines[1].strip() if len(lines) > 1 else ''

        log_entry = {
            'raw_a': r1, 'raw_b': r2,
            'similarity': round(ratio, 3),
            'verdict': verdict,
            'reason': reason,
            'context_a': [c.get('person', '') for c in ctx1[:2]],
            'context_b': [c.get('person', '') for c in ctx2[:2]],
        }

        if verdict == 'SAME':
            for r in list(canonicals.get(c2, [c2])):
                clusters[r] = c1
                if r not in canonicals.get(c1, []):
                    canonicals[c1].append(r)
            if c2 in canonicals:
                del canonicals[c2]
            if c1 in raw_by_cluster and c2 in raw_by_cluster:
                raw_by_cluster[c1].extend(raw_by_cluster.pop(c2, []))
            log_entry['merged_into'] = c1
            resolved_merged += 1
        else:
            resolved_separate += 1

        llm_log.append(log_entry)

        if (idx + 1) % 20 == 0:
            print(f"    LLM progress: {idx+1}/{len(candidates)} | m={resolved_merged} s={resolved_separate}")

    print(f"    LLM decisions: {resolved_merged} merged, {resolved_separate} kept separate")
    return clusters, llm_log


def apply_merges(db_path, clusters, dry_run=False):
    """Update fact.object to point to canonical entity ID for merged institutions."""
    db = sqlite3.connect(db_path)

    # Build old_name → canonical_name map
    name_to_canonical = clusters

    # Build entity_id map: old entity_id → canonical entity_id
    id_map = {}
    for old_name, canonical_name in name_to_canonical.items():
        old_eid = db.execute("SELECT id FROM entity WHERE name=?", [old_name]).fetchone()
        canon_eid = db.execute("SELECT id FROM entity WHERE name=?", [canonical_name]).fetchone()
        if old_eid and canon_eid:
            old_eid = old_eid[0]
            canon_eid = canon_eid[0]
            if old_eid != canon_eid:
                id_map[old_eid] = canon_eid

    if not id_map:
        print("  No entity ID merges needed")
        return 0

    if dry_run:
        print(f"  DRY RUN: would remap {len(id_map)} entity IDs")
        for old_eid, canon_eid in list(id_map.items())[:5]:
            old_name = db.execute("SELECT name FROM entity WHERE id=?", [old_eid]).fetchone()
            canon_name = db.execute("SELECT name FROM entity WHERE id=?", [canon_eid]).fetchone()
            print(f"    {old_name[0] if old_name else old_eid} → {canon_name[0] if canon_name else canon_eid}")
        return 0

    total_updates = 0
    for old_eid, canon_eid in id_map.items():
        # Update facts
        result = db.execute("UPDATE fact SET object = ? WHERE object = ? AND predicate = 'educated_at'",
                            [canon_eid, old_eid])
        n = result.rowcount
        if n:
            total_updates += n
            # Also update provenance? No — provenance points to fact_id, not entity

    db.commit()

    # Clean up: remove orphan institution entities
    db.execute("""
        DELETE FROM entity WHERE category = 'university'
        AND id NOT IN (SELECT DISTINCT object FROM fact WHERE predicate = 'educated_at')
    """)

    db.commit()
    db.close()
    return total_updates


def main():
    dry_run = '--dry-run' in __import__('sys').argv

    if not API_KEY:
        print("ERROR: DEEPSEEK_API_KEY not set")
        return

    os.makedirs(MANIFEST_DIR, exist_ok=True)

    # Get institutions
    institutions = get_institutions(DB)
    print(f"{len(institutions)} unique educational institutions")

    # Get evidence context
    print("Loading evidence context...")
    edu_context = extract_context(DB, institutions)

    # Dedup
    clusters, llm_log = deduplicate(institutions, edu_context)

    canonicals = set(clusters.values())
    print(f"  Final: {len(set(clusters.keys()))} raw → {len(canonicals)} canonical names")

    # Save audit
    auto_merged = {}
    for canonical in sorted(canonicals):
        raws = [r for r, c in clusters.items() if c == canonical]
        if len(raws) > 1:
            auto_merged[canonical] = raws

    dedup_summary = {
        'raw_count': len(set(clusters.keys())),
        'canonical_count': len(canonicals),
        'auto_merged': auto_merged,
        'llm_decisions': llm_log,
        'clusters': {c: [r for r, cs in clusters.items() if cs == c] for c in sorted(canonicals)},
    }

    out_path = os.path.join(MANIFEST_DIR, '_edu_dedup.json')
    with open(out_path, 'w') as f:
        json.dump(dedup_summary, f, indent=2, ensure_ascii=False)
    print(f"Saved {out_path}")

    # Apply to DB
    updates = apply_merges(DB, clusters, dry_run=dry_run)
    if updates:
        print(f"Updated {updates} fact targets")
    elif not dry_run:
        print("0 updates needed")

    print(f"\nRemaining institutions after dedup:")
    db = sqlite3.connect(DB)
    count = db.execute("SELECT COUNT(DISTINCT object) FROM fact WHERE predicate='educated_at'").fetchone()[0]
    db.close()
    print(f"  {count} unique")


if __name__ == '__main__':
    main()
