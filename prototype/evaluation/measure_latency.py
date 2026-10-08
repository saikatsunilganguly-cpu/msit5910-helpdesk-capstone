"""
End-to-end latency check (Unit 6, Part B).

Starts the real Flask app as a separate server process, the same way app.py does
(Flask development server, debug on, reloader off) but on a free local port and a
temporary database. It then logs in as agent1 and times POST /submit requests.
Each timing covers the full HTTP round trip: routing, categorisation, the SQLite
write, template rendering and the response.

Safe to run: it never touches helpdesk.db.
Run from the prototype folder:   python evaluation/measure_latency.py
Options:                         --n 60 (timed requests)   --warmup 3 (untimed GETs)
"""
import argparse
import json
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import time
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

# Same call as the bottom of app.py, but with a temporary database and a chosen port.
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
    ap.add_argument("--n", type=int, default=60, help="number of timed POST /submit requests")
    ap.add_argument("--warmup", type=int, default=3, help="number of untimed warm-up requests")
    args = ap.parse_args()

    if not (APP_DIR / "templates").is_dir():
        sys.exit("No 'templates' folder found next to app.py.\n"
                 "Use your original templates folder, or copy 'templates_reconstructed' to 'templates'.")
    try:
        import requests
    except ImportError:
        sys.exit("This script needs the 'requests' package:  python -m pip install requests")

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    latencies = []

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        log_path = Path(tmp) / "server.log"
        with open(log_path, "w") as log:
            proc = subprocess.Popen(
                [sys.executable, "-c", LAUNCHER, str(APP_DIR), str(Path(tmp) / "eval.db"), str(port)],
                cwd=str(APP_DIR), stdout=log, stderr=log)
        try:
            for _ in range(100):                                  # wait up to ~10 s for the server
                if proc.poll() is not None:
                    sys.exit("The server stopped immediately:\n" + log_path.read_text())
                try:
                    if requests.get(base + "/login", timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    time.sleep(0.1)
            else:
                sys.exit("The server did not start in time:\n" + log_path.read_text())

            s = requests.Session()
            s.post(base + "/login", data={"username": "agent1"}).raise_for_status()
            for _ in range(args.warmup):
                s.get(base + "/submit").raise_for_status()
            for i in range(args.n):
                desc = DESCRIPTIONS[i % len(DESCRIPTIONS)]
                t0 = time.perf_counter()
                r = s.post(base + "/submit", data={"description": desc})
                t1 = time.perf_counter()
                r.raise_for_status()
                latencies.append((t1 - t0) * 1000)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    ordered = sorted(latencies)
    print(f"Platform: {platform.platform()} | Python {platform.python_version()}")
    print()
    print(f"N = {len(latencies)} POST /submit requests (full HTTP round trip)")
    print(f"Mean latency:   {statistics.mean(latencies):.2f} ms")
    print(f"Median latency: {statistics.median(latencies):.2f} ms")
    print(f"Std dev:        {statistics.stdev(latencies):.2f} ms")
    print(f"Min / Max:      {min(latencies):.2f} ms / {max(latencies):.2f} ms")
    print(f"p95:            {ordered[int(len(ordered) * 0.95)]:.2f} ms")

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / "latency_results.json", "w", encoding="utf-8") as f:
        json.dump(latencies, f)
    print()
    print(f"Saved: {out_dir / 'latency_results.json'}")


if __name__ == "__main__":
    main()
