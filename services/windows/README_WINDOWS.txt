COLLATZ FRONTIER — WINDOWS PACKAGE
====================================
https://github.com/huggablehacker/Collatz-Frontier

No Python required. These are standalone .exe files.


WHAT'S IN THIS FOLDER
----------------------
  collatz_coordinator.exe  — run on ONE machine (the coordinator)
  collatz_worker.exe       — run on every machine that contributes compute
  launch_coordinator.bat   — double-click launcher for the coordinator
  launch_worker.bat        — double-click launcher for a worker
  README_WINDOWS.txt       — this file


QUICK START
-----------

1. COORDINATOR (run this on one machine):

   Double-click:  launch_coordinator.bat

   When Windows Firewall asks, click "Allow access".
   The coordinator will print your IP address and the URL workers
   should connect to.

   Live dashboard opens in your browser at:
     http://YOUR-IP:5555/status
     http://YOUR-IP:5555/workers      (top 50 leaderboard)
     http://YOUR-IP:5555/milestones   (frontier milestones)


2. WORKERS (run on every machine):

   Double-click:  launch_worker.bat

   Enter the coordinator's IP address when prompted.
   Enter a name for this machine (e.g. "office-pc", "gaming-rig").
   Press Enter to use all CPU cores.

   That's it. The worker will start pulling chunks and testing numbers.


STOPPING AND RESUMING
---------------------
Press Ctrl+C in any window to stop cleanly.

The coordinator saves a checkpoint automatically (collatz_coordinator_checkpoint.json).
Just double-click launch_coordinator.bat again to resume exactly where you left off.


RUNNING WITHOUT THE LAUNCHER
-----------------------------
You can also run the .exe files directly from Command Prompt:

  Coordinator:
    collatz_coordinator.exe --port 5555 --chunk 500000

  Worker:
    collatz_worker.exe --coordinator http://192.168.1.100:5555 --name my-pc --cores 8


FIREWALL SETUP
--------------
Windows Firewall will prompt you the first time the coordinator runs.
Click "Allow access" for both private and public networks.

If workers can't connect, open Windows Defender Firewall manually:
  1. Open "Windows Defender Firewall with Advanced Security"
  2. Click "Inbound Rules" -> "New Rule"
  3. Choose "Port" -> TCP -> "5555"
  4. Allow the connection
  5. Click Finish


OUTPUT FILES
------------
These files are written in the same folder as the coordinator:

  collatz_distributed_fails.txt           — any potential counterexamples (will be empty)
  collatz_coordinator_checkpoint.json     — progress checkpoint (auto-saved)


MULTIPLE WORKERS ON ONE MACHINE
--------------------------------
Open multiple Command Prompt windows and run:

  collatz_worker.exe --coordinator http://localhost:5555 --name worker-1 --cores 4
  collatz_worker.exe --coordinator http://localhost:5555 --name worker-2 --cores 4

This lets you split your cores between named workers.


PERFORMANCE TIPS
----------------
- Use all cores (default) for maximum throughput
- Run the coordinator on a machine that stays on 24/7
- Workers can be started and stopped at any time without losing progress
- The coordinator handles crashed workers automatically (re-issues their chunks)


NIGHTLY GITHUB UPLOAD
---------------------
To upload the frontier position to GitHub every night at 8pm EST:

  1. Get a GitHub Personal Access Token at https://github.com/settings/tokens
     (check the "repo" scope)

  2. Open Command Prompt and run:
       set GITHUB_TOKEN=ghp_your_token_here
       collatz_upload_frontier.exe

  Or add --now to upload immediately and exit:
       collatz_upload_frontier.exe --now


TROUBLESHOOTING
---------------
Problem: "Windows protected your PC" (SmartScreen warning)
Fix:     Click "More info" -> "Run anyway"
         The .exe was built with PyInstaller, not code-signed.
         This is expected for self-built executables.

Problem: Coordinator exits immediately
Fix:     Check that no other program is using port 5555.
         Try: netstat -ano | findstr :5555

Problem: Workers show "Cannot reach coordinator"
Fix:     Check the coordinator is running.
         Check firewall (see FIREWALL SETUP above).
         Try pinging the coordinator IP from the worker machine.

Problem: Very slow on first chunk
Fix:     Normal — Python's multiprocessing takes a moment to warm up.
         Speed stabilises after the first few chunks.

Problem: "DLL load failed" on startup
Fix:     Install the Visual C++ Redistributable:
         https://aka.ms/vs/17/release/vc_redist.x64.exe


BUILDING FROM SOURCE
--------------------
If you want to rebuild the .exe files yourself (requires Python):

  1. Install Python 3.8+ from https://www.python.org/downloads/
     (check "Add Python to PATH" during install)

  2. Copy all .py and .spec files into one folder

  3. Double-click build_windows.bat

  The build takes 1-3 minutes and produces a new Collatz-Frontier-Windows\ folder.


SOURCE CODE & UPDATES
---------------------
https://github.com/huggablehacker/Collatz-Frontier

Check the repository for the latest versions, bug fixes, and results.
