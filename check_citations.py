"""
check_citations.py — LLM-powered cross-checker for paper citations.

Reads a LaTeX file, extracts all \footnote{} and \cite{} commands,
finds the corresponding PDF or text file in papers/, extracts text,
and uses DeepSeek to evaluate whether the claim is substantiated.

Usage:
    .venv/bin/python check_citations.py assets/papers/methodology/paper.tex

Produces verification_report.csv with columns:
    paper_section, claim, citation, pdf_file, evidence_found, confidence
"""
import re, os, sys, csv, json, urllib.request, urllib.parse, hashlib

API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
PDF_DIR = 'papers'


def extract_text(path):
    """Extract text from PDF or text file."""
    if path.endswith('.txt'):
        with open(path) as f:
            content = f.read()
        # Check if it's HTML (Internet Archive often serves .txt as HTML)
        if content[:500].strip().startswith('<!DOCTYPE') or content[:500].strip().startswith('<html'):
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
        # Skip Internet Archive boilerplate by finding actual text start
        markers = ['THE POWER ELITE', 'The Higher Circles', 'Chapter 1', 'CHAPTER 1',
                   'Introduction', 'INTRODUCTION']
        for marker in markers:
            idx = content.find(marker)
            if idx > 1000:  # Only skip if marker is well past the header
                content = content[idx:]
                break
        return content  # full text — DeepSeek V4 handles 1M tokens

    result = None

    # Try pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        result = ' '.join(p.extract_text() or '' for p in reader.pages[:50])
        if result.strip():
            return result[:100000]
    except:
        pass

    # Try pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            result = ' '.join(p.extract_text() or '' for p in pdf.pages[:50])
            if result.strip():
                return result[:100000]
    except:
        pass

    # Try pdftotext
    try:
        import subprocess
        r = subprocess.run(['pdftotext', '-l', '50', path, '-'],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout[:100000]
    except:
        pass

    # Fallback: try .txt version of same file
    txt_path = path.replace('.pdf', '.txt')
    if os.path.exists(txt_path):
        with open(txt_path) as f:
            return f.read()[:8000]

    return None


def call_llm(prompt, max_tokens=200):
    """Call DeepSeek API."""
    if not API_KEY:
        return None
    payload = json.dumps({
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.0,
    }).encode()
    req = urllib.request.Request(
        'https://api.deepseek.com/v1/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json',
        })
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        return json.loads(resp.read())['choices'][0]['message']['content'].strip()
    except:
        return None


def find_citations(tex_path):
    """Extract all \footnote{...} and \cite{...} from a LaTeX file."""
    with open(tex_path) as f:
        text = f.read()

    citations = []

    # Find \footnote{...} and \cite{...} — handle nested braces
    for pattern in [r'\\footnote\{', r'\\cite\{']:
        for m in re.finditer(pattern, text):
            pos = m.end()
            depth = 1
            end = pos
            while end < len(text) and depth > 0:
                if text[end] == '{':
                    depth += 1
                elif text[end] == '}':
                    depth -= 1
                end += 1
            content = text[pos:end-1] if depth == 0 else text[pos:]
            # Get the sentence containing this citation
            sentence_start = max(0, text.rfind('.', 0, m.start()))
            if sentence_start > 0:
                sentence_start += 2  # skip '. '
            claim = text[sentence_start:m.start()].strip()
            claim = re.sub(r'\\[a-z]+\{([^}]*)\}', r'\1', claim)
            claim = re.sub(r'\\[a-z]+', '', claim)
            claim = re.sub(r'\s+', ' ', claim).strip()
            citations.append({
                'type': 'cite',
                'content': content[:300],
                'claim': claim[:300],
            })

    return citations


def resolve_source(citation_content, tex_dir):
    """Find matching PDF or text file for a citation.
    Attempts to resolve from: 1) bibtex key, 2) refs.bib author/year, 3) heuristic matching."""
    clean = citation_content.strip()
    
    # If it's a bibtex key (plain text, no spaces), look it up in refs.bib
    bib_path = os.path.join(os.path.dirname(tex_dir), 'refs.bib') if tex_dir else 'refs.bib'
    # Also try same directory as tex file
    if not os.path.exists(bib_path):
        bib_path = os.path.join(tex_dir, 'refs.bib') if tex_dir else None
    
    if bib_path and os.path.exists(bib_path) and ' ' not in clean and len(clean) < 50:
        try:
            with open(bib_path) as f:
                bib_text = f.read()
            # Find the entry for this key
            pattern = r'@\w+\{' + re.escape(clean) + r',\s*(.*?)\n\}'
            match = re.search(pattern, bib_text, re.DOTALL)
            if match:
                entry = match.group(1)
                # Extract author and year from bibtex entry
                authors = re.findall(r'author\s*=\s*\{(.*?)\}', entry, re.DOTALL)
                years = re.findall(r'year\s*=\s*\{?(\d{4})\}?', entry)
                # Build search terms from author last names
                search_terms = []
                if authors:
                    names = authors[0].split(' and ')
                    for name in names[:2]:
                        parts = name.strip().split(',')
                        if len(parts) > 1:
                            search_terms.append(parts[0].strip().lower())
                        else:
                            words = name.strip().split()
                            if words:
                                search_terms.append(words[-1].strip().lower())
                if years:
                    search_terms.append(years[0])
                # Match against files
                return _match_file(search_terms)
        except:
            pass
    
    # Heuristic: parse author names and years from citation text
    clean_lower = re.sub(r'\\[a-z]+\{([^}]*)\}', r'\1', clean).lower()
    clean_lower = re.sub(r'["`]', '', clean_lower)
    
    authors = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', clean[:150])
    years = re.findall(r'(\d{4})', clean)
    search_terms = [a.lower() for a in authors[:2]] + years[:1]
    return _match_file(search_terms)


def _match_file(search_terms):
    """Score files in papers/ against search terms."""
    best_score = 0
    best_path = None
    for f in os.listdir(PDF_DIR):
        if not f.endswith(('.pdf', '.txt')) or f == 'BIBLIOGRAPHY.md':
            continue
        f_lower = f.lower()
        score = 0
        for term in search_terms:
            if term and term in f_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_path = os.path.join(PDF_DIR, f)
    if best_score >= max(1, len(search_terms) * 0.5):
        return best_path
    return None


def evaluate_with_llm(claim, source_text, source_name):
    """Use phrase-level LLM approach to evaluate whether the source substantiates the claim.
    
    Splits the source into numbered phrases, asks the LLM to identify the specific
    phrase that supports (or fails to support) the claim, with a reason.
    """
    if not API_KEY or not source_text:
        return False, "No source text or API key", 0.0, -1

    # Split source into numbered phrases (same as our extraction pipeline)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', source_text) if len(s.strip()) > 20]
    phrases = sentences[:500]  # DeepSeek V4 handles 1M tokens
    numbered = '\n'.join(f"[{i}] {phrases[i][:300]}" for i in range(len(phrases)))

    prompt = f"""Does this source document substantiate the following claim made in our paper?

CLAIM: {claim}

SOURCE: {source_name}
NUMBERED PHRASES:
{numbered}

If the source substantiates the claim, reply:
If the source substantiates the claim, rate your confidence on this scale:
1 = no content suggesting the claim
2 = some related information but insufficient for citation
3 = related but not strongly supported
4 = supported with some question of interpretation
5 = exact match of the cited content

Reply in this format:
VERIFIED | confidence=N | phrase=[N] or phrase=[N-M] | reason=<one sentence>
or
UNSUBSTANTIATED | confidence=N | reason=<one sentence>

where N is your confidence level (1-5).

Answer:"""

    resp = call_llm(prompt, max_tokens=200)
    if not resp:
        return False, "LLM call failed", 0.0, -1

    verdict = resp.strip()
    parts = verdict.split('|')
    label = parts[0].strip().upper()
    phrase_idx = -1
    reason = ''

    for part in parts[1:]:
        part = part.strip()
        if part.startswith('phrase='):
            try:
                val = part.split('=')[1].strip()
                # Handle range like [24-26] or single [24]
                phrase_match = re.match(r'\[(\d+)(?:-(\d+))?\]', val)
                if phrase_match:
                    phrase_idx = int(phrase_match.group(1))  # store start of range
                else:
                    phrase_idx = int(val)
            except:
                pass
        elif part.startswith('reason='):
            reason = part.split('=', 1)[1].strip()
        elif 'reason' not in part and 'phrase' not in part:
            reason = part

    if not reason:
        reason = verdict

    evidence_found = label.startswith('VERIFIED')
    return evidence_found, reason, 1.0 if evidence_found else 0.0, phrase_idx


def main():
    if len(sys.argv) < 2:
        print("Usage: check_citations.py <paper.tex>")
        sys.exit(1)

    tex_path = sys.argv[1]
    tex_dir = os.path.dirname(os.path.abspath(tex_path))

    if not API_KEY:
        print("WARNING: DEEPSEEK_API_KEY not set — LLM evaluation disabled")

    # Find all citations
    citations = find_citations(tex_path)
    print(f"Found {len(citations)} citations\n")

    results = []
    # Load hash cache to skip unchanged claims
    cache_path = os.path.join(tex_dir, 'verification_cache.json')
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path) as f:
                cache = json.load(f)
        except:
            pass

    for cit in citations:
        source_path = resolve_source(cit['content'], tex_dir)

        if source_path:
            short_name = os.path.basename(source_path)[:50]
            print(f"Checking: {cit['content'][:80]}...")
            
            # Check hash cache
            cache_key = hashlib.sha256(f"{cit['claim']}|{cit['content']}".encode()).hexdigest()
            if cache_key in cache:
                cached = cache[cache_key]
                print(f"  (cached: {cached['evidence_found']}, confidence={cached['confidence']})")
                results.append(cached)
                continue
            
            source_text = extract_text(source_path)

            if API_KEY and source_text:
                evidence, reason, confidence, phrase_idx = evaluate_with_llm(cit['claim'], source_text, short_name)
            elif source_text:
                evidence = True
                reason = "Source found but LLM not available (no API key)"
                confidence = 0.5
                phrase_idx = -1
            else:
                evidence = False
                reason = "Could not extract text from source"
                confidence = 0.0
                phrase_idx = -1

            results.append({
                'paper_section': 'main',
                'claim': cit['claim'],
                'citation': cit['content'][:200],
                'pdf_file': os.path.relpath(source_path, tex_dir),
                'evidence_found': 'YES' if evidence else 'NO',
                'confidence': f'{confidence:.2f}',
                'reason': reason,
            })
            # Save to cache
            cache[cache_key] = results[-1]
        else:
            results.append({
                'paper_section': 'main',
                'claim': cit['claim'],
                'citation': cit['content'][:200],
                'pdf_file': 'NOT FOUND',
                'evidence_found': 'UNCHECKED',
                'confidence': '0.00',
                'reason': f'No matching file in {PDF_DIR}/',
            })

    # Write report
    out_path = os.path.join(tex_dir, 'verification_report.csv')
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['paper_section', 'claim', 'citation',
                                                'pdf_file', 'evidence_found', 'confidence', 'reason'])
        writer.writeheader()
        writer.writerows(results)

    verified = sum(1 for r in results if r['evidence_found'] == 'YES')
    failed = sum(1 for r in results if r['evidence_found'] == 'NO')
    unchecked = sum(1 for r in results if r['evidence_found'] == 'UNCHECKED')

    print(f"\nResults: {verified} VERIFIED, {failed} UNSUBSTANTIATED, {unchecked} UNCHECKED")
    print(f"Report: {out_path}")
    
    # Save cache
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)
    print(f"Cache: {cache_path} ({len(cache)} entries)")

    for r in results:
        status = r['evidence_found']
        symbol = '✓' if status == 'YES' else ('✗' if status == 'NO' else '?')
        print(f"  {symbol} [{r['pdf_file'][:40]}] {r['claim'][:80]}...")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
