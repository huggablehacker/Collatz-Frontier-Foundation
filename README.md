# Collatz Frontier

[![GitHub](https://img.shields.io/badge/GitHub-huggablehacker%2FCollatz--Frontier-blue?logo=github)](https://github.com/huggablehacker/Collatz-Frontier)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

A distributed, optimized brute-force search for counterexamples to the **Collatz Conjecture**, starting at 2⁶⁸ — the edge of what has previously been verified by supercomputers.

> *"Mathematics is not yet ready for such problems."* — Paul Erdős

See Live Status [HERE](http://collatzfrontier.ddns.net:5555/status)

---

## What is the Collatz Conjecture?

Take any positive integer. If it's even, divide by 2. If it's odd, multiply by 3 and add 1. Repeat. The conjecture states that no matter what number you start with, you will always eventually reach 1.

Simple to state. Unproven for over 80 years.

Every number up to **2⁶⁸ (295,147,905,179,352,825,856)** has been verified. This project starts there and keeps going.

---

## How it works

Three stacked algorithmic optimizations over a naive implementation:

| Optimization | Mechanism | Speedup |
|---|---|---|
| **Early exit** | Stop each sequence the moment it drops below 2⁶⁸ (re-entering verified territory) | ~10× |
| **Odd-only testing** | Even starting numbers immediately halve to their odd counterpart — skip them | 2× |
| **Syracuse steps** | Jump directly from odd → next odd via a single bit-shift, skipping all intermediate even values | ~2× |
| **Combined** | Multiplicative, not additive | **~100×+** |

Work is distributed across any number of machines via a lightweight HTTP coordinator. Workers use Python's `multiprocessing.Pool` for true CPU parallelism (bypasses the GIL). Only **FAIL** entries are ever written to disk — so the output file stays empty as long as the conjecture holds.

---

## Repository structure

```
Collatz-Frontier/
│
├── coordinator/                     ← Run on ONE machine
│   ├── collatz_coordinator.py       ← Main coordinator server
│   ├── collatz_upload_frontier.py   ← Nightly GitHub uploader (8pm EST)
│   └── HOW-TO.md
│
├── worker/                          ← Run on every machine contributing compute
│   ├── collatz_worker.py            ← Distributed worker
│   ├── collatz_merge.py             ← Merge result files from multiple sources
│   └── HOW-TO.md
│
├── standalone/                      ← Single-machine tools, no network needed
│   ├── collatz.py                   ← Basic iterator from n=1
│   ├── collatz_frontier_fast.py     ← Optimized frontier iterator from 2⁶⁸
│   ├── collatz_graph.py             ← Graph results as a chart
│   └── HOW-TO.md
│
├── services/
│   ├── linux/                       ← Headless systemd services (Linux / Mac)
│   │   ├── install_service.sh       ← One-command installer (coordinator + uploader)
│   │   ├── install_worker_service.sh← One-command installer (worker)
│   │   ├── collatz.service          ← Coordinator unit file
│   │   ├── collatz-uploader.service ← Uploader unit file
│   │   ├── collatz-worker.service   ← Worker unit file
│   │   └── HOW-TO.md
│   │
│   └── windows/                     ← Standalone .exe package (no Python needed)
│       ├── build_windows.bat        ← Build all .exe files (run once)
│       ├── launch_coordinator.bat   ← Double-click to start coordinator
│       ├── launch_worker.bat        ← Double-click to start a worker
│       ├── *.spec                   ← PyInstaller build configs
│       ├── README_WINDOWS.txt       ← Windows user guide
│       └── HOW-TO.md
│
└── docs/
    ├── Collatz_HowTo.docx           ← Full how-to guide (Word)
    ├── Collatz_Academic_Paper.docx  ← Peer-review paper (Word)
    ├── collatz_mcom.tex             ← Peer-review paper (AMS MCOM LaTeX)
    └── HOW-TO.md
```

Each folder has its own `HOW-TO.md` covering everything specific to those files.

---

## Quick Start

### 1. Install dependencies

**Coordinator machine:**
```bash
pip install flask waitress      # waitress = production server (recommended)
```

**Each worker machine:**
```bash
pip install requests
```

**Optional — 3–5× faster big integer arithmetic (all machines):**
```bash
pip install gmpy2
```

### 2. Start the coordinator

```bash
cd coordinator/
python3 collatz_coordinator.py
```

If Waitress is installed it is used automatically — you'll see `Server: Waitress (production)` in the banner.

### 3. Start workers

```bash
cd worker/

# All cores (default)
python3 collatz_worker.py --coordinator http://192.168.1.100:5555

# Limit cores, custom name
python3 collatz_worker.py --coordinator http://192.168.1.100:5555 --name gpu-rig-2 --cores 8
```

Workers are stateless — add as many as you want at any time, including while already running.

### 4. Stop and resume

Press `Ctrl+C` to stop cleanly. The coordinator checkpoints automatically. On next start it resumes exactly where it left off:

```bash
python3 collatz_coordinator.py   # detects checkpoint, resumes automatically
```

### 5. Make it headless (survives SSH disconnects + reboots)

```bash
cd services/linux/
bash install_service.sh           # coordinator machine — installs both services
bash install_worker_service.sh    # each worker machine
```

---

## Dashboard

Once the coordinator is running, open a browser to:

| URL | What it shows |
|---|---|
| `/status` | Live stats, frontier position, active workers, QR code to join from a phone |
| `/workers` | Top 50 leaderboard — ranked by numbers tested, with speed and FAIL count |
| `/milestones` | Progress through named number thresholds (Trillion → Centillion) |
| `/join` | Mobile browser worker — scan the QR code on `/status` to contribute from any phone or tablet, no app needed |

All pages auto-refresh every 15 seconds.

---

## Production Server Setup

The coordinator is a web server. For deployments with **10+ workers**, use a production server instead of Flask's built-in dev server.

### Option A — Waitress (recommended for most users)

Pure Python, works on Windows / Linux / Mac. Auto-detected when installed.

```bash
pip install waitress
python3 collatz_coordinator.py   # Waitress used automatically
```

### Option B — Gunicorn (Linux / Mac, highest performance)

```bash
pip install gunicorn
gunicorn -w 1 --threads 32 -b 0.0.0.0:5555 collatz_coordinator:app
```

> **⚠️ Always use `-w 1`.** State lives in memory — multiple processes would each have a separate copy and issue the same chunks twice. Use `--threads` for concurrency instead.

#### Fixing the PATH warning

After `pip install gunicorn` you may see:

```
WARNING: The script gunicorn is installed in '/Users/yourname/Library/Python/3.9/bin'
which is not on PATH.
```

Fix it permanently:

**Mac / Linux — zsh** (default on modern Macs):
```bash
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Mac / Linux — bash:**
```bash
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile
```

**Linux — pip installs to `~/.local/bin`:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Server comparison

| Server | Platforms | Workers | How to use |
|---|---|---|---|
| Waitress | Win / Lin / Mac | Up to ~100 | `pip install waitress`, then run normally |
| Gunicorn | Linux / Mac | 1,000+ | `gunicorn -w 1 --threads 32 -b 0.0.0.0:5555 collatz_coordinator:app` |
| Flask dev | All | Up to ~10 | Automatic fallback. Fine for testing. |

---

## Configuration

### Coordinator (CLI flags — when running directly)

| Flag | Default | Description |
|---|---|---|
| `--start` | `2^68` | First number to test |
| `--chunk` | `500000` | Odd numbers per chunk issued to workers |
| `--port` | `5555` | HTTP port |

### Coordinator (environment variables — when running under Gunicorn)

Gunicorn bypasses the CLI argument parser, so use environment variables instead:

| Variable | Default | Description |
|---|---|---|
| `COLLATZ_START` | `2^68` | First number to test |
| `COLLATZ_CHUNK` | `500000` | Odd numbers per chunk |

```bash
COLLATZ_CHUNK=1000000 gunicorn -w 1 --threads 32 -b 0.0.0.0:5555 collatz_coordinator:app
```

### Worker

| Flag | Default | Description |
|---|---|---|
| `--coordinator` | *(required)* | Coordinator URL, e.g. `http://192.168.1.100:5555` |
| `--name` | hostname | Human-readable name for this worker |
| `--cores` | all CPUs | Number of CPU cores to use |

---

## Output files

| File | Contents |
|---|---|
| `collatz_distributed_fails.txt` | FAIL entries only. Stamped with date, time, and worker. Empty = conjecture held for all tested numbers. |
| `collatz_coordinator_checkpoint.json` | Coordinator state. Written atomically every 50 chunks or immediately on any FAIL. Safe to restart at any point. |
| `collatz_local_fails_*.txt` | Written by workers when coordinator is unreachable. Use `collatz_merge.py` to consolidate. |
| `frontier_log.txt` | Nightly status report uploaded to this repo by `collatz_upload_frontier.py` |

A FAIL entry looks like:
```
n=295147905179352912345    | FAIL *** POTENTIAL COUNTEREXAMPLE *** | steps=10000001 | peak=9999999999 | found=2026-03-21 18:32:30 | worker=rig-2
```

An empty file below the header is the expected result.

---

## Performance

| Setup | Throughput | 1 billion numbers |
|---|---|---|
| 1 machine, 1 core | ~800k odd/sec | ~25 min |
| 1 machine, 8 cores | ~6.4M odd/sec | ~3 min |
| 10 machines × 8 cores | ~64M odd/sec | ~16 sec |
| 100 machines × 8 cores | ~640M odd/sec | ~1.6 sec |
| Phone (mobile browser worker) | ~5,000–20,000 odd/sec | — |

> **Reality check:** Even at 640M/sec across 100 machines, sweeping all of 2⁶⁸ from scratch would take ~974,000 years. The conjecture cannot be proven by brute force — but every new number tested is in genuinely unverified territory.

---

## Architecture

```
┌─────────────────────────────────────┐
│           Coordinator               │
│  Gunicorn / Waitress / Flask        │  ← http://IP:5555
│  -w 1 --threads 32 (single process) │
│                                     │
│  /status  /workers  /milestones     │
│  /join (mobile QR worker)           │
│                                     │
│  - Owns the number line             │
│  - Issues odd-number chunks         │
│  - Checkpoints every 50 chunks      │
│  - Writes FAILs to txt              │
│  - Tracks milestones                │
└──────────────┬──────────────────────┘
               │  GET /chunk  →  {start, end, chunk_id}
               │  POST /results  ←  {fails[], count}
      ┌────────┴────────┬────────────────┐
      │                 │                │
┌─────┴────┐   ┌────────┴────┐   ┌──────┴─────┐
│ Worker 1 │   │  Worker 2   │   │ 📱 Phone   │
│ 8 cores  │   │  8 cores    │   │  Browser   │
│ Pool.map │   │  Pool.map   │   │  BigInt JS │
└──────────┘   └─────────────┘   └────────────┘
```

Each Python worker splits its chunk into sub-chunks, one per CPU core, and runs them in parallel using `multiprocessing.Pool`. No shared state. No GIL contention. Mobile workers run the same Syracuse kernel in JavaScript using `BigInt`, connecting from any browser by scanning the QR code on `/status`.

---

## Milestones

The coordinator tracks when the frontier first crosses each named large number and records which worker pushed it there:

| Milestone | Value | Status |
|---|---|---|
| Trillion | 10¹² | pre-verified |
| Quadrillion | 10¹⁵ | pre-verified |
| Quintillion | 10¹⁸ | pre-verified |
| Sextillion | 10²¹ | 🎯 first target |
| Septillion | 10²⁴ | pending |
| … | … | … |
| Vigintillion | 10⁶³ | pending |
| Centillion | 10³⁰³ | pending |

View the live milestone board at `/milestones`.

---

## Nightly frontier upload

`collatz_upload_frontier.py` uploads a plain-text status report to this repository every night at **8:00 PM EST**, showing the current frontier position, numbers covered, and top contributors. View the latest at [`frontier_log.txt`](frontier_log.txt).

To run it:
```bash
export GITHUB_TOKEN="ghp_your_token_here"   # needs 'repo' scope
python3 coordinator/collatz_upload_frontier.py
```

---

## Headless operation

Both the coordinator and worker die when you close your SSH session unless you run them as services. One-command installers handle everything:

```bash
# On the coordinator machine
bash services/linux/install_service.sh

# On each worker machine
bash services/linux/install_worker_service.sh
```

After installation, both services survive SSH disconnects, restart automatically on crash, and start on every reboot. View logs with `journalctl -u collatz -f`.

---

## Windows

A Windows package is available that requires no Python installation on the target machines — everything is bundled into standalone `.exe` files.

To build the package:
1. Install Python from python.org (check "Add Python to PATH")
2. Copy all `.py` files and the contents of `services/windows/` into one folder
3. Double-click `build_windows.bat`

The result is a `Collatz-Frontier-Windows\` folder ready to zip and share. See `services/windows/HOW-TO.md` for full instructions.

---

## The math behind the optimizations

### Syracuse step (the key insight)

A standard Collatz loop for an odd number `n` produces: `3n+1` (even) → divide repeatedly → next odd number. Instead of iterating those intermediate steps individually:

```python
x = 3 * n + 1                        # guaranteed even
k = (x & -x).bit_length() - 1        # count trailing zeros (halvings needed)
next_odd = x >> k                     # strip all factors of 2 in one shift
steps += k + 1                        # account for all skipped steps
```

This reduces ~550 average iterations (at 2⁶⁸ scale) to ~10, with no loss of fidelity.

### Why odd-only is correct

Any even starting number `n` produces `n/2` as its first step. If `n/2 < 2⁶⁸`, it's already verified. If `n/2 ≥ 2⁶⁸`, we'll test it when we get there. Either way, testing even starting numbers adds no new information.

### Early exit correctness

Everything below 2⁶⁸ is verified to reach 1 by prior work. Dropping below the threshold is logically equivalent to reaching 1 — without the redundant computation.

---

## FAQ

**The output file is empty — did something go wrong?**
No. Empty = the conjecture held for every number tested. This is the expected outcome.

**Which server should I use?**
Waitress for simplicity (auto-detected, works everywhere). Gunicorn for maximum performance on Linux/Mac with many workers. Flask dev server is fine for a handful of workers during testing.

**Why must Gunicorn use `-w 1`?**
The coordinator keeps the entire number line and all progress in memory. Multiple processes each get their own copy and would issue the same chunks to different workers. Use `--threads` for concurrency instead.

**What if the coordinator crashes?**
It checkpoints every 50 completed chunks (and immediately on any FAIL). Restart it and it resumes automatically. In-flight chunks are re-issued after a 10-minute stale timeout.

**Can I contribute from my phone?**
Yes — open `/join` on the coordinator URL in any mobile browser, or scan the QR code on the `/status` page. No app or Python needed. The full Syracuse kernel runs in JavaScript using `BigInt`.

**What does a FAIL actually mean?**
A sequence ran for more than 10,000,000 compressed Syracuse steps without re-entering verified territory. It doesn't definitively prove a counterexample — it's a strong signal requiring manual investigation. No FAIL has ever been found.

**Will this ever prove the conjecture?**
No. Brute force cannot prove a statement about all integers. A mathematical proof requires a fundamentally different approach.

---

## Contributing

Pull requests welcome. Some useful directions:

- **C extension** for the inner loop — a C extension for the Syracuse step would give another 10–50× speedup
- **CUDA/GPU worker** — the inner loop is embarrassingly parallel at the per-number level
- **Adaptive chunk sizing** — tune chunk size based on observed worker throughput
- **launchd plist** — macOS equivalent of the Linux systemd service files

To contribute compute right now, scan the QR code on the `/status` page or clone the repo and run a worker.

---

## Academic paper

A peer-review ready paper covering the formal proofs, algorithm design, distributed architecture, and experimental results is in [`docs/`](docs/). It is formatted for submission to *Mathematics of Computation* (AMS) using the official `mcom-l` LaTeX class.

---

## License

MIT License. See [LICENSE](https://github.com/huggablehacker/Collatz-Frontier/blob/main/LICENSE) for details.

---

## References

- Collatz, L. (1937). Original conjecture
- Oliveira e Silva, T. (2010). Empirical verification up to 2⁶⁸
- Tao, T. (2022). ["Almost all Collatz orbits attain almost bounded values"](https://arxiv.org/abs/1909.03562) — the closest anyone has come to a proof
- Lagarias, J. C. (2010). *The Ultimate Challenge: The 3x+1 Problem*. AMS.
