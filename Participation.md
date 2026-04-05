# Participation & Compensation Structure

**Collatz Frontier Foundation, Inc.**
*A North Carolina 501(c)(3) Nonprofit Corporation*

---

Every device that joins the Collatz Frontier network contributes to a permanent, cumulative record of verified mathematical territory. Whether you run a browser tab for an hour or a dedicated server for a year, your work is real and your place in the mathematical record is permanent.

People participate in two distinct ways. Understanding the difference matters — especially if a milestone prize is on the table.

---

## Contributors

A contributor is anyone who runs a worker voluntarily, with no financial relationship with the Foundation.

**What contributors get:**
- Full credit on the public leaderboard
- A permanent cryptographic record of every number their machine verifies
- **All milestone prizes they win, in full, with no obligation to the Foundation**

**What contributors owe:**
- Nothing. Participation is entirely voluntary. Stop any time, for any reason.

If a contributor's worker crosses the Sextillion threshold — or any other milestone — that prize belongs to them completely. The Foundation has no claim on it and will not seek repayment. Ever.

Contributors may choose to donate to the Foundation separately. That is always welcome and entirely their own decision. It has no bearing on their prize eligibility or leaderboard standing.

> **To participate as a contributor:** just run a worker. No paperwork required.
> See the [README](./README.md) for setup instructions.

---

## Contractors

A contractor is someone who provides professional services to the Foundation and is compensated for that work. This includes software developers, mathematicians, algorithm specialists, technical writers, and any other paid consultant.

**What contractors receive:**
- Consulting fees for their professional services, set by the Board of Directors at a fair market rate

**What contractors are required to do:**
- Perform the agreed professional services and deliver the agreed outputs
- **Run a Collatz Frontier worker (web or Python) for the duration of the engagement** — this is a material condition of the contract, not optional
- **Return any milestone prize won during the engagement period to the Foundation**

The milestone return requirement is the key distinction. A contractor is being paid from Foundation funds for their work. The milestone prizes are funded by the Foundation's prize reserve. Allowing a paid contractor to collect both consulting fees and a prize from Foundation funds in the same engagement would create a double benefit inconsistent with the Foundation's nonprofit obligations. So by contract, prizes won during an engagement go back.

**Prizes won outside the engagement period — before or after the contract — belong to the contractor like anyone else.**

If a contractor later chooses to donate to the Foundation, that is a separate voluntary act with no connection to their consulting arrangement.

> **To participate as a contractor:** contact the Foundation. A formal agreement is required before any paid engagement begins. The Foundation will provide the necessary documents.

---

## Side-by-Side Summary

|  | Contributor | Contractor |
|---|---|---|
| Paid by the Foundation? | No | Yes — consulting fees |
| Worker required? | Encouraged, never obligatory | Yes — required by contract |
| Keeps milestone prizes? | **Yes — always** | No — prizes return to Foundation during engagement |
| Signs an agreement? | Optional | Required before work begins |
| Can donate separately? | Yes | Yes — entirely separate transaction |

---

## How Workers Are Verified

The Foundation verifies contractor network participation through the public leaderboard and status dashboard. Contractors register a specific worker name when they sign their agreement — that name appears on the leaderboard and its contribution totals are publicly visible throughout the engagement.

There is no self-reporting. The network records the work.

---

## Milestone Prizes — How They Work

When any worker crosses a milestone threshold, the network responds with a cryptographically signed claim token — an HMAC-SHA256 signature proving that a specific machine, at a specific time, crossed a specific frontier. This token is saved to the worker's identity file automatically.

To claim a prize:
1. Go to `/milestones` on the network dashboard
2. Click **verify claim** next to the milestone
3. Paste the values from your identity file
4. Open a GitHub Issue titled `Prize Claim: [Milestone Name]`

The claim is the token. **Back up your identity file.** If it is lost, the prize cannot be claimed.

| Milestone | Value | Prize |
|---|---|---|
| Sextillion | 10²¹ | $10,000 |
| Septillion | 10²⁴ | $20,000 |
| Octillion | 10²⁷ | $40,000 |
| Nonillion | 10³⁰ | $80,000 |
| *(doubles each level)* | | |
| Vigintillion | 10⁶³ | $163,840,000 |
| Centillion | 10³⁰³ | $327,680,000 |

---

## About the Foundation

Collatz Frontier Foundation, Inc. is a North Carolina 501(c)(3) public charity organized to advance open mathematical science. Its purposes are:

- Conducting and enabling computational verification of the Collatz Conjecture
- Developing and freely distributing open-source distributed computing infrastructure
- Educating the public about unsolved mathematical problems and volunteer science

The Foundation is governed by a Board of Directors. All compensation decisions are made by the Board at arm's length. No individual has an ownership interest in the Foundation. Contributions are tax-deductible to the extent permitted by law.

---

## Getting the Documents

The Foundation maintains formal agreements for all paid engagements and optional participation agreements for contributors who want a written record of the prize terms. These documents are not published here to keep this repository focused on the science and the code.

If you are interested in a contractor engagement, or would like a copy of the contributor participation agreement, open a GitHub Issue or contact the Foundation directly at **[contact email]**.

---

*Collatz Frontier Foundation, Inc. · North Carolina · EIN [XX-XXXXXXX]*
*All software in this repository is licensed under the MIT License. See [LICENSE](./LICENSE).*
