"""
scrape_mep_bios.py — Scrape Wikipedia bios for SDT-relevant MEPs.
Reads SDT MEP list from mep_lists/sdt_meps_with_wiki.csv,
fetches full Wikipedia page text via REST API, saves to sources/wikipedia/{slug}.txt.
"""
import csv, os, re, time, urllib.request, urllib.parse

HEADERS = {'User-Agent': 'euro-sdt/1.0 (research project; contact@example.com)'}
WIKI_DIR = 'sources/wikipedia'
MEP_LIST = 'mep_lists/sdt_meps_with_wiki.csv'


def extract_text(html):
    """Extract clean text from Wikipedia REST API HTML."""
    # Remove style/script
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    # Remove table of contents
    html = re.sub(r'<nav[^>]*id="toc"[^>]*>.*?</nav>', '', html, flags=re.DOTALL)
    # Remove infobox tables
    html = re.sub(r'<table[^>]*class="[^"]*infobox[^"]*"[^>]*>.*?</table>', '', html, flags=re.DOTALL)
    # Remove references
    html = re.sub(r'<ol[^>]*class="references"[^>]*>.*?</ol>', '', html, flags=re.DOTALL)
    # Replace <br> with newline
    html = html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    # Strip all remaining tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Clean whitespace
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def main():
    os.makedirs(WIKI_DIR, exist_ok=True)

    with open(MEP_LIST) as f:
        meps = list(csv.DictReader(f))

    scraped = 0
    skipped = 0
    errors = 0

    for m in meps:
        slug = m['slug'].strip()
        title = m['wikipedia_title'].strip()
        name = m['name'].strip()

        out_path = os.path.join(WIKI_DIR, f'{slug}.txt')
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            skipped += 1
            continue

        # Fetch via REST API
        encoded = urllib.parse.quote(title.replace(' ', '_'), safe='/_()')
        url = f'https://en.wikipedia.org/api/rest_v1/page/html/{encoded}'

        req = urllib.request.Request(url, headers=HEADERS)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            html = resp.read().decode('utf-8')
            text = extract_text(html)

            if len(text) < 300:
                print(f"  SHORT: {name} ({len(text)} chars)")
                errors += 1
                continue

            with open(out_path, 'w') as f:
                f.write(text)
            scraped += 1

            if scraped % 10 == 0:
                print(f"  {scraped} scraped... (latest: {name}, {len(text)} chars)")

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Try without disambiguation
                simple_title = re.sub(r'\s*\([^)]*\)', '', title).strip()
                encoded = urllib.parse.quote(simple_title.replace(' ', '_'), safe='/_()')
                url = f'https://en.wikipedia.org/api/rest_v1/page/html/{encoded}'
                try:
                    req = urllib.request.Request(url, headers=HEADERS)
                    resp = urllib.request.urlopen(req, timeout=30)
                    html = resp.read().decode('utf-8')
                    text = extract_text(html)
                    if len(text) > 300:
                        with open(out_path, 'w') as f:
                            f.write(text)
                        scraped += 1
                        print(f"  OK (retry): {name} → {simple_title} ({len(text)} chars)")
                        time.sleep(1)
                        continue
                except:
                    pass
                print(f"  404: {name} ({title})")
            elif e.code == 429:
                print(f"  RATE LIMITED, waiting 30s...")
                time.sleep(30)
                continue
            else:
                print(f"  HTTP {e.code}: {name}")
            errors += 1
        except Exception as e:
            print(f"  ERR: {name} — {e}")
            errors += 1

        time.sleep(1.5)

    print(f"\nDone. Scraped: {scraped}, Skipped: {skipped}, Errors: {errors}")


if __name__ == '__main__':
    main()
