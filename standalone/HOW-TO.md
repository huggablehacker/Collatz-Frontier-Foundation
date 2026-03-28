# Standalone Tools — How-To Guide

These tools run on a **single machine with no network**. Use them to explore the conjecture locally, test the math, or graph results.

---

## Files in this folder

| File | Purpose |
|---|---|
| `collatz.py` | Basic iterator — tests every integer from 1 upward, writes all results |
| `collatz_frontier_fast.py` | Optimized iterator — starts at 2⁶⁸, FAILs only, checkpointed |
| `collatz_graph.py` | Reads a results file and produces a multi-panel chart |

---

## collatz.py

The original brute-force iterator. Tests every positive integer starting from 1 and writes the result (PASS or FAIL, steps, peak value) to a flat text file.

### Run it
```bash
python3 collatz.py
```

Press `Ctrl+C` to stop cleanly. Progress is **not** checkpointed — it always starts from 1.

### Output

`collatz_results.txt` — one line per number:
```
n=27                 | PASS    | steps=111        | peak=9232
```

### Performance

~36,000 numbers/sec on small integers. Slows as numbers grow larger. Use `collatz_frontier_fast.py` for anything near 2⁶⁸.

### Notes

- This writes **every** result — the file grows quickly (roughly 100 MB per million numbers)
- No number has ever failed
- Mathematicians have already verified up to 2⁶⁸ by supercomputer — this tool won't reach new territory for a very long time

---

## collatz_frontier_fast.py

The production-grade single-machine version. Starts exactly at 2⁶⁸, uses all four optimizations, writes **FAILs only**, and checkpoints automatically.

### Optimizations applied

| Optimization | Speedup | How |
|---|---|---|
| Early exit at 2⁶⁸ | ~10× | Stop when sequence drops into verified territory |
| Odd numbers only | 2× | Even starting numbers are redundant (proven) |
| Syracuse steps | ~2× | Jump directly odd→odd via bit-shift |
| All combined | **~113×** | Multiplicative |

### Run it
```bash
python3 collatz_frontier_fast.py
```

### Optional: faster arithmetic

```bash
pip install gmpy2   # uses GMP — 3-5× faster on 70-digit numbers
```

The script detects `gmpy2` automatically. Falls back to Python's built-in integers if not available.

### Output

`collatz_frontier_fails.txt` — FAILs only. This file will be empty below the header as long as the conjecture holds (which it always has):

```
COLLATZ CONJECTURE — POTENTIAL COUNTEREXAMPLES
Started : 2026-03-21 18:32:30
Start n : 2^68 = 295147905179352825856  (odd numbers only)
An empty file below this line means the conjecture held for all tested numbers.
----------------------------------------------------------------------------------------------------
```

`collatz_frontier_checkpoint.json` — progress checkpoint. On restart, the script reads this and continues from the last tested number automatically.

### Performance

~800,000 odd/sec (single core, no gmpy2) at 2⁶⁸ scale — about **113× faster** than a naive implementation.

### Checkpoint / resume

Checkpoint is saved every 100,000 numbers and on Ctrl+C. To resume:

```bash
python3 collatz_frontier_fast.py   # detects checkpoint, prints resume message
```

To start fresh, delete `collatz_frontier_checkpoint.json`.

---

## collatz_graph.py

Reads a results file (from `collatz.py` or `collatz_merge.py`) and produces a three-panel PNG chart:

1. **Steps to reach 1** — per starting integer
2. **Peak value reached** — per starting integer
3. **Distribution of step counts** — histogram

### Requirements
```bash
pip install matplotlib
```

### Run it
```bash
# Default: reads collatz_results.txt, writes collatz_graph.png
python3 collatz_graph.py

# Custom file
python3 collatz_graph.py --file my_results.txt --out my_chart.png

# Apply rolling average to smooth the noise
python3 collatz_graph.py --smooth 200

# Only graph the first 10,000 numbers
python3 collatz_graph.py --max 10000
```

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--file` | `collatz_results.txt` | Input file |
| `--out` | `collatz_graph.png` | Output image |
| `--smooth` | `0` (off) | Rolling average window size |
| `--max` | all | Maximum numbers to graph |

### Notes

- The graph uses `collatz_results.txt` format (all results, not FAILs-only)
- For graphing distributed results, run `collatz_merge.py` first then point `--file` at the merged output
- At large scales (millions of numbers), use `--smooth 200` or higher to see the trend through the noise

---

## Which tool should I use?

| Goal | Tool |
|---|---|
| Explore the conjecture, understand the data | `collatz.py` + `collatz_graph.py` |
| Push the verified frontier on one machine | `collatz_frontier_fast.py` |
| Push the frontier across many machines | `../coordinator/` + `../worker/` |
| Graph distributed results | `collatz_graph.py --file ../worker/merged_fails.txt` |
