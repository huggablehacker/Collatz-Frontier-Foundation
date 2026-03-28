# Linux Services — How-To Guide

These files turn the coordinator, uploader, and worker into **systemd services** — proper background processes that:

- Survive SSH disconnections
- Start automatically on every reboot
- Restart automatically if they crash
- Log to the system journal (`journalctl`)

---

## Files in this folder

| File | Purpose |
|---|---|
| `install_service.sh` | One-command installer for coordinator + uploader (run on coordinator machine) |
| `install_worker_service.sh` | One-command installer for worker (run on each worker machine) |
| `collatz.service` | Systemd unit for the coordinator (reference / manual install) |
| `collatz-uploader.service` | Systemd unit for the nightly uploader (reference / manual install) |
| `collatz-worker.service` | Systemd unit template for a worker (reference / manual install) |

---

## Coordinator machine — install both services

Copy `install_service.sh` and your Python files to the same folder, then:

```bash
bash install_service.sh
```

The script will:
1. Auto-detect your username, working directory, and gunicorn path
2. Ask for your GitHub token (for nightly uploads)
3. Write `/etc/systemd/system/collatz.service`
4. Write `/etc/systemd/system/collatz-uploader.service`
5. Enable and start both services
6. Print your dashboard URL

### Prerequisites

```bash
pip install flask waitress gunicorn
```

Make sure `gunicorn` is on your PATH. If you see a PATH warning after installing, see the PATH fix section below.

---

## Worker machines — install the worker service

Copy `install_worker_service.sh` and `collatz_worker.py` to the same folder, then:

```bash
bash install_worker_service.sh
```

The script will:
1. Ask for the coordinator's IP address (and test connectivity)
2. Ask for a worker name (defaults to hostname)
3. Ask how many cores to use
4. Optionally install **multiple worker services** on one machine (splits cores evenly)
5. Write and start the service(s)

### Prerequisites

```bash
pip install requests
```

---

## Fixing the Gunicorn PATH warning

After `pip install gunicorn` you may see:

```
WARNING: The script gunicorn is installed in '/Users/you/Library/Python/3.9/bin'
which is not on PATH.
```

Fix it permanently:

**macOS / Linux — zsh** (default on modern Macs):
```bash
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**macOS / Linux — bash:**
```bash
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile
```

**Linux — pip installs to `~/.local/bin`:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify:
```bash
gunicorn --version
```

---

## Daily commands

### Check status
```bash
sudo systemctl status collatz
sudo systemctl status collatz-uploader
sudo systemctl status collatz-worker
```

### Live logs
```bash
journalctl -u collatz -f                           # coordinator
journalctl -u collatz-uploader -f                  # uploader
journalctl -u collatz-worker -f                    # worker
journalctl -u collatz -u collatz-uploader -f       # both together
```

### Last N lines of logs
```bash
journalctl -u collatz -n 100
journalctl -u collatz-worker -n 50
```

### Restart after updating a script
```bash
sudo systemctl restart collatz
sudo systemctl restart collatz-uploader
sudo systemctl restart collatz-worker
```

### Stop / start
```bash
sudo systemctl stop collatz
sudo systemctl start collatz
```

---

## Updating the coordinator URL on a worker

If you move the coordinator to a different machine:

```bash
sudo systemctl edit collatz-worker
```

This opens a drop-in config file. Add:

```ini
[Service]
Environment="COLLATZ_COORDINATOR=http://NEW_IP:5555"
```

Save, then:

```bash
sudo systemctl restart collatz-worker
```

---

## Updating the GitHub token

```bash
sudo systemctl edit collatz-uploader
```

Add:

```ini
[Service]
Environment="GITHUB_TOKEN=ghp_your_new_token_here"
```

```bash
sudo systemctl restart collatz-uploader
```

---

## Manual install (without the script)

If you prefer to install manually rather than using the script:

1. Edit `collatz.service` — replace `YOUR_USERNAME` and paths
2. Copy to systemd:
   ```bash
   sudo cp collatz.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable collatz
   sudo systemctl start collatz
   ```
3. Repeat for `collatz-uploader.service` and `collatz-worker.service`

---

## Service restart behaviour

| Service | Restart delay | Reason |
|---|---|---|
| `collatz` (coordinator) | 5 seconds | Fast recovery — workers retry every 10s |
| `collatz-uploader` | 10 seconds | Avoids GitHub API rate-limit loops |
| `collatz-worker` | 10 seconds | Gives coordinator time to come back up |

All services have `StartLimitIntervalSec=0` — systemd will keep restarting them indefinitely rather than giving up after a burst of failures.

---

## macOS note

macOS uses `launchd` instead of `systemd`. The installer scripts won't work directly on Mac. For Mac servers, use one of:

- `nohup` for a simple solution (no auto-restart on reboot)
- `launchd` plist files for a proper service
- A Linux VM or VPS as your coordinator machine (recommended for 24/7 operation)
