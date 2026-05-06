# Project Fingerprint Schema

## Revision triggers
This doc gets revisited when any of these happen:
- A project comes up whose fingerprint can't be described with these 6 dimensions
- Two projects share the same fingerprint but rules that help one actively hurt the other
- We find ourselves adding a 7th dimension because the 6 aren't distinguishing enough
- After PATS-Copy retrofit completes — sanity check whether the fingerprint we gave it matched the rules that helped

*Last revised: 2026-04-24*

---

## What this is

A fingerprint is a compact description of what kind of project this is. Two projects with similar fingerprints can usefully share rules. The goal is to be **granular enough** that useful rules transfer, and **coarse enough** that the taxonomy stays manageable.

A fingerprint is a tuple of 6 values, one per dimension. Each value is chosen from a small discrete set.

---

## The 6 dimensions

### 1. Money — what's at stake financially

| Value | Meaning |
|---|---|
| `none` | No money involved (internal tools, personal projects, creative work) |
| `paper` | Simulated money (paper trading, demos, sandbox environments) |
| `live` | Real money flows through the system (production trading, payments, billing) |

### 2. Data velocity — how fast data flows

| Value | Meaning |
|---|---|
| `batch` | Periodic bulk operations (nightly jobs, weekly reports, scheduled tasks) |
| `streaming` | Continuous ingestion or processing (APIs, message queues, event feeds) |
| `realtime` | Latency-sensitive, usually sub-second (trading, live events, gaming) |

### 3. External dependencies — reliance on systems outside our control

| Value | Meaning |
|---|---|
| `isolated` | Runs entirely locally, no external calls |
| `few` | 1–3 key external services |
| `many` | 4+ external services, orchestration required |

### 4. State complexity — how state is managed

| Value | Meaning |
|---|---|
| `stateless` | No persistent state (pure functions, scripts, transforms) |
| `single-source` | One authoritative data store |
| `multi-source` | Multiple stores that must stay consistent |
| `distributed` | State spread across systems, eventual consistency |

### 5. Human in loop — how often a person is required

| Value | Meaning |
|---|---|
| `always` | Every action requires approval (clinical, creative review, regulated) |
| `milestones` | Approval at checkpoints (code review, deploy gates, release cuts) |
| `never` | Fully autonomous (monitoring bots, trading bots post-launch) |

### 6. Reversibility — what happens when something goes wrong

| Value | Meaning |
|---|---|
| `reversible` | Easy to undo (local file edits, text generation, ephemeral state) |
| `costly` | Undoable but expensive (code deploys, content publishing, DB migrations) |
| `irreversible` | Cannot be undone (real-money trades, deleted customer data, social posts) |

---

## Example fingerprints — known projects

| Project | Money | Data velocity | External deps | State complexity | Human in loop | Reversibility |
|---|---|---|---|---|---|---|
| **PATS-Copy** (Polymarket paper trading) | paper | realtime | many | multi-source | never | costly |
| **claude-hq** (orchestration brain) | none | batch | few | single-source | always | costly |
| **Wasserman NFL Spain** (creative project) | none | batch | few | stateless | always | reversible |
| **future Polymarket live** (hypothetical) | live | realtime | many | multi-source | never | **irreversible** |

The PATS-Copy → Polymarket-live transition illustrates why fingerprints matter: **only two dimensions change** (money and reversibility), but those two changes unlock a different tier of rules entirely. Rules that were optional at paper level become mandatory at live-money level.

---

## How fingerprints are used

When a new watchdog is spawned, it:
1. Reads its project's fingerprint (declared at spawn or inferred)
2. Walks the canonical rule library
3. For each rule, checks whether the rule's `fingerprints` tags match this project's fingerprint
4. If match: **inherit**. If adjacent (1 dimension off): **flag for manual review**. If very different: **discard**.

Specifics of matching live in [rule-tagging-schema.md](rule-tagging-schema.md).

---

## Choosing values

A project might feel like it straddles two values. Pick the **higher-risk** one by default. Examples:

- Partially automated, partially human → `milestones` (not `never`)
- Mostly paper but some live → `live`
- Single-source but with eventually-consistent caches → `multi-source`

If you pick wrong, the revision triggers above will catch it.

---

## Core principles (protected — don't casually change)

1. **6 dimensions, not 5 or 7.** The set was chosen to be the minimum where PATS-Copy, claude-hq, and Wasserman are all distinguishable. Expanding makes tagging harder without adding signal. Contracting collapses useful distinctions.
2. **Discrete levels, not continuous scores.** Easier to tag, easier to match, easier to reason about. "Somewhat streaming" is a tagging problem, not a refinement.
3. **Money + Reversibility are the safety axis.** Data velocity + State complexity are the architecture axis. External deps + Human-in-loop are the operational axis. Each dimension belongs to one axis and together they triangulate project nature.
4. **Fingerprints can evolve.** A project that starts as `paper` can become `live`. When it transitions, we re-fingerprint it and re-evaluate inherited rules. Fingerprints aren't set in stone — they're a point-in-time description.

---

## Open questions (to settle when we hit them)

- Does `human in loop` need finer granularity? (code review vs creative review vs clinical approval feel different)
- Should we add a 7th dimension for **blast radius** (personal vs team vs public)? Currently partially captured by Reversibility but maybe not enough.
- How do we version the fingerprint when a project matures? (Git commit that changes the fingerprint file? Explicit `as_of` dates per dimension?)

These are parked. We'll answer them only when a real project forces the question.
