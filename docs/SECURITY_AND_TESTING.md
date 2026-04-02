# Collatz Frontier — Security Assessment & Testing Plan

**Date:** 2026-03-29  
**Scope:** All components — coordinator, worker, mobile worker, prize system, nightly uploader, Windows package, systemd services, cleanup script  
**Threat model:** Hobbyist distributed compute project, internet-facing coordinator, real financial prizes (~$655M pool)

---

## Executive Summary

The system is well-designed for its purpose and the crypto underpinning the prize system (`HMAC-SHA256` with `hmac.compare_digest`) is sound. The primary risks are:

1. **No authentication on any endpoint** — anyone who can reach port 5555 can interact with the coordinator
2. **No TLS** — claim tokens travel in plaintext over HTTP
3. **`coordinator_secret` stored world-readable** — the root prize key has no file permission protection
4. **No rate limiting** — coordinator is trivially DoS-able and prize-verification endpoint is enumerable
5. **Mobile claim tokens in `localStorage`** — one browser data clear = lost prize proof

None of these are showstoppers for a trusted-network deployment. Several need attention before exposing the coordinator to the open internet.

---

## 1. Attack Surface Map

| Component | Exposure | Auth Required | Notes |
|---|---|---|---|
| `GET /chunk` | Network | None | Any host can pull work |
| `POST /results` | Network | None | Any host can post fake results |
| `GET /status` | Network | None | Leaks frontier position |
| `GET /workers` | Network | None | Leaks worker names/hostnames |
| `GET /milestones` | Network | None | Leaks prize claim status |
| `POST /verify` | Network | None | Public prize verification |
| `GET /join` | Network | None | Serves mobile worker JS |
| `GET /sw.js` | Network | None | Service worker JS |
| `GET /mobile_chunk` | Network | None | Mobile chunk dispatch |
| Checkpoint JSON | Filesystem | OS user | Contains `coordinator_secret` |
| Identity JSON | Filesystem | OS user | Contains `secret_key` |
| Service unit files | Filesystem | Root | May contain `GITHUB_TOKEN` |

---

## 2. Findings by Severity

---

### CRITICAL

#### C1 — `coordinator_secret` stored world-readable

**File:** `collatz_coordinator_checkpoint.json`  
**Current permissions:** `-rw-r--r--` (644) — readable by all users on the machine  
**Impact:** Anyone with local shell access can read the HMAC key, forge claim tokens for any milestone, and claim all prizes fraudulently.

**Fix:**
```bash
# Immediately after the coordinator first starts and generates the secret:
chmod 600 collatz_coordinator_checkpoint.json

# Better: set umask before launching
umask 077
python3 collatz_coordinator.py
# or in the service file:
# UMask=0077
```

Add to `_startup()`:
```python
import stat
cp = Path(CHECKPOINT_FILE)
if cp.exists():
    cp.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
```

---

#### C2 — Claim tokens transmitted over plain HTTP

**Impact:** Any network observer between a worker and the coordinator can intercept the claim token from the `/results` POST response. With the token and the worker's identity file, they can claim the prize.

**Fix — Option A (easy, no cert needed):** Enforce the coordinator runs behind a reverse proxy with TLS:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/yourdomain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain/privkey.pem;
    location / { proxy_pass http://localhost:5555; }
}
```

**Fix — Option B (LAN-only, no internet exposure):** Document clearly that the coordinator must only be run on a trusted LAN, and tokens are only valid on that network. Add a banner to `/status` and the README.

---

### HIGH

#### H1 — No authentication on `/results` — fake work injection

**Impact:** Any host that can reach port 5555 can POST fake results, artificially inflating any worker's `tested` count and `chunks_done`, polluting the leaderboard and potentially triggering milestone crossings for numbers that were never actually tested.

**Realistic attack:**
```bash
curl -X POST http://coordinator:5555/results \
  -H "Content-Type: application/json" \
  -d '{"chunk_id":99999,"worker":"attacker","worker_id":"fake-uuid","count":999999999,"elapsed_sec":0.001,"fails":[]}'
```

**Impact on prize system:** If the attacker's UUID matches a milestone crossing, they get a valid claim token for a number they didn't test.

**Fix:** Add a shared secret to the worker ↔ coordinator protocol:
```python
# In coordinator constants:
WORKER_TOKEN = os.environ.get("COLLATZ_WORKER_TOKEN", "")

# In post_results:
if WORKER_TOKEN:
    provided = request.headers.get("X-Worker-Token", "")
    if not hmac.compare_digest(provided, WORKER_TOKEN):
        return jsonify({"error": "unauthorized"}), 401
```

Workers then set `session.headers["X-Worker-Token"] = WORKER_TOKEN`.

---

#### H2 — No rate limiting on `/verify`

**Impact:** An attacker who knows a valid `worker_id`, `milestone`, `frontier_n`, and `crossed_at` (all logged in `milestone_log` inside the checkpoint) only needs to brute-force the 64-hex-character claim token. At 256-bit entropy this is computationally infeasible — BUT they can also use `/verify` to confirm whether a stolen token is valid, and enumerate which milestone/worker combinations exist.

**Fix:** Rate limit `/verify` to e.g. 10 requests/minute per IP:
```python
from collections import defaultdict
_verify_attempts = defaultdict(list)

@app.route("/verify", methods=["POST"])
def verify_claim():
    ip  = request.remote_addr
    now = time.time()
    _verify_attempts[ip] = [t for t in _verify_attempts[ip] if now - t < 60]
    if len(_verify_attempts[ip]) >= 10:
        return jsonify({"error": "rate limited"}), 429
    _verify_attempts[ip].append(now)
    # ... rest of handler
```

---

#### H3 — `coordinator_secret` has no backup/rotation mechanism

**Impact:** If the checkpoint file is lost or corrupted, the coordinator secret is gone. All existing claim tokens become unverifiable. Prize claims from before the loss cannot be validated.

**Fix:** Print the secret to stdout on first generation (one time only), and instruct the operator to write it down / store in a password manager. Add a manual backup command:
```bash
python3 -c "
import json
cp = json.load(open('collatz_coordinator_checkpoint.json'))
print('COORDINATOR SECRET (keep this safe):')
print(cp['coordinator_secret'])
"
```

---

### MEDIUM

#### M1 — `identity.json` and service unit files have no permission guidance

**Files:** `collatz_identity.json`, `/etc/systemd/system/collatz*.service`  
**Impact:** Service unit files may contain `GITHUB_TOKEN` in plaintext. Identity files contain `secret_key`. Both are world-readable by default.

**Fix:**
```bash
# Identity file — worker machines
chmod 600 collatz_identity.json

# Service file with GitHub token
sudo chmod 600 /etc/systemd/system/collatz-uploader.service
# Better: use systemd credentials or a separate env file:
# EnvironmentFile=/etc/collatz/secrets.env  (chmod 600, owned by service user)
```

---

#### M2 — Mobile `localStorage` claim tokens have no redundancy

**Impact:** Browser "Clear site data" silently destroys claim tokens. There is no server-side record of which token was issued (only which worker_id crossed which milestone). A user who clears their browser cannot re-request their token.

**Partial fix already in place:** The "View My Identity" modal and Copy button.  
**Additional fix needed:** The coordinator should store a copy of issued claim tokens server-side in `milestone_log`, so the coordinator owner can re-issue a token to a worker who lost theirs (after manual identity verification):

```python
# In milestone_log entries, store the token server-side too:
milestone_log[name] = {
    ...
    "claim_token": token,  # already done — good
}
```

This is actually already implemented. The coordinator can re-derive any token given the four inputs (worker_id, milestone, frontier_n, crossed_at) since `_generate_claim_token` is deterministic. The coordinator owner can run `/verify` with the stored values to confirm and re-issue manually.

---

#### M3 — No input validation on POST /results

**Impact:** A malicious worker can send arbitrarily large `count` values, negative values, or non-numeric `elapsed_sec` to corrupt statistics.

**Fix:**
```python
count   = max(0, min(int(data.get("count",   0)), state["chunk_size"] * 2))
elapsed = max(0.001, float(data.get("elapsed_sec", 1)))
```

---

#### M4 — `/status`, `/workers`, `/milestones` leak operational intelligence

**Impact:** An adversary can monitor frontier progress, worker names, hostnames, and milestone crossing times without contributing. On a LAN this is fine; on the open internet it may not be desirable.

**Fix:** Add optional HTTP Basic Auth for the dashboard pages only:
```python
import base64
DASHBOARD_PASSWORD = os.environ.get("COLLATZ_DASHBOARD_PASSWORD", "")

def check_dashboard_auth():
    if not DASHBOARD_PASSWORD:
        return True  # no password set — open
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        try:
            creds = base64.b64decode(auth[6:]).decode()
            _, pwd = creds.split(":", 1)
            return hmac.compare_digest(pwd, DASHBOARD_PASSWORD)
        except Exception:
            pass
    return False
```

---

#### M5 — Cleanup script has no lock against running while coordinator is up

**Impact:** Running `collatz_cleanup.py` while the coordinator is running creates a race condition — the coordinator may write the checkpoint mid-cleanup, losing changes or corrupting state.

**Fix:** Check if the coordinator port is active before writing:
```python
import socket
def coordinator_is_running(port=5555):
    with socket.socket() as s:
        return s.connect_ex(('localhost', port)) == 0

if coordinator_is_running():
    print("ERROR: Coordinator appears to be running on port 5555.")
    print("Stop it first: sudo systemctl stop collatz")
    return 1
```

---

### LOW

#### L1 — External CDN dependency in `/status` page

**File:** `https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js`  
**Impact:** If cdnjs is unreachable the QR code silently fails (gracefully handled with try/catch). Not a security risk on its own, but a supply-chain concern — a compromised CDN could inject malicious JS into the coordinator's dashboard.

**Fix:** Vendor the QR code library locally, served from the coordinator itself.

---

#### L2 — `hmac.new()` should be `hmac.new()`

**Current code:**
```python
return hmac.new(
    coordinator_secret.encode(),
    msg,
    hashlib.sha256
).hexdigest()
```

This is correct Python — `hmac.new()` is the right call. No issue here. ✓

---

#### L3 — `worker_id` is self-reported — no binding proof

**Impact:** A worker can claim any `worker_id` in its requests. There's no cryptographic proof that the worker actually owns the UUID it claims. This matters for milestone attribution: an attacker who knows a target's `worker_id` could post results under that ID and steal the milestone crossing credit.

**Mitigating factor:** They would still need the coordinator secret to forge the claim token. The coordinator secret is never exposed via the API. So attribution can be stolen but the claim token itself cannot be forged.

**Fix (future):** Use a challenge-response: the coordinator issues a random nonce with each chunk, and the worker signs it with their `secret_key`. The coordinator verifies the signature using the public portion. This makes UUID ownership provable without transmitting the secret.

---

#### L4 — No FAIL entry integrity check

**Impact:** A worker can submit fake FAIL entries (`n` values that aren't actually counterexamples) to trigger milestone alerts or pollute the results file. The milestone check is based on `state["next_n"]` (the frontier position) not on FAIL entries, so this doesn't affect prize claims — but it could generate false alarms.

---

## 3. What the Crypto Gets Right

These are explicitly confirmed as sound:

| Mechanism | Assessment |
|---|---|
| `HMAC-SHA256` for claim tokens | ✅ Correct algorithm |
| `hmac.compare_digest()` for verification | ✅ Timing-safe comparison — prevents timing attacks |
| `secrets.token_hex(32)` for coordinator secret | ✅ 256-bit CSPRNG — computationally unbreakable |
| `secrets.token_hex(32)` for worker secret_key | ✅ Good entropy |
| `uuid.uuid4()` for worker IDs | ✅ 122-bit random — collision probability negligible |
| HMAC includes `frontier_n` and `crossed_at` | ✅ Prevents replay across milestones |
| Token stored in milestone_log server-side | ✅ Allows re-derivation if worker loses theirs |

---

## 4. Testing Plan

### 4.1 Unit Tests

#### T-U1: HMAC token generation and verification
```python
def test_hmac_roundtrip():
    # Token verifies against its own inputs
    token = _generate_claim_token("uuid-a", "Sextillion", "123456", "2026-04-01 20:00:00")
    assert verify_claim_token("uuid-a", "Sextillion", "123456", "2026-04-01 20:00:00", token)

def test_hmac_wrong_worker():
    token = _generate_claim_token("uuid-a", "Sextillion", "123456", "2026-04-01 20:00:00")
    assert not verify_claim_token("uuid-b", "Sextillion", "123456", "2026-04-01 20:00:00", token)

def test_hmac_wrong_milestone():
    token = _generate_claim_token("uuid-a", "Sextillion", "123456", "2026-04-01 20:00:00")
    assert not verify_claim_token("uuid-a", "Septillion", "123456", "2026-04-01 20:00:00", token)

def test_hmac_tampered_token():
    token = _generate_claim_token("uuid-a", "Sextillion", "123456", "2026-04-01 20:00:00")
    bad   = token[:-4] + "0000"
    assert not verify_claim_token("uuid-a", "Sextillion", "123456", "2026-04-01 20:00:00", bad)
```

#### T-U2: Milestone detection logic
```python
def test_milestone_crossed():
    # Frontier passing through a milestone boundary triggers detection
    # Frontier before Sextillion (10^21) — should not trigger
    # Frontier after Sextillion — should trigger exactly once

def test_pre_verified_milestones():
    # Trillion, Quadrillion, Quintillion are seeded at startup
    # They should never be re-recorded if frontier advances past them
```

#### T-U3: Checkpoint atomic write
```python
def test_checkpoint_atomic():
    # Write should use .tmp + rename, not direct write
    # Verify no partial-write state is possible by checking
    # the .tmp file is cleaned up after save_checkpoint()
```

#### T-U4: Cleanup script merge logic
```python
def test_merge_token_holder_wins():
    # Worker with fewer tested numbers but a token wins over
    # worker with more tested numbers but no token

def test_merge_sums_correctly():
    # chunks, tested, fails, total_sec all sum across merged workers

def test_merge_timestamps():
    # first_seen = earliest across all merged
    # last_seen  = latest across all merged
```

#### T-U5: Syracuse kernel correctness
```python
def test_known_sequences():
    # 27 -> 1 in exactly 111 steps (standard reference)
    # 871 -> peak 190996 (known record for small numbers)
    
def test_odd_only_equivalence():
    # Verify that testing only odd n gives identical coverage
    # as testing all n >= threshold

def test_early_exit_correctness():
    # A sequence that drops below 2^68 is correctly flagged PASS
    # even if it hasn't reached 1 yet
```

---

### 4.2 Integration Tests

#### T-I1: Full coordinator + worker cycle
```bash
# Start coordinator, run worker for 10 chunks, verify:
# - chunks_done == 10 in checkpoint
# - total_tested == 10 * chunk_size
# - worker appears in worker_stats and worker_registry
# - no FAILs in results file
```

#### T-I2: Worker reconnect after coordinator restart
```bash
# Start coordinator + worker
# Kill coordinator mid-chunk
# Restart coordinator
# Worker should reconnect automatically within RestartSec (10s)
# Stale chunk should be re-issued after STALE_TIMEOUT
# No numbers should be double-counted (monotonic frontier)
```

#### T-I3: Milestone crossing end-to-end
```bash
# Set DEFAULT_START just below a milestone (e.g. Sextillion - 10000)
# Run worker
# Verify:
#   - milestone_log["Sextillion"] is set with claim_token
#   - worker's identity file has the token
#   - /verify endpoint confirms the token as valid
#   - /milestones page shows the milestone as crossed
```

#### T-I4: Fake results injection
```bash
# POST to /results with inflated count (chunk_id that was never issued)
# Verify coordinator handles gracefully — no crash, no state corruption
# (chunk not in in_flight — just a no-op pop)
```

#### T-I5: Multiple workers, correct frontier progression
```bash
# Run 3 workers simultaneously
# Verify:
#   - No two workers receive overlapping chunk ranges
#   - Frontier advances monotonically
#   - Sum of all workers' tested == total_tested in checkpoint
```

#### T-I6: /verify endpoint
```bash
# Valid claim → 200 + {valid: true}
# Wrong worker_id → 400 + {valid: false}
# Tampered token → 400 + {valid: false}
# Unknown milestone → 400 + {valid: false}
# Missing fields → 400 + {valid: false, message: "Missing required fields"}
# Milestone not yet crossed → 400 + {valid: false}
```

#### T-I7: Mobile worker identity persistence
```bash
# Open /join in a browser
# Start worker, complete 5 chunks
# Close tab, reopen /join
# Verify: same worker_id loaded from localStorage
# Verify: worker appears in /workers leaderboard by UUID
```

#### T-I8: Cleanup script safety
```bash
# Run cleanup with --dry-run — verify checkpoint unchanged (byte-identical)
# Run cleanup on a fresh checkpoint with no duplicates — verify "nothing to do"
# Run cleanup with --merge-by-hostname — verify merged worker has correct totals
# Verify backup file is always written before any live run
```

---

### 4.3 Security-Specific Tests

#### T-S1: Token timing safety
```python
# Verify verify_claim_token uses hmac.compare_digest not ==
# Time 1000 calls with wrong token vs right token — variance should be <5%
import time
wrong = "0" * 64
right = _generate_claim_token("id", "Sextillion", "n", "ts")
# Both should take ~identical time
```

#### T-S2: Coordinator secret uniqueness
```bash
# Delete checkpoint, start coordinator, record secret
# Delete checkpoint again, restart, record new secret
# Verify secrets are different (no hardcoded default)
```

#### T-S3: File permission check (post-fix)
```bash
ls -la collatz_coordinator_checkpoint.json  # should be 600
ls -la collatz_identity.json                # should be 600
```

#### T-S4: Replay attack resistance
```python
# Token for "Sextillion" should not verify as "Septillion"
# Token for worker-A should not verify for worker-B
# Token with correct fields but wrong frontier_n should fail
```

#### T-S5: Fake milestone injection via /results
```bash
# POST fake results that would push frontier past Sextillion
# The fake chunk_id won't be in in_flight — verify coordinator
# gracefully skips the in_flight.pop() and doesn't double-count
# Then verify frontier was NOT actually advanced by the fake POST
# (frontier advances only in get_chunk, not post_results)
```

#### T-S6: Large payload DoS
```bash
# POST /results with fails[] containing 100,000 entries
# Verify coordinator doesn't crash or run out of memory
# Verify file write is bounded
```

---

### 4.4 Mobile / Browser Tests

#### T-M1: Identity survival across tab lifecycle
- Close tab → reopen → identity intact ✓
- Navigate away → return → identity intact ✓  
- Hard refresh (Ctrl+Shift+R) → identity intact ✓
- Clear localStorage → identity gone (expected — warning shown) ✓

#### T-M2: Service worker background compute
- Start worker, navigate to different tab → SW continues ✓ (Android Chrome)
- Start worker, lock screen → SW continues for ~30min (Android) ✓
- Start worker on iOS Safari, switch apps → pauses after ~30s (expected limitation) ✓

#### T-M3: Milestone modal on phone
- Manually trigger `showMilestone()` in browser console
- Verify: gold card renders, modal auto-opens, JSON is copyable
- Verify: claim_token highlighted in gold
- Verify: Copy button works on iOS (fallback `execCommand` path)

#### T-M4: Identity modal — Copy JSON
- Open modal, tap Copy
- Paste into Notes/Messages
- Verify: complete valid JSON with all fields

---

### 4.5 Load Tests

#### T-L1: Coordinator under 200 workers
```bash
# Spin up 200 simulated workers (can use threading or locust)
# Each pulls chunks and posts results at realistic speed
# Monitor: response time for /chunk and /results
# Monitor: checkpoint write time (should stay under 50ms at CHECKPOINT_EVERY=50)
# Monitor: memory usage of coordinator process
```

#### T-L2: Gunicorn thread saturation
```bash
# gunicorn -w 1 --threads 32
# Fire 32 simultaneous requests to /chunk
# All 32 should respond within 500ms
# No deadlock on the threading.Lock()
```

---

## 5. Priority Order for Fixes

| Priority | Finding | Effort | Impact |
|---|---|---|---|
| 1 | **C1** — chmod 600 checkpoint | 5 min | Protects coordinator_secret |
| 2 | **C2** — TLS via reverse proxy | 30 min | Protects token transit |
| 3 | **H1** — Worker auth token | 1 hr | Prevents fake result injection |
| 4 | **H3** — Print/backup coordinator secret | 15 min | Disaster recovery |
| 5 | **M5** — Cleanup lock check | 15 min | Prevents race condition |
| 6 | **H2** — Rate limit /verify | 30 min | Prevents enumeration |
| 7 | **M3** — Input validation | 30 min | Prevents stat corruption |
| 8 | **M1** — Env file for GitHub token | 20 min | Reduces secret exposure |
| 9 | **M4** — Dashboard password | 1 hr | Optional privacy |
| 10 | **L1** — Vendor QR library | 20 min | Supply chain hygiene |

---

## 6. Deployment Recommendations

**Minimum safe configuration for internet-facing deployment:**

```bash
# 1. Restrict checkpoint file immediately
chmod 600 collatz_coordinator_checkpoint.json

# 2. Run behind nginx with TLS (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# 3. Firewall — only expose 443 (HTTPS via nginx) not 5555 directly
sudo ufw allow 443
sudo ufw deny 5555

# 4. Add worker shared token to service file
sudo systemctl edit collatz
# Add: Environment="COLLATZ_WORKER_TOKEN=<random 32 char string>"
# Workers must set same token in their service files

# 5. Back up coordinator secret
python3 -c "import json; cp=json.load(open('collatz_coordinator_checkpoint.json')); print(cp['coordinator_secret'])"
# Store output in password manager
```

**For LAN-only deployment (trusted network):**  
Items 1 (chmod) and 4 (backup secret) are still strongly recommended. Items 2 and 3 can wait.
