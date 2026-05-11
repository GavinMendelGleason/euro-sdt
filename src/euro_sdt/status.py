"""Quick status check for the provenance system."""

from euro_sdt.config import DB_PATH, DEEPSEEK_API_KEY, DEEPSEEK_API_URL, MANIFEST_DIR, WIKI_DIR, WIKI_IMG_DIR, WIKIDATA_SPARQL
import sqlite3, os, time

def status():
    db = sqlite3.connect(DB_PATH)
    t   = db.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
    pi0 = db.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index = 0").fetchone()[0]
    pi_pos = db.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index > 0").fetchone()[0]
    pi_neg = db.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index = -1").fetchone()[0]
    c = db.execute("SELECT COUNT(*) FROM fact WHERE confidence='confirmed'").fetchone()[0]
    d = db.execute("SELECT COUNT(*) FROM fact WHERE confidence='disputed'").fetchone()[0]
    db.close()

    running_rematch = os.popen("pgrep -f rematch_parallel.py | wc -l").read().strip()
    running_verify  = os.popen("pgrep -f verify.py | wc -l").read().strip()

    print(f"COVERAGE ({t} total facts)")
    print(f"  Phrase-index quotes:     {pi_pos:>4} ({pi_pos/t*100:.0f}%) — exact sentence in source")
    print(f"  Name-in-page references: {pi_neg:>4} ({pi_neg/t*100:.0f}%) — name found in source page")
    print(f"  File-level references:   {pi0:>4} ({pi0/t*100:.0f}%) — source file documented")
    print()
    print(f"CONFIDENCE")
    print(f"  Confirmed: {c} ({c/t*100:.0f}%)")
    print(f"  Disputed:  {d} ({d/t*100:.0f}%)")
    print()
    print(f"PROCESSES")
    print(f"  Rematcher:  {'RUNNING' if running_rematch != '0' else 'idle'}")
    print(f"  Verifier:   {'RUNNING' if running_verify != '0' else 'idle'}")

    # Show verification results if available
    if os.path.exists('verification_report.csv'):
        mtime = os.path.getmtime('verification_report.csv')
        ago = int(time.time() - mtime)
        try:
            import pandas as pd
            df = pd.read_csv('verification_report.csv')
            s = (df['verdict']=='SUPPORTED').sum()
            u = (df['verdict']=='UNSUPPORTED').sum()
            checked_phrase = pi_pos + pi_neg  # all phrase-index and name-in-page
            print(f"\nAI VERIFICATION ({ago}s ago, {len(df)} facts checked)")
            print(f"  Supported: {s}/{len(df)} ({s/len(df)*100:.0f}%) — quote proves claim")
            print(f"  Unsupported: {u}/{len(df)} ({u/len(df)*100:.0f}%) — quote doesn't prove claim")
            print(f"  Unchecked (have quotes, not yet verified): {checked_phrase - len(df)}")
            if len(df) > 0:
                print(f"\n  Verified rate by predicate:")
                for pred, grp in df.groupby('predicate'):
                    sup = (grp['verdict']=='SUPPORTED').sum(); tot = len(grp)
                    print(f"    {pred:<28} {sup:>3}/{tot:<3} ({sup/tot*100:.0f}%)")
        except: pass

if __name__ == '__main__':
    status()
