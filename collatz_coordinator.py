"""
Collatz Distributed Coordinator  —  Production Ready
------------------------------------------------------
Supports three server modes, auto-detected in order of preference:

  1. Gunicorn  (Linux/Mac — best performance)
     pip install gunicorn
     gunicorn -w 1 --threads 8 -b 0.0.0.0:5555 collatz_coordinator:app

  2. Waitress  (Windows/Linux/Mac — good performance, pure Python)
     pip install waitress
     python3 collatz_coordinator.py

  3. Flask dev server  (fallback — fine for small deployments, warns you)
     python3 collatz_coordinator.py

IMPORTANT — Gunicorn worker count:
  Always use -w 1 (one process). State lives in memory, so multiple processes
  would have separate copies and hand out the same chunks twice.
  Use --threads to handle concurrent requests instead:
    gunicorn -w 1 --threads 8 -b 0.0.0.0:5555 collatz_coordinator:app

Configuration via environment variables (used when running under Gunicorn):
  COLLATZ_START   — starting n (default: 2^68)
  COLLATZ_CHUNK   — odd numbers per chunk (default: 500000)
  COLLATZ_PORT    — port (default: 5555, only used in direct mode)

Configuration via CLI flags (used when running directly):
  --start, --chunk, --port

Endpoints:
  GET  /chunk    -> assign next chunk to a worker
  POST /results  -> worker submits FAILs for a completed chunk
  GET  /status   -> live progress dashboard
"""

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("ERROR: pip install flask")
    raise SystemExit(1)

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_START      = 2 ** 68
DEFAULT_CHUNK_SIZE = 500_000
DEFAULT_PORT       = 5555
RESULTS_FILE       = "collatz_distributed_fails.txt"
CHECKPOINT_FILE    = "collatz_coordinator_checkpoint.json"
STALE_TIMEOUT      = 600    # seconds before re-issuing an in-flight chunk

# Suppress Flask's default request logging — we do our own
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

# ── Shared state (single process, protected by lock) ──────────────────────────

lock  = threading.Lock()
state = {
    "next_n":        DEFAULT_START,
    "chunk_size":    DEFAULT_CHUNK_SIZE,
    "chunks_issued": 0,
    "chunks_done":   0,
    "total_tested":  0,
    "fails":         0,
    "in_flight":     {},
    "started_at":    time.time(),
}

# Per-worker lifetime stats — persisted in checkpoint
# { worker_id: {chunks, tested, fails, total_sec, first_seen, last_seen} }
worker_stats = {}


# ── Checkpoint ────────────────────────────────────────────────────────────────

def save_checkpoint():
    data = {k: v for k, v in state.items() if k not in ("in_flight", "started_at")}
    data["worker_stats"] = worker_stats
    tmp  = CHECKPOINT_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    Path(tmp).replace(CHECKPOINT_FILE)


def load_checkpoint():
    p = Path(CHECKPOINT_FILE)
    if not p.exists():
        return False
    try:
        with open(p) as f:
            saved = json.load(f)
        ws = saved.pop("worker_stats", {})
        state.update(saved)
        state["in_flight"]  = {}
        state["started_at"] = time.time()
        worker_stats.update(ws)
        return True
    except Exception as e:
        print(f"  Warning: checkpoint unreadable ({e}) -- fresh start")
        return False


# ── Startup (runs at import time — works under both Gunicorn and direct) ──────

def _startup(start_n=None, chunk_size=None):
    """
    Load checkpoint or initialise fresh state, write results file header,
    and launch the watchdog thread.  Called once at module load time.
    """
    # Config: CLI args take priority, then env vars, then defaults
    if start_n is None:
        start_n = int(os.environ.get("COLLATZ_START", DEFAULT_START))
    if chunk_size is None:
        chunk_size = int(os.environ.get("COLLATZ_CHUNK", DEFAULT_CHUNK_SIZE))

    resumed = load_checkpoint()

    if not resumed:
        n = start_n if start_n % 2 == 1 else start_n + 1
        state["next_n"]     = n
        state["chunk_size"] = chunk_size
        with open(RESULTS_FILE, "w") as rf:
            rf.write("COLLATZ CONJECTURE -- DISTRIBUTED FRONTIER FAILS\n")
            rf.write(f"Started    : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            rf.write(f"Start n    : 2^68 = {DEFAULT_START}  (odd numbers only)\n")
            rf.write(f"Chunk size : {chunk_size:,} odd numbers\n")
            rf.write(f"FAIL       : sequence exceeded step limit without dropping below 2^68\n")
            rf.write(f"Empty section below = conjecture held for all tested numbers.\n")
            rf.write("-" * 100 + "\n")
    else:
        with open(RESULTS_FILE, "a") as rf:
            rf.write(
                f"\n--- Restarted {time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(resuming from n={state['next_n']:,}, "
                f"tested so far={state['total_tested']:,}) ---\n"
            )

    threading.Thread(target=_watchdog, daemon=True).start()
    return resumed


# ── Stale chunk watchdog ──────────────────────────────────────────────────────

def _watchdog():
    while True:
        time.sleep(60)
        now = time.time()
        with lock:
            stale = [
                cid for cid, info in list(state["in_flight"].items())
                if now - info["issued_at"] > STALE_TIMEOUT
            ]
            for cid in stale:
                info = state["in_flight"].pop(cid)
                if info["start"] < state["next_n"]:
                    state["next_n"]        = info["start"]
                    state["chunks_issued"] -= 1
                print(
                    f"  [WATCHDOG] Re-queuing stale chunk {cid} "
                    f"from '{info['worker']}' (timed out after {STALE_TIMEOUT}s)",
                    flush=True
                )


# ── Flask app ─────────────────────────────────────────────────────────────────

app = Flask(__name__)


@app.route("/chunk", methods=["GET"])
def get_chunk():
    worker_id = request.args.get("worker", "unknown")
    with lock:
        chunk_id = state["chunks_issued"]
        start    = state["next_n"]
        if start % 2 == 0:
            start += 1
        end = start + state["chunk_size"] * 2 - 2   # last odd in range (inclusive)

        state["next_n"]        = end + 2
        state["chunks_issued"] += 1
        state["in_flight"][str(chunk_id)] = {
            "worker":    worker_id,
            "start":     start,
            "end":       end,
            "issued_at": time.time(),
        }
        save_checkpoint()

    print(f"  [CHUNK {chunk_id:>6}] {start} -> {end}  ->  '{worker_id}'", flush=True)
    return jsonify({"chunk_id": chunk_id, "start": start, "end": end,
                    "chunk_size": state["chunk_size"]})


@app.route("/results", methods=["POST"])
def post_results():
    data      = request.get_json(force=True)
    chunk_id  = str(data.get("chunk_id"))
    worker_id = data.get("worker", "unknown")
    fails     = data.get("fails", [])
    count     = int(data.get("count", 0))
    elapsed   = float(data.get("elapsed_sec", 1))

    if fails:
        with open(RESULTS_FILE, "a", buffering=1) as rf:
            for r in fails:
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                rf.write(
                    f"n={r['n']:<30} | FAIL *** POTENTIAL COUNTEREXAMPLE *** | "
                    f"steps={r['steps']:<10} | peak={r['peak']} | "
                    f"found={ts} | worker={worker_id}\n"
                )
        print(f"\n{'!'*70}", flush=True)
        print(f"  *** POTENTIAL COUNTEREXAMPLE(S) FROM '{worker_id}' ***")
        for r in fails:
            print(f"      n={r['n']}  steps={r['steps']}  peak={r['peak']}")
        print(f"{'!'*70}\n", flush=True)

    with lock:
        state["chunks_done"]  += 1
        state["total_tested"] += count
        state["fails"]        += len(fails)
        state["in_flight"].pop(chunk_id, None)

        # Update per-worker lifetime stats
        now_ts = time.strftime("%Y-%m-%d %H:%M:%S")
        if worker_id not in worker_stats:
            worker_stats[worker_id] = {
                "chunks":      0,
                "tested":      0,
                "fails":       0,
                "total_sec":   0.0,
                "first_seen":  now_ts,
                "last_seen":   now_ts,
            }
        w = worker_stats[worker_id]
        w["chunks"]    += 1
        w["tested"]    += count
        w["fails"]     += len(fails)
        w["total_sec"] += elapsed
        w["last_seen"]  = now_ts

        save_checkpoint()

    rate = count / elapsed if elapsed > 0 else 0
    print(
        f"  [CHUNK {int(chunk_id):>6}] Done '{worker_id}' | "
        f"{count:,} odd tested | {rate:,.0f}/sec | "
        f"fails={len(fails)} | done={state['chunks_done']}",
        flush=True
    )
    return jsonify({"status": "ok"})


@app.route("/status", methods=["GET"])
def status():
    with lock:
        elapsed = time.time() - state["started_at"]
        rate    = state["total_tested"] / elapsed if elapsed > 0 else 0
        workers = list({v["worker"] for v in state["in_flight"].values()})
        offset  = state["next_n"] - DEFAULT_START

    lines = [
        "=" * 65,
        " COLLATZ COORDINATOR  --  status",
        "=" * 65,
        f" Next n (frontier)  : {state['next_n']}",
        f" Offset from 2^68   : +{offset:,}",
        f" Chunks issued      : {state['chunks_issued']:,}",
        f" Chunks completed   : {state['chunks_done']:,}",
        f" In-flight          : {len(state['in_flight'])}",
        f" Odd numbers tested : {state['total_tested']:,}",
        f" Numbers covered    : ~{state['total_tested'] * 2:,}",
        f" Rate (session)     : {rate:,.0f} odd/sec",
        f" Active workers     : {workers}",
        f" FAILs found        : {state['fails']}",
        f" Elapsed            : {elapsed:,.1f}s",
        "=" * 65,
        "",
        " \u2192  Top 50 Workers Leaderboard: <a href='/workers'>/workers</a>",
    ]
    return "<pre style='font-family:monospace'>" + "\n".join(lines) + "</pre>"


@app.route("/workers", methods=["GET"])
def workers_leaderboard():
    with lock:
        snapshot = {wid: dict(w) for wid, w in worker_stats.items()}
        active   = {v["worker"] for v in state["in_flight"].values()}

    # Sort by numbers tested descending, take top 50
    ranked = sorted(snapshot.items(), key=lambda x: x[1]["tested"], reverse=True)[:50]

    now = time.time()

    rows_html = ""
    for rank, (wid, w) in enumerate(ranked, 1):
        avg_rate = w["tested"] / w["total_sec"] if w["total_sec"] > 0 else 0
        is_active = wid in active
        status_dot  = (
            "<span style='color:#4ade80'>&#9679; active</span>"
            if is_active else
            "<span style='color:#6b7280'>&#9679; idle</span>"
        )
        rank_style = ""
        if rank == 1:
            rank_style = "style='color:#f59e0b;font-weight:700'"  # gold
        elif rank == 2:
            rank_style = "style='color:#94a3b8;font-weight:700'"  # silver
        elif rank == 3:
            rank_style = "style='color:#b45309;font-weight:700'"  # bronze

        rows_html += f"""
        <tr>
          <td {rank_style}>#{rank}</td>
          <td style='font-family:monospace'>{wid}</td>
          <td>{w['tested']:,}</td>
          <td>{w['chunks']:,}</td>
          <td>{avg_rate:,.0f}</td>
          <td style='color:#f87171'>{w['fails']}</td>
          <td>{status_dot}</td>
          <td style='color:#6b7280;font-size:0.85em'>{w['last_seen']}</td>
        </tr>"""

    total_workers   = len(snapshot)
    active_count    = len(active)
    session_elapsed = now - state["started_at"]
    session_rate    = state["total_tested"] / session_elapsed if session_elapsed > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="15">
  <title>Collatz Frontier — Worker Leaderboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0f172a;
      color: #e2e8f0;
      font-family: 'Segoe UI', system-ui, sans-serif;
      padding: 2rem;
      min-height: 100vh;
    }}
    h1 {{
      font-size: 1.6rem;
      font-weight: 700;
      color: #f8fafc;
      margin-bottom: 0.25rem;
    }}
    .subtitle {{
      color: #94a3b8;
      font-size: 0.9rem;
      margin-bottom: 1.5rem;
    }}
    .subtitle a {{
      color: #60a5fa;
      text-decoration: none;
    }}
    .subtitle a:hover {{ text-decoration: underline; }}
    .stats-bar {{
      display: flex;
      gap: 1.5rem;
      flex-wrap: wrap;
      margin-bottom: 1.75rem;
    }}
    .stat {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 0.75rem 1.25rem;
      min-width: 160px;
    }}
    .stat-label {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #64748b;
      margin-bottom: 0.2rem;
    }}
    .stat-value {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #f1f5f9;
      font-variant-numeric: tabular-nums;
    }}
    .stat-value.green {{ color: #4ade80; }}
    .stat-value.blue  {{ color: #60a5fa; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}
    thead th {{
      background: #1e293b;
      color: #94a3b8;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 0.6rem 0.9rem;
      text-align: left;
      border-bottom: 1px solid #334155;
      white-space: nowrap;
    }}
    tbody tr {{
      border-bottom: 1px solid #1e293b;
      transition: background 0.1s;
    }}
    tbody tr:hover {{ background: #1e293b; }}
    tbody tr:nth-child(1) {{ background: rgba(245,158,11,0.05); }}
    tbody tr:nth-child(2) {{ background: rgba(148,163,184,0.04); }}
    tbody tr:nth-child(3) {{ background: rgba(180,83,9,0.05); }}
    td {{
      padding: 0.6rem 0.9rem;
      vertical-align: middle;
      white-space: nowrap;
    }}
    .refresh-note {{
      margin-top: 1rem;
      font-size: 0.78rem;
      color: #475569;
    }}
    .no-workers {{
      text-align: center;
      padding: 3rem;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <h1>&#127942; Collatz Frontier &mdash; Worker Leaderboard</h1>
  <p class="subtitle">
    Top 50 workers by numbers tested &nbsp;&bull;&nbsp;
    <a href="/status">&#8592; Back to status</a>
    &nbsp;&bull;&nbsp;
    <a href="https://github.com/huggablehacker/Collatz-Frontier" target="_blank">GitHub</a>
  </p>

  <div class="stats-bar">
    <div class="stat">
      <div class="stat-label">Total workers</div>
      <div class="stat-value blue">{total_workers:,}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Active now</div>
      <div class="stat-value green">{active_count}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Numbers covered</div>
      <div class="stat-value">{state['total_tested'] * 2:,}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Session rate</div>
      <div class="stat-value">{session_rate:,.0f} <span style="font-size:0.75rem;color:#94a3b8">odd/sec</span></div>
    </div>
    <div class="stat">
      <div class="stat-label">FAILs found</div>
      <div class="stat-value" style="color:{'#f87171' if state['fails'] else '#4ade80'}">{state['fails']}</div>
    </div>
  </div>

  {'<table><thead><tr>' +
   '<th>#</th><th>Worker</th><th>Numbers tested</th>' +
   '<th>Chunks done</th><th>Avg speed (odd/s)</th>' +
   '<th>FAILs</th><th>Status</th><th>Last seen</th>' +
   '</tr></thead><tbody>' + rows_html + '</tbody></table>'
   if ranked else
   '<div class="no-workers">No workers have submitted results yet.</div>'}

  <p class="refresh-note">Auto-refreshes every 15 seconds.</p>
</body>
</html>"""
    return html


# ── Gunicorn hook — runs startup inside the worker process after fork ─────────
# Gunicorn calls this automatically when it forks a worker process.

def post_fork(server, worker):
    _startup()


# ── Module-level init for Gunicorn (import-time, before any request) ──────────
# When Gunicorn imports this module, _startup() is called once here.
# The post_fork hook above also fires but load_checkpoint() is idempotent.
_gunicorn_running = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "") or \
                    any("gunicorn" in arg for arg in sys.argv)

if _gunicorn_running:
    _startup()


# ── Direct execution ──────────────────────────────────────────────────────────

def _print_banner(port, resumed):
    print()
    print("=" * 65)
    print(" Collatz Distributed Coordinator -- Production Ready")
    print("=" * 65)
    if resumed:
        print(f" RESUMED     -- next n      = {state['next_n']:,}")
        print(f"                tested      = {state['total_tested']:,}")
        print(f"                chunks done = {state['chunks_done']:,}")
    else:
        print(f" Fresh start -- n = {state['next_n']:,}")
    print(f" Chunk size  : {state['chunk_size']:,} odd numbers")
    print(f" Port        : {port}")
    print(f" Results     : {RESULTS_FILE}  (FAILs only)")
    print(f" Checkpoint  : {CHECKPOINT_FILE}")
    print()
    print(f" Workers:  python3 collatz_worker.py --coordinator http://<THIS_IP>:{port}")
    print(f" Dashboard: http://localhost:{port}/status")
    print()
    print(" To run with Gunicorn (recommended for many workers):")
    print(f"   gunicorn -w 1 --threads 8 -b 0.0.0.0:{port} collatz_coordinator:app")
    print()
    print(" To run with Waitress (good on Windows/Linux, pure Python):")
    print(f"   pip install waitress")
    print(f"   python3 collatz_coordinator.py  # auto-detected")
    print("=" * 65)
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Collatz distributed coordinator")
    parser.add_argument("--start", type=int, default=DEFAULT_START)
    parser.add_argument("--chunk", type=int, default=DEFAULT_CHUNK_SIZE,
                        help=f"Odd numbers per chunk (default {DEFAULT_CHUNK_SIZE:,})")
    parser.add_argument("--port",  type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    resumed = _startup(start_n=args.start, chunk_size=args.chunk)
    _print_banner(args.port, resumed)

    # Try production servers in order, fall back to Flask dev server
    try:
        from waitress import serve
        print("  Server: Waitress (production)")
        serve(app, host="0.0.0.0", port=args.port, threads=8)

    except ImportError:
        try:
            import gunicorn  # noqa: F401
            # If gunicorn is installed, tell the user to use it properly
            print("  Gunicorn detected — for best performance, run via:")
            print(f"  gunicorn -w 1 --threads 8 -b 0.0.0.0:{args.port} collatz_coordinator:app")
            print()
            print("  Falling back to Flask dev server for now...")
            print("  WARNING: Flask dev server is fine for small setups but")
            print("  may bottleneck under 20+ simultaneous workers.")
            print()
        except ImportError:
            print("  Server: Flask dev server")
            print("  TIP: pip install waitress  for a production server")
            print()

        app.run(host="0.0.0.0", port=args.port, threaded=True)
