"""
Stability test (Unit 7, Part A): many users submitting tickets at the same time.

Starts the real app as a separate server process (the same way measure_latency.py does,
on a free port and a temporary database), then several simulated users log in and submit
tickets concurrently. It reports failures, throughput and latency, and then checks data
integrity: every successful submission must be in the database exactly once, with a
matching audit entry.

Safe to run: it never touches helpdesk.db.
Run from the prototype folder:   python evaluation/stability_test.py
Options:                         --workers 10 (simulated users)   --tickets 30 (per user)
"""
import argparse
import json
import platform
import socket
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_DIR = HERE.parent

DESCRIPTIONS = [
    "I am locked out of my account and need a password reset",
    "My laptop keyboard is not working",
    "The application keeps crashing when I open it",
    "I cannot connect to the office wifi",
    "I need permission to the shared drive for the finance folder",
]

LAUNCHER = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import models
models.DB_PATH = Path(sys.argv[2])
models.init_db()
from app import app
app.run(host="127.0.0.1", port=int(sys.argv[3]), debug=True, use_reloader=False)
"""


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10, help="simulated users acting at the same time")
    ap.add_argument("--tickets", type=int, default=30, help="tickets each user submits")
    args = ap.parse_args()

    if not (APP_DIR / "templates").is_dir():
        sys.exit("No 'templates' folder found next to app.py.")
    try:
        import requests
    except ImportError:
        sys.exit("This script needs the 'requests' package:  python -m pip install requests")

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    results = []          # (ok, milliseconds, error text)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_file = Path(tmp) / "stability.db"
        log_path = Path(tmp) / "server.log"
        with open(log_path, "w") as log:
            proc = subprocess.Popen(
                [sys.executable, "-c", LAUNCHER, str(APP_DIR), str(db_file), str(port)],
                cwd=str(APP_DIR), stdout=log, stderr=log)
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    sys.exit("The server stopped immediately:\n" + log_path.read_text())
                try:
                    if requests.get(base + "/login", timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    time.sleep(0.1)
            else:
                sys.exit("The server did not start in time:\n" + log_path.read_text())

            def user(n):
                out = []
                s = requests.Session()
                s.post(base + "/login", data={"username": "agent1" if n % 2 == 0 else "idmgmt1"}, timeout=30)
                for i in range(args.tickets):
                    text = DESCRIPTIONS[(n + i) % len(DESCRIPTIONS)]
                    t0 = time.perf_counter()
                    try:
                        r = s.post(base + "/submit", data={"description": text}, timeout=30)
                        out.append((r.status_code == 200, (time.perf_counter() - t0) * 1000, "" if r.status_code == 200 else f"HTTP {r.status_code}"))
                    except Exception as e:                      # connection errors, timeouts
                        out.append((False, (time.perf_counter() - t0) * 1000, type(e).__name__))
                return out

            wall0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                for batch in pool.map(user, range(args.workers)):
                    results.extend(batch)
            wall = time.perf_counter() - wall0
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        # data-integrity check, read straight from the database file
        conn = sqlite3.connect(db_file)
        tickets = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        distinct = conn.execute("SELECT COUNT(DISTINCT id) FROM tickets").fetchone()[0]
        audit_submits = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'submit_ticket'").fetchone()[0]
        audit_logins = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'login'").fetchone()[0]
        conn.close()

    ok = [r for r in results if r[0]]
    failed = [r for r in results if not r[0]]
    lat = sorted(r[1] for r in results)
    integrity = (tickets == len(ok) == audit_submits == distinct) and audit_logins == args.workers
    verdict = "PASS" if (not failed and integrity) else "FAIL"

    print(f"Platform: {platform.platform()} | Python {platform.python_version()}")
    print()
    print(f"Simulated users: {args.workers} at the same time, {args.tickets} tickets each")
    print(f"Requests sent:        {len(results)}")
    print(f"Successful:           {len(ok)}")
    print(f"Failed:               {len(failed)}" + (f"  ({', '.join(sorted({r[2] for r in failed}))})" if failed else ""))
    print(f"Total time:           {wall:.2f} s   ({len(ok) / wall:.1f} successful requests per second)")
    print(f"Latency mean / p95 / max: {statistics.mean(lat):.1f} / {lat[int(len(lat) * 0.95)]:.1f} / {lat[-1]:.1f} ms")
    print(f"Tickets in database:  {tickets}   (distinct ids: {distinct})")
    print(f"Audit entries:        {audit_submits} submissions, {audit_logins} logins")
    print(f"Data integrity:       {'OK' if integrity else 'MISMATCH'}")
    print(f"RESULT: {verdict}")

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / "stability_results.json", "w", encoding="utf-8") as f:
        json.dump({"workers": args.workers, "tickets_each": args.tickets, "requests": len(results),
                   "successful": len(ok), "failed": len(failed), "seconds": wall,
                   "mean_ms": statistics.mean(lat), "p95_ms": lat[int(len(lat) * 0.95)], "max_ms": lat[-1],
                   "tickets_in_db": tickets, "audit_submissions": audit_submits, "integrity_ok": integrity,
                   "result": verdict, "platform": platform.platform(), "python": platform.python_version()}, f, indent=2)
    print()
    print(f"Saved: {out_dir / 'stability_results.json'}")


if __name__ == "__main__":
    main()
