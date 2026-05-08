"""
rematch.py — AI-powered re-matching for unsupported provenance records.

For facts where DeepSeek V4 flagged the citation as UNSUPPORTED,
re-reads the source document and asks the LLM to find the correct
supporting sentence, then updates the provenance with the new phrase.

Usage:
    export DEEPSEEK_API_KEY="your-key"
    python rematch.py
"""
import sqlite3
import json
import os
import re
import time
import urllib.request
import urllib.parse
from extract_sources import sentence_offsets, SOURCES_DIR
from populate_provenance import slugify, read_source

DB_PATH = 'euro_sdt.db'
API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
API_URL = 'https://api.deepseek.com/v1/chat/completions'
VERIFICATION_REPORT = 'verification_report.csv'

PREDICATE_CONTEXT = {
    'served_on_commission':     'This person served as a commissioner on this Commission.',
    'held_portfolio':           'This person held this portfolio as a European Commissioner.',
    'from_country':             'This person is from this country.',
    'nominated_by':             'This person was nominated by this country.',
    'educated_at':              'This person studied at or attended this educational institution.',
    'studied_field':            'This person has a degree or studied in this academic field.',
    'held_degree':              'This person holds this degree.',
    'member_of':                'This person is a member of this organisation.',
    'post_mandate_occupation':  'This person took up this occupation after their commissioner role.',
    'held_position':            'This person held this position.',
}


def call_deepseek(prompt, max_tokens=300, timeout=60):
    if not API_KEY:
        return None
    payload = json.dumps({
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.0,
    }).encode()
    req = urllib.request.Request(API_URL, data=payload, headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'User-Agent': 'euro-sdt-rematcher/1.0'
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f'ERROR: {e}'


def find_supporting_sentence(text, phrases, person_name, predicate, obj, qualifier):
    """Present numbered phrases to DeepSeek and ask which number supports the claim."""
    context = PREDICATE_CONTEXT.get(predicate, '')
    
    # Build numbered phrase list (limit to 50 phrases to fit in context window)
    phrase_list = []
    max_phrases = min(len(phrases), 80)
    for i in range(max_phrases):
        sent = phrases[i][2]
        if len(sent) > 5:  # skip empty/trivial phrases
            phrase_list.append(f"[{i}] {sent}")
    
    numbered_text = '\n'.join(phrase_list) if phrase_list else text[:3000]
    
    prompt = f"""You are a fact-checker. Below are numbered sentences from a source document.

CLAIM: {person_name} — {predicate}: {obj}
MEANING: {context}

NUMBERED SENTENCES:
{numbered_text}

TASK: Which sentence number BEST supports or confirms the claim?
Reply with just the number (e.g., "5") or NOT FOUND if none does.
If multiple sentences support it, pick the best one.

NUMBER: """
    
    response = call_deepseek(prompt, max_tokens=20)
    if not response or 'ERROR' in str(response):
        return None
    
    # Parse the number
    m = re.search(r'(\d+)', response)
    if m:
        idx = int(m.group(1))
        if idx < len(phrases):
            return idx, phrases[idx][2]
    
    if 'NOT FOUND' in response:
        return None
    
    return None


def rematch_unsupported(db):
    """For each unsupported OR batch-cited fact, find the correct sentence in the source."""
    if not API_KEY:
        print("No API key. Set DEEPSEEK_API_KEY.")
        return
    
    # Get both disputed AND batch-cited facts
    all_to_fix = db.execute("""
        SELECT p.id as prov_id, p.fact_id, p.citation_id, f.entity_id, f.predicate,
               f.object, f.object_type, f.qualifier, f.confidence, p.phrase_index,
               e.name as entity_name,
               COALESCE((SELECT name FROM entity WHERE id = f.object), f.object) as obj_display
        FROM provenance p
        JOIN fact f ON p.fact_id = f.id
        JOIN entity e ON e.id = f.entity_id
        WHERE (f.confidence = 'disputed' OR p.phrase_index = 0)
          AND f.predicate NOT IN ('classified_as', 'funding_notes', 'has_description',
                                   'started_on', 'has_sector')
        ORDER BY p.phrase_index DESC, f.predicate, e.name
    """).fetchall()
    
    total = len(all_to_fix)
    print(f"Total facts to extract source quotes for: {total}\n")
    print(f"  disputed: {sum(1 for r in all_to_fix if r['confidence']=='disputed')}")
    print(f"  batch (phrase_index=0): {sum(1 for r in all_to_fix if r['phrase_index']==0)}")
    print()
    
    updated = 0
    for i, row in enumerate(all_to_fix):
        prov_id, fact_id, cit_id, entity_id, predicate, obj, obj_type, qualifier, confidence, phrase_index, entity_name, obj_display = row
        
        # Find source document
        # The provenance id pattern tells us the source type
        subdir = 'wikipedia'  # default
        if cit_id == 'cit-dg-cvs':
            subdir = 'dg_cvs'
        elif cit_id == 'cit-vdl2-declarations':
            subdir = 'declarations'
        elif cit_id == 'cit-revolving-door':
            subdir = 'revolving_door'
        elif cit_id == 'cit-vdl2-wikipedia' or cit_id == 'cit-commission-cvs-wikidata':
            subdir = 'wikipedia'
        
        # Try different source lookup strategies
        person_safe = slugify(entity_name)
        text, phrases = read_source(subdir, person_safe)
        
        if not text and predicate in ('served_on_commission', 'held_portfolio', 'from_country', 'nominated_by'):
            # Commission facts: search in the commission page, not the person page
            comm_id = obj if predicate == 'served_on_commission' else None
            if not comm_id:
                comm = db.execute("SELECT object FROM fact WHERE entity_id=? AND predicate='served_on_commission'", (entity_id,)).fetchone()
                comm_id = comm[0] if comm else None
            if comm_id:
                text, phrases = read_source('wikipedia', comm_id)
        
        if not text:
            continue
        
        # Ask LLM to find the supporting sentence number
        result = find_supporting_sentence(text, phrases, entity_name, predicate, obj_display, qualifier or '')
        
        if result:
            phrase_idx, sentence = result
            
            # Update provenance with the LLM-confirmed match
            db.execute("""UPDATE provenance SET quote_text = ?, phrase_index = ?, context_text = ?
                WHERE id = ?""", (sentence, phrase_idx, text[:500], prov_id))
            db.execute("UPDATE fact SET confidence = 'confirmed', updated_at = date('now') WHERE id = ?", (fact_id,))
            
            updated += 1
            if updated % 10 == 0 or updated == 1:
                print(f'  [{updated}/{total}] rematched — {entity_name} → {predicate}: {obj_display} (phrase {phrase_idx})')
        else:
            if 'NOT FOUND' in str(result or ''):
                pass  # genuinely not in the source
        
        time.sleep(0.6)
    
    db.commit()
    print(f'\nRematched {updated}/{total} facts. Confidence restored to confirmed.')


def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    rematch_unsupported(db)
    db.close()


if __name__ == '__main__':
    main()
