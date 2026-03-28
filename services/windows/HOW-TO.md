# Windows Package — How-To Guide

These files build standalone `.exe` files for Windows. **No Python required on the target machines** — everything is bundled inside the executables.

---

## Files in this folder

| File | Purpose |
|---|---|
| `build_windows.bat` | Run once to build all .exe files |
| `coordinator.spec` | PyInstaller config for `collatz_coordinator.exe` |
| `worker.spec` | PyInstaller config for `collatz_worker.exe` |
| `uploader.spec` | PyInstaller config for `collatz_upload_frontier.exe` |
| `launch_coordinator.bat` | Double-click launcher — starts coordinator, prints IP and URLs |
| `launch_worker.bat` | Double-click launcher — prompts for coordinator IP, name, cores |
| `README_WINDOWS.txt` | Windows user guide (plain text) |

---

## Building the .exe files (do this once)

### Requirements

Python 3.8+ must be installed on the **build machine** (the machine where you run `build_windows.bat`). Python is **not** needed on machines that only run the resulting .exe files.

Install Python from https://www.python.org/downloads/ — check **"Add Python to PATH"** during installation.

### Steps

1. Copy all files from this folder **plus** the three Python scripts into one folder:
   - `collatz_coordinator.py`
   - `collatz_worker.py`
   - `collatz_upload_frontier.py`
   - Everything from this `windows/` folder

2. Double-click `build_windows.bat`

3. Wait 1–3 minutes — it installs dependencies and builds the executables

4. A `Collatz-Frontier-Windows\` folder appears containing:
   ```
   collatz_coordinator.exe
   collatz_worker.exe
   collatz_upload_frontier.exe
   launch_coordinator.bat
   launch_worker.bat
   README_WINDOWS.txt
   ```

5. Zip up `Collatz-Frontier-Windows\` and share it — anyone on Windows can run it without Python

---

## Running the coordinator (Windows)

Double-click `launch_coordinator.bat`

- Windows Firewall will ask permission — click **"Allow access"**
- The window prints your IP address and the dashboard URLs
- Open your browser to `http://YOUR_IP:5555/status`

Or from Command Prompt:
```
collatz_coordinator.exe --port 5555 --chunk 500000
```

---

## Running a worker (Windows)

Double-click `launch_worker.bat`

It prompts you for:
- Coordinator IP (e.g. `192.168.1.100`)
- Worker name (defaults to computer hostname)
- Number of cores (defaults to all)

Or from Command Prompt:
```
collatz_worker.exe --coordinator http://192.168.1.100:5555 --name my-pc --cores 8
```

---

## Nightly GitHub upload (Windows)

```
set GITHUB_TOKEN=ghp_your_token_here
collatz_upload_frontier.exe
```

Or upload immediately:
```
collatz_upload_frontier.exe --now
```

---

## Firewall setup

Windows Firewall prompts on first run. Click **"Allow access"** for both private and public networks.

If workers can't connect, open Windows Defender Firewall manually:
1. "Windows Defender Firewall with Advanced Security"
2. "Inbound Rules" → "New Rule"
3. Port → TCP → `5555` → Allow → Finish

---

## SmartScreen warning

When running the .exe for the first time:

> *"Windows protected your PC"*

Click **"More info"** → **"Run anyway"**

This is expected — the executables are built with PyInstaller and aren't code-signed. This is safe for self-built executables.

---

## Troubleshooting

**`collatz_coordinator.exe` exits immediately**
Check that port 5555 isn't in use:
```
netstat -ano | findstr :5555
```

**Worker shows "Cannot reach coordinator"**
- Confirm coordinator is running
- Check firewall (see above)
- Try `ping COORDINATOR_IP` from the worker machine

**Very slow on first chunk**
Normal — Python's multiprocessing takes a moment to warm up. Speed stabilises after a few chunks.

**"DLL load failed" on startup**
Install the Visual C++ Redistributable:
https://aka.ms/vs/17/release/vc_redist.x64.exe

---

## Running without the launcher

All three executables accept the same flags as the Python scripts:

```
collatz_coordinator.exe --port 5555 --chunk 500000
collatz_worker.exe --coordinator http://192.168.1.100:5555 --name rig-1 --cores 8
collatz_upload_frontier.exe --now
```

---

## Making the coordinator headless on Windows

The `.exe` runs in a console window — closing the window stops it. For true background operation on Windows:

**Option 1 — Task Scheduler** (built-in, recommended):
1. Open Task Scheduler
2. "Create Basic Task" → name it "Collatz Coordinator"
3. Trigger: "When the computer starts"
4. Action: "Start a program" → browse to `collatz_coordinator.exe`
5. Tick "Run whether user is logged on or not"

**Option 2 — NSSM** (Non-Sucking Service Manager):
```
nssm install CollatzCoordinator collatz_coordinator.exe
nssm start CollatzCoordinator
```
Download NSSM from https://nssm.cc
