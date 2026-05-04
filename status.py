"""Quick status check for rematch progress."""
import sqlite3, os

def status():
    db = sqlite3.connect('euro_sdt.db')
    pi_gt0 = db.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index > 0").fetchone()[0]
    total  = db.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
    batch  = db.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index = 0").fetchone()[0]
    d = db.execute("SELECT COUNT(*) FROM fact WHERE confidence='disputed'").fetchone()[0]
    c = db.execute("SELECT COUNT(*) FROM fact WHERE confidence='confirmed'").fetchone()[0]
    db.close()

    running = os.popen("pgrep -f rematch.py | wc -l").read().strip()
    
    print(f"Phrase quotes: {pi_gt0}/{total} ({pi_gt0/total*100:.0f}%)")
    print(f"Batch:         {batch}/{total} ({batch/total*100:.0f}%)")
    print(f"Confirmed:     {c}/{total} ({c/total*100:.0f}%)")
    print(f"Disputed:      {d}/{total} ({d/total*100:.0f}%)")
    print(f"Rematcher:     {'RUNNING' if running != '0' else 'complete'}")

    # Show last progress line
    log = 'rematch_log2.txt'
    if os.path.exists(log):
        with open(log) as f:
            lines = [l for l in f if 'rematched' in l and '/' in l]
            if lines:
                print(f"Progress:      {lines[-1].strip()}")

if __name__ == '__main__':
    status()
