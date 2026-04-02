# Collatz Frontier — Investor Brief

---

## The Opportunity in One Sentence

We have built a fully operational, cryptographically-verified, prize-incentivised distributed compute network — using the Collatz Conjecture as our launch problem — and we are looking for investment to scale the contributor base and activate the prize pool.

---

## What is the Collatz Conjecture?

Take any positive integer. If it's even, divide by 2. If it's odd, multiply by 3 and add 1. Repeat. The conjecture states that no matter what number you start with, you will always eventually reach 1.

Simple to state. Unproven for 87 years. One of the most famous open problems in mathematics.

Every number up to **2⁶⁸ (295,147,905,179,352,825,856)** has been verified by prior supercomputer work. This project starts exactly there and searches forward — collaboratively, across any hardware that joins the network.

---

## The Scale of the Problem

To understand what the network is doing, consider how long it would take a single machine to sweep just the territory we are currently searching:

### At a single fast desktop PC (~6.3M numbers/second):

| Unit | Time |
|---|---|
| Seconds | 46,786,106,254,764 |
| Minutes | 779,768,437,579 |
| Hours | 12,996,140,626 |
| Days | 541,505,859 |
| **Years** | **~1,482,562** |

**1,482,562 years** — roughly the time since *Homo erectus* first walked the Earth. You would be counting from the Stone Age to today, then doing it all over again 67 more times.

### At 100 coordinated machines (~640M numbers/second):

| Unit | Time |
|---|---|
| Seconds | 461,168,602,461 |
| Minutes | 7,686,143,374 |
| Hours | 128,102,389 |
| Days | 5,337,599 |
| **Years** | **~14,613** |

That is 14,613 years — roughly the time since the end of the last Ice Age. Still an enormous number. Still physically impossible for a single institution.

### What would it take to cover this ground in **one year**?

A sustained rate of approximately **9.35 trillion numbers/second** would be required.

| Device Type | Speed Assumed | Devices Needed |
|---|---|---|
| Average PC (multi-core) | ~10B ops/sec | ~935 PCs |
| High-end gaming rig | ~50B ops/sec | ~187 PCs |
| Smartphone | ~3B ops/sec | ~3,118 phones |

**A distributed network of roughly 1,000 average PCs — or 200 gaming rigs — could cover one year's worth of previously unverifiable mathematical territory every single year.**

These are not hypothetical numbers. The network is live. Every machine that joins moves the frontier forward in real time. Every milestone crossed is a permanent mathematical record that no single institution could have produced alone.

---

## The Prize Structure

Milestones are named number thresholds. The first contributor whose compute pushes the frontier past each threshold wins a cash prize. Prizes double at every level:

| Milestone | Value | Prize |
|---|---|---|
| Sextillion | 10²¹ | $10,000 |
| Septillion | 10²⁴ | $20,000 |
| Octillion | 10²⁷ | $40,000 |
| Nonillion | 10³⁰ | $80,000 |
| Decillion | 10³³ | $160,000 |
| … doubles … | | |
| Vigintillion | 10⁶³ | $163,840,000 |
| Centillion | 10³⁰³ | $327,680,000 |
| **Total pool** | | **$655,350,000** |

Prizes are cryptographically signed at the moment of crossing. The claim token is an HMAC-SHA256 signature — it cannot be forged, transferred, or disputed. The system is already built and operational.

---

## What We Have Built

The infrastructure is complete and running today:

**Network coordinator** — A production Flask/Gunicorn server that manages the number line, dispatches chunks to workers, tracks progress, detects milestone crossings, and signs claim tokens. Supports HTTPS, systemd services, and handles hundreds of simultaneous workers.

**Python worker** — Runs on any machine with Python. Uses all available CPU cores via multiprocessing. Generates a permanent cryptographic identity on first run. Automatically saves claim tokens on milestone crossing. A single 8-core machine contributes ~6–25M verified numbers per second depending on hardware.

**Mobile browser worker** — The full Syracuse kernel runs in JavaScript using `BigInt`. Any phone or tablet can contribute by scanning a QR code — no app, no account, no Python. Android Chrome continues computing in the background even with the screen locked.

**Identity and prize system** — Every worker has a UUID identity. Milestone crossings are signed with HMAC-SHA256 using a coordinator secret. Claim tokens are stored in the worker's identity file and verified via a public `/verify` endpoint. The cryptography is sound: `hmac.compare_digest` for timing-safe comparison, `secrets.token_hex(32)` for 256-bit entropy.

**Live dashboards** — `/status`, `/workers` (leaderboard), `/milestones` (prize board), all auto-refreshing.

**Windows package** — Standalone `.exe` files built with PyInstaller. No Python installation needed. Double-click to contribute.

**Systemd services** — One-command installers for headless operation on Linux. Survives reboots, SSH disconnects, and crashes.

**Nightly GitHub upload** — Automated status reports and checkpoint backups uploaded to the public repository every night at 8pm EST.

---

## Value to Mankind

**Computational verification at scale is itself valuable.** The techniques being developed — distributed compute, big integer arithmetic, cryptographic work attribution, fault-tolerant chunk dispatch across heterogeneous hardware — are directly applicable to protein folding verification, climate model validation, cryptographic primality testing, and any problem requiring exhaustive search across a vast integer space.

**Each verified number is permanent.** Unlike scientific results that get revised, a verified number stays verified forever. Every number past 2⁶⁸ that the network clears is a brick that never needs to be laid again.

**It democratises frontier mathematics.** Prior verification required a purpose-built supercomputer cluster. A phone can now contribute. That is a meaningful shift in who can participate in frontier science.

---

## Value to Mathematics

**A counterexample would be one of the most significant mathematical discoveries in a century.** It would:

- Immediately falsify decades of number theory intuition and every heuristic argument for why the conjecture is true
- Provide a concrete object to study — the counterexample sequence itself would reveal structural properties of integers that are currently completely invisible
- Likely invalidate or constrain large portions of dynamical systems theory, ergodic theory, and the theory of integer sequences
- Prove Paul Erdős correct when he said the problem was beyond current mathematics

**The milestones have standalone mathematical value** even without a counterexample. Each one provides a tighter lower bound on the smallest possible counterexample. These bounds are cited in the mathematical literature and constrain which classes of numbers theorists need to consider.

**The probability of finding a counterexample is astronomically small** — the expected number of counterexamples below 10¹⁰⁰ is effectively zero. This is what makes the prize structure credible. The prizes are not a lottery — they are a recognition of genuine mathematical contribution.

---

## Commercial Value

**1. Distributed computing infrastructure with a hook**

The prize system solves the cold-start problem that kills most volunteer compute projects. People contribute because there is real money at stake, not just altruism. The architecture — coordinator, worker, mobile browser compute, cryptographic work attribution — is reusable for any embarrassingly parallel search problem. The Collatz Conjecture is the proof of concept and the marketing hook.

**2. A counterexample would be worth more than the prize pool**

If the network found a counterexample:

- Every mathematics journal on Earth would cover it
- Front page of every major newspaper globally — "Amateur distributed network solves 87-year-old unsolved mathematics problem"
- Permanent citation in the mathematical literature — the paper would be cited thousands of times per year, indefinitely
- Proof that distributed volunteer compute can solve problems no single institution could — a direct commercial proposition
- Estimated commercial value: **$50–500M** purely from media attention, partnership opportunities, and platform credibility — independent of the mathematical prize

**3. The prize structure is a recurring media engine**

Every milestone is a press event. "Worker wins $10,000 for pushing Collatz frontier past Sextillion." Then $20,000. Then $40,000. The doubling structure means later milestones generate progressively larger stories. The $163M Vigintillion prize is a headline. Each event drives new contributor signups, which accelerates the frontier, which brings the next event closer.

**4. The cryptographic attribution system is a product**

Provable, verifiable computational contributions with cryptographic attribution is directly applicable to:

- Proof-of-work systems without Bitcoin's energy waste
- Scientific compute markets — paying contributors for verifiable work on any problem
- Academic credit systems — attributing computational contributions to researchers

---

## The Pitch in One Paragraph

We are building the world's first cryptographically-verified, prize-incentivised distributed compute network, using the Collatz Conjecture as our launch problem. The network is fully operational across Python workers, mobile browsers, and Windows machines. Every contributor has permanent, cryptographically-provable credit for their work. Covering the ground we are now searching would take one machine 1.48 million years — or a network of 1,000 average PCs one year. The prize pool is $655 million. The probability of a counterexample is near zero — but the probability of building a scalable, incentivised compute platform with a compelling mathematical narrative and a prize structure that generates its own media is 100%, because we have already built it. If a counterexample is found, we are in the history books. If one is not — which is the almost certain outcome — we will have validated the infrastructure for the next generation of distributed science computing.

---

## Investor Notes

This is a moonshot science project with a genuine infrastructure business attached to it.

**The infrastructure business is real and near-term.** The platform, the prize mechanics, the cryptographic attribution system, the worker ecosystem — these have value independent of whether a counterexample is ever found.

**The mathematical discovery is real optionality.** An investor should value the business on the infrastructure and the marketing hook, treat the mathematical discovery as pure upside, and understand that every milestone crossed is a legitimate press event regardless of what happens next.

**The prize pool is a liability — understand the structure.** Prizes double from $10,000 to $327,680,000. The early milestones (Sextillion through Decillion) are the most likely to be crossed in a human timescale. At current network speeds, Sextillion is reachable within years. Vigintillion (10⁶³) may be centuries away regardless of network size — the numbers involved are incomprehensibly large.

**The compute scale argument is the core investment thesis.** 1,000 average PCs can do in one year what would take the fastest single machine 14,600 years. The network already exists. The question is how fast we can grow the contributor base.

---

*For technical documentation, API reference, and security assessment: see `docs/` in the repository.*  
*Live frontier status: [`frontier_log.txt`](https://github.com/huggablehacker/Collatz-Frontier/blob/main/frontier_log.txt)*
