"""
Collatz Distributed Worker  —  Optimized
-----------------------------------------
Connects to the coordinator, pulls chunks, and processes them using:

  - Syracuse compressed steps  (odd -> next odd in one operation)
  - Odd-only testing           (even starting numbers are redundant)
  - Early exit at 2^68         (stop when sequence re-enters verified territory)
  - multiprocessing.Pool       (true CPU parallelism, bypasses Python GIL)
  - gmpy2 fast big integers    (optional, pip install gmpy2)

The --cores flag controls how many CPU cores to use per machine.
Each core processes its own sub-chunk independently — no shared state,
no GIL contention.

Usage:
    pip install requests
    python3 collatz_worker.py --coordinator http://192.168.1.100:5555

    python3 collatz_worker.py --coordinator http://192.168.1.100:5555 --name rig-2 --cores 8
"""

import argparse
import os
import socket
import sys
import time

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

# multiprocessing must be imported at top level for pool workers to pickle correctly
import multiprocessing
from multiprocessing import Pool

DEFAULT_PORT = 5555
MAX_STEPS    = 10_000_000
THRESHOLD    = 2 ** 68


# ── Core Collatz (runs inside worker processes — must be top-level for pickling) ──

def _has_gmpy2():
    try:
        import gmpy2
        return True
    except ImportError:
        return False


def process_subchunk(args):
    """
    Process a contiguous block of odd numbers.
    This function runs in a subprocess (via Pool), so it re-imports gmpy2 locally.
    Returns list of fail dicts and count of numbers tested.
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

def run_worker(coordinator_url, worker_id, num_cores):
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    total_tested  = 0
    total_fails   = 0
    chunks_done   = 0
    session_start = time.time()

    print(f"  [{worker_id}] Starting with {num_cores} core(s)")

    with Pool(processes=num_cores) as pool:
        while True:
            # 1. Request a chunk from coordinator
            try:
                resp = session.get(
                    f"{coordinator_url}/chunk",
                    params={"worker": worker_id},
                    timeout=30,
                )
                resp.raise_for_status()
                chunk = resp.json()
            except Exception as e:
                print(f"  [{worker_id}] Chunk request failed: {e} -- retrying in 5s")
                time.sleep(5)
                continue

            chunk_id   = chunk["chunk_id"]
            start      = int(chunk["start"])
            end        = int(chunk["end"])
            chunk_size = chunk["chunk_size"]

            # 2. Split chunk into sub-chunks, one per core
            #    Each sub-chunk is a contiguous range of odd numbers
            total_odds = (end - start) // 2 + 1
            per_core   = max(1, total_odds // num_cores)

            subchunks = []
            sub_start = start
            for i in range(num_cores):
                sub_end = sub_start + (per_core - 1) * 2
                if i == num_cores - 1:
                    sub_end = end   # last core takes the remainder
                subchunks.append((sub_start, sub_end, THRESHOLD, MAX_STEPS))
                sub_start = sub_end + 2
                if sub_start > end:
                    break

            t0 = time.time()

            # 3. Run all sub-chunks in parallel across cores
            results = pool.map(process_subchunk, subchunks)

            elapsed = time.time() - t0
            all_fails = []
            count     = 0
            for fails, c in results:
                all_fails.extend(fails)
                count += c

            # 4. POST results back (FAILs only + count for stats)
            payload = {
                "chunk_id":    chunk_id,
                "worker":      worker_id,
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
            except Exception as e:
                print(f"  [{worker_id}] Failed to post results: {e} -- saving locally")
                _save_locally(worker_id, chunk_id, all_fails)

            # 5. Stats
            total_tested += count
            total_fails  += len(all_fails)
            chunks_done  += 1
            rate = count / elapsed if elapsed > 0 else 0
            session_elapsed = time.time() - session_start
            session_rate    = total_tested / session_elapsed if session_elapsed > 0 else 0

            if all_fails:
                print(f"\n  [{worker_id}] *** FAIL(S) in chunk {chunk_id}: {[r['n'] for r in all_fails]} ***\n")

            print(
                f"  [{worker_id}] chunk={chunk_id:>5} | "
                f"{count:,} odd tested | {rate:,.0f}/sec | "
                f"session avg={session_rate:,.0f}/sec | "
                f"fails={total_fails}"
            )


def _save_locally(worker_id, chunk_id, fails):
    fname = f"collatz_local_fails_{worker_id}_chunk{chunk_id}.txt"
    with open(fname, "a") as f:
        for r in fails:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"n={r['n']:<30} | FAIL *** POTENTIAL COUNTEREXAMPLE *** | "
                f"steps={r['steps']:<10} | peak={r['peak']} | found={ts}\n"
            )
    print(f"  [{worker_id}] Saved locally -> {fname}")


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
    # Required on Windows and some Linux setups for multiprocessing
    multiprocessing.freeze_support()

    args = parse_args()
    url  = args.coordinator.rstrip("/")

    print("=" * 65)
    print(" Collatz Distributed Worker -- Optimized")
    print("=" * 65)
    print(f" Worker name : {args.name}")
    print(f" Coordinator : {url}")
    print(f" Cores       : {args.cores}")
    print(f" gmpy2       : {'YES' if _has_gmpy2() else 'NO  (pip install gmpy2 for extra speed)'}")
    print(f" Opts        : Syracuse steps + odd-only + early-exit at 2^68")
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
        run_worker(url, args.name, args.cores)
    except KeyboardInterrupt:
        print(f"\n  [{args.name}] Stopped.")
        sys.exit(0)
