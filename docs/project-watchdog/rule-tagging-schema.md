# Rule Tagging Schema

## Revision triggers
This doc gets revisited when any of these happen:
- More than 5 rules get generated that don't fit cleanly into existing mechanism tags
- We find rules that fire correctly for one fingerprint but cause false positives on another with overlapping tags
- After the first 20 rules are tagged and tested across at least 2 projects — we look back and see which tags carried signal and which didn't
- After PATS-Copy retrofit completes — check whether the rules we tagged correctly transferred

*Last revised: 2026-04-24*

---

## What this is

Every rule has two kinds of tags:

1. **Fingerprint tags** — WHICH projects this rule applies to (environment)
2. **Mechanism tags** — WHAT KIND of flaw this rule catches (pattern)

A new watchdog sees a rule and asks: "does this environment match mine?" then "is this a kind of thing I should watch for?" Both yes → inherit.

Get tagging right and rules transfer cleanly across projects. Get it wrong and you either miss helpful rules or pollute new watchdogs with irrelevant ones.

---

## The shape of a rule

Rules live as YAML. One file per rule is ideal, but they can also be collected in bundles.

```yaml
id: pos-001-unify-position-type
title: "Positions must have a single type definition across the codebase"
description: |
  When a project has multiple independent type definitions for a core
  domain object like Position, Order, or Trade, they drift over time.
  This causes data to be mutated in one place and read correctly from
  another, producing subtle bugs.

fingerprints:
  # Which projects this rule applies to. Missing dimension = "any value"
  # (wildcard). Listed values are "any of these".
  money: [paper, live]
  reversibility: [costly, irreversible]
  state_complexity: [multi-source, distributed]
  # data_velocity, external_deps, human_in_loop not listed → wildcard

mechanisms:
  # Multi-select from the controlled vocabulary below
  - type-drift
  - single-source-of-truth

severity: warn | critical | info

check:
  # How the watchdog actually verifies this rule
  type: static | behavioural | relational
  pattern: |
    Find interface/type/class declarations where the same name
    (case-insensitive) appears in >1 file with different shapes.

provenance:
  source:
    project: PATS-Copy
    date: 2026-04-24
    trigger: "position tracking drift incident, April 2026"
  status: local | candidate | canonical | retired
  validated_on: [PATS-Copy]   # projects where the rule fired correctly
  rejected_on: []              # projects where operator said "not applicable"
```

---

## Fingerprint tags — how matching works

A rule's `fingerprints` section lists accepted values per dimension. Dimensions not listed are wildcards.

**Matching logic:**
- For each listed dimension: project's value must appear in the rule's accepted list
- For each unlisted dimension: any value matches
- Rule inherits when ALL listed dimensions match

**Examples using the rule above (money=paper/live, reversibility=costly/irreversible, state_complexity=multi-source/distributed):**

| Project fingerprint | Inherit? | Why |
|---|---|---|
| PATS-Copy (paper, realtime, many, multi-source, never, costly) | ✅ Yes | All 3 listed dimensions match |
| claude-hq (none, batch, few, single-source, always, costly) | ❌ No | `money` is `none` (not in `[paper, live]`) and `state_complexity` is `single-source` (not in list) |
| Future Polymarket live (live, realtime, many, multi-source, never, irreversible) | ✅ Yes | All match; stricter values actually |
| Wasserman NFL Spain (none, batch, few, stateless, always, reversible) | ❌ No | 3 listed dimensions all mismatch |

**Adjacency rule (for review, not auto-inherit):**
When a rule's listed dimensions have only **1 mismatch** with a project's fingerprint, the watchdog surfaces it for manual review instead of silently discarding. Operator decides: adapt the rule, create a variant, or discard.

---

## Mechanism tags — controlled vocabulary

This is the starter set. Grows via the promotion gate (see [promotion-gate.md](promotion-gate.md)) — new mechanism tags require explicit operator approval before they become part of the vocabulary.

| Tag | What it catches |
|---|---|
| `state-drift` | Inconsistency between components sharing state |
| `single-source-of-truth` | Violations of canonical data store principle |
| `type-drift` | Same concept with multiple inconsistent type definitions |
| `external-api-drift` | External API changes breaking assumptions |
| `silent-failure` | Errors being swallowed without surfacing |
| `rate-limiting` | Unbounded calls to rate-limited services |
| `secret-handling` | Credentials in logs, source, or transit |
| `reversibility-violation` | Irreversible action taken without confirmation |
| `observability-gap` | Something happens with no trace or log |
| `dead-code-hazard` | Unreachable code that looks live |
| `concurrency-hazard` | Shared state mutated from multiple execution paths |
| `configuration-drift` | Environment-specific config leaking into core logic |

**Rules can have multiple mechanism tags.** The position-type rule above has `type-drift` and `single-source-of-truth` because it's both — different mechanism lenses on the same flaw.

---

## How this gets used at watchdog spawn

```
New project created
   ↓
Project's fingerprint declared (or inferred from Commander Step 0)
   ↓
Watchdog walks the canonical rule library
   ↓
For each rule:
   - All listed fingerprint dimensions match?  → inherit
   - 1 mismatch                                 → flag for review
   - 2+ mismatches                              → discard silently
   ↓
Inherited rules become the project's starting rule set
   ↓
Watchdog runs those rules. Fires alerts when they trigger.
   ↓
Operator confirms/rejects. Provenance updates.
```

---

## Core principles (protected — don't casually change)

1. **Fingerprint tags describe environment. Mechanism tags describe pattern.** Never conflate them. A rule saying "trading bots need single-source-of-truth" is wrong; the real rule is "multi-source state with costly/irreversible writes needs single-source-of-truth", which happens to apply to trading bots among others.
2. **Wildcard by omission.** If a dimension isn't listed, the rule is fingerprint-agnostic on that dimension. Forces authors to list only what matters.
3. **Mechanism vocabulary is controlled.** New tags require the promotion gate. Free-form mechanism tags cause drift.
4. **Adjacency = review, not inherit.** Automatic inheritance on near-matches causes false positives. Near-matches deserve a look, not a silent yes.
5. **Provenance is mandatory.** Every rule must record where it came from and where it's been validated. This powers both the promotion gate and later audits.

---

## Open questions (parked)

- Should mechanism tags be hierarchical? (`state-drift/schema-drift` vs `state-drift/value-drift`) — might help when vocabulary grows past ~20 tags
- Do we need rule combinators? (e.g., "rule A only applies if rule B's precondition holds") — currently each rule is independent
- How do we handle rules that require **any of these fingerprints** AND **NOT this one**? (exclusion logic) — not urgent
- Confidence score per rule? — currently captured implicitly by status (local < candidate < canonical)

Parked until a real rule forces the question.
