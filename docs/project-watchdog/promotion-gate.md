# Rule Promotion Gate

## Revision triggers
This doc gets revisited when any of these happen:
- A rule gets promoted to canonical and then produces false positives on a third project
- Operator approval and cross-validation disagree (operator says yes, new project rejects it — or vice versa)
- We hit 10 rules at canonical status — sanity check whether the gate has been too strict or too lenient
- We observe a watchdog "gaming" its own promotion (e.g., identical rule fires from the same project counted as multiple validations)

*Last revised: 2026-04-24*

---

## What this is

Rules emerge from individual projects. Before those rules affect other watchdogs, they go through a gate. The gate has one job: **balance two failure modes**.

| Failure mode | What it looks like |
|---|---|
| Gate too strict | Good rules never promote. Each project re-invents the same learnings. System stops compounding. |
| Gate too lenient | Bad rules spread. Watchdogs become noisy. You train yourself to ignore them. System becomes worse than no system. |

The balance point isn't fixed — the revision triggers above catch drift in either direction.

---

## Rule lifecycle

```
Local → Candidate → Canonical
                 ↓
              Retired (at any point)
```

### 1. Local — the default on creation

- Applies only to the project it was born in
- No effect on any other watchdog
- Lives in the project's own rules file
- Created by: the project's watchdog generating it, or a human authoring it directly

### 2. Candidate — visible to the network, not auto-inherited

Promotes from Local when **any one** of:

- **Operator promotion**: you explicitly mark it as candidate (via Telegram, CLI, or editing the rule's status field)
- **Auto-promotion**: rule fires correctly ≥3 times in 14 days AND has zero rejections

State:
- Other watchdogs see it in their registry but do NOT auto-inherit it
- Surfaced in the weekly promotion digest for cross-validation
- Marked as "proposed" so operator and other watchdogs can evaluate it

### 3. Canonical — auto-inherited by matching fingerprints

Promotes from Candidate when **both**:

- **Cross-validation**: the rule has fired correctly on at least 1 OTHER project with matching fingerprint (not just the source project)
- **Operator approval**: explicit approval, or silent approval after 7 days in candidate status with no objection

Effect:
- Any new watchdog spawned with a matching fingerprint auto-inherits it
- Existing watchdogs with matching fingerprints pick it up on next reconciliation
- Rejection on any project demotes it back to Candidate and flags for review

### 4. Retired — archived, never deleted

Moves to Retired when any of:

- **Three consecutive rejections** across any projects
- **No firings in 90 days** (with operator confirmation — prevents retiring seasonal rules)
- **Explicit retirement** by operator

Retired rules stay in the archive. Never deleted — they're institutional memory. New watchdogs don't inherit them, but they're searchable if a similar pattern resurfaces later.

---

## What "fires correctly" means

A firing counts toward promotion only if all three hold:

1. The rule's check triggered (an alert was generated)
2. The operator did NOT reject the alert as "not applicable"
3. Either (a) a real fix followed the alert, OR (b) the operator explicitly confirmed the rule call was correct

Silent acknowledgment (no rejection within 72 hours) counts as implicit confirmation.

---

## What "rejected" means

A rejection counts when:

- Operator replies "not applicable" to the alert on Telegram
- Operator marks the rule as false-positive in the CLI
- The rule fires but the operator makes no fix and explicitly dismisses it

Rejections are logged in the rule's `rejected_on` provenance field with project + date.

---

## Protected invariants — cannot be auto-promoted or auto-retired

Three categories always require **explicit operator approval**, never auto-promotion:

1. **Critical-severity rules** — too expensive to get wrong
2. **Security-category rules** (secret-handling, rate-limiting, reversibility-violation) — silent spread of flawed security rules is dangerous
3. **Live-money fingerprints** — rules tagged for `money: [live]` always require explicit approval before reaching canonical

These are the Zone C equivalent for the rule lifecycle.

---

## Weekly promotion digest

Sunday 08:00, via Telegram, plain English. Same pattern as the HQ Watchdog's Zone B digest.

Typical contents:

```
Weekly promotion digest

Up for your call:

A) Promote to canonical: "Positions must have a single type definition"
   From PATS-Copy, fired correctly 3x in 14 days, cross-validated once
   Reply A to approve, skip to reject.

B) Demote to candidate: "Rate limits for external APIs"
   Rejected once on Wasserman (not applicable to stateless creative work)
   Needs a second look before it keeps getting inherited.

C) Retire: "Backup before destructive operation"
   No firings in 90 days. Still relevant, just no-one has needed it.
   Reply keep to preserve, retire to archive.
```

Single-letter approval, per the same pattern as the existing watchdog digest.

---

## Example flows

### Flow A — healthy promotion

```
Day 0:  Rule born on PATS-Copy. Status: local.
Day 5:  Rule fires. Operator doesn't reject. (count 1/3)
Day 9:  Rule fires. Operator doesn't reject. (count 2/3)
Day 12: Rule fires. Operator doesn't reject. (count 3/3 → auto-promote to candidate)
Day 15: New project spins up with matching fingerprint. Rule surfaces in its registry.
Day 20: Rule fires correctly on new project → cross-validated.
Day 20: Operator silently approves over the next 7 days → canonical.
```

### Flow B — false positive, retired

```
Day 0:  Rule born on Project A.
Day 3:  Rule fires. Operator rejects ("not applicable here").
Day 8:  Rule fires again. Operator rejects.
Day 15: Rule fires third time. Operator rejects → auto-retire.
```

### Flow C — canonical rule contested

```
Pre-existing: Rule is canonical, inherited by Projects A, B, C.
Day 0:  Rule fires on Project B. Operator rejects.
Day 0:  Rule immediately demoted back to candidate.
Day 0:  Flagged in the next weekly digest: "Project B rejected this canonical rule — keep, rewrite, or retire?"
Day 7:  Operator responds. Rule updated accordingly.
```

---

## Core principles (protected — don't casually change)

1. **Promotion requires evidence across projects.** A rule that "works" on one project isn't proven — one-project validation is local, not canonical.
2. **Rejections matter more than firings.** A rule with 3 firings and 1 rejection is weaker than 3 firings and 0 rejections. Rejection signal is loud.
3. **Silent approval after a waiting period.** Forcing operator to explicitly approve everything creates decision fatigue. Silent approval is the default for healthy candidates.
4. **Canonical is not permanent.** Any project rejecting a canonical rule demotes it. Canonical status is earned and can be lost.
5. **Retirement doesn't delete.** Retired rules stay in the archive, searchable, for the lifetime of the system.

---

## Open questions (parked)

- Should `live` money require **2+ cross-validation sites** instead of 1 before canonical? Currently tempted to say yes but this might slow promotion too much given low project count.
- How do we prevent a watchdog from "gaming" its own promotion — e.g., generating the same rule 3 times from 3 different hook fires on the same underlying code? Probably: dedupe by rule ID + project before counting firings.
- Do we want a "test canonical" tier where a promoted rule runs in observe-only mode for N days? Would add a layer of safety but also complexity.
- When multiple projects' watchdogs propose the same-but-slightly-different rule simultaneously, how does the system deduplicate? Currently: operator sees both in the weekly digest and picks or merges.

Parked until we hit a real case.
