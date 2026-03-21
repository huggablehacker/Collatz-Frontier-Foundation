"""
Collatz Results Merger
-----------------------
Combines the coordinator's FAILs file with any locally-saved worker fail files
into a single sorted report. Useful when a worker couldn't reach the coordinator
and saved results locally.

Usage:
    python3 collatz_merge.py
    python3 collatz_merge.py --main collatz_distributed_fails.txt --out merged_fails.txt
"""

import argparse
import re
import time
from pathlib import Path

FAIL_RE = re.compile(
    r"n=\s*(\d+)\s*\|.*?FAIL.*?\|\s*steps=\s*(\d+)\s*\|\s*peak=(\d+)"
)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--main", default="collatz_distributed_fails.txt",
                   help="Primary coordinator results file")
    p.add_argument("--out",  default="collatz_merged_fails.txt",
                   help="Output file")
    return p.parse_args()


def parse_file(path):
    records = []
    try:
        with open(path) as f:
            for line in f:
                m = FAIL_RE.search(line)
                if m:
                    records.append({
                        "n":     int(m.group(1)),
                        "steps": int(m.group(2)),
                        "peak":  int(m.group(3)),
                        "raw":   line.rstrip(),
                    })
    except FileNotFoundError:
        pass
    return records


def main():
    args  = parse_args()
    t0    = time.time()
    files = [Path(args.main)] + sorted(Path(".").glob("collatz_local_fails_*.txt"))

    print("=" * 60)
    print(" Collatz Results Merger")
    print("=" * 60)
    print(f" Scanning: {[str(f) for f in files if f.exists()]}")

    records = []
    for f in files:
        batch = parse_file(f)
        if batch:
            print(f"  {f.name}: {len(batch)} FAILs")
        records.extend(batch)

    records.sort(key=lambda r: r["n"])
    records = list({r["n"]: r for r in records}.values())  # deduplicate by n

    with open(args.out, "w") as f:
        f.write("COLLATZ CONJECTURE -- MERGED FAIL REPORT\n")
        f.write(f"Generated : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Sources   : {len(files)} file(s)\n")
        f.write(f"Total FAILs: {len(records)}\n")
        f.write("-" * 100 + "\n")
        for r in records:
            f.write(r["raw"] + "\n")

    elapsed = time.time() - t0
    print(f"\n  Total unique FAILs : {len(records)}")
    if len(records) == 0:
        print(f"  Conjecture held for all tested numbers.")
    else:
        print(f"  *** {len(records)} POTENTIAL COUNTEREXAMPLE(S) — CHECK {args.out} ***")
    print(f"  Written -> {args.out}  ({elapsed:.2f}s)")
    print("=" * 60)


if __name__ == "__main__":
    main()
