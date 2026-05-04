"""
rematch_parallel.py — 4-thread parallel source extraction for all unconfirmed facts.
Each worker independently queries facts and rematches them.
Skip facts already confirmed with phrase_index > 0.
"""
import sqlite3, json, os, re, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from extract_sources import sentence_offsets, SOURCES_DIR
from populate_provenance import slugify, read_source

API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
API_URL = 'https://api.deepseek.com/v1/chat/completions'
DB = 'euro_sdt.db'
WORKERS = 4

CONTEXT = {
    'served_on_commission': 'This person served as a commissioner on this Commission.',
    'held_portfolio': 'This person held this portfolio as a European Commissioner.',
    'from_country': 'This person is from this country.',
    'nominated_by': 'This person was nominated by this country.',
    'educated_at': 'This person studied at this educational institution.',
    'studied_field': 'This person has a degree in this academic field.',
    'held_degree': 'This person holds this degree.',
    'member_of': 'This person is a member of this organisation.',
    'post_mandate_occupation': 'This person took up this occupation after their commissioner role.',
    'held_position': 'This person held this position.',
}

def call_llm(prompt):
    if not API_KEY: return None
    payload = json.dumps({'model':'deepseek-chat','messages':[{'role':'user','content':prompt}],'max_tokens':20,'temperature':0.0}).encode()
    req = urllib.request.Request(API_URL, data=payload, headers={'Authorization':f'Bearer {API_KEY}','Content-Type':'application/json','User-Agent':'euro-sdt/1.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=45)
        return json.loads(resp.read())['choices'][0]['message']['content'].strip()
    except: return None

def find_phrase(text, phrases, person_name, predicate, obj):
    """Ask LLM to pick the numbered phrase that supports the claim."""
    numbered = '\n'.join(f"[{i}] {phrases[i][2]}" for i in range(min(len(phrases), 80)) if len(phrases[i][2]) > 5)
    prompt = f"""CLAIM: {person_name} — {predicate}: {obj}
MEANING: {CONTEXT.get(predicate,'')}

NUMBERED SENTENCES:
{numbered}

Which number BEST supports the claim? Reply with just the number, or NOT FOUND.
NUMBER:"""
    resp = call_llm(prompt)
    if not resp: return None
    m = re.search(r'(\d+)', resp)
    if m and int(m.group(1)) < len(phrases):
        return int(m.group(1)), phrases[int(m.group(1))][2]
    return None

def get_source(person_name, predicate, obj, cit_id, db_conn):
    """Find the source document for a fact."""
    subdir = 'wikipedia'
    if cit_id == 'cit-dg-cvs': subdir = 'dg_cvs'
    elif cit_id == 'cit-vdl2-declarations': subdir = 'declarations'
    elif cit_id == 'cit-revolving-door': subdir = 'revolving_door'

    person_safe = slugify(person_name)
    text, phrases = read_source(subdir, person_safe)

    # Commission service facts: search the Wikipedia commission page
    if not text and predicate in ('served_on_commission','held_portfolio','from_country','nominated_by'):
        comm_id = obj if predicate == 'served_on_commission' else None
        if not comm_id and db_conn:
            r = db_conn.execute("SELECT object FROM fact WHERE entity_id=(SELECT id FROM entity WHERE name=?) AND predicate='served_on_commission'", (person_name,)).fetchone()
            comm_id = r[0] if r else None
        if comm_id:
            text, phrases = read_source('wikipedia', comm_id)

    return text, phrases

def process_fact(row):
    """Process one fact: find source, ask LLM, update DB."""
    prov_id, fact_id, cit_id, name, predicate, obj, qualifier = row
    
    # Skip if already confirmed with a good phrase-index
    local = sqlite3.connect(DB)
    check = local.execute(
        "SELECT p.phrase_index, f.confidence FROM provenance p JOIN fact f ON p.fact_id=f.id WHERE p.id=?",
        (prov_id,)).fetchone()
    if check and check[0] > 0 and check[1] == 'confirmed':
        local.close()
        return None  # already done
    
    text, phrases = get_source(name, predicate, obj, cit_id, local)
    
    if not text or not phrases:
        local.close()
        return None
    
    result = find_phrase(text, phrases, name, predicate, obj)
    
    if result:
        idx, sent = result
        local.execute("UPDATE provenance SET quote_text=?, phrase_index=?, context_text=? WHERE id=?",
                      (sent, idx, text[:500], prov_id))
        local.execute("UPDATE fact SET confidence='confirmed', updated_at=date('now') WHERE id=?", (fact_id,))
        local.commit()
        local.close()
        return True
    
    local.close()
    return None

def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    
    # Get all unconfirmed facts
    facts = db.execute("""
        SELECT p.id, p.fact_id, p.citation_id, e.name as entity_name,
               f.predicate, f.object, f.qualifier
        FROM provenance p JOIN fact f ON p.fact_id = f.id JOIN entity e ON e.id = f.entity_id
        WHERE (f.confidence != 'confirmed' OR p.phrase_index = 0)
          AND f.predicate NOT IN ('classified_as','funding_notes','has_description','started_on')
        ORDER BY f.confidence, p.phrase_index
    """).fetchall()
    db.close()
    
    total = len(facts)
    print(f"Processing {total} facts with {WORKERS} workers...")
    
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(process_fact, tuple(r)) for r in facts]
        for future in futures:
            result = future.result()
            done += 1
            if result:
                if done % 50 == 0 or done == 1:
                    # Quick status
                    db2 = sqlite3.connect(DB)
                    pi = db2.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index>0").fetchone()[0]
                    c  = db2.execute("SELECT COUNT(*) FROM fact WHERE confidence='confirmed'").fetchone()[0]
                    db2.close()
                    print(f'  [{done}/{total}] rematched — {pi} phrase quotes, {c} confirmed')
    
    # Final count
    db2 = sqlite3.connect(DB)
    pi = db2.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index>0").fetchone()[0]
    c  = db2.execute("SELECT COUNT(*) FROM fact WHERE confidence='confirmed'").fetchone()[0]
    t  = db2.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
    db2.close()
    print(f'\nDone. {pi}/{t} phrase quotes ({pi/t*100:.0f}%), {c} confirmed.')

if __name__ == '__main__':
    main()
