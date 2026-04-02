# Worker — How-To Guide

Run this on **every machine** that contributes compute. Workers are stateless — they pull chunks, crunch numbers, and post results. You can start and stop them at any time without losing progress.

---

## Files in this folder

| File | Purpose |
|---|---|
| `collatz_worker.py` | Distributed worker — connects to coordinator and processes chunks |
| `collatz_merge.py` | Merges result files when workers saved locally instead of posting |

---

## collatz_worker.py

### Requirements
```bash
pip install requests
```

Optional but recommended — gives 3–5× faster arithmetic on 70-digit numbers at 2⁶⁸:
```bash
pip install gmpy2
```

### Run it
```bash
python3 collatz_worker.py --coordinator http://192.168.1.100:5555
```

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--coordinator` | *(required)* | Coordinator URL |
| `--name` | hostname | Name shown in the leaderboard |
| `--cores` | all CPUs | CPU cores to use on this machine |

### Examples

```bash
# Use all cores, auto-name from hostname
python3 collatz_worker.py --coordinator http://192.168.1.100:5555

# Limit to 4 cores, custom name
python3 collatz_worker.py --coordinator http://192.168.1.100:5555 --name office-pc --cores 4

# Run on the same machine as the coordinator
python3 collatz_worker.py --coordinator http://localhost:5555
```

### Multiple workers on one machine

Open separate terminals (or run as separate services — see `../services/linux/HOW-TO.md`):

```bash
python3 collatz_worker.py --coordinator http://localhost:5555 --name rig-a --cores 8
python3 collatz_worker.py --coordinator http://localhost:5555 --name rig-b --cores 8
```

### How it works

Each worker:
1. Requests a chunk of 500,000 odd numbers from the coordinator
2. Splits the chunk across all available CPU cores using `multiprocessing.Pool`
3. Runs the optimized Syracuse kernel on each starting number:
   - **Early exit** — stops when the sequence drops below 2⁶⁸ (already verified territory)
   - **Odd-only** — even starting numbers are skipped (covered by Theorem 3.2)
   - **Syracuse steps** — each iteration jumps to the next odd number directly via bit-shift
4. Posts any FAILs back to the coordinator (the results file stays empty if none are found)
5. Immediately requests the next chunk

### What a FAIL means

A FAIL means a sequence ran for more than 10,000,000 compressed Syracuse steps without dropping below 2⁶⁸. It does **not** prove a counterexample — it flags the number for investigation. No FAIL has ever been found.

### If the coordinator is unreachable

The worker retries every 5 seconds. If it still can't connect, it saves results locally to `collatz_local_fails_<name>_chunk<N>.txt`. Use `collatz_merge.py` to consolidate these later.

### Performance expectations

| Hardware | Approx throughput |
|---|---|
| Single core (laptop) | ~800,000 odd/sec |
| 8-core desktop | ~6.4M odd/sec |
| 16-core workstation | ~12.8M odd/sec |
| With gmpy2 | +30–50% on top of above |

---

## collatz_merge.py

Combines the coordinator's results file with any locally-saved worker files into one sorted report. Useful when workers couldn't reach the coordinator and saved files locally.

### Run it
```bash
# Default: merges collatz_distributed_fails.txt + any collatz_local_fails_*.txt files
python3 collatz_merge.py

# Custom file locations
python3 collatz_merge.py --main collatz_distributed_fails.txt --out merged_fails.txt
```

The merger deduplicates by `n`, sorts numerically, and writes a timestamped combined report.

---

## Making the worker headless

See `../services/linux/HOW-TO.md` for turning the worker into a systemd service that survives SSH disconnects and reboots.
