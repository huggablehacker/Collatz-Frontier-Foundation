"""
collatz_upload_frontier.py
---------------------------
Reads the coordinator checkpoint and uploads a frontier status file
to GitHub every night at 8:00 PM EST (01:00 UTC the following day).

Can be run two ways:

  1. Standalone scheduler (runs forever, fires at 8pm EST daily):
       python3 collatz_upload_frontier.py

  2. One-shot (upload right now and exit — useful for cron):
       python3 collatz_upload_frontier.py --now

  3. Cron (add to crontab — 8pm EST = 01:00 UTC next day):
       0 1 * * * /usr/bin/python3 /path/to/collatz_upload_frontier.py --now

Setup — create a GitHub Personal Access Token:
  1. Go to https://github.com/settings/tokens
  2. Click "Generate new token (classic)"
  3. Give it a name, e.g. "collatz-frontier-uploader"
  4. Check the "repo" scope (needed to write files)
  5. Click "Generate token" and copy it
  6. Set the environment variable:
       export GITHUB_TOKEN="ghp_your_token_here"
     Or paste it directly into GITHUB_TOKEN below (less secure).

The script writes to:
  https://github.com/huggablehacker/Collatz-Frontier/blob/main/frontier_log.txt
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")   # set via env var
GITHUB_OWNER      = "huggablehacker"
GITHUB_REPO       = "Collatz-Frontier"
GITHUB_BRANCH     = "main"
GITHUB_FILE_PATH  = "frontier_log.txt"       # path inside the repo

CHECKPOINT_FILE   = "collatz_coordinator_checkpoint.json"
DEFAULT_START     = 2 ** 68

# 8:00 PM EST = UTC-5 standard / UTC-4 daylight
# We target 01:00 UTC which covers both (conservative — always after 8pm EST)
UPLOAD_HOUR_UTC   = 1     # 1:00 AM UTC = 8:00 PM EST
UPLOAD_MINUTE_UTC = 0


# ── GitHub API helpers ────────────────────────────────────────────────────────

def _api_request(method, path, body=None):
    """Make an authenticated GitHub API request. Returns (status, data)."""
    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is not set.\n"
            "Export it: export GITHUB_TOKEN='ghp_your_token_here'\n"
            "Get one at: https://github.com/settings/tokens"
        )

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept":        "application/vnd.github.v3+json",
        "Content-Type":  "application/json",
        "User-Agent":    "collatz-frontier-uploader/1.0",
    }

    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        return e.code, {"error": body_text}


def get_current_file_sha():
    """Get the SHA of the existing file (needed for updates). Returns None if new."""
    status, data = _api_request("GET", GITHUB_FILE_PATH)
    if status == 200:
        return data.get("sha")
    return None  # 404 = file doesn't exist yet


def upload_to_github(content: str) -> bool:
    """
    Create or update frontier_log.txt in the repo.
    Returns True on success.
    """
    # Encode content as base64 (required by GitHub API)
    encoded = base64.b64encode(content.encode()).decode()

    sha = get_current_file_sha()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    body = {
        "message": f"Frontier update: {now_str}",
        "content": encoded,
        "branch":  GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha   # required for updates, omitted for new files

    method = "PUT"   # PUT creates or updates
    status, data = _api_request(method, GITHUB_FILE_PATH, body)

    if status in (200, 201):
        print(f"  Uploaded successfully (HTTP {status})")
        return True
    else:
        print(f"  Upload failed (HTTP {status}): {data.get('error', data)}")
        return False


# ── Checkpoint reader ─────────────────────────────────────────────────────────

def read_checkpoint():
    """Read the coordinator checkpoint and return a dict of stats."""
    p = Path(CHECKPOINT_FILE)
    if not p.exists():
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except Exception as e:
        print(f"  Warning: could not read checkpoint: {e}")
        return None


# ── Content builder ───────────────────────────────────────────────────────────

def build_frontier_content(cp) -> str:
    """Build the flat file content from checkpoint data."""
    now_utc = datetime.now(timezone.utc)
    # EST = UTC-5 (standard) / UTC-4 (daylight) — approximate with -5
    now_est = now_utc - timedelta(hours=5)

    next_n      = int(cp.get("next_n", DEFAULT_START))
    offset      = next_n - DEFAULT_START
    total_tested= int(cp.get("total_tested", 0))
    chunks_done = int(cp.get("chunks_done", 0))
    fails       = int(cp.get("fails", 0))
    chunk_size  = int(cp.get("chunk_size", 500_000))

    # Worker stats summary
    ws = cp.get("worker_stats", {})
    top_workers = sorted(ws.items(), key=lambda x: x[1].get("tested", 0), reverse=True)[:10]

    worker_lines = ""
    for i, (wid, w) in enumerate(top_workers, 1):
        avg_rate = w.get("tested", 0) / w.get("total_sec", 1) if w.get("total_sec", 0) > 0 else 0
        worker_lines += (
            f"  {i:>2}. {wid:<30} "
            f"tested={w.get('tested', 0):>15,}  "
            f"chunks={w.get('chunks', 0):>8,}  "
            f"avg={avg_rate:>10,.0f}/sec\n"
        )
    if not worker_lines:
        worker_lines = "  (no worker data)\n"

    lines = [
        "COLLATZ FRONTIER — NIGHTLY STATUS REPORT",
        "=" * 72,
        f"Report generated : {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}  "
        f"({now_est.strftime('%Y-%m-%d %H:%M:%S EST')})",
        f"Repository       : https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}",
        "",
        "FRONTIER",
        "-" * 72,
        f"  Next n to test   : {next_n}",
        f"  Offset from 2^68 : +{offset:,}",
        f"  Numbers covered  : ~{total_tested * 2:,}",
        f"  Odd tested       : {total_tested:,}",
        "",
        "PROGRESS",
        "-" * 72,
        f"  Chunks completed : {chunks_done:,}",
        f"  Chunk size       : {chunk_size:,} odd numbers",
        f"  FAILs found      : {fails}  "
        f"{'<-- INVESTIGATE IMMEDIATELY' if fails else '(none — conjecture holds for all tested)'}",
        "",
        "TOP 10 WORKERS (all-time)",
        "-" * 72,
        worker_lines.rstrip(),
        "",
        "=" * 72,
        "This file is updated automatically every night at 8:00 PM EST.",
        f"For live status visit: http://YOUR_COORDINATOR_IP:5555/status",
    ]

    return "\n".join(lines) + "\n"


# ── Upload logic ──────────────────────────────────────────────────────────────

def do_upload():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running nightly frontier upload...")

    cp = read_checkpoint()
    if cp is None:
        print("  No checkpoint found — nothing to upload.")
        print(f"  Expected: {CHECKPOINT_FILE}")
        return False

    next_n = int(cp.get("next_n", DEFAULT_START))
    print(f"  Frontier n : {next_n:,}")
    print(f"  Offset     : +{next_n - DEFAULT_START:,} beyond 2^68")
    print(f"  Uploading to: github.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_FILE_PATH}")

    content = build_frontier_content(cp)
    success = upload_to_github(content)

    if success:
        print(f"  Done. View at: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/blob/{GITHUB_BRANCH}/{GITHUB_FILE_PATH}")
    return success


# ── Scheduler ─────────────────────────────────────────────────────────────────

def seconds_until_next_upload():
    """Seconds until next 01:00 UTC (= 8pm EST)."""
    now   = datetime.now(timezone.utc)
    today = now.replace(hour=UPLOAD_HOUR_UTC, minute=UPLOAD_MINUTE_UTC,
                        second=0, microsecond=0)
    target = today if now < today else today + timedelta(days=1)
    return (target - now).total_seconds()


def run_scheduler():
    print("=" * 60)
    print(" Collatz Frontier — Nightly Uploader")
    print("=" * 60)
    print(f" Target     : {UPLOAD_HOUR_UTC:02d}:{UPLOAD_MINUTE_UTC:02d} UTC (8:00 PM EST)")
    print(f" Repo       : github.com/{GITHUB_OWNER}/{GITHUB_REPO}")
    print(f" File       : {GITHUB_FILE_PATH}")
    print(f" Checkpoint : {CHECKPOINT_FILE}")
    print()

    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN environment variable is not set.")
        print("  export GITHUB_TOKEN='ghp_your_token_here'")
        print("  Get a token at: https://github.com/settings/tokens")
        sys.exit(1)

    while True:
        wait = seconds_until_next_upload()
        h, rem = divmod(int(wait), 3600)
        m, s   = divmod(rem, 60)
        next_run = datetime.now(timezone.utc) + timedelta(seconds=wait)
        print(
            f"  Next upload in {h}h {m}m {s}s  "
            f"(at {next_run.strftime('%Y-%m-%d %H:%M UTC')})"
        )

        time.sleep(wait)
        do_upload()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload Collatz frontier status to GitHub nightly at 8pm EST."
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Upload immediately and exit (use with cron instead of scheduler)."
    )
    parser.add_argument(
        "--token",
        default="",
        help="GitHub Personal Access Token (overrides GITHUB_TOKEN env var)."
    )
    args = parser.parse_args()

    if args.token:
        GITHUB_TOKEN = args.token

    if args.now:
        success = do_upload()
        sys.exit(0 if success else 1)
    else:
        try:
            run_scheduler()
        except KeyboardInterrupt:
            print("\n  Uploader stopped.")
            sys.exit(0)
