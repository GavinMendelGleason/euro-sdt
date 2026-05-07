"""
check_citations.py — Cross-check paper citations against the cited PDFs.

Reads a LaTeX file, extracts all \footnote{} and \cite{} commands,
finds the corresponding PDF in papers/ (NOT assets/papers/ — that's for *our* papers),
extracts text from the PDF, and verifies that the claim the citation supports
is actually substantiated by the cited work.

Usage:
    .venv/bin/python check_citations.py assets/papers/methodology/paper.tex

Produces verification_report.csv with columns:
    paper_section, claim, citation, pdf_file, evidence_found, confidence
"""
import re, os, sys, csv
from collections import defaultdict

PDF_DIR = 'papers'


def extract_text_from_pdf(path):
    """Extract text from a PDF file. Requires PyPDF2 or pdfplumber."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return ' '.join(p.extract_text() or '' for p in reader.pages)
    except ImportError:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return ' '.join(p.extract_text() or '' for p in pdf.pages)
    except ImportError:
        pass
    # Fallback: use pdftotext command
    import subprocess
    try:
        result = subprocess.run(['pdftotext', path, '-'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    except:
        pass
    return None


def find_citations(tex_path):
    """Extract all \footnote{...} and \cite{...} from a LaTeX file."""
    with open(tex_path) as f:
        text = f.read()

    citations = []
    # Match \footnote{...}
    for m in re.finditer(r'\\footnote\{([^}]+)\}', text):
        content = m.group(1)
        citations.append({
            'type': 'footnote',
            'content': content,
            'start': m.start(),
        })

    # Match \cite{...}
    for m in re.finditer(r'\\cite\{([^}]+)\}', text):
        content = m.group(1)
        citations.append({
            'type': 'cite',
            'content': content,
            'start': m.start(),
        })

    return citations


def get_surrounding_context(tex_text, position, window=300):
    """Get the sentence or paragraph containing the citation."""
    start = max(0, position - window)
    end = min(len(tex_text), position + window)
    snippet = tex_text[start:end]
    # Clean LaTeX commands for readability
    snippet = re.sub(r'\\[a-z]+\{([^}]*)\}', r'\1', snippet)
    snippet = re.sub(r'\\[a-z]+', '', snippet)
    snippet = re.sub(r'\s+', ' ', snippet).strip()
    return snippet


def resolve_pdf(citation_content):
    """Resolve a citation to a PDF file path."""
    # Extract author, year, title hints from citation text
    content_lower = citation_content.lower()

    # Map known citations to PDF files
    known_pdfs = {}
    for root, dirs, files in os.walk(PDF_DIR):
        for f in files:
            if f.endswith('.pdf'):
                known_pdfs[f.lower()] = os.path.join(root, f)

    # Try to match by author and year
    authors = re.findall(r'([A-Z][a-z]+)', citation_content[:100])
    years = re.findall(r'(\d{4})', citation_content)

    # Search PDF content for author names
    for pdf_name, pdf_path in known_pdfs.items():
        score = 0
        for author in authors[:3]:
            if author.lower() in pdf_name.lower():
                score += 1
        for year in years:
            if year in pdf_name:
                score += 1
        if score >= 2:
            return pdf_path

    return None


def check_claim_against_pdf(claim_text, pdf_text):
    """Check whether the citing claim is substantiated by the PDF text."""
    if not pdf_text:
        return False, "PDF could not be extracted", 0.0

    # Extract key terms from the claim
    claim_lower = claim_text.lower()

    # Method 1: direct substring search (most reliable)
    # Extract key phrases from the claim (3+ word phrases)
    words = claim_lower.split()
    phrases_found = 0
    phrases_total = 0
    for i in range(len(words) - 2):
        phrase = ' '.join(words[i:i+3])
        if len(phrase) > 15:  # meaningful phrases
            phrases_total += 1
            if phrase in pdf_text.lower():
                phrases_found += 1

    # Method 2: check if key named entities appear
    named_entities = re.findall(r'[A-Z][a-z]+ [A-Z][a-z]+', claim_text)
    entities_found = sum(1 for e in named_entities if e.lower() in pdf_text.lower())

    # Method 3: check topic words
    topic_words = [w for w in words if len(w) > 5 and w not in
                   {'which', 'these', 'their', 'about', 'there', 'would', 'could', 'should'}]
    topics_found = sum(1 for t in topic_words if t in pdf_text.lower())

    # Compute confidence
    phrase_score = phrases_found / max(phrases_total, 1)
    entity_score = entities_found / max(len(named_entities), 1) if named_entities else 0.5
    topic_score = topics_found / max(len(topic_words), 1) if topic_words else 0

    confidence = (0.5 * phrase_score + 0.2 * entity_score + 0.3 * topic_score)
    evidence_found = confidence > 0.3

    if evidence_found:
        return True, f"Key phrases and entities found in PDF ({confidence:.0%} match)", confidence
    else:
        best_phrase = next((w for w in topic_words if w in pdf_text.lower()), "none")
        return False, f"Insufficient evidence (best match: '{best_phrase}')", confidence


def main():
    if len(sys.argv) < 2:
        print("Usage: check_citations.py <paper.tex>")
        sys.exit(1)

    tex_path = sys.argv[1]
    tex_dir = os.path.dirname(os.path.abspath(tex_path))

    with open(tex_path) as f:
        tex_text = f.read()

    # Extract sections for context
    sections = re.split(r'\\section\{([^}]+)\}', tex_text)
    section_map = {}
    for i in range(1, len(sections), 2):
        section_name = sections[i].strip()
        section_text = sections[i+1] if i+1 < len(sections) else ''
        section_map[section_name] = section_text

    # Find all citations
    citations = find_citations(tex_path)

    results = []
    for cit in citations:
        # Find which section this citation is in
        section = 'preamble'
        for sec_name, sec_text in section_map.items():
            if cit['start'] > tex_text.find(sec_text):
                section = sec_name

        claim = get_surrounding_context(tex_text, cit['start'])
        pdf_path = resolve_pdf(cit['content'])

        if pdf_path:
            print(f"Checking: {cit['content'][:60]}...")
            pdf_text = extract_text_from_pdf(pdf_path)
            evidence, reason, confidence = check_claim_against_pdf(claim, pdf_text)
            results.append({
                'paper_section': section,
                'claim': claim[:200],
                'citation': cit['content'][:200],
                'pdf_file': os.path.relpath(pdf_path, tex_dir),
                'evidence_found': 'YES' if evidence else 'NO',
                'confidence': f'{confidence:.2f}',
                'reason': reason,
            })
        else:
            results.append({
                'paper_section': section,
                'claim': claim[:200],
                'citation': cit['content'][:200],
                'pdf_file': 'NOT FOUND',
                'evidence_found': 'UNCHECKED',
                'confidence': '0.00',
                'reason': 'No matching PDF found in assets/papers/',
            })

    # Write report
    out_path = os.path.join(os.path.dirname(tex_path) or '.', 'verification_report.csv')
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['paper_section', 'claim', 'citation',
                                                'pdf_file', 'evidence_found', 'confidence', 'reason'])
        writer.writeheader()
        writer.writerows(results)

    verified = sum(1 for r in results if r['evidence_found'] == 'YES')
    failed = sum(1 for r in results if r['evidence_found'] == 'NO')
    unchecked = sum(1 for r in results if r['evidence_found'] == 'UNCHECKED')

    print(f"\nResults: {verified} verified, {failed} unsubstantiated, {unchecked} unchecked")
    print(f"Report: {out_path}")

    if failed > 0:
        print("\nUNSUBSTANTIATED — fix before submitting:")
        for r in results:
            if r['evidence_found'] == 'NO':
                print(f"  [{r['paper_section']}] {r['citation'][:80]}")
                print(f"    Claim: {r['claim'][:120]}")
                print(f"    Reason: {r['reason']}")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
