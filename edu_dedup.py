"""
edu_dedup.py — Systematic education institution deduplication.
Same two-pass approach as organisation dedup:
  1. String similarity >= 0.95 → auto-merge
  2. Pairs in [0.30, 0.95) → LLM judge with context
  3. Saves running merge list to _edu_dedup.json for reproducibility

Usage:
    .venv/bin/python edu_dedup.py
"""
import sqlite3, json, os, re, difflib, urllib.request, urllib.parse, time
from collections import defaultdict

API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DB = 'euro_sdt.db'
MANIFEST_DIR = 'manifests'


def call_llm(prompt, max_tokens=80):
    if not API_KEY: return None
    payload = json.dumps({
        'model': 'deepseek-v4-pro',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.0, 'thinking': {'type': 'disabled'},
    }).encode()
    req = urllib.request.Request(
        'https://api.deepseek.com/v1/chat/completions',
        data=payload,
        headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    )
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            return json.loads(resp.read())['choices'][0]['message']['content'].strip()
        except:
            if attempt < 2: time.sleep(2 * (attempt + 1))
    return None


def slugify(t):
    return re.sub(r'[^a-z0-9]+', '-', t.lower().strip()).strip('-')


def get_institutions(db):
    """Get all institution names with attendee counts."""
    return db.execute("""
        SELECT obj.name, obj.id, COUNT(DISTINCT f.entity_id) as n
        FROM fact f JOIN entity obj ON obj.id = f.object
        WHERE f.predicate = 'educated_at'
        GROUP BY obj.name ORDER BY n DESC
    """).fetchall()


def dedup_edu(db, institutions, auto_threshold=0.95, llm_min=0.30, max_llm=100):
    """Two-pass institution dedup."""
    names = [r[0] for r in institutions]
    
    # Pass 1: auto-merge
    clusters = {}; canonicals = {}
    for name in sorted(names):
        lower = name.lower().strip()
        matched = False
        for canonical in list(canonicals.keys()):
            if difflib.SequenceMatcher(None, lower, canonical.lower()).ratio() >= auto_threshold:
                clusters[name] = canonical
                canonicals[canonical].append(name)
                matched = True; break
        if not matched:
            clusters[name] = name
            canonicals[name] = [name]
    
    print(f"  Pass 1 (auto-merge >= {auto_threshold}): {len(names)} raw → {len(canonicals)} clusters")
    
    # Pass 2: LLM judge for borderline pairs
    raw_by_cluster = defaultdict(list)
    for name in names:
        raw_by_cluster[clusters.get(name, name)].append(name)
    
    canonical_list = sorted(raw_by_cluster.keys(), key=lambda c: -len(raw_by_cluster[c]))
    candidates = []; seen_pairs = set()
    
    for ci in range(len(canonical_list)):
        c1 = canonical_list[ci]
        reps1 = sorted(raw_by_cluster[c1], key=len)[:3]
        for cj in range(ci + 1, len(canonical_list)):
            c2 = canonical_list[cj]
            reps2 = sorted(raw_by_cluster[c2], key=len)[:3]
            best_ratio = 0; best_pair = None
            for r1 in reps1:
                for r2 in reps2:
                    ratio = difflib.SequenceMatcher(None, r1.lower(), r2.lower()).ratio()
                    if ratio > best_ratio: best_ratio = ratio; best_pair = (r1, r2)
            if llm_min <= best_ratio < auto_threshold and best_pair:
                pk = tuple(sorted(best_pair))
                if pk not in seen_pairs:
                    seen_pairs.add(pk)
                    candidates.append((best_ratio, best_pair[0], best_pair[1], c1, c2))
    
    candidates.sort(key=lambda x: -x[0])
    if len(candidates) > max_llm:
        candidates = candidates[:max_llm]
    
    print(f"  Pass 2 candidates: {len(candidates)} borderline pairs")
    
    llm_log = []; resolved_merged = 0; resolved_separate = 0
    for idx, (ratio, r1, r2, c1, c2) in enumerate(candidates):
        # Get context: who attended each institution?
        ctx1 = db.execute("""
            SELECT e.name FROM fact f JOIN entity e ON e.id = f.entity_id
            JOIN entity obj ON obj.id = f.object
            WHERE f.predicate = 'educated_at' AND obj.name = ? LIMIT 3
        """, [r1]).fetchall()
        ctx2 = db.execute("""
            SELECT e.name FROM fact f JOIN entity e ON e.id = f.entity_id
            JOIN entity obj ON obj.id = f.object
            WHERE f.predicate = 'educated_at' AND obj.name = ? LIMIT 3
        """, [r2]).fetchall()
        
        e1 = ', '.join(r[0] for r in ctx1) or '(no data)'
        e2 = ', '.join(r[0] for r in ctx2) or '(no data)'
        
        prompt = f"""Same institution?
A: "{r1}" (attended by: {e1})
B: "{r2}" (attended by: {e2})

SAME or DIFFERENT? One word, then reason:"""
        
        resp = call_llm(prompt, max_tokens=80)
        if not resp: continue
        
        lines = resp.strip().split('\n')
        verdict = lines[0].strip().upper()
        reason = lines[1].strip() if len(lines) > 1 else ''
        
        log_entry = {
            'raw_a': r1, 'raw_b': r2,
            'similarity': round(ratio, 3),
            'verdict': verdict,
            'reason': reason,
            'context_a': e1, 'context_b': e2,
        }
        
        if verdict == 'SAME':
            # Find ultimate canonical (c1 may have been merged into something else)
            while c1 not in canonicals:
                c1 = clusters.get(c1, c1)
            while c2 not in canonicals:
                c2 = clusters.get(c2, c2)
            if c1 == c2: continue  # Already merged
            
            for r in list(canonicals.get(c2, [c2])):
                clusters[r] = c1
                if r not in canonicals.get(c1, []): canonicals[c1].append(r)
            if c2 in canonicals: del canonicals[c2]
            if c1 in raw_by_cluster and c2 in raw_by_cluster:
                raw_by_cluster[c1].extend(raw_by_cluster.pop(c2, []))
            log_entry['merged_into'] = c1
            resolved_merged += 1
        else:
            resolved_separate += 1
        
        llm_log.append(log_entry)
        
        if (idx + 1) % 20 == 0:
            print(f"    progress: {idx+1}/{len(candidates)} | m={resolved_merged} s={resolved_separate}")
    
    print(f"    LLM decisions: {resolved_merged} merged, {resolved_separate} kept separate")
    return clusters, llm_log


def apply_merges(db, clusters):
    """Update fact.object to canonical entity ID, verifying evidence supports the merge."""
    name_to_canonical = clusters
    id_map = {}
    
    for old_name, canonical_name in name_to_canonical.items():
        old_eid = db.execute("SELECT id FROM entity WHERE name=?", [old_name]).fetchone()
        canon_eid = db.execute("SELECT id FROM entity WHERE name=?", [canonical_name]).fetchone()
        if old_eid and canon_eid and old_eid[0] != canon_eid[0]:
            id_map[old_eid[0]] = canon_eid[0]
    
    updates = 0
    for old_eid, canon_eid in id_map.items():
        # SAFETY CHECK: for each fact pointing to old_eid, verify the evidence
        # actually supports the canonical institution before merging
        bogus = db.execute("""
            SELECT COUNT(*) FROM fact f JOIN provenance p ON p.fact_id = f.id
            WHERE f.predicate = 'educated_at' AND f.object = ?
            AND LENGTH(p.quote_text) > 10
            AND LOWER(p.quote_text) NOT LIKE '%' || LOWER((SELECT name FROM entity WHERE id = ?)) || '%'
        """, [old_eid, canon_eid]).fetchone()[0]
        
        if bogus > 0:
            print(f"  SKIP: {old_eid} → {canon_eid} ({bogus} facts have non-matching evidence)")
            continue
        
        n = db.execute("UPDATE fact SET object=? WHERE object=? AND predicate='educated_at'",
                       [canon_eid, old_eid]).rowcount
        if n:
            updates += n
            db.execute("DELETE FROM entity WHERE id=?", [old_eid])
    
    db.commit()
    return updates


def main():
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    db = sqlite3.connect(DB)
    
    institutions = get_institutions(db)
    print(f"{len(institutions)} unique institutions\n")
    
    # Load existing merge list if available
    dedup_path = os.path.join(MANIFEST_DIR, '_edu_dedup.json')
    if os.path.exists(dedup_path):
        with open(dedup_path) as f:
            existing = json.load(f)
        # Apply existing merges
        for canonical, raws in existing.get('clusters', {}).items():
            for raw in raws:
                if raw != canonical:
                    old = db.execute("SELECT id FROM entity WHERE name=?", [raw]).fetchone()
                    new = db.execute("SELECT id FROM entity WHERE name=?", [canonical]).fetchone()
                    if old and new:
                        db.execute("UPDATE fact SET object=? WHERE object=? AND predicate='educated_at'",
                                   [new[0], old[0]])
                        db.execute("DELETE FROM entity WHERE id=?", [old[0]])
        db.commit()
        print(f"  Applied {len(existing['clusters'])} existing merges from {dedup_path}\n")
    
    # Re-load after applying existing merges
    institutions = get_institutions(db)
    clusters, llm_log = dedup_edu(db, institutions)
    
    canonicals = set(clusters.values())
    print(f"  Final: {len(set(clusters.keys()))} raw → {len(canonicals)} canonical\n")
    
    # Save merge list
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
        'clusters': {c: [r for r, cs in clusters.items() if cs == c]
                     for c in sorted(canonicals)},
    }
    
    with open(dedup_path, 'w') as f:
        json.dump(dedup_summary, f, indent=2, ensure_ascii=False)
    print(f"  Saved merge list to {dedup_path}")
    
    # Apply to DB
    updates = apply_merges(db, clusters)
    print(f"  Updated {updates} fact references")
    
    db.close()


if __name__ == '__main__':
    main()
