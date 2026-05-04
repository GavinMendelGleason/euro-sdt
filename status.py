"""Quick status check for the provenance system."""
import sqlite3, os, time

def status():
    db = sqlite3.connect('euro_sdt.db')
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
            print(f"\nLAST VERIFICATION ({ago}s ago, {len(df)} facts checked)")
            print(f"  Supported: {s}/{len(df)} ({s/len(df)*100:.0f}%)")
        except: pass

if __name__ == '__main__':
    status()
