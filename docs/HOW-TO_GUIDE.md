# Collatz Frontier — How-To Guide

**Repository:** https://github.com/huggablehacker/Collatz-Frontier

---

## Table of Contents

1. [First-Time Setup](#1-first-time-setup)
2. [Running the Coordinator](#2-running-the-coordinator)
3. [Running Workers](#3-running-workers)
4. [Making It Headless (Services)](#4-making-it-headless-services)
5. [Contributing from a Phone](#5-contributing-from-a-phone)
6. [Monitoring and Dashboards](#6-monitoring-and-dashboards)
7. [Prize Claims and Milestone Verification](#7-prize-claims-and-milestone-verification)
8. [Nightly GitHub Uploads](#8-nightly-github-uploads)
9. [Checkpoint Management and Recovery](#9-checkpoint-management-and-recovery)
10. [Cleaning Up Workers](#10-cleaning-up-workers)
11. [Windows](#11-windows)
12. [Standalone Single-Machine Mode](#12-standalone-single-machine-mode)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. First-Time Setup

### Requirements

| Role | Python | Packages |
|---|---|---|
| Coordinator | 3.8+ | `flask waitress` |
| Worker | 3.8+ | `requests` |
| Optional | any | `gmpy2` (3–5× faster arithmetic) |
| Optional | any | `gunicorn` (best performance with 50+ workers) |

```bash
# Coordinator machine
pip install flask waitress

# Each worker machine
pip install requests

# Optional speedup (all machines)
pip install gmpy2

# Optional production server (coordinator, Linux/Mac)
pip install gunicorn
```

### Getting your IP address

Workers need to know the coordinator's IP. On the coordinator machine:

**Linux/Mac:**
```bash
hostname -I | awk '{print $1}'
# or
ip route get 1.1.1.1 | awk '{print $7; exit}'
```

**macOS:**
```bash
ipconfig getifaddr en0
```

**Windows:**
```
ipconfig | findstr IPv4
```

---

## 2. Running the Coordinator

### Quick start

```bash
cd coordinator/
python3 collatz_coordinator.py
```

On first run it prints your coordinator address and starts a fresh search from 2⁶⁸. On subsequent runs it detects the checkpoint and resumes automatically:

```
=================================================================
 Collatz Distributed Coordinator -- Production Ready
=================================================================
 RESUMED     -- next n      = 295,147,905,182,352,825,857
               tested      = 2,999,000,000
               chunks done = 5,998
 Chunk size  : 500,000 odd numbers
 Port        : 5555
 Results     : collatz_distributed_fails.txt  (FAILs only)
 Checkpoint  : collatz_coordinator_checkpoint.json
=================================================================
```

### Production server (10+ workers)

**Waitress** (Windows/Linux/Mac — auto-detected if installed):
```bash
pip install waitress
python3 collatz_coordinator.py   # Waitress used automatically
```

**Gunicorn** (Linux/Mac — best performance):
```bash
pip install gunicorn
gunicorn -w 1 --threads 32 -b 0.0.0.0:5555 collatz_coordinator:app
```

> **Always use `-w 1`.** The coordinator keeps all state in memory. Multiple processes each get a separate copy and would issue the same chunks to different workers.

### HTTPS with Certbot

If certbot is already installed, two options are available. Option B is recommended.

#### Option A — Direct TLS (Gunicorn reads certs, no nginx needed)

```bash
gunicorn -w 1 --threads 32 \
  --certfile /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem \
  --keyfile  /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem \
  -b 0.0.0.0:443 \
  collatz_coordinator:app
```

Workers connect with `https://`:
```bash
python3 collatz_worker.py --coordinator https://YOUR_DOMAIN
```

#### Option B — nginx Reverse Proxy (certbot's default)

certbot typically configures nginx automatically. After running `sudo certbot --nginx -d YOUR_DOMAIN`, verify your nginx config proxies with the forwarded headers:

```nginx
location / {
    proxy_pass         http://localhost:5555;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   Host              $host;
}
```

Then tell the coordinator it's behind a proxy — add to your service file (or set before running):

```bash
# Service file:  /etc/systemd/system/collatz.service
Environment="COLLATZ_PROXY=1"
Environment="COLLATZ_DOMAIN=YOUR_DOMAIN"
```

```bash
# Or as env vars before running directly:
COLLATZ_PROXY=1 COLLATZ_DOMAIN=YOUR_DOMAIN python3 collatz_coordinator.py
```

**Why `COLLATZ_PROXY=1` is required:** Without it, the coordinator sees all internal requests as `http://` even though clients connected via `https://`. This causes the QR code on `/status`, the mobile worker's `BASE_URL` in `/join`, and the startup banner to all generate wrong `http://` URLs.

The `install_service.sh` script asks which HTTPS mode you're using and writes the correct `ExecStart` and environment variables automatically.

### CLI flags

```bash
python3 collatz_coordinator.py --start 295147905179352825857  # resume from specific n
python3 collatz_coordinator.py --chunk 1000000                # larger chunks (faster workers)
python3 collatz_coordinator.py --port 8080                    # different port
```

### Environment variables (Gunicorn)

Gunicorn bypasses CLI flags — use environment variables instead:

```bash
COLLATZ_CHUNK=1000000 gunicorn -w 1 --threads 32 -b 0.0.0.0:5555 collatz_coordinator:app
```

| Variable | Default | Description |
|---|---|---|
| `COLLATZ_START` | `2^68` | Starting n |
| `COLLATZ_CHUNK` | `500000` | Chunk size |

### Fixing the Gunicorn PATH warning

After `pip install gunicorn` you may see:
```
WARNING: The script gunicorn is installed in '/Users/you/Library/Python/3.9/bin'
which is not on PATH.
```

**macOS / Linux (zsh):**
```bash
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

**macOS / Linux (bash):**
```bash
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.bash_profile && source ~/.bash_profile
```

**Linux (pip to ~/.local):**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

---

## 3. Running Workers

### Basic start

```bash
cd worker/
python3 collatz_worker.py --coordinator http://192.168.1.100:5555
```

On first run, a `collatz_identity.json` file is created in the current directory. This is your permanent worker identity and prize proof — **back it up.**

```
=================================================================
 Collatz Distributed Worker -- Optimized + Identified
=================================================================
  NEW IDENTITY created: collatz_identity.json
  Worker ID : 864bb37e-cf58-4abd-8cfe-04b8e6b89cbc
  *** BACK UP THIS FILE — it proves milestone crossings ***

 Worker name : rig-1
 Worker ID   : 864bb37e-cf58-4abd-8cfe-04b8e6b89cbc
 Hostname    : mybox.local
 IP          : 192.168.1.5
 Coordinator : http://192.168.1.100:5555
 Cores       : 16
 gmpy2       : YES
 Identity    : collatz_identity.json
```

### Common options

```bash
# Custom name (shows in leaderboard)
python3 collatz_worker.py --coordinator http://192.168.1.100:5555 --name "gpu-rig"

# Limit cores (leave some for other work)
python3 collatz_worker.py --coordinator http://192.168.1.100:5555 --cores 8

# Worker on the same machine as coordinator
python3 collatz_worker.py --coordinator http://localhost:5555
```

### Multiple workers on one machine

Open separate terminals and split your cores:

```bash
# Terminal 1 — first 8 cores
python3 collatz_worker.py --coordinator http://localhost:5555 --name rig-a --cores 8

# Terminal 2 — next 8 cores
python3 collatz_worker.py --coordinator http://localhost:5555 --name rig-b --cores 8
```

### Backing up your identity file

Do this immediately after first run, and again after any milestone crossing:

```bash
# Back up to home directory
cp collatz_identity.json ~/collatz_identity_backup.json

# Back up to a USB drive or cloud
cp collatz_identity.json /Volumes/USB/collatz_identity_$(hostname).json
```

### Stopping cleanly

Press `Ctrl+C`. The worker finishes its current chunk, posts results, and exits. No work is lost.

---

## 4. Making It Headless (Services)

Once running as a service, the process survives SSH disconnects, restarts after crashes, and starts automatically on reboot.

### Coordinator machine

Copy `services/linux/install_service.sh` and your Python files to the same folder, then:

```bash
bash install_service.sh
```

The script auto-detects your username, working directory, and Gunicorn path. It asks for your GitHub token once and writes both the coordinator and uploader service files.

**Useful commands after installation:**

```bash
# Check status
sudo systemctl status collatz
sudo systemctl status collatz-uploader

# Watch live logs
journalctl -u collatz -f
journalctl -u collatz-uploader -f

# Restart after updating coordinator.py
sudo systemctl restart collatz

# Stop
sudo systemctl stop collatz
```

### Worker machines

```bash
bash install_worker_service.sh
```

Prompts for coordinator IP, worker name, and core count. Optionally installs multiple worker services on one machine (splits cores evenly).

**Update coordinator URL if coordinator moves:**

```bash
sudo systemctl edit collatz-worker
# Add:
# [Service]
# Environment="COLLATZ_COORDINATOR=http://NEW_IP:5555"
sudo systemctl restart collatz-worker
```

> **Important:** After the worker service starts for the first time, it creates `collatz_identity.json` in its working directory. Back this up — it contains your prize claim tokens.

---

## 5. Contributing from a Phone

No app or Python required. Any phone or tablet with a browser works.

### Scanning the QR code

1. Open `http://YOUR_COORDINATOR_IP:5555/status` in a browser on any machine
2. A QR code appears at the bottom of the page
3. Scan it with your phone's camera app
4. The `/join` page opens in your mobile browser

### Starting compute

1. Type your name (or leave blank — it auto-generates one like `iPhone-x7f2`)
2. Tap **Start**
3. The page begins pulling and processing chunks immediately

Live stats update on screen: integers tested, speed, chunks completed.

### Background operation

| Device | Background behavior |
|---|---|
| Android Chrome | Full background via Service Worker — survives tab close |
| Android Firefox | Good — survives app switch, stops if tab closed |
| iPhone/iPad Safari | Pauses after ~30 sec when you leave the app (iOS limitation) |
| iPhone/iPad Chrome | Same as Safari — iOS enforces this |
| Desktop browser | Runs indefinitely in background tab |

### Backing up your mobile identity

Your identity (including any prize claim tokens) is stored in your browser's `localStorage`. It will survive tab closes and phone reboots, but **not** "Clear site data" or "Clear browser storage."

To back it up:
1. Tap the **"View My Identity & Claim Tokens"** button (always visible on the `/join` page)
2. Tap **Copy JSON**
3. Paste into Notes, iCloud, or a password manager and save

**Do this immediately if you cross a milestone.** The modal opens automatically when a milestone is crossed.

---

## 6. Monitoring and Dashboards

All dashboards auto-refresh every 15 seconds.

### /status

`http://YOUR_IP:5555/status`

| Panel | Shows |
|---|---|
| Frontier box | Current `n` value and offset from 2⁶⁸ |
| Stats grid | Numbers covered, session rate, chunks done, in-flight count, active workers, FAILs, uptime, chunk size |
| Active workers | Blue pills showing currently-working machines |
| In-flight chunks | Table of chunks currently being processed (orange if >5 min old) |
| Phone QR code | Scan to open `/join` on any mobile device |

### /workers

`http://YOUR_IP:5555/workers`

Top 50 workers by lifetime numbers tested. Shows: rank (gold/silver/bronze), name, UUID prefix, hostname, numbers tested, chunks done, average speed, FAILs, active/idle status, last seen. Workers who crossed a milestone show a gold trophy badge.

### /milestones

`http://YOUR_IP:5555/milestones`

Prize pool banner ($655,350,000 total), progress bar, and full milestone table with status badges and "verify claim" buttons for any crossed milestones.

### Reading the logs (service mode)

```bash
# Last 50 lines
journalctl -u collatz -n 50

# Live tail
journalctl -u collatz -f

# Since a specific time
journalctl -u collatz --since "2026-04-15 20:00:00"

# Search for milestones
journalctl -u collatz | grep MILESTONE

# Search for potential counterexamples
journalctl -u collatz | grep COUNTEREXAMPLE
```

---

## 7. Prize Claims and Milestone Verification

### When you cross a milestone

**Python worker:** The terminal prints a banner:

```
  *** MILESTONE: Sextillion (1.00e+21) crossed by 'rig-1' — claim token generated ***
```

The claim token is saved to `collatz_identity.json` automatically:

```json
{
  "milestones": {
    "Sextillion": {
      "claim_token": "a3f8c2d1...",
      "crossed_at":  "2026-04-15 20:00:01",
      "frontier_n":  "1000000000000000000001",
      "prize":       "$10,000"
    }
  }
}
```

**Mobile worker:** A glowing gold card appears on screen and the identity modal opens automatically showing your JSON. **Copy it immediately.**

### Verifying your claim

The `/verify` endpoint confirms your token is authentic:

```bash
curl -X POST http://coordinator:5555/verify \
  -H "Content-Type: application/json" \
  -d '{
    "worker_id":   "864bb37e-cf58-4abd-8cfe-04b8e6b89cbc",
    "milestone":   "Sextillion",
    "frontier_n":  "1000000000000000000001",
    "crossed_at":  "2026-04-15 20:00:01",
    "claim_token": "a3f8c2d1..."
  }'
```

**Valid response:**
```json
{
  "valid":       true,
  "message":     "Claim verified. Sextillion was crossed by this worker.",
  "milestone":   "Sextillion",
  "worker_name": "rig-1",
  "hostname":    "mybox.local",
  "crossed_at":  "2026-04-15 20:00:01",
  "prize":       "$10,000"
}
```

You can also click **"verify claim"** on the `/milestones` page and paste your values into the prompts — it calls `/verify` automatically.

### Claiming your prize

1. Verify your token is valid using either method above
2. Open a GitHub Issue at https://github.com/huggablehacker/Collatz-Frontier/issues
3. Title: `Prize Claim: [Milestone Name]`
4. Include: your `collatz_identity.json` (or just the milestone entry within it)
5. The project owner will run `/verify` on the coordinator to confirm and arrange payment

### If you lose your claim token

If you still have your `worker_id` and the approximate crossing date, the coordinator owner can re-derive your token from the `milestone_log` stored in the checkpoint. The coordinator stores `claim_token` server-side for exactly this reason — open a GitHub Issue and ask.

---

## 8. Nightly GitHub Uploads

The uploader reads the coordinator's checkpoint and posts a status report to `frontier_log.txt` in the GitHub repository every night at **8:00 PM EST**.

### Setup

1. Get a GitHub Personal Access Token at https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Name it `collatz-frontier-uploader`
   - Check the **`repo`** scope
   - Copy the token (starts with `ghp_`)

2. Set the token as an environment variable:
   ```bash
   export GITHUB_TOKEN="ghp_your_token_here"
   ```
   Add to `~/.zshrc` or `~/.bashrc` to make it permanent.

### Running modes

**Scheduler** (runs forever, fires at 8pm EST):
```bash
python3 coordinator/collatz_upload_frontier.py
```

**One-shot** (upload now and exit — use with cron):
```bash
python3 coordinator/collatz_upload_frontier.py --now
```

**Cron** (alternative to built-in scheduler):
```bash
crontab -e
# Add:
0 1 * * * GITHUB_TOKEN=ghp_... python3 /path/to/collatz_upload_frontier.py --now
```

The output file will be live at:  
`https://github.com/huggablehacker/Collatz-Frontier/blob/main/frontier_log.txt`

---

## 9. Checkpoint Management and Recovery

### What the checkpoint contains

The coordinator checkpoint at `collatz_coordinator_checkpoint.json` stores everything needed to resume: the frontier position, all worker stats, the worker registry, all milestone records, and the coordinator secret. It is written atomically every 50 chunks (and immediately on any FAIL or milestone).

### Recovering from a crash

Just restart the coordinator. It detects the checkpoint automatically:

```bash
python3 collatz_coordinator.py
# or
sudo systemctl start collatz
```

In-flight chunks (those issued but not completed before the crash) are re-issued automatically after 600 seconds (the stale timeout). No numbers are skipped.

### Backing up the coordinator secret

The coordinator secret is the root of all prize verification. If it is lost, no existing claim tokens can be verified.

Back it up after the coordinator first starts:

```bash
python3 -c "
import json
cp = json.load(open('collatz_coordinator_checkpoint.json'))
print('COORDINATOR SECRET:')
print(cp['coordinator_secret'])
print('Store this in your password manager.')
"
```

### File permissions (important)

The checkpoint contains the coordinator secret in plaintext. Restrict its permissions:

```bash
chmod 600 collatz_coordinator_checkpoint.json
```

Add `UMask=0077` to the coordinator service file to ensure it's always created with 600 permissions:

```bash
sudo systemctl edit collatz
# Add:
# [Service]
# UMask=0077
sudo systemctl restart collatz
```

### Manually inspecting the checkpoint

```bash
python3 -c "
import json
cp = json.load(open('collatz_coordinator_checkpoint.json'))
print(f'Frontier n      : {cp[\"next_n\"]:,}')
print(f'Offset from 2^68: +{cp[\"next_n\"] - 2**68:,}')
print(f'Chunks done     : {cp[\"chunks_done\"]:,}')
print(f'Total tested    : {cp[\"total_tested\"]:,}')
print(f'FAILs           : {cp[\"fails\"]}')
print(f'Workers         : {len(cp[\"worker_stats\"])}')
print(f'Milestones      : {list(cp[\"milestone_log\"].keys())}')
"
```

---

## 10. Cleaning Up Workers

Use `collatz_cleanup.py` on the coordinator machine while the coordinator is **stopped**.

```bash
sudo systemctl stop collatz
python3 collatz_cleanup.py [options]
sudo systemctl start collatz
```

### Preview before committing

Always run with `--dry-run` first:

```bash
python3 collatz_cleanup.py --dry-run
```

### Remove idle workers (15+ hours)

```bash
python3 collatz_cleanup.py --idle-hours 15
```

### Remove specific workers

```bash
# By display name
python3 collatz_cleanup.py --remove "old-laptop" "guest-phone"

# By UUID prefix
python3 collatz_cleanup.py --remove "864bb37e"

# Partial name match (removes anything containing "test")
python3 collatz_cleanup.py --remove "test"
```

If you're unsure of names, run with a non-existent target to list all workers:
```bash
python3 collatz_cleanup.py --remove "?" --dry-run
```

### Merge workers manually

Combine multiple entries (e.g. from the same machine that restarted several times) into one:

```bash
python3 collatz_cleanup.py \
    --merge "rig-1-morning" "rig-1-afternoon" "rig-1-evening" \
    --into "rig-1"
```

The merged entry gets the sum of all chunks, tested numbers, and compute time. If any of the merged workers holds a milestone claim token, that worker's UUID wins and becomes the surviving identity.

### Merge by hostname

Consolidate all entries from the same physical machine:

```bash
python3 collatz_cleanup.py --merge-by-hostname
```

### Remove anonymous workers (no hostname)

Remove pre-identity workers or mobile browsers that never registered a hostname:

```bash
python3 collatz_cleanup.py --remove-no-hostname
```

### Full cleanup example

```bash
python3 collatz_cleanup.py \
    --merge-by-hostname \
    --remove-no-hostname \
    --idle-hours 24 \
    --dry-run
# Review output, then:
python3 collatz_cleanup.py \
    --merge-by-hostname \
    --remove-no-hostname \
    --idle-hours 24
```

A timestamped backup (`checkpoint.json.bak.20260329_130450`) is always written before any live run.

---

## 11. Windows

A Windows package that requires no Python installation is available in `services/windows/`.

### Building the .exe files

1. Install Python from https://www.python.org/downloads/ — check **"Add Python to PATH"**
2. Copy your `.py` files and the contents of `services/windows/` into one folder
3. Double-click `build_windows.bat`
4. A `Collatz-Frontier-Windows\` folder appears — zip it up and share

### Running on Windows

**Coordinator:** Double-click `launch_coordinator.bat`
- Automatically prints your IP and all dashboard URLs
- Click "Allow access" when Windows Firewall prompts

**Worker:** Double-click `launch_worker.bat`
- Prompts for coordinator IP, machine name, and core count
- Press Enter to use all cores

### SmartScreen warning

When running for the first time: click **"More info"** → **"Run anyway"**. This is expected for self-built PyInstaller executables.

### Making it headless on Windows

**Task Scheduler (built-in):**
1. Open Task Scheduler
2. "Create Basic Task" → name "Collatz Coordinator"
3. Trigger: "When the computer starts"
4. Action: "Start a program" → browse to `collatz_coordinator.exe`
5. Check "Run whether user is logged on or not"

**NSSM (Non-Sucking Service Manager):**
```
nssm install CollatzCoordinator collatz_coordinator.exe
nssm start CollatzCoordinator
```
Download from https://nssm.cc

---

## 12. Standalone Single-Machine Mode

No coordinator or network needed. Tests numbers locally from 2⁶⁸, writes only FAILs, checkpoints automatically.

```bash
cd standalone/
python3 collatz_frontier_fast.py
```

Output:
```
========================================================================
 Collatz Frontier — Optimized  (FAILs only)
========================================================================
 Worker ID   : 864bb37e-cf58-4abd-8cfe-04b8e6b89cbc
 Identity    : collatz_identity.json
 Output file : collatz_frontier_fails.txt  (stays empty if conjecture holds)
 Checkpoint  : collatz_frontier_checkpoint.json  (every 100,000 numbers)
 Press Ctrl+C to stop safely.
========================================================================
```

Press `Ctrl+C` to stop cleanly — it saves a checkpoint and resumes on next run. At ~800,000 odd integers per second it's about 25 minutes per billion numbers.

### Graphing results

```bash
cd standalone/

# Graph the results file (requires matplotlib)
pip install matplotlib
python3 collatz_graph.py

# Custom options
python3 collatz_graph.py --smooth 200 --max 10000 --out my_chart.png
```

### Merging distributed results

If workers saved locally when the coordinator was unreachable:

```bash
cd worker/
python3 collatz_merge.py

# Custom paths
python3 collatz_merge.py \
    --main ../collatz_distributed_fails.txt \
    --out  merged_fails.txt
```

---

## 13. Troubleshooting

### "ERROR: pip install requests"

`requests` is already installed but on a different Python than the one running the script:

```bash
python3 -m pip install requests
# Then always use python3, not python
python3 collatz_worker.py ...
```

### Workers can't connect to coordinator

1. Confirm the coordinator is running: open `http://COORDINATOR_IP:5555/status` in a browser
2. Check the firewall:
   ```bash
   # Linux
   sudo ufw allow 5555
   # or
   sudo iptables -I INPUT -p tcp --dport 5555 -j ACCEPT
   ```
3. Confirm you're using the right IP:
   ```bash
   ping COORDINATOR_IP
   ```
4. Confirm port 5555 is listening:
   ```bash
   # On coordinator machine
   netstat -tlnp | grep 5555
   ```

### Coordinator exits immediately

Port 5555 is already in use:
```bash
# Find what's using it
lsof -i :5555
# Kill it
kill -9 PID
```

### "gunicorn: command not found"

See [Fixing the Gunicorn PATH warning](#fixing-the-gunicorn-path-warning) above.

### Checkpoint won't load (coordinator starts fresh every time)

The checkpoint is unreadable — usually a permissions issue or corrupted JSON:
```bash
# Check it's valid JSON
python3 -c "import json; json.load(open('collatz_coordinator_checkpoint.json'))"

# Check permissions (should be 600 or 644)
ls -la collatz_coordinator_checkpoint.json

# If corrupt, restore from backup
cp collatz_coordinator_checkpoint.json.bak.TIMESTAMP collatz_coordinator_checkpoint.json
```

### Worker is very slow on first chunk

Normal — `multiprocessing.Pool` takes a few seconds to spin up worker processes. Speed stabilizes after the first chunk.

### Service won't start after install

```bash
# Check the logs
journalctl -u collatz -n 30

# Common fix: Gunicorn not on PATH for root
# Edit the service file to use the full path
sudo systemctl edit --force collatz
# Add: ExecStart=/home/you/Library/Python/3.9/bin/gunicorn ...

sudo systemctl daemon-reload
sudo systemctl restart collatz
```

### Identity file missing after service install

The service creates `collatz_identity.json` in its `WorkingDirectory` (the folder where your Python files are). Check there:

```bash
ls -la /path/to/your/collatz/folder/collatz_identity.json
```

Back it up immediately:
```bash
cp /path/to/collatz_identity.json ~/collatz_identity_backup.json
```

### Mobile worker not connecting

The phone must be on the **same Wi-Fi network** as the coordinator, or the coordinator must be publicly reachable. The QR code points to your LAN IP — it won't work over cellular unless you expose port 5555 to the internet.

To verify: on the phone, open `http://COORDINATOR_IP:5555/status` in a browser manually. If that loads, the `/join` page will work.

### Lost my mobile claim token

Open a GitHub Issue at https://github.com/huggablehacker/Collatz-Frontier/issues with:
- Your worker_id (visible in the "View My Identity" modal on `/join`)
- The milestone name
- Approximate date and time of crossing

The coordinator owner can re-derive your claim token from the server-side `milestone_log` and verify it for you.
