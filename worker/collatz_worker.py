"""
Collatz Distributed Worker  —  Optimized + Identified
------------------------------------------------------
Connects to the coordinator, pulls chunks, and processes them using:

  - Syracuse compressed steps  (odd -> next odd in one operation)
  - Odd-only testing           (even starting numbers are redundant)
  - Early exit at 2^68         (stop when sequence re-enters verified territory)
  - multiprocessing.Pool       (true CPU parallelism, bypasses Python GIL)
  - gmpy2 fast big integers    (optional, pip install gmpy2)

Worker Identity
---------------
On first run this script generates collatz_identity.json in the same folder.
This file contains a unique UUID, your hostname, IP, and secret key.
It is tied to this specific machine and is NEVER sent to the coordinator.

When your compute pushes the frontier past a named milestone (Sextillion,
Septillion, etc.), the coordinator sends back a signed claim token that is
saved to your identity file. This token is your proof of the achievement
and is required to claim the prize.

KEEP YOUR collatz_identity.json FILE SAFE. It is the only proof you crossed
a milestone. Back it up somewhere.

Usage:
    pip install requests
    python3 collatz_worker.py --coordinator http://192.168.1.100:5555

    python3 collatz_worker.py --coordinator http://192.168.1.100:5555 --name rig-2 --cores 8
"""

import argparse
import json
import os
import secrets
import socket
import sys
import time
import uuid
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

import multiprocessing
from multiprocessing import Pool

DEFAULT_PORT    = 5555
MAX_STEPS       = 10_000_000
THRESHOLD       = 2 ** 68
IDENTITY_FILE   = "collatz_identity.json"

# H1 — Worker auth token. Must match COLLATZ_WORKER_TOKEN on the coordinator.
# Set via environment: export COLLATZ_WORKER_TOKEN=<same value as coordinator>
WORKER_TOKEN = os.environ.get("COLLATZ_WORKER_TOKEN", "").strip()


# ── Worker identity ───────────────────────────────────────────────────────────

def _get_local_ip():
    """Best-effort local IP detection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"


def load_or_create_identity(worker_name):
    """
    Load existing identity from collatz_identity.json, or create a new one.
    The identity is permanent — it never changes once created.
    Returns the identity dict.
    """
    p = Path(IDENTITY_FILE)

    if p.exists():
        try:
            with open(p) as f:
                identity = json.load(f)
            # Update mutable fields in case machine name/IP changed
            identity["name"]     = worker_name
            identity["hostname"] = socket.gethostname()
            identity["ip"]       = _get_local_ip()
            _save_identity(identity)
            print(f"  Identity loaded: {IDENTITY_FILE}")
            print(f"  Worker ID : {identity['worker_id']}")
            print(f"  Milestones: {len(identity.get('milestones', {}))}")
            return identity
        except Exception as e:
            print(f"  WARNING: Could not load {IDENTITY_FILE}: {e}")
            print(f"  Creating a new identity file.")

    # Generate fresh identity
    identity = {
        "worker_id":   str(uuid.uuid4()),
        "name":        worker_name,
        "hostname":    socket.gethostname(),
        "ip":          _get_local_ip(),
        "secret_key":  secrets.token_hex(32),   # never sent to coordinator
        "created_at":  time.strftime("%Y-%m-%d %H:%M:%S"),
        "milestones":  {},
    }
    _save_identity(identity)

    print(f"  NEW IDENTITY created: {IDENTITY_FILE}")
    print(f"  Worker ID : {identity['worker_id']}")
    print(f"  *** BACK UP THIS FILE — it proves milestone crossings ***")
    return identity


def _save_identity(identity):
    """Write identity file atomically and restrict to owner-only (600)."""
    tmp = IDENTITY_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(identity, f, indent=2)
    os.chmod(tmp, 0o600)
    Path(tmp).replace(IDENTITY_FILE)


def save_milestone_claim(identity, milestone_data):
    """
    Save a milestone claim token to the identity file.
    Called when the coordinator reports a milestone crossing.
    """
    name  = milestone_data["milestone"]
    prize = milestone_data.get("prize")

    identity.setdefault("milestones", {})[name] = {
        "claim_token": milestone_data["claim_token"],
        "crossed_at":  milestone_data["crossed_at"],
        "frontier_n":  milestone_data["frontier_n"],
        "prize":       f"${prize:,}" if prize else "none",
    }
    _save_identity(identity)

    prize_str = f" — ${prize:,} prize!" if prize else ""
    print(f"\n  {'!'*60}")
    print(f"  *** MILESTONE CROSSED: {name}{prize_str} ***")
    print(f"  Claim token saved to {IDENTITY_FILE}")
    print(f"  To claim your prize, open a GitHub Issue at:")
    print(f"  https://github.com/huggablehacker/Collatz-Frontier/issues")
    print(f"  and attach your identity file.")
    print(f"  {'!'*60}\n")


# ── Core Collatz (top-level for multiprocessing pickling) ─────────────────────

def _has_gmpy2():
    try:
        import gmpy2
        return True
    except ImportError:
        return False


def process_subchunk(args):
    """
    Process a contiguous block of odd numbers.
    Runs in a subprocess via Pool — re-imports gmpy2 locally.
    Returns (list of fail dicts, count of numbers tested).
    """
    start, end, threshold, max_steps = args

    try:
        import gmpy2
        gmpy2.get_context().precision = 256
        def mpz(n): return gmpy2.mpz(n)
    except ImportError:
        def mpz(n): return n

    thr   = mpz(threshold)
    fails = []
    count = 0
    n     = start

    while n <= end:
        steps   = 0
        max_val = n
        cur     = mpz(n)

        while cur >= thr:
            if steps > max_steps:
                fails.append({"n": n, "steps": steps, "peak": int(max_val)})
                break
            x   = 3 * cur + 1
            k   = (x & -x).bit_length() - 1
            cur = x >> k
            steps += k + 1
            if cur > max_val:
                max_val = cur

        count += 1
        n     += 2  # odd numbers only

    return fails, count


# ── Worker loop ───────────────────────────────────────────────────────────────

def run_worker(coordinator_url, identity, num_cores):
    worker_id   = identity["worker_id"]
    worker_name = identity["name"]

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    if WORKER_TOKEN:
        session.headers["X-Worker-Token"] = WORKER_TOKEN

    total_tested  = 0
    total_fails   = 0
    chunks_done   = 0
    session_start = time.time()

    print(f"  [{worker_name}] Starting with {num_cores} core(s)")

    with Pool(processes=num_cores) as pool:
        while True:
            # 1. Request a chunk — send both UUID and display name
            try:
                resp = session.get(
                    f"{coordinator_url}/chunk",
                    params={
                        "worker":    worker_name,
                        "worker_id": worker_id,
                        "hostname":  identity["hostname"],
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                chunk = resp.json()
            except Exception as e:
                print(f"  [{worker_name}] Chunk request failed: {e} -- retrying in 5s")
                time.sleep(5)
                continue

            chunk_id   = chunk["chunk_id"]
            start      = int(chunk["start"])
            end        = int(chunk["end"])

            # 2. Split into sub-chunks, one per core
            total_odds = (end - start) // 2 + 1
            per_core   = max(1, total_odds // num_cores)

            subchunks = []
            sub_start = start
            for i in range(num_cores):
                sub_end = sub_start + (per_core - 1) * 2
                if i == num_cores - 1:
                    sub_end = end
                subchunks.append((sub_start, sub_end, THRESHOLD, MAX_STEPS))
                sub_start = sub_end + 2
                if sub_start > end:
                    break

            t0 = time.time()

            # 3. Run in parallel
            results = pool.map(process_subchunk, subchunks)

            elapsed   = time.time() - t0
            all_fails = []
            count     = 0
            for fails, c in results:
                all_fails.extend(fails)
                count += c

            # 4. POST results — include worker_id so coordinator can track by UUID
            payload = {
                "chunk_id":    chunk_id,
                "worker":      worker_name,
                "worker_id":   worker_id,
                "fails":       all_fails,
                "count":       count,
                "elapsed_sec": elapsed,
            }
            try:
                resp = session.post(
                    f"{coordinator_url}/results",
                    json=payload,
                    timeout=60,
                )
                resp.raise_for_status()
                result_data = resp.json()

                # 5. Check for milestone notifications in the response
                for ms in result_data.get("milestones_crossed", []):
                    save_milestone_claim(identity, ms)

            except Exception as e:
                print(f"  [{worker_name}] Failed to post results: {e} -- saving locally")
                _save_locally(worker_name, worker_id, chunk_id, all_fails)

            # 6. Stats
            total_tested += count
            total_fails  += len(all_fails)
            chunks_done  += 1
            rate          = count / elapsed if elapsed > 0 else 0
            session_elapsed = time.time() - session_start
            session_rate    = total_tested / session_elapsed if session_elapsed > 0 else 0

            if all_fails:
                print(f"\n  [{worker_name}] *** FAIL(S) in chunk {chunk_id}: "
                      f"{[r['n'] for r in all_fails]} ***\n")

            print(
                f"  [{worker_name}] chunk={chunk_id:>5} | "
                f"{count:,} odd tested | {rate:,.0f}/sec | "
                f"session avg={session_rate:,.0f}/sec | "
                f"fails={total_fails}"
            )


def _save_locally(worker_name, worker_id, chunk_id, fails):
    fname = f"collatz_local_fails_{worker_name}_chunk{chunk_id}.txt"
    with open(fname, "a") as f:
        for r in fails:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"n={r['n']:<30} | FAIL *** POTENTIAL COUNTEREXAMPLE *** | "
                f"steps={r['steps']:<10} | peak={r['peak']} | "
                f"found={ts} | worker_id={worker_id}\n"
            )
    print(f"  [{worker_name}] Saved locally -> {fname}")


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    default_name = socket.gethostname()
    cpu_count    = multiprocessing.cpu_count()
    p = argparse.ArgumentParser(description="Collatz distributed worker")
    p.add_argument("--coordinator", required=True,
                   help="Coordinator URL, e.g. http://192.168.1.100:5555")
    p.add_argument("--name",  default=default_name,
                   help=f"Worker name (default: hostname '{default_name}')")
    p.add_argument("--cores", type=int, default=cpu_count,
                   help=f"CPU cores to use (default: all = {cpu_count})")
    return p.parse_args()


if __name__ == "__main__":
    multiprocessing.freeze_support()

    args = parse_args()
    url  = args.coordinator.rstrip("/")

    print("=" * 65)
    print(" Collatz Distributed Worker -- Optimized + Identified")
    print("=" * 65)

    # Load or create worker identity
    identity = load_or_create_identity(args.name)

    print()
    print(f" Worker name : {args.name}")
    print(f" Worker ID   : {identity['worker_id']}")
    print(f" Hostname    : {identity['hostname']}")
    print(f" IP          : {identity['ip']}")
    print(f" Coordinator : {url}")
    print(f" Cores       : {args.cores}")
    print(f" gmpy2       : {'YES' if _has_gmpy2() else 'NO  (pip install gmpy2 for extra speed)'}")
    print(f" Auth token  : {'ENABLED' if WORKER_TOKEN else 'DISABLED (set COLLATZ_WORKER_TOKEN to enable)'}")
    print(f" Identity    : {IDENTITY_FILE}")
    if identity.get("milestones"):
        print(f" Milestones  : {', '.join(identity['milestones'].keys())}")
    print("=" * 65)
    print()

    # Verify coordinator is reachable
    try:
        r = requests.get(f"{url}/status", timeout=10)
        print(f"  Coordinator reachable")
    except Exception as e:
        print(f"  ERROR: Cannot reach coordinator at {url}")
        print(f"  {e}")
        sys.exit(1)

    print()

    try:
        run_worker(url, identity, args.cores)
    except KeyboardInterrupt:
        print(f"\n  [{args.name}] Stopped.")
        sys.exit(0)
