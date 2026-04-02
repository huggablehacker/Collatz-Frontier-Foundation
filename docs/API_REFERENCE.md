# Collatz Frontier — API Reference

**Base URL:** `http://YOUR_COORDINATOR_IP:5555`  (HTTP) or `https://YOUR_DOMAIN` (HTTPS with certbot)
**Protocol:** HTTP/1.1 or HTTPS/1.1 — see [HTTPS Configuration](#https-configuration) below  
**Content-Type:** All POST bodies must be `application/json`  
**Authentication:** None by default (see Security Assessment — H1)

---

## Table of Contents

- [HTTPS Configuration](#https-configuration)
- [GET /chunk](#get-chunk)
- [POST /results](#post-results)
- [GET /mobile_chunk](#get-mobile_chunk)
- [POST /verify](#post-verify)
- [GET /status](#get-status)
- [GET /workers](#get-workers)
- [GET /milestones](#get-milestones)
- [GET /join](#get-join)
- [GET /sw.js](#get-swjs)
- [Data Structures](#data-structures)
- [Error Responses](#error-responses)
- [Milestone Names Reference](#milestone-names-reference)

---

## HTTPS Configuration

With certbot installed there are two ways to enable HTTPS. Both work — Option B is recommended for most deployments.

### Option A — Direct TLS (Gunicorn handles certs, no nginx)

Gunicorn reads the certbot certificates directly. Simpler setup, no nginx required.

```bash
gunicorn -w 1 --threads 32 \
  --certfile /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem \
  --keyfile  /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem \
  -b 0.0.0.0:443 \
  collatz_coordinator:app
```

Or via CLI flags:
```bash
python3 collatz_coordinator.py \
  --certfile /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem \
  --keyfile  /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem \
  --port 443
```

Workers connect using `https://`:
```bash
python3 collatz_worker.py --coordinator https://YOUR_DOMAIN
```

---

### Option B — nginx Reverse Proxy (certbot's default, recommended)

certbot typically configures nginx automatically. nginx terminates TLS on port 443 and forwards to the coordinator on `localhost:5555`.

**nginx config** (certbot usually writes this automatically — verify it includes the proxy headers):
```nginx
server {
    listen 443 ssl;
    server_name YOUR_DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;

    location / {
        proxy_pass         http://localhost:5555;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   Host              $host;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name YOUR_DOMAIN;
    return 301 https://$host$request_uri;
}
```

**Set `COLLATZ_PROXY=1`** in your service file so the coordinator knows it's behind a proxy. Without this, `request.scheme` returns `http` internally even though clients connect via `https`, and generated URLs (QR code, mobile worker `BASE_URL`) will be wrong:

```bash
# /etc/systemd/system/collatz.service
Environment="COLLATZ_PROXY=1"
Environment="COLLATZ_DOMAIN=YOUR_DOMAIN"
```

Then restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart collatz
```

---

### Environment Variables for HTTPS

| Variable | Description |
|---|---|
| `COLLATZ_PROXY=1` | Activates `ProxyFix` — makes `request.scheme` return `https` when behind nginx. Required for Option B. |
| `COLLATZ_DOMAIN=host` | Sets the public hostname shown in the startup banner and used to build worker connection URLs. |
| `COLLATZ_CERTFILE=path` | Path to `fullchain.pem`. Used with direct TLS (Option A). |
| `COLLATZ_KEYFILE=path` | Path to `privkey.pem`. Used with direct TLS (Option A). |

### CLI Flags for HTTPS

| Flag | Description |
|---|---|
| `--certfile PATH` | Path to fullchain.pem (enables direct TLS, sets default port to 443) |
| `--keyfile PATH` | Path to privkey.pem (must be paired with --certfile) |
| `--proxy` | Activates ProxyFix for nginx reverse proxy mode |
| `--domain HOST` | Public hostname for banner display |

### What ProxyFix does

`ProxyFix` is Werkzeug middleware that reads the `X-Forwarded-Proto` header set by nginx. Without it, the coordinator sees all requests as `http://` even when the client connected via `https://`. This breaks:

- The QR code on `/status` — would generate `http://` URLs
- The `BASE_URL` constant in `/join` and `/sw.js` — mobile workers would try to connect over HTTP
- The worker connection URL printed in the startup banner

---

## GET /chunk

Request the next chunk of odd integers to test. Used by Python workers.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `worker` | string | No | Display name for this worker (shown in leaderboard). Defaults to `"unknown"`. |
| `worker_id` | string | No | UUID from `collatz_identity.json`. Used for persistent identity tracking and milestone attribution. |
| `hostname` | string | No | Machine hostname. Stored in registry for display and cleanup operations. |

### Response

**200 OK**

```json
{
  "chunk_id":   1042,
  "start":      295147905179852825857,
  "end":        295147905179853825855,
  "chunk_size": 500000
}
```

| Field | Type | Description |
|---|---|---|
| `chunk_id` | integer | Unique chunk identifier. Must be sent back with `/results`. |
| `start` | integer | First odd integer to test (inclusive). Always odd. |
| `end` | integer | Last odd integer to test (inclusive). Always odd. |
| `chunk_size` | integer | Number of odd integers in this chunk. |

### Behavior

- Atomically advances the coordinator's frontier pointer by `chunk_size * 2` each call.
- Records the chunk as in-flight. If not completed within `STALE_TIMEOUT` (600 seconds), the chunk is re-issued to the next requester.
- If `worker_id` is provided and not yet registered, creates a new entry in `worker_registry`.
- Saves checkpoint on every call.

### Example

```bash
curl "http://coordinator:5555/chunk?worker=rig-1&worker_id=864bb37e-cf58-4abd-8cfe-04b8e6b89cbc&hostname=mybox"
```

---

## POST /results

Submit completed results for a chunk. Used by Python workers after processing.

### Request Body

```json
{
  "chunk_id":    1042,
  "worker":      "rig-1",
  "worker_id":   "864bb37e-cf58-4abd-8cfe-04b8e6b89cbc",
  "count":       500000,
  "elapsed_sec": 0.621,
  "fails":       []
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `chunk_id` | integer | Yes | The `chunk_id` returned from `/chunk`. |
| `worker` | string | No | Display name. Updates worker_stats display name. |
| `worker_id` | string | No | UUID from identity file. Used as the stats key if provided. |
| `count` | integer | Yes | Number of odd integers actually tested in this chunk. |
| `elapsed_sec` | float | Yes | Wall-clock seconds taken to process the chunk. Used for speed calculation. |
| `fails` | array | Yes | Array of FAIL objects (see below). Empty array `[]` is the normal case. |

#### FAIL Object

```json
{
  "n":     "295147905179852912345",
  "steps": 10000001,
  "peak":  "999999999999999999999999"
}
```

| Field | Type | Description |
|---|---|---|
| `n` | string or integer | The starting number that failed. |
| `steps` | integer | Compressed Syracuse steps taken before hitting the step limit. |
| `peak` | string or integer | Maximum value reached during the sequence. |

### Response

**200 OK — Normal case (no milestone)**

```json
{
  "status": "ok"
}
```

**200 OK — Milestone crossed**

```json
{
  "status": "ok",
  "milestones_crossed": [
    {
      "milestone":   "Sextillion",
      "crossed_at":  "2026-04-15 20:00:01",
      "frontier_n":  "1000000000000000000001",
      "claim_token": "a3f8c2d1e5b9f0c7a4d8e2f6b1c9d3e7f4a8b2c6d0e4f8a1b5c9d3e7f2a6b0",
      "prize":       10000
    }
  ]
}
```

#### milestones_crossed Entry

| Field | Type | Description |
|---|---|---|
| `milestone` | string | Name of the milestone crossed (e.g. `"Sextillion"`). |
| `crossed_at` | string | Timestamp when the crossing was detected (`"YYYY-MM-DD HH:MM:SS"`). |
| `frontier_n` | string | The frontier value at the moment of crossing. |
| `claim_token` | string | 64-character hex HMAC-SHA256 token. **Save this immediately.** |
| `prize` | integer or null | Prize amount in USD, or null for pre-verified milestones. |

### Behavior

- Increments `chunks_done`, `total_tested`, and `fails` counters.
- Removes the chunk from the in-flight set.
- Updates `worker_stats` for the submitting worker.
- Runs milestone detection against the updated frontier.
- Checkpoints every `CHECKPOINT_EVERY` (50) chunks, or immediately on any FAIL or milestone crossing.

### Example

```bash
curl -X POST http://coordinator:5555/results \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_id": 1042,
    "worker": "rig-1",
    "worker_id": "864bb37e-cf58-4abd-8cfe-04b8e6b89cbc",
    "count": 500000,
    "elapsed_sec": 0.621,
    "fails": []
  }'
```

---

## GET /mobile_chunk

Request a small chunk sized for mobile browser workers. Used by the `/join` page JavaScript. Identical behavior to `/chunk` but with a fixed chunk size of 2,000 odd integers and returns `start`/`end` as strings (required for JavaScript `BigInt` parsing).

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `worker` | string | No | Display name. |
| `worker_id` | string | No | UUID from browser `localStorage`. |
| `hostname` | string | No | Browser user agent string (truncated to 40 chars). |

### Response

**200 OK**

```json
{
  "chunk_id":   2841,
  "start":      "295147905179852825857",
  "end":        "295147905179852829855",
  "chunk_size": 2000
}
```

> **Note:** `start` and `end` are returned as **strings**, not integers. JavaScript's `Number` type cannot represent integers above 2⁵³ accurately. Parse with `BigInt(start)`.

### Example

```javascript
const resp = await fetch('/mobile_chunk?worker=iPhone-x7f2&worker_id=uuid-here');
const { start, end, chunk_id } = await resp.json();
const startN = BigInt(start);  // correct
const startBad = start * 1;   // WRONG — precision loss
```

---

## POST /verify

Cryptographically verify a prize claim token. Used to prove that a specific worker crossed a specific milestone frontier.

### Request Body

```json
{
  "worker_id":   "864bb37e-cf58-4abd-8cfe-04b8e6b89cbc",
  "milestone":   "Sextillion",
  "frontier_n":  "1000000000000000000001",
  "crossed_at":  "2026-04-15 20:00:01",
  "claim_token": "a3f8c2d1e5b9f0c7a4d8e2f6b1c9d3e7f4a8b2c6d0e4f8a1b5c9d3e7f2a6b0"
}
```

All five fields are required. They come directly from the worker's `collatz_identity.json` milestone entry.

| Field | Type | Description |
|---|---|---|
| `worker_id` | string | The worker's UUID. |
| `milestone` | string | The milestone name (see [Milestone Names Reference](#milestone-names-reference)). |
| `frontier_n` | string | The frontier value from the identity file entry. |
| `crossed_at` | string | The timestamp from the identity file entry. |
| `claim_token` | string | The 64-character hex token from the identity file entry. |

### Response — Valid Claim

**200 OK**

```json
{
  "valid":       true,
  "message":     "Claim verified. Sextillion was crossed by this worker.",
  "milestone":   "Sextillion",
  "worker_id":   "864bb37e-cf58-4abd-8cfe-04b8e6b89cbc",
  "worker_name": "rig-1",
  "hostname":    "mybox.local",
  "ip":          "192.168.1.5",
  "crossed_at":  "2026-04-15 20:00:01",
  "frontier_n":  "1000000000000000000001",
  "prize":       "$10,000"
}
```

### Response — Invalid Claim

**400 Bad Request**

```json
{
  "valid":   false,
  "message": "Claim token does not match — token may be tampered or worker_id incorrect"
}
```

Possible `message` values:

| Message | Cause |
|---|---|
| `"Missing required fields: ..."` | One or more fields not provided. |
| `"Unknown milestone: X"` | `milestone` is not a recognized name. |
| `"X has not been crossed yet"` | The milestone exists but hasn't been reached. |
| `"Claim token does not match ..."` | HMAC verification failed — wrong fields or tampered token. |
| `"Token is cryptographically valid but this worker_id (...) does not match the recorded winner."` | Token is authentic but issued to a different worker. |

### How Verification Works

The coordinator computes:
```
expected = HMAC-SHA256(coordinator_secret, worker_id + ":" + milestone + ":" + frontier_n + ":" + crossed_at)
```
and compares it to `claim_token` using a timing-safe comparison (`hmac.compare_digest`). Only the coordinator that issued the token can verify it, because only it knows `coordinator_secret`.

### Example

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

---

## GET /status

Returns the live coordinator dashboard as HTML. Not a JSON API — intended for browser viewing.

**URL:** `http://coordinator:5555/status`

Auto-refreshes every 15 seconds. Shows: frontier position, chunks issued/done, numbers covered, session rate, active workers (as pills), in-flight chunks table, and a QR code linking to `/join`.

---

## GET /workers

Returns the top 50 workers leaderboard as HTML. Not a JSON API.

**URL:** `http://coordinator:5555/workers`

Auto-refreshes every 15 seconds. Sorted by lifetime numbers tested descending. Shows: rank (gold/silver/bronze for top 3), worker name, UUID prefix, hostname, numbers tested, chunks done, average speed, FAILs found, active/idle status, last seen timestamp. Workers who have crossed a milestone show a gold trophy badge.

---

## GET /milestones

Returns the milestone crossing hall of fame as HTML. Not a JSON API.

**URL:** `http://coordinator:5555/milestones`

Auto-refreshes every 15 seconds. Shows: the prize pool banner, progress bar, and a table of all 19 milestones with their status (pre-verified / crossed / pending), prize amount, crossing timestamp, worker name + UUID, frontier value at crossing, and a "verify claim" button for crossed milestones.

---

## GET /join

Returns the mobile browser worker page as HTML. Not a JSON API.

**URL:** `http://coordinator:5555/join`

Serves a self-contained single-page application that runs the Collatz Syracuse kernel in JavaScript using `BigInt`. Handles its own identity generation (`localStorage`), chunk requests (`/mobile_chunk`), result posting (`/results`), milestone notifications, and the identity backup modal. Intended to be opened by scanning the QR code on `/status`.

---

## GET /sw.js

Returns the Service Worker JavaScript. Not a JSON API — consumed automatically by the browser on the `/join` page.

**URL:** `http://coordinator:5555/sw.js`

Implements background compute that survives tab navigation on Android Chrome. Contains the full Syracuse kernel, chunk/results fetch logic, and a `postMessage` channel back to the main page for log messages, result notifications, and milestone alerts.

---

## Data Structures

### collatz_identity.json (Worker Identity File)

Generated on first run of `collatz_worker.py` or `collatz_frontier_fast.py`. Stored in the working directory. **Never transmitted to the coordinator.**

```json
{
  "worker_id":   "864bb37e-cf58-4abd-8cfe-04b8e6b89cbc",
  "name":        "rig-1",
  "hostname":    "mybox.local",
  "ip":          "192.168.1.5",
  "secret_key":  "68c06c9d135d1b80...",
  "created_at":  "2026-03-29 01:18:38",
  "milestones":  {
    "Sextillion": {
      "claim_token": "a3f8c2d1...",
      "crossed_at":  "2026-04-15 20:00:01",
      "frontier_n":  "1000000000000000000001",
      "prize":       "$10,000"
    }
  }
}
```

| Field | Description |
|---|---|
| `worker_id` | UUID4. Permanent. Used as the coordinator-side key for stats and registry. |
| `name` | Display name. Mutable — updates on each run if `--name` changes. |
| `hostname` | Machine hostname at creation time. |
| `ip` | LAN IP at creation time. |
| `secret_key` | 64 hex chars (256-bit random). **Never sent anywhere.** Reserved for future challenge-response authentication. |
| `created_at` | ISO timestamp of first run. |
| `milestones` | Dict of milestones crossed by this worker. Keys are milestone names. |

### Checkpoint File (collatz_coordinator_checkpoint.json)

Internal coordinator state. Written atomically (write `.tmp` → rename). **Should be chmod 600.**

```json
{
  "next_n":         295147905179852825857,
  "chunk_size":     500000,
  "chunks_issued":  14200,
  "chunks_done":    14198,
  "total_tested":   7099000000,
  "fails":          0,
  "worker_stats":   { ... },
  "worker_registry": { ... },
  "milestone_log":  { ... },
  "coordinator_secret": "0c5d2b..."
}
```

> `coordinator_secret` — the HMAC key for all prize claim tokens. **Never share this.**

---

## Error Responses

All JSON endpoints return standard HTTP status codes.

| Code | Meaning |
|---|---|
| `200` | Success. |
| `400` | Bad request — missing fields, unknown milestone, invalid token. |
| `404` | Route not found. |
| `500` | Internal server error (check coordinator logs). |

There is currently no `401 Unauthorized` or `429 Too Many Requests` — see Security Assessment findings H1 and H2.

---

## Milestone Names Reference

These are the exact strings accepted by `/verify` and returned in `milestones_crossed`:

| Name | Value | Prize | Notes |
|---|---|---|---|
| `"Trillion"` | 10¹² | — | Pre-verified (Oliveira e Silva 2010) |
| `"Quadrillion"` | 10¹⁵ | — | Pre-verified |
| `"Quintillion"` | 10¹⁸ | — | Pre-verified |
| `"Sextillion"` | 10²¹ | $10,000 | First claimable milestone |
| `"Septillion"` | 10²⁴ | $20,000 | |
| `"Octillion"` | 10²⁷ | $40,000 | |
| `"Nonillion"` | 10³⁰ | $80,000 | |
| `"Decillion"` | 10³³ | $160,000 | |
| `"Undecillion"` | 10³⁶ | $320,000 | |
| `"Duodecillion"` | 10³⁹ | $640,000 | |
| `"Tredecillion"` | 10⁴² | $1,280,000 | |
| `"Quattuordecillion"` | 10⁴⁵ | $2,560,000 | |
| `"Quindecillion"` | 10⁴⁸ | $5,120,000 | |
| `"Sexdecillion"` | 10⁵¹ | $10,240,000 | |
| `"Septendecillion"` | 10⁵⁴ | $20,480,000 | |
| `"Octodecillion"` | 10⁵⁷ | $40,960,000 | |
| `"Novemdecillion"` | 10⁶⁰ | $81,920,000 | |
| `"Vigintillion"` | 10⁶³ | $163,840,000 | |
| `"Centillion"` | 10³⁰³ | $327,680,000 | |

**Total prize pool: $655,350,000**
