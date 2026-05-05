"""
extract_orgs.py — Phrase-level extraction of ALL organisation memberships from
commissioner Wikipedia biographies.

Discipline:
  1. Read source text, split into numbered phrases (sentence_offsets)
  2. Send numbered phrases to LLM — it returns {phrase_offset, organisation, role, reasoning}
  3. Save results to manifests/ directory as structured JSON per commissioner
  4. Deduplicate org names using string distance (difflib)
  5. Create affiliated_with facts + provenance in euro_sdt.db

Usage:
    .venv/bin/python extract_orgs.py [--dry-run] [--limit N]
"""
import sqlite3, json, os, re, sys, urllib.request, urllib.parse, glob, time, difflib
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
API_URL = 'https://api.deepseek.com/v1/chat/completions'
DB = 'euro_sdt.db'
WORKERS = 4
MANIFEST_DIR = 'manifests'
WIKI_DIR = 'sources/wikipedia'

BLACKLIST_PATTERNS = [
    r'\beuropean\s+commission\b', r'\beuropean\s+parliament\b',
    r'\bcouncil\s+of\s+the\s+european\s+union\b', r'\beuropean\s+union\b',
    r'\bunited\s+nations\b', r'\beuropean\s+council\b',
    r'\beuropean\s+cen?tral\s+bank\b',
    r'\bcjue\b', r'\bcourt\s+of\s+justice\b',
    r'\bnato\b(?!\s*foundation|\s*trust|\s*parliamentary)',  # org name, not alliance itself
    r'\bwto\b', r'\bimf\b', r'\bworld\s+bank\b', r'\bwho\b',
    r'\boecd\b', r'\bthe\s+commission\b',
    r'\bcommission\s+of\s+the\s+european\s+communities\b',
    r'\bhigh\s+authority\b.*\becsc\b',
    r'\bcouncil\s+of\s+ministers\b',
    r'\beuropean\s+community\b',
    r'\bec\b.*\bcommission\b',
    r'\beuropean\s+economic\s+community\b',
]

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower().strip()).strip('-')


def call_llm(prompt, max_tokens=3000):
    if not API_KEY: return None
    payload = json.dumps({
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.0,
    }).encode()
    req = urllib.request.Request(API_URL, data=payload, headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'User-Agent': 'euro-sdt/1.0',
    })
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            body = json.loads(resp.read())
            return body['choices'][0]['message']['content'].strip()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
            else:
                return None


def split_phrases(text):
    """Split text into numbered phrases (sentences)."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    phrases = []
    for i, s in enumerate(sentences):
        s = s.strip()
        if len(s) > 15:  # skip very short fragments
            phrases.append((i, s))
    return phrases


def extract_orgs_phrase(text, person_name):
    """Send numbered phrases to LLM, get phrase-level org extractions back."""
    phrases = split_phrases(text)

    # Truncate to reasonable length (keep first ~60 + last ~20 phrases)
    if len(phrases) > 80:
        phrases = phrases[:60] + phrases[-20:]

    # Build numbered phrase block
    numbered = '\n'.join(f"[{pi}] {pt}" for pi, pt in phrases)

    prompt = f"""Extract EVERY organisation that {person_name} has been a member of, served on the board of, held a position at, been affiliated with, or been a fellow of, from the numbered phrases below.

RULES:
- INCLUDE: think tanks, policy institutes, foundations, commissions, councils, networks, forums, advocacy groups, lobby groups, research institutes, professional associations, academic societies, international bodies, political foundations, NGOs.
- EXCLUDE: government ministries/departments, universities/schools, EU institutions (European Commission, Parliament, Council, CJEU, ECB), companies/businesses, political parties (the party itself), UN agencies, WTO, IMF, World Bank, OECD, NATO (the alliance itself).

For each organisation found, output:
- "phrase": the phrase number [N] where the evidence appears
- "organisation": the organisation's name exactly as written
- "role": brief relationship (member, board member, fellow, founder, chair, etc.)
- "reasoning": one sentence explaining WHY this phrase indicates membership

NUMBERED PHRASES:
{numbered}

Respond as a JSON array: [{{"phrase":N, "organisation":"...", "role":"...", "reasoning":"..."}}]
If no organisations found, respond: []
Respond ONLY with the JSON array:"""

    resp = call_llm(prompt, max_tokens=3000)
    if not resp: return []

    # Parse JSON
    json_str = resp.strip()
    if json_str.startswith('```'):
        json_str = re.sub(r'^```\w*\n', '', json_str)
        json_str = re.sub(r'\n```$', '', json_str)

    try:
        results = json.loads(json_str)
        if isinstance(results, list):
            valid = []
            for item in results:
                if not isinstance(item, dict):
                    continue
                if 'organisation' not in item or 'phrase' not in item:
                    continue
                # Validate phrase number exists
                try:
                    item['phrase'] = int(item['phrase'])
                except (ValueError, TypeError):
                    continue
                valid.append(item)
            return valid
        return []
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', json_str, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return []


def is_blacklisted(org_name):
    """Check if an org name matches blacklist patterns."""
    name_lower = org_name.lower().strip()
    for pat in BLACKLIST_PATTERNS:
        if re.search(pat, name_lower):
            return True
    return False


def process_commissioner(slug, name):
    """Extract orgs from one commissioner's Wikipedia bio into a manifest."""
    wiki_path = os.path.join(WIKI_DIR, f'{slug}.txt')
    if not os.path.exists(wiki_path):
        return {'status': 'skip', 'reason': 'no Wikipedia text', 'slug': slug, 'name': name}

    try:
        with open(wiki_path) as f:
            text = f.read()
    except Exception as e:
        return {'status': 'error', 'reason': str(e), 'slug': slug, 'name': name}

    if len(text.strip()) < 200:
        return {'status': 'skip', 'reason': 'text too short', 'slug': slug, 'name': name}

    results = extract_orgs_phrase(text, name)

    # Build phrase lookup for evidence text
    phrases = split_phrases(text)
    phrase_map = {pi: pt for pi, pt in phrases}

    orgs = []
    for r in results:
        org_name = r.get('organisation', '').strip()
        if not org_name or is_blacklisted(org_name):
            continue

        phrase_idx = r.get('phrase', -1)
        evidence = phrase_map.get(phrase_idx, '')

        if len(org_name) < 3:
            continue
        if org_name.lower() in ('education', 'early life', 'career', 'personal life',
                                 'references', 'further reading', 'external links',
                                 'european council', 'european committee', 'first pillar'):
            continue

        orgs.append({
            'organisation': org_name,
            'role': r.get('role', ''),
            'reasoning': r.get('reasoning', ''),
            'phrase': phrase_idx,
            'evidence': evidence,
        })

    return {
        'status': 'ok',
        'slug': slug,
        'name': name,
        'orgs': orgs,
        'count': len(orgs),
    }


def deduplicate_orgs(all_manifests, threshold=0.85):
    """Deduplicate organisation names across all manifests using string similarity."""
    # Collect all unique org names with their occurrences
    org_occurrences = defaultdict(list)  # canonical name → list of (manifest, raw_name)
    raw_names = set()

    for manifest in all_manifests:
        if manifest['status'] != 'ok':
            continue
        for org in manifest.get('orgs', []):
            raw = org['organisation']
            raw_names.add(raw)
            org_occurrences[raw].append((manifest['slug'], org))

    if not raw_names:
        return {}

    # Cluster similar names using greedy matching
    raw_list = sorted(raw_names)
    clusters = {}  # raw → canonical
    canonicals = {}  # canonical → list of raw

    for raw in raw_list:
        raw_lower = raw.lower().strip()
        matched = False
        for canonical in list(canonicals.keys()):
            # Compare
            ratio = difflib.SequenceMatcher(None, raw_lower, canonical.lower()).ratio()
            if ratio >= threshold:
                clusters[raw] = canonical
                canonicals[canonical].append(raw)
                matched = True
                break
        if not matched:
            clusters[raw] = raw
            canonicals[raw] = [raw]

    return clusters


def insert_facts(manifests, org_clusters, dry_run=False):
    """Insert deduplicated org facts into DB with provenance."""
    if dry_run:
        total = 0
        for m in manifests:
            if m['status'] == 'ok':
                total += m.get('count', 0)
        print(f"  DRY RUN: would insert {total} facts")
        return

    db = sqlite3.connect(DB)
    db.execute("PRAGMA journal_mode=WAL")

    total_inserted = 0

    for manifest in manifests:
        if manifest['status'] != 'ok':
            continue

        slug = manifest['slug']
        name = manifest['name']

        # Ensure citation exists
        citation_id = f'cit-wiki-{slug}'
        db.execute("""INSERT OR IGNORE INTO citation (id, source_name, source_type, url, access_date, description)
                      VALUES (?, ?, 'wikipedia', ?, '2026-05-05', ?)""",
                   [citation_id,
                    f'Wikipedia article: {name}',
                    f'https://en.wikipedia.org/wiki/{name.replace(" ", "_")}',
                    f'Commissioner biography for {name}'])

        for org in manifest.get('orgs', []):
            raw_name = org['organisation']
            # Use canonical name from dedup
            canonical_name = org_clusters.get(raw_name, raw_name)
            role = org.get('role', '')
            phrase_idx = org.get('phrase', -1)
            evidence = org.get('evidence', '')

            if not canonical_name:
                continue

            org_slug = slugify(canonical_name)
            if not org_slug or len(org_slug) < 2:
                continue

            # Create org entity
            db.execute("INSERT OR IGNORE INTO entity (id, name, category) VALUES (?, ?, 'organisation')",
                       [org_slug, canonical_name])

            # Create fact
            fact_id = slugify(f"{slug}-affiliated_with-{org_slug}")[:64]
            qualifier = role if role else None

            exists = db.execute("SELECT id FROM fact WHERE id=?", [fact_id]).fetchone()
            if exists:
                if qualifier:
                    db.execute("UPDATE fact SET qualifier=? WHERE id=?", [qualifier, fact_id])
                continue

            db.execute("""INSERT INTO fact (id, entity_id, predicate, object, object_type, qualifier, confidence)
                          VALUES (?, ?, 'affiliated_with', ?, 'entity', ?, 'confirmed')""",
                       [fact_id, slug, org_slug, qualifier])

            # Create provenance
            prov_id = slugify(f"prov-{fact_id}")[:64]
            db.execute("""INSERT OR IGNORE INTO provenance (id, fact_id, citation_id, quote_text, phrase_index)
                          VALUES (?, ?, ?, ?, ?)""",
                       [prov_id, fact_id, citation_id, evidence[:500], phrase_idx])

            total_inserted += 1

    db.commit()
    db.close()
    return total_inserted


def main():
    dry_run = '--dry-run' in sys.argv
    limit = None

    for i, arg in enumerate(sys.argv):
        if arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    if not API_KEY:
        print("ERROR: DEEPSEEK_API_KEY not set")
        sys.exit(1)

    os.makedirs(MANIFEST_DIR, exist_ok=True)

    # Get commissioners
    db = sqlite3.connect(DB)
    commissioners = list(db.execute(
        "SELECT id, name FROM entity WHERE category='commissioner' ORDER BY name"
    ))
    db.close()

    # Filter out non-person slugs
    skip = {'barroso-commission', 'european-commission', 'president-of-the-european-commission'}
    commissioners = [(s, n) for s, n in commissioners if s not in skip]

    if limit:
        commissioners = commissioners[:limit]

    print(f"Extracting org memberships for {len(commissioners)} commissioners ({WORKERS} workers)...\n")

    # Phase 1: LLM extraction → manifests
    manifests = []
    processed = 0
    total_orgs = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(process_commissioner, slug, name): name for slug, name in commissioners}

        for fut in as_completed(futures):
            name = futures[fut]
            try:
                manifest = fut.result()
                manifests.append(manifest)

                if manifest['status'] == 'ok':
                    processed += 1
                    total_orgs += manifest['count']
                    org_names = [o['organisation'] for o in manifest['orgs']]
                    print(f"  {name}: {manifest['count']} orgs — {', '.join(org_names[:3])}"
                          + (f', ...' if len(org_names) > 3 else ''))
                else:
                    print(f"  SKIP: {name} — {manifest['reason']}")

                # Save individual manifest
                mpath = os.path.join(MANIFEST_DIR, f"{manifest['slug']}.json")
                with open(mpath, 'w') as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)

            except Exception as e:
                print(f"  ERROR: {name} — {e}")

    # Phase 2: Deduplication
    print(f"\nDeduplicating {total_orgs} raw org names...")
    org_clusters = deduplicate_orgs(manifests, threshold=0.85)
    canonicals = set(org_clusters.values())
    print(f"  {len(set(org_clusters.keys()))} raw → {len(canonicals)} canonical names")

    # Save dedup manifest
    dedup_summary = {
        'raw_count': len(set(org_clusters.keys())),
        'canonical_count': len(canonicals),
        'clusters': {},
    }
    for canonical in sorted(canonicals):
        raws = [r for r, c in org_clusters.items() if c == canonical]
        dedup_summary['clusters'][canonical] = raws

    with open(os.path.join(MANIFEST_DIR, '_dedup.json'), 'w') as f:
        json.dump(dedup_summary, f, indent=2, ensure_ascii=False)

    # Save full manifest index
    with open(os.path.join(MANIFEST_DIR, '_index.json'), 'w') as f:
        json.dump({
            'total_commissioners': len(commissioners),
            'processed': processed,
            'total_org_facts': total_orgs,
            'unique_orgs': len(canonicals),
            'manifests': [{'slug': m['slug'], 'name': m['name'], 'status': m['status'], 'count': m.get('count', 0)}
                         for m in manifests],
        }, f, indent=2)

    # Phase 3: Insert into DB
    print(f"\nInserting facts into DB...")
    inserted = insert_facts(manifests, org_clusters, dry_run=dry_run)
    if not dry_run:
        print(f"  {inserted} facts inserted")

    print(f"\nDone. Manifests in {MANIFEST_DIR}/")
    print(f"  {processed}/{len(commissioners)} processed, {total_orgs} org facts, {len(canonicals)} unique orgs")


if __name__ == '__main__':
    main()
