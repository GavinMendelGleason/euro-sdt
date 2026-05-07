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
import re, os, sys, csv, json, urllib.request, urllib.parse

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
        return content[:8000]

    result = None

    # Try pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        result = ' '.join(p.extract_text() or '' for p in reader.pages[:20])
        if result.strip():
            return result[:8000]
    except:
        pass

    # Try pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            result = ' '.join(p.extract_text() or '' for p in pdf.pages[:20])
            if result.strip():
                return result[:8000]
    except:
        pass

    # Try pdftotext
    try:
        import subprocess
        r = subprocess.run(['pdftotext', '-l', '20', path, '-'],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout[:8000]
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


def resolve_source(citation_content):
    """Find matching PDF or text file for a citation by parsing author names and years from the citation text."""
    # Clean LaTeX formatting
    clean = re.sub(r'\\[a-z]+\{([^}]*)\}', r'\1', citation_content)
    clean = re.sub(r'\\[a-z]+', '', clean)
    clean = re.sub(r'["`]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean_lower = clean.lower()

    # Extract author surnames (capitalized words before a year)
    authors = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', clean[:150])
    years = re.findall(r'(\d{4})', clean)

    # Score each file in papers/
    best_score = 0
    best_path = None

    for f in os.listdir(PDF_DIR):
        if not f.endswith(('.pdf', '.txt')):
            continue
        if f == 'BIBLIOGRAPHY.md':
            continue

        f_lower = f.lower()
        score = 0

        # Match first author surname (most distinctive)
        if authors:
            surname = authors[0].lower()
            if surname in f_lower:
                score += 3
            # Also check if other significant parts of first author appear
            first_author_words = authors[0].lower().split()
            for w in first_author_words:
                if len(w) > 3 and w in f_lower:
                    score += 1

        # Match years
        for year in years:
            if year in f_lower:
                score += 2
                break

        # Match distinctive title words
        title_words = re.findall(r'[a-z]{5,}', clean_lower[:200])
        significant = [w for w in title_words if w not in
                       {'which', 'these', 'their', 'there', 'about', 'would', 'could', 'should',
                        'press', 'university', 'volume', 'pages', 'survey', 'generation'}]
        for w in significant[:5]:
            if w in f_lower:
                score += 1

        if score > best_score:
            best_score = score
            best_path = os.path.join(PDF_DIR, f)

    if best_score >= 3:
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
    phrases = sentences[:80]  # limit for LLM context
    numbered = '\n'.join(f"[{i}] {phrases[i][:300]}" for i in range(len(phrases)))

    prompt = f"""Does this source document substantiate the following claim made in our paper?

CLAIM: {claim}

SOURCE: {source_name}
NUMBERED PHRASES:
{numbered}

If the source substantiates the claim, reply:
VERIFIED | phrase=[N] or phrase=[N-M] | reason=<one sentence explaining how the cited phrase(s) support the claim>

If the source does NOT substantiate the claim, reply:
UNSUBSTANTIATED | reason=<one sentence explaining why>

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
    for cit in citations:
        source_path = resolve_source(cit['content'])

        if source_path:
            short_name = os.path.basename(source_path)[:50]
            print(f"Checking: {cit['content'][:80]}...")
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

    for r in results:
        status = r['evidence_found']
        symbol = '✓' if status == 'YES' else ('✗' if status == 'NO' else '?')
        print(f"  {symbol} [{r['pdf_file'][:40]}] {r['claim'][:80]}...")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
