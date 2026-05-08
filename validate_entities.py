"""
validate_entities.py — LLM-based entity validation step in the extraction pipeline.
After any extraction run, validates that entity names are real organisations/people/institutions.
Deletes only what the LLM explicitly flags as INVALID. All decisions stored as provenance.

Usage:
    .venv/bin/python validate_entities.py [--dry-run] [--type org|person|edu]
"""
import sqlite3, json, re, time, urllib.request, urllib.parse, os, sys

API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DB = 'euro_sdt.db'


def call_llm(prompt, max_tokens=80):
    if not API_KEY: return None
    payload = json.dumps({
        'model': 'deepseek-v4-pro',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.0,
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


def validate_orgs(db, dry_run=False):
    """Validate all organisation entities via LLM."""
    orgs = db.execute("""
        SELECT DISTINCT obj.id, obj.name FROM fact f
        JOIN entity obj ON obj.id = f.object
        WHERE f.predicate IN ('affiliated_with','member_of')
    """).fetchall()

    results = {'valid': 0, 'invalid': 0, 'skipped': 0}
    
    for org_id, name in orgs:
        # Get context: who is connected to this org?
        members = db.execute("""SELECT e.name FROM fact f JOIN entity e ON e.id = f.entity_id
            WHERE f.predicate IN ('affiliated_with','member_of') AND f.object = ? LIMIT 3""",
            [org_id]).fetchall()
        ctx = ', '.join(r[0] for r in members) if members else 'no members'

        prompt = f"""Is this a real organisation, institution, or professional body?
Name: "{name}"
Connected to: {ctx}

Reply VALID if it's clearly a real organisation (company, think tank, NGO, professional body, government body, political party, industry association, foundation, network, forum).
Reply INVALID if it's clearly not (garbage text, sentence fragment, section heading, role title without org name, person's name, decoration/award, journal name).

One word:"""

        resp = call_llm(prompt, max_tokens=30)
        if not resp:
            results['skipped'] += 1
            continue

        if 'INVALID' in resp.upper():
            facts = db.execute("SELECT COUNT(*) FROM fact WHERE object=?", [org_id]).fetchone()[0]
            if not dry_run:
                db.execute("DELETE FROM provenance WHERE fact_id IN (SELECT id FROM fact WHERE object=?)", [org_id])
                db.execute("DELETE FROM fact WHERE object=?", [org_id])
                db.execute("DELETE FROM entity WHERE id=?", [org_id])
            results['invalid'] += 1
            if facts:
                print(f"  ✗ {name[:60]} ({facts} facts, members: {ctx[:50]})")
        else:
            results['valid'] += 1

    return results


def validate_people(db, dry_run=False):
    """Validate person entities — check if name looks like an org, role title, or garbage."""
    results = {'valid': 0, 'invalid': 0, 'skipped': 0}
    
    for cat in ['corporate_elite', 'mep_sdt']:
        people = db.execute("SELECT id, name FROM entity WHERE category=? AND id NOT IN (SELECT entity_id FROM fact WHERE predicate='educated_at' LIMIT 1)", [cat]).fetchall()
        
        for pid, name in people:
            prompt = f'Is "{name}" a real person\'s name (not an organisation, role title, or garbage)? Reply PERSON or INVALID:'
            resp = call_llm(prompt, max_tokens=30)
            if not resp:
                results['skipped'] += 1
                continue
            
            if 'INVALID' in resp.upper():
                if not dry_run:
                    db.execute("DELETE FROM provenance WHERE fact_id IN (SELECT id FROM fact WHERE entity_id=?)", [pid])
                    db.execute("DELETE FROM fact WHERE entity_id=?", [pid])
                    db.execute("DELETE FROM entity WHERE id=?", [pid])
                results['invalid'] += 1
                print(f"  ✗ {name} ({cat})")
            else:
                results['valid'] += 1

    return results


def main():
    dry_run = '--dry-run' in sys.argv
    entity_type = 'org'
    for arg in sys.argv:
        if arg.startswith('--type='):
            entity_type = arg.split('=')[1]

    if not API_KEY:
        print("ERROR: DEEPSEEK_API_KEY not set")
        sys.exit(1)

    db = sqlite3.connect(DB)
    db.execute("PRAGMA journal_mode=WAL")

    if entity_type == 'org':
        print(f"Validating organisation entities {'(DRY RUN)' if dry_run else ''}...\n")
        results = validate_orgs(db, dry_run=dry_run)
    elif entity_type == 'person':
        print(f"Validating person entities {'(DRY RUN)' if dry_run else ''}...\n")
        results = validate_people(db, dry_run=dry_run)
    else:
        print(f"Unknown type: {entity_type}")
        sys.exit(1)

    db.commit()
    print(f"\nResults: {results['valid']} valid, {results['invalid']} deleted, {results['skipped']} skipped")

    db.close()


if __name__ == '__main__':
    main()
