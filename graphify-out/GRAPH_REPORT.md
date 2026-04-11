# Graph Report - commander  (2026-04-11)

## Corpus Check
- Corpus is ~4,356 words - fits in a single context window. You may not need a graph.

## Summary
- 70 nodes · 89 edges · 9 communities detected
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 7 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `Boris Cherny Engineering Principles` - 9 edges
2. `Cost Control Protocol` - 9 edges
3. `JARVIS System` - 8 edges
4. `Activation Protocol (7 steps)` - 8 edges
5. `Layer 2: Knowledge (Memory + Context)` - 7 edges
6. `Commander Orchestration Agent` - 7 edges
7. `Five Layer Architecture` - 6 edges
8. `Step 1: Load Context` - 6 edges
9. `Mission Board Template` - 6 edges
10. `Tool Combinations (stacks)` - 5 edges

## Surprising Connections (you probably didn't know these)
- `Layer 1: Commander (Orchestration Brain)` --references--> `Commander Orchestration Agent`  [EXTRACTED]
  commander/PLANNING.md → commander/COMMANDER.md
- `Model Routing Table (Haiku/Sonnet/Opus)` --semantically_similar_to--> `Token Cost Model Routing`  [INFERRED] [semantically similar]
  commander/COMMANDER.md → commander/COST_CONTROL.md
- `Step 1: Load Context` --references--> `JARVIS System`  [EXTRACTED]
  commander/COMMANDER.md → commander/PLANNING.md
- `Layer 2: Knowledge (Memory + Context)` --references--> `LESSONS.md Global Self-Improvement Log`  [EXTRACTED]
  commander/PLANNING.md → commander/LESSONS.md
- `Step 1: Load Context` --references--> `registry.json catalog`  [EXTRACTED]
  commander/COMMANDER.md → commander/PLANNING.md

## Hyperedges (group relationships)
- **Commander activation context load** —  [EXTRACTED 1.00]
- **Web Design Stack tool composition** —  [EXTRACTED 1.00]
- **Cost Control Tier Hierarchy** —  [EXTRACTED 1.00]

## Communities

### Community 0 - "Engineering Principles"
Cohesion: 0.14
Nodes (17): Autonomous Bug Fixing, No Laziness — Root Cause, Boris Cherny Engineering Principles, Staff Engineer Quality Bar, Self-Improvement Loop (LESSONS.md), Simplicity First / Minimal Impact, One Task Per Subagent, Activation Protocol (7 steps) (+9 more)

### Community 1 - "Cost Control & Routing"
Cohesion: 0.15
Nodes (14): Commander Orchestration Agent, Model Routing Table (Haiku/Sonnet/Opus), Cost Control Protocol, Cost Enforcement Protocol, Cost Ledger, Token Cost Model Routing, Tier 1: Free First, Tier 2: One-Time Over Recurring (+6 more)

### Community 2 - "Task Stacks & Registry"
Cohesion: 0.22
Nodes (11): Task Classification Rules, Full Creative Brief Stack, registry.json catalog, Tool Combinations (stacks), humanizer, nano-banana-2-skill, OpenMontage, SuperDesign + MCP (+3 more)

### Community 3 - "Knowledge & Memory Layer"
Cohesion: 0.27
Nodes (10): Layer 2: Knowledge (Memory + Context), Phase 1: Knowledge Layer, Research & Analysis Stack, claude-mem, code-review-graph, graphify, Lightpanda, MemPalace (+2 more)

### Community 4 - "JARVIS Architecture"
Cohesion: 0.22
Nodes (9): Five Layer Architecture, JARVIS System, Layer 1: Commander (Orchestration Brain), Layer 3: Execution (Tools + Agents + Skills), Layer 4: Inter-Agent Communication, Layer 5: Runtime Environment, Phase 2: Execution Tools, Phase 4: Inter-Agent Communication (+1 more)

### Community 5 - "Mission Board Planning"
Cohesion: 0.4
Nodes (6): Plan Mode Default, Step 4: Plan (Mission Board), Risk Flags Section, Task Graph Section, Mission Board Template, Rationale: Plan Mode reduces ambiguity and rework

### Community 6 - "SEED Incubator"
Cohesion: 1.0
Nodes (1): SEED

### Community 7 - "PAUL Ideation"
Cohesion: 1.0
Nodes (1): PAUL

### Community 8 - "ruflo Agent Swarm"
Cohesion: 1.0
Nodes (1): ruflo

## Knowledge Gaps
- **32 isolated node(s):** `Layer 3: Execution (Tools + Agents + Skills)`, `Layer 4: Inter-Agent Communication`, `Layer 5: Runtime Environment`, `Phase 2: Execution Tools`, `Phase 4: Inter-Agent Communication` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `SEED Incubator`** (1 nodes): `SEED`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PAUL Ideation`** (1 nodes): `PAUL`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ruflo Agent Swarm`** (1 nodes): `ruflo`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Step 1: Load Context` connect `Engineering Principles` to `Cost Control & Routing`, `Task Stacks & Registry`, `JARVIS Architecture`?**
  _High betweenness centrality (0.254) - this node is a cross-community bridge._
- **Why does `Phase 3: Commander Agent` connect `Cost Control & Routing` to `Engineering Principles`, `JARVIS Architecture`, `Mission Board Planning`?**
  _High betweenness centrality (0.210) - this node is a cross-community bridge._
- **Why does `JARVIS System` connect `JARVIS Architecture` to `Engineering Principles`, `Cost Control & Routing`, `Task Stacks & Registry`, `Knowledge & Memory Layer`?**
  _High betweenness centrality (0.205) - this node is a cross-community bridge._
- **What connects `Layer 3: Execution (Tools + Agents + Skills)`, `Layer 4: Inter-Agent Communication`, `Layer 5: Runtime Environment` to the rest of the system?**
  _32 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Engineering Principles` be split into smaller, more focused modules?**
  _Cohesion score 0.14 - nodes in this community are weakly interconnected._