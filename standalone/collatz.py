"""
Collatz Conjecture Iterator
----------------------------
Iterates all positive integers indefinitely, testing each one against
the Collatz Conjecture (3n+1 problem).

For each number n:
  - If even:  n = n / 2
  - If odd:   n = 3n + 1
  - Repeat until reaching 1 (PASS) or detecting a non-terminating cycle (FAIL)

Output: collatz_results.txt (flat text file, one result per line)

NOTE: No number has ever failed. If one does, it's a mathematical discovery.
      Numbers have been verified up to 2^68 by supercomputers.
"""

import time
import sys

OUTPUT_FILE = "collatz_results.txt"

# Safety cap: max steps before declaring a number "suspicious" (not a true FAIL,
# since no failing number is known — just a guard against runaway loops)
MAX_STEPS = 10_000_000

# How many results to buffer before flushing to disk (for performance)
WRITE_BUFFER_SIZE = 1000

# Print a console summary every N numbers
CONSOLE_REPORT_EVERY = 10_000


def collatz(n):
    """
    Run the Collatz sequence on n.
    Returns (steps, max_value, passed)
      - steps:     number of iterations to reach 1
      - max_value: highest value reached in the sequence
      - passed:    True if reached 1, False if MAX_STEPS exceeded
    """
    steps = 0
    max_val = n
    current = n

    while current != 1:
        if steps > MAX_STEPS:
            return steps, max_val, False  # Suspected non-termination

        if current % 2 == 0:
            current //= 2
        else:
            current = 3 * current + 1

        if current > max_val:
            max_val = current

        steps += 1

    return steps, max_val, True


def format_line(n, steps, max_val, passed):
    status = "PASS" if passed else "FAIL *** POTENTIAL COUNTEREXAMPLE ***"
    return f"n={n:<20} | {status:<40} | steps={steps:<10} | peak={max_val}\n"


def main():
    start_time = time.time()
    buffer = []
    total_tested = 0
    fails = 0

    print("=" * 70)
    print(" Collatz Conjecture Iterator")
    print("=" * 70)
    print(f" Output file : {OUTPUT_FILE}")
    print(f" Max steps   : {MAX_STEPS:,} (per number, before flagging as FAIL)")
    print(f" Buffer size : {WRITE_BUFFER_SIZE:,} lines")
    print(f" Press Ctrl+C to stop at any time.")
    print("=" * 70)
    print()

    with open(OUTPUT_FILE, "w", buffering=1) as f:
        # Write header
        f.write("COLLATZ CONJECTURE RESULTS\n")
        f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Rule: if even -> n/2 | if odd -> 3n+1 | until reaching 1\n")
        f.write(f"PASS = reached 1  |  FAIL = exceeded {MAX_STEPS:,} steps (no known FAIL exists)\n")
        f.write("-" * 90 + "\n")

        n = 1
        try:
            while True:
                steps, max_val, passed = collatz(n)
                total_tested += 1

                if not passed:
                    fails += 1
                    # Write immediately on a potential fail — don't buffer it
                    f.write(format_line(n, steps, max_val, passed))
                    f.flush()
                    print(f"\n!!! POTENTIAL COUNTEREXAMPLE FOUND: n={n} !!!\n")
                else:
                    buffer.append(format_line(n, steps, max_val, passed))

                # Flush buffer to disk periodically
                if len(buffer) >= WRITE_BUFFER_SIZE:
                    f.writelines(buffer)
                    buffer.clear()

                # Console progress report
                if total_tested % CONSOLE_REPORT_EVERY == 0:
                    elapsed = time.time() - start_time
                    rate = total_tested / elapsed if elapsed > 0 else 0
                    eta_to_billion = (1_000_000_000 - total_tested) / rate if rate > 0 else float('inf')
                    print(
                        f"  Tested: {total_tested:>15,} | "
                        f"Current n: {n:>15,} | "
                        f"Rate: {rate:>10,.0f}/sec | "
                        f"Fails: {fails} | "
                        f"Elapsed: {elapsed:,.1f}s"
                    )

                n += 1

        except KeyboardInterrupt:
            # Flush remaining buffer on exit
            if buffer:
                f.writelines(buffer)

            elapsed = time.time() - start_time
            summary = (
                f"\n{'=' * 90}\n"
                f"STOPPED BY USER\n"
                f"Stopped at  : {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Last n tested: {n:,}\n"
                f"Total tested : {total_tested:,}\n"
                f"Total FAILs  : {fails} {'(none — conjecture holds for all tested)' if fails == 0 else '*** CHECK THESE ***'}\n"
                f"Elapsed      : {elapsed:,.2f} seconds\n"
                f"Avg rate     : {total_tested / elapsed:,.0f} numbers/sec\n"
                f"{'=' * 90}\n"
            )
            f.write(summary)
            print("\n" + summary)
            print(f"Results saved to: {OUTPUT_FILE}")
            sys.exit(0)


if __name__ == "__main__":
    main()
