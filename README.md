# Collatz Frontier

[![GitHub](https://img.shields.io/badge/GitHub-huggablehacker%2FCollatz--Frontier-blue?logo=github)](https://github.com/huggablehacker/Collatz-Frontier)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Frontier](https://img.shields.io/badge/Frontier-Live-brightgreen)](https://github.com/huggablehacker/Collatz-Frontier/blob/main/frontier_log.txt)

A distributed hunt for a counterexample to the **Collatz Conjecture** — one of mathematics' most famous unsolved problems. Every computer that joins pushes the frontier further into uncharted territory. If you find a counterexample, you win a prize.

> *"Mathematics is not yet ready for such problems."* — Paul Erdős

See Live Status [HERE](http://collatzfrontier.ddns.net:5555/status)

---

## What is the Collatz Conjecture?

Take any positive integer. If it's even, divide by 2. If it's odd, multiply by 3 and add 1. Repeat. The conjecture states that no matter what number you start with, you will always eventually reach 1.

Simple to state. Unproven for over 80 years.

Every number up to **2⁶⁸ (295,147,905,179,352,825,856)** has been verified by prior work. This project starts there and keeps going — collaboratively, across any hardware that wants to join.

---

## Prize Pool — $655,350,000

The search is divided into **milestones** — named number thresholds. The first worker whose contribution pushes the frontier past each milestone wins a cash prize. Prizes double at each level:

| Milestone | Value | Prize |
|---|---|---|
| Sextillion | 10²¹ | **$10,000** ← first target |
| Septillion | 10²⁴ | $20,000 |
| Octillion | 10²⁷ | $40,000 |
| Nonillion | 10³⁰ | $80,000 |
| … doubles each level … | | |
| Vigintillion | 10⁶³ | $163,840,000 |
| Centillion | 10³⁰³ | $327,680,000 |

Prizes are verified cryptographically — when your machine crosses a milestone, it receives a unique claim token signed by the network. No token, no prize. No one can fake a crossing.

See the live milestone board at [`frontier_log.txt`](frontier_log.txt).

---

## Join from Your Phone — No App Needed

The easiest way to contribute. Open the network's `/join` page in any mobile browser — the full search algorithm runs in JavaScript, right in your browser tab.

1. Scan the QR code on the `/status` dashboard, or open the link directly
2. Enter your name
3. Tap **Start**

Works on Android Chrome, iPhone, iPad, and any desktop browser. No Python, no install, no account.

**Android Chrome** keeps computing even if you switch apps or lock the screen (Service Worker background mode). iOS Safari stays active while the tab is open.

Your browser generates a permanent identity stored locally. If you cross a milestone, a claim token is saved automatically — tap **View My Identity** to copy and back it up.

---

## Join with Python — Full Speed

For maximum throughput, run the Python worker. It uses all your CPU cores in parallel.

### Requirements

```bash
pip install requests          # required
pip install gmpy2             # optional — 3–5× faster big integer arithmetic
```

### Connect to the network

```bash
cd worker/
python3 collatz_worker.py --coordinator http://collatzfrontier.ddns.net:5555
```

On first run, a `collatz_identity.json` file is created in the current directory — this is your permanent worker identity and your proof of any milestone crossings. **Back it up.**

### Options

```bash
# Custom name (shows in leaderboard)
python3 collatz_worker.py --coordinator http://collatzfrontier.ddns.net:5555 --name my-rig

# Limit cores (leave some for other work)
python3 collatz_worker.py --coordinator http://collatzfrontier.ddns.net:5555 --cores 4
```

Add as many machines as you want at any time. Workers are stateless — they pull chunks, test numbers, and report back.

---

## Make It Headless

Workers die when you close your terminal. To keep them running permanently — surviving reboots and SSH disconnects — install the systemd service:

```bash
cd services/linux/
bash install_worker_service.sh
```

The script asks for the network URL, your worker name, and how many cores to use. After installation:

```bash
sudo systemctl status collatz-worker   # check it's running
journalctl -u collatz-worker -f        # watch live output
sudo systemctl restart collatz-worker  # restart after updates
```

> **Before going headless:** back up your `collatz_identity.json` — it holds your claim tokens:
> ```bash
> cp collatz_identity.json ~/collatz_identity_backup.json
> ```

---

## Windows

No Python required. Download the pre-built package, double-click `launch_worker.bat`, enter the network URL when prompted, and you're contributing.

To build the package yourself:
1. Install Python from python.org (check "Add Python to PATH")
2. Copy all `.py` files and `services/windows/` into one folder
3. Double-click `build_windows.bat`

See `services/windows/HOW-TO.md` for full details.

---

## How Your Contribution Works

Three stacked optimizations make the search ~100× faster than a naive implementation:

| Optimization | Mechanism | Speedup |
|---|---|---|
| **Early exit** | Stop each sequence the moment it drops below 2⁶⁸ | ~10× |
| **Odd-only testing** | Even numbers halve immediately to their odd counterpart — skip them | 2× |
| **Syracuse steps** | Jump directly from odd → next odd via a single bit-shift | ~2× |
| **Combined** | Multiplicative, not additive | **~100×+** |

The network hands each worker a contiguous range of odd integers. Your machine tests every number in that range and reports back. If any sequence runs for more than 10,000,000 compressed steps without re-entering verified territory, it's flagged as a potential counterexample.

---

## Performance

| Setup | Throughput | Notes |
|---|---|---|
| Phone (browser) | ~5,000–20,000 odd/sec | Varies by device |
| 1 core, Python | ~800,000 odd/sec | |
| 8 cores, Python | ~6,400,000 odd/sec | Good laptop or desktop |
| 8 cores + gmpy2 | ~25,000,000 odd/sec | With big-integer speedup |
| 10 machines × 8 cores | ~64,000,000 odd/sec | |

> **Reality check:** Even at 640M/sec across 100 machines, sweeping all of 2⁶⁸ from scratch would take ~974,000 years. The conjecture cannot be proven by brute force — but every new number tested is in genuinely unverified territory, and every milestone is a legitimate mathematical record.

---

## Claiming a Prize

When your machine crosses a milestone, the network responds with a signed claim token. The worker saves it automatically to `collatz_identity.json`:

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

To verify and claim:
1. Go to `/milestones` on the network dashboard
2. Click **verify claim** next to the milestone you crossed
3. Paste the four values from your identity file
4. Open a GitHub Issue titled `Prize Claim: [Milestone Name]` with your verification

The claim token is an HMAC-SHA256 signature — it cryptographically proves that your specific machine, at that specific moment, was responsible for the crossing. It cannot be forged or transferred.

**Back up your identity file.** If you use the browser worker, tap **View My Identity** and copy the JSON somewhere safe — clearing browser data will erase it permanently.

---

## What Happens If Someone Finds a Counterexample?

A counterexample — a number whose Collatz sequence never reaches 1 — would be one of the most significant mathematical discoveries in a century. It would immediately falsify over 80 years of accumulated intuition, provide a concrete object for number theorists to study, and likely reshape large parts of dynamical systems theory.

The statistical likelihood is astronomically small. The expected number of counterexamples below 10¹⁰⁰ is effectively zero. But that is precisely what makes it interesting — every number tested is another brick in an edifice that has held for eight decades, and the prize pool is there because the question is genuinely open.

---

## The Math Behind the Algorithm

### Syracuse step — the key insight

A standard Collatz loop for an odd number `n` produces: `3n+1` (even) → divide repeatedly → next odd. Instead of iterating those intermediate steps individually:

```python
x = 3 * n + 1                        # guaranteed even
k = (x & -x).bit_length() - 1        # count trailing zeros (halvings needed)
next_odd = x >> k                     # strip all factors of 2 in one shift
steps += k + 1                        # account for all skipped steps
```

This reduces ~550 average iterations (at 2⁶⁸ scale) to ~10, with no loss of fidelity.

### Why odd-only is correct

Any even starting number `n` immediately produces `n/2`. If `n/2 < 2⁶⁸` it's already verified. If `n/2 ≥ 2⁶⁸` we'll test it when we reach it. Either way, testing even numbers adds no new information.

### Early exit correctness

Everything below 2⁶⁸ is verified to reach 1 by Oliveira e Silva et al. (2010). Dropping below the threshold is logically equivalent to reaching 1 — without the redundant computation.

---

## Repository Structure

```
Collatz-Frontier/
│
├── worker/                          ← Start here to contribute compute
│   ├── collatz_worker.py            ← Distributed worker (all platforms)
│   ├── collatz_merge.py             ← Merge result files from multiple sources
│   └── HOW-TO.md
│
├── services/
│   ├── linux/                       ← Headless systemd services
│   │   ├── install_worker_service.sh← One-command worker installer
│   │   ├── install_service.sh       ← Network operator installer
│   │   └── HOW-TO.md
│   │
│   └── windows/                     ← Standalone .exe package (no Python needed)
│       ├── launch_worker.bat        ← Double-click to start a worker
│       ├── build_windows.bat        ← Build all .exe files (run once)
│       └── HOW-TO.md
│
└── docs/
    ├── HOW-TO_GUIDE.md              ← Full guide (all roles)
    ├── API_REFERENCE.md             ← Network API documentation
    ├── SECURITY_AND_TESTING.md      ← Security assessment and test plan
    ├── Collatz_Academic_Paper.docx  ← Peer-review paper (Word)
    └── collatz_mcom.tex             ← Peer-review paper (AMS MCOM LaTeX)
```

---

## FAQ

**The output file is empty — did something go wrong?**
No. Empty = the conjecture held for every number tested. This is the expected and hoped-for outcome.

**Can I contribute from my phone?**
Yes — open `/join` in any mobile browser or scan the QR code on the `/status` page. No app or Python needed.

**What does a FAIL actually mean?**
A sequence ran for more than 10,000,000 compressed Syracuse steps without re-entering verified territory. It requires manual investigation but doesn't definitively prove a counterexample. No FAIL has ever been found.

**What if I lose my identity file?**
Open a GitHub Issue with your worker name and approximate crossing date. The network operator can recover and re-issue your claim token from server-side records.

**Will this ever prove the conjecture?**
No. Brute force cannot prove a statement about all integers. A mathematical proof requires a fundamentally different approach — but every verified number strengthens the evidence and every milestone is a mathematical record.

---

## Contributing Code

Pull requests welcome. High-impact directions:

- **C extension** — a C extension for the inner loop would give another 10–50× speedup
- **CUDA / GPU worker** — the inner loop is embarrassingly parallel at the per-number level
- **Adaptive chunk sizing** — tune chunk size based on observed worker throughput
- **launchd plist** — macOS equivalent of the Linux systemd service files

---

## License

MIT. See [LICENSE](https://github.com/huggablehacker/Collatz-Frontier/blob/main/LICENSE) for details.

---

## References

- Collatz, L. (1937). Original conjecture
- Oliveira e Silva, T. (2010). Empirical verification up to 2⁶⁸
- Tao, T. (2022). ["Almost all Collatz orbits attain almost bounded values"](https://arxiv.org/abs/1909.03562)
- Lagarias, J. C. (2010). *The Ultimate Challenge: The 3x+1 Problem*. AMS.
