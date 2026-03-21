"""
Collatz Distributed Coordinator  —  Optimized + Checkpointed
--------------------------------------------------------------
Run ONE instance of this. Workers connect to it, pull chunks of odd numbers
to test, and POST back any FAILs only. The coordinator tracks progress,
checkpoints to disk after every completed chunk, and resumes automatically
on restart.

Only FAIL entries are written to the results file. An empty results section
means the conjecture held for every number tested so far.

Usage:
    pip install flask
    python3 collatz_coordinator.py

    python3 collatz_coordinator.py --start 295147905179352825856 --chunk 500000 --port 5555

Endpoints:
    GET  /chunk       -> assign next chunk to a worker
    POST /results     -> worker submits FAILs for a completed chunk
    GET  /status      -> live progress dashboard
"""

import argparse
import json
import threading
import time
from pathlib import Path

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("ERROR: pip install flask")
    raise SystemExit(1)

DEFAULT_START      = 2 ** 68
DEFAULT_CHUNK_SIZE = 500_000          # odd numbers per chunk (covers 1M integers)
DEFAULT_PORT       = 5555
RESULTS_FILE       = "collatz_distributed_fails.txt"
CHECKPOINT_FILE    = "collatz_coordinator_checkpoint.json"
STALE_TIMEOUT      = 600             # seconds before re-issuing a stale chunk

app  = Flask(__name__)
lock = threading.Lock()

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


# ── Checkpoint ────────────────────────────────────────────────────────────────

def save_checkpoint():
    data = {k: v for k, v in state.items() if k not in ("in_flight", "started_at")}
    tmp = CHECKPOINT_FILE + ".tmp"
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
        state.update(saved)
        state["in_flight"]  = {}
        state["started_at"] = time.time()
        return True
    except Exception as e:
        print(f"  Warning: could not load checkpoint ({e}) -- fresh start")
        return False


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.route("/chunk", methods=["GET"])
def get_chunk():
    worker_id = request.args.get("worker", "unknown")
    with lock:
        chunk_id = state["chunks_issued"]
        start    = state["next_n"]
        if start % 2 == 0:
            start += 1
        # end is last odd number in range (inclusive)
        end = start + state["chunk_size"] * 2 - 2

        state["next_n"]        = end + 2
        state["chunks_issued"] += 1
        state["in_flight"][str(chunk_id)] = {
            "worker":    worker_id,
            "start":     start,
            "end":       end,
            "issued_at": time.time(),
        }
        save_checkpoint()

    print(f"  [CHUNK {chunk_id:>6}] {start} -> {end}  ->  '{worker_id}'")
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
        print(f"\n{'!'*70}")
        print(f"  *** POTENTIAL COUNTEREXAMPLE(S) FROM '{worker_id}' ***")
        for r in fails:
            print(f"      n={r['n']}  steps={r['steps']}  peak={r['peak']}")
        print(f"{'!'*70}\n")

    with lock:
        state["chunks_done"]  += 1
        state["total_tested"] += count
        state["fails"]        += len(fails)
        state["in_flight"].pop(chunk_id, None)
        save_checkpoint()

    rate = count / elapsed if elapsed > 0 else 0
    print(
        f"  [CHUNK {int(chunk_id):>6}] Done '{worker_id}' | "
        f"{count:,} odd tested | {rate:,.0f}/sec | "
        f"fails={len(fails)} | done={state['chunks_done']}"
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
    ]
    return "<pre style='font-family:monospace'>" + "\n".join(lines) + "</pre>"


# ── Stale chunk watchdog ──────────────────────────────────────────────────────

def watchdog():
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
                print(f"  [WATCHDOG] Re-queuing stale chunk {cid} from '{info['worker']}'")


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Collatz distributed coordinator")
    p.add_argument("--start", type=int, default=DEFAULT_START)
    p.add_argument("--chunk", type=int, default=DEFAULT_CHUNK_SIZE,
                   help=f"Odd numbers per chunk (default {DEFAULT_CHUNK_SIZE:,})")
    p.add_argument("--port",  type=int, default=DEFAULT_PORT)
    return p.parse_args()


if __name__ == "__main__":
    args   = parse_args()
    resumed = load_checkpoint()

    if not resumed:
        state["next_n"]     = args.start if args.start % 2 == 1 else args.start + 1
        state["chunk_size"] = args.chunk
        with open(RESULTS_FILE, "w") as rf:
            rf.write("COLLATZ CONJECTURE -- DISTRIBUTED FRONTIER FAILS\n")
            rf.write(f"Started : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            rf.write(f"Start n : 2^68 = {DEFAULT_START}  (odd numbers only)\n")
            rf.write(f"FAIL    : sequence exceeded step limit without dropping below 2^68\n")
            rf.write(f"Empty section below = conjecture held for all tested numbers.\n")
            rf.write("-" * 100 + "\n")
    else:
        with open(RESULTS_FILE, "a") as rf:
            rf.write(f"\n--- Coordinator restarted {time.strftime('%Y-%m-%d %H:%M:%S')} "
                     f"(resuming from n={state['next_n']:,}) ---\n")

    threading.Thread(target=watchdog, daemon=True).start()

    print()
    print("=" * 65)
    print(" Collatz Distributed Coordinator -- Optimized")
    print("=" * 65)
    if resumed:
        print(f" RESUMED     -- next n    = {state['next_n']:,}")
        print(f"                tested    = {state['total_tested']:,}")
        print(f"                chunks done = {state['chunks_done']:,}")
    else:
        print(f" Fresh start -- n = {state['next_n']:,}")
    print(f" Chunk size  : {state['chunk_size']:,} odd numbers")
    print(f" Port        : {args.port}")
    print(f" Results     : {RESULTS_FILE}  (FAILs only)")
    print(f" Checkpoint  : {CHECKPOINT_FILE}")
    print()
    print(f" Workers:  python3 collatz_worker.py --coordinator http://<THIS_IP>:{args.port}")
    print(f" Dashboard: http://localhost:{args.port}/status")
    print("=" * 65)
    print()

    app.run(host="0.0.0.0", port=args.port, threaded=True)
