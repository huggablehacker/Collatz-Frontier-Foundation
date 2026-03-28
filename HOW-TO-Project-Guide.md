# Collatz Frontier — Project Guide

**Repository:** https://github.com/huggablehacker/Collatz-Frontier

A distributed, optimized system for verifying the Collatz Conjecture beyond 2⁶⁸ — the furthest point ever verified by prior computational work.

---

## Folder Structure

```
Collatz-Frontier/
│
├── README.md                        ← GitHub front page (this project's public face)
│
├── coordinator/                     ← Run on ONE machine — the hub of the network
│   ├── collatz_coordinator.py       ← Main coordinator server
│   ├── collatz_upload_frontier.py   ← Nightly GitHub uploader
│   └── HOW-TO.md
│
├── worker/                          ← Run on every machine contributing compute
│   ├── collatz_worker.py            ← Distributed worker
│   ├── collatz_merge.py             ← Merge result files from multiple sources
│   └── HOW-TO.md
│
├── standalone/                      ← Single-machine tools (no network needed)
│   ├── collatz.py                   ← Basic iterator from n=1
│   ├── collatz_frontier_fast.py     ← Optimized frontier iterator from 2^68
│   ├── collatz_graph.py             ← Graph results as a chart
│   └── HOW-TO.md
│
├── services/                        ← Make everything headless and auto-restart
│   ├── linux/                       ← systemd services (Linux / Mac with systemd)
│   │   ├── collatz.service          ← Coordinator service unit
│   │   ├── collatz-uploader.service ← Uploader service unit
│   │   ├── collatz-worker.service   ← Worker service unit (template)
│   │   ├── install_service.sh       ← One-command installer (coordinator + uploader)
│   │   ├── install_worker_service.sh← One-command installer (worker, multi-machine)
│   │   └── HOW-TO.md
│   │
│   └── windows/                     ← Standalone .exe package for Windows
│       ├── build_windows.bat        ← Build the .exe files (run once)
│       ├── coordinator.spec         ← PyInstaller spec for coordinator.exe
│       ├── worker.spec              ← PyInstaller spec for worker.exe
│       ├── uploader.spec            ← PyInstaller spec for uploader.exe
│       ├── launch_coordinator.bat   ← Double-click launcher (coordinator)
│       ├── launch_worker.bat        ← Double-click launcher (worker)
│       ├── README_WINDOWS.txt       ← Windows user guide
│       └── HOW-TO.md
│
└── docs/                            ← Documentation and academic paper
    ├── Collatz_HowTo.docx           ← Full how-to guide (Word document)
    ├── Collatz_Academic_Paper.docx  ← Peer-review paper (Word format)
    ├── collatz_mcom.tex             ← Peer-review paper (AMS MCOM LaTeX format)
    └── HOW-TO.md
```

---

## Quick Start (3 minutes)

### Step 1 — Install dependencies on the coordinator machine
```bash
pip install flask waitress requests
```

### Step 2 — Start the coordinator
```bash
cd coordinator/
python3 collatz_coordinator.py
```

Open the dashboard: `http://YOUR_IP:5555/status`

### Step 3 — Start workers on every other machine
```bash
cd worker/
python3 collatz_worker.py --coordinator http://YOUR_IP:5555
```

### Step 4 — Make it headless (survives SSH disconnect + reboots)
```bash
cd services/linux/
bash install_service.sh          # coordinator machine
bash install_worker_service.sh   # each worker machine
```

---

## Dashboard URLs (once coordinator is running)

| URL | What it shows |
|---|---|
| `/status` | Live coordinator stats, frontier position, QR code |
| `/workers` | Top 50 workers leaderboard |
| `/milestones` | Named number crossings (Trillion → Centillion) |
| `/join` | Mobile browser worker — scan QR code to contribute from a phone |

---

## What is the Collatz Conjecture?

Take any positive integer. If even divide by 2, if odd multiply by 3 and add 1. Repeat. The conjecture says you always reach 1. It has been verified for every number up to 2⁶⁸ (295 quintillion). This project verifies numbers beyond that frontier.

No counterexample has ever been found. If this system finds one, it would be one of the most significant mathematical discoveries in decades.

---

## Performance at a glance

| Setup | Throughput |
|---|---|
| 1 machine, 1 core | ~800,000 odd/sec |
| 1 machine, 8 cores | ~6.4M odd/sec |
| 10 machines × 8 cores | ~64M odd/sec |
| 100 machines × 8 cores | ~640M odd/sec |
| Phone (mobile worker) | ~5,000–20,000 odd/sec |
