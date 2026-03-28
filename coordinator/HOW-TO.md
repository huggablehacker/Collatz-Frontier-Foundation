# Coordinator — How-To Guide

Run **one instance** of this on one machine. It owns the number line, hands out work to workers, collects results, and hosts the dashboard.

---

## Files in this folder

| File | Purpose |
|---|---|
| `collatz_coordinator.py` | The coordinator server |
| `collatz_upload_frontier.py` | Uploads nightly frontier status to GitHub |

---

## collatz_coordinator.py

### Requirements
```bash
pip install flask waitress
```
`waitress` is optional but strongly recommended for any serious deployment — it replaces Flask's dev server with a production-grade server automatically.

### Run it
```bash
python3 collatz_coordinator.py
```

### Production (many workers — recommended)
```bash
pip install gunicorn
gunicorn -w 1 --threads 32 -b 0.0.0.0:5555 collatz_coordinator:app
```

> **Always use `-w 1`.** State lives in memory — multiple processes would each have a separate copy and issue the same chunks twice.

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--start` | `2^68` | First number to test |
| `--chunk` | `500000` | Odd numbers per chunk per worker |
| `--port` | `5555` | HTTP port |

### Environment variables (for Gunicorn — bypasses CLI)

| Variable | Default | Description |
|---|---|---|
| `COLLATZ_START` | `2^68` | First number to test |
| `COLLATZ_CHUNK` | `500000` | Odd numbers per chunk |

```bash
COLLATZ_CHUNK=1000000 gunicorn -w 1 --threads 32 -b 0.0.0.0:5555 collatz_coordinator:app
```

### Dashboard endpoints

| URL | Description |
|---|---|
| `/status` | Live stats, frontier position, active workers, QR code |
| `/workers` | Top 50 workers leaderboard (auto-refreshes every 15s) |
| `/milestones` | Named milestone crossings (Trillion → Centillion) |
| `/join` | Mobile browser worker — scan QR to contribute from a phone |
| `/chunk` | (used by workers) — GET next chunk |
| `/results` | (used by workers) — POST completed results |

### Output files

| File | Contents |
|---|---|
| `collatz_distributed_fails.txt` | FAILs only. Empty = conjecture held for all tested numbers |
| `collatz_coordinator_checkpoint.json` | Progress checkpoint, saved every 50 chunks or on any FAIL |

### Checkpointing and resume

The coordinator checkpoints after every 50 completed chunks (and immediately on any FAIL). To resume after a restart, just run the same command — it detects the checkpoint automatically:

```bash
python3 collatz_coordinator.py   # prints "RESUMED from n=..."
```

### Scaling notes

| Workers | Recommended server | Threads |
|---|---|---|
| 1–50 | Waitress (auto-detected) | 32 |
| 50–200 | Gunicorn | 32 |
| 200–1000+ | Gunicorn | 32 |

Checkpoint frequency is already tuned (every 50 chunks) to reduce lock contention under high worker load.

---

## collatz_upload_frontier.py

Reads the coordinator's checkpoint file and uploads a status report to your GitHub repo every night at **8:00 PM EST**.

### Requirements

No extra packages — uses only Python's standard library.

### Setup — get a GitHub token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name it `collatz-frontier-uploader`, check the **`repo`** scope
4. Copy the token (starts with `ghp_`)

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

### Run modes

**Scheduler** (runs forever, fires at 8pm EST nightly):
```bash
python3 collatz_upload_frontier.py
```

**One-shot** (upload right now and exit):
```bash
python3 collatz_upload_frontier.py --now
```

**Cron** (alternative to the built-in scheduler):
```bash
# Add to crontab: 8pm EST = 01:00 UTC
0 1 * * * GITHUB_TOKEN=ghp_... python3 /path/to/collatz_upload_frontier.py --now
```

### What gets uploaded

A plain text file `frontier_log.txt` in your repo showing:
- Current frontier `n` and offset from 2⁶⁸
- Numbers covered and chunks completed
- FAIL count
- Top 10 workers by contribution

View it at: `https://github.com/huggablehacker/Collatz-Frontier/blob/main/frontier_log.txt`

### PATH note (macOS/Linux)

If you see a warning that `ghp_...` is not a recognized command, you need to export the token as an environment variable rather than passing it inline:

```bash
export GITHUB_TOKEN="ghp_your_token_here"
python3 collatz_upload_frontier.py
```

---

## Making the coordinator headless

See `../services/linux/HOW-TO.md` for turning both scripts into systemd services that survive SSH disconnects and reboots.
