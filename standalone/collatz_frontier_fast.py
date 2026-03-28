"""
Collatz Frontier — Optimized (FAILs only, with checkpointing)
---------------------------------------------------------------
Resumes automatically from the last tested number if restarted.
Only writes FAIL entries to the results file.

  OPT 1 — Early exit at 2^68 threshold
  OPT 2 — Odd starting numbers only
  OPT 3 — Syracuse compressed steps
  OPT 4 — gmpy2 fast big integers (auto-detected, pip install gmpy2)
"""

import time
import sys
import json
from pathlib import Path

try:
    import gmpy2
    gmpy2.get_context().precision = 256
    def mpz(n): return gmpy2.mpz(n)
    HAS_GMPY2 = True
except ImportError:
    def mpz(n): return n
    HAS_GMPY2 = False

START_N        = 2 ** 68
THRESHOLD      = START_N
OUTPUT_FILE    = "collatz_frontier_fails.txt"
CHECKPOINT_FILE= "collatz_frontier_checkpoint.json"
MAX_STEPS      = 10_000_000
REPORT_EVERY   = 10_000
CHECKPOINT_EVERY = 100_000   # save checkpoint every N tested numbers


# ── Checkpoint ────────────────────────────────────────────────────────────────

def save_checkpoint(n, tested, fails):
    data = {
        "n":          n,
        "tested":     tested,
        "fails":      fails,
        "saved_at":   time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    tmp = CHECKPOINT_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    Path(tmp).replace(CHECKPOINT_FILE)   # atomic replace — never corrupts


def load_checkpoint():
    p = Path(CHECKPOINT_FILE)
    if not p.exists():
        return None
    try:
        with open(p) as f:
            data = json.load(f)
        # n must be odd and >= START_N
        n = int(data["n"])
        if n < START_N or n % 2 == 0:
            return None
        return data
    except Exception:
        return None


# ── Core ──────────────────────────────────────────────────────────────────────

def collatz_fast(n, threshold):
    steps, max_val, cur = 0, n, mpz(n)
    thr = mpz(threshold)
    while cur >= thr:
        if steps > MAX_STEPS:
            return steps, int(max_val), False
        x   = 3 * cur + 1
        k   = (x & -x).bit_length() - 1
        cur = x >> k
        steps += k + 1
        if cur > max_val:
            max_val = cur
    return steps, int(max_val), True


def fmt_fail(n, steps, peak):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"n={n:<30} | FAIL *** POTENTIAL COUNTEREXAMPLE *** | "
        f"steps={steps:<10} | peak={peak} | found={ts}\n"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()

    # ── Resume or fresh start ─────────────────────────────────────────────────
    checkpoint = load_checkpoint()
    if checkpoint:
        n      = int(checkpoint["n"])
        tested = int(checkpoint["tested"])
        fails  = int(checkpoint["fails"])
        resume = True
    else:
        n      = START_N if START_N % 2 == 1 else START_N + 1
        tested = 0
        fails  = 0
        resume = False

    print("=" * 72)
    print(" Collatz Frontier — Optimized  (FAILs only)")
    print("=" * 72)
    if resume:
        print(f" RESUMING from checkpoint:")
        print(f"   Last n   : {int(checkpoint['n']):,}")
        print(f"   Tested   : {tested:,}")
        print(f"   Saved at : {checkpoint['saved_at']}")
    else:
        print(f" Fresh start at : {n:,}  (first odd >= 2^68)")
    print(f" gmpy2       : {'YES' if HAS_GMPY2 else 'NO  (pip install gmpy2 for extra speed)'}")
    print(f" Output file : {OUTPUT_FILE}  (stays empty if conjecture holds)")
    print(f" Checkpoint  : {CHECKPOINT_FILE}  (every {CHECKPOINT_EVERY:,} numbers)")
    print(f" Press Ctrl+C to stop safely.")
    print("=" * 72)
    print()

    # Open results file in append mode so previous FAILs are preserved on resume
    file_mode = "a" if resume else "w"
    with open(OUTPUT_FILE, file_mode, buffering=1) as f:

        if not resume:
            f.write("COLLATZ CONJECTURE — POTENTIAL COUNTEREXAMPLES\n")
            f.write(f"Started : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Start n : 2^68 = {START_N}  (odd numbers only)\n")
            f.write(f"gmpy2   : {'yes' if HAS_GMPY2 else 'no'}\n")
            f.write(f"FAIL    : sequence exceeded {MAX_STEPS:,} steps without dropping below 2^68\n")
            f.write(f"An empty file below this line means the conjecture held for all tested numbers.\n")
            f.write("-" * 100 + "\n")
        else:
            f.write(f"\n--- Resumed at {time.strftime('%Y-%m-%d %H:%M:%S')}  (n={n:,}, previously tested={tested:,}) ---\n")

        try:
            while True:
                steps, peak, passed = collatz_fast(n, THRESHOLD)
                tested += 1

                if not passed:
                    fails += 1
                    f.write(fmt_fail(n, steps, peak))
                    f.flush()
                    print(f"\n{'!'*70}\n  POTENTIAL COUNTEREXAMPLE: n={n}\n{'!'*70}\n")

                n += 2  # odd numbers only

                if tested % CHECKPOINT_EVERY == 0:
                    save_checkpoint(n, tested, fails)

                if tested % REPORT_EVERY == 0:
                    elapsed = time.time() - t0
                    rate    = tested / elapsed if elapsed > 0 else 0
                    print(
                        f"  Tested: {tested:>12,} | "
                        f"n: {n} | "
                        f"Rate: {rate:>8,.0f} odd/sec | "
                        f"Coverage: {rate*2:>10,.0f} n/sec | "
                        f"Fails: {fails}"
                    )

        except KeyboardInterrupt:
            save_checkpoint(n, tested, fails)
            elapsed = time.time() - t0
            rate    = tested / elapsed if elapsed > 0 else 0
            summary = (
                f"\n{'=' * 100}\n"
                f"STOPPED BY USER\n"
                f"Stopped at     : {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Last n tested  : {n:,}\n"
                f"Offset         : 2^68 + {n - START_N:,}\n"
                f"Total tested   : {tested:,}  (odd numbers only)\n"
                f"Numbers covered: ~{tested * 2:,}  (odd + their even partners)\n"
                f"FAILs          : {fails}  {'(none — conjecture holds for all tested)' if fails == 0 else '*** CHECK THE FILE ***'}\n"
                f"Elapsed        : {elapsed:,.2f}s\n"
                f"Rate           : {rate:,.0f} odd/sec  (~{rate*2:,.0f} effective n/sec)\n"
                f"Checkpoint     : saved to {CHECKPOINT_FILE}\n"
                f"{'=' * 100}\n"
            )
            f.write(summary)
            print("\n" + summary)
            print(f"Results  : {OUTPUT_FILE}")
            print(f"Checkpoint saved — next run will resume from n={n:,}")
            sys.exit(0)


if __name__ == "__main__":
    main()
