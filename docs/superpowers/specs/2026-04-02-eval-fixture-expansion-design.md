# Eval Fixture Expansion — Design Spec

**Date:** 2026-04-02  
**Status:** Approved

---

## Goal

Expand all 7 eval fixture files by 20× to stress-test the Mumbai Mobility Agent more thoroughly. Current total: 62 cases. Target total: ~1,240 cases.

| Area | Current | Target |
|------|---------|--------|
| Intent Parsing | 20 | 400 |
| Constraint Application | 10 | 200 |
| Route Optimization | 11 | 220 |
| Schedule Feasibility | 4 | 80 |
| Conversation Flow | 8 | 160 |
| What-If Scenarios | 4 | 80 |
| Route Availability | 5 | 100 |

---

## Approach

A single generator script `eval/generate_fixtures.py` reads the real graph from `data/mumbai_routes.py` and writes all 7 fixture JSON files. It runs once; output is committed to the repo. The existing evaluators are unchanged — they consume the fixture files as before.

---

## Per-Area Generation Strategy

### 1. Intent Parsing (`intent_parsing.json`) — 400 cases

Enumerate action × location pair × mode with template-based phrasing.

**Action types and case budget:**
- `plan` — 20 phrasings (e.g. "plan my day", "sort out my route", "can you plan today?")
- `replan` — 20 phrasings (e.g. "replan", "redo the route", "recalculate please")
- `explain` — 20 phrasings (e.g. "why this route?", "explain the plan", "how did you pick this?")
- `update_preferences` (global avoid) — 4 modes × 10 phrasings each = 40 cases
- `avoid_mode_on_leg` — 4 modes × ~15 location pairs × 2 phrasings = ~120 cases
- `edit_leg` (force mode on leg) — 4 modes × ~15 location pairs × 2 phrasings = ~120 cases
- `clear_leg_override` — ~15 location pairs × 2 phrasings = ~30 cases
- `clear_leg_preference` — ~15 location pairs × 2 phrasings = ~30 cases

Phrasing templates per action are pre-written in the script. Location pairs are drawn from all 12 graph nodes (not just direct edges, since intent parsing doesn't require a routable path).

### 2. Constraint Application (`constraint_application.json`) — 200 cases

Systematically test every `ActionAgent` mutation against all modes and location pairs.

**Coverage:**
- Global avoid: all 4 modes, all combinations of 2 and 3 modes together
- Leg override: all 4 modes × all ~20 direct graph edges
- Leg avoid: all 4 modes × all ~20 direct graph edges
- Conflict resolution: global-avoid-clears-leg-override for all 4 modes
- Conflict resolution: leg-override-clears-leg-avoid for all 4 modes
- Clear operations: `clear_leg_override` and `clear_leg_preference` for all edges
- Accumulation: sequential global avoids stacking
- Case insensitivity: uppercase/mixed location names for all leg operations

### 3. Route Optimization (`route_optimization.json`) — 220 cases

Use real graph edges for valid routes; use disconnected pairs and tight time windows for failures.

**Coverage:**
- 2-meeting valid plans: all routable adjacent pairs, no constraints (~30 cases)
- 2-meeting valid plans with single global avoid: all 4 modes (~30 cases)
- 2-meeting valid plans with all-but-cab avoided: multiple pairs (~15 cases)
- Leg overrides on specific edges (~20 cases)
- Leg avoids on specific edges (~20 cases)
- 3-meeting plans: varied location triples (~30 cases)
- 4-meeting plans: varied location quads (~20 cases)
- Impossible time windows: <10 min gap between distant locations (~20 cases)
- Single meeting → 0 legs (~10 cases across different locations)
- Unknown location → `failed` (~10 cases)
- Avoid all 4 modes → infeasible (~15 cases)

### 4. Schedule Feasibility (`schedule_feasibility.json`) — 80 cases

Generate 2–5 meeting lists in random orders and assert the sorted output.

**Coverage:**
- 2 meetings: 20 cases (varied times, some already sorted, some not)
- 3 meetings: 20 cases (all 6 permutations × varied start times)
- 4 meetings: 20 cases
- 5 meetings: 20 cases

Times span 07:00–20:00 in 30-minute increments.

### 5. Conversation Flow (`conversation_flow.json`) — 160 cases

Multi-turn sequences where WorldState must persist correctly across turns.

**Coverage:**
- Global avoid → plan (modes absent): all 4 modes × multiple location pairs (~40 cases)
- Leg override → replan (mode applied): all 4 modes × multiple edges (~30 cases)
- Set → clear → plan (override absent): all 4 modes × edges (~20 cases)
- Multi-constraint stacking: 2–3 avoids combined, plan respects all (~20 cases)
- Conflict detection: global avoid then force same mode on leg (~20 cases)
- What-if preview: plan → what-if → expect `proposal_preview` status (~15 cases)
- Three stacked global avoids → only cab (~15 cases)

### 6. What-If Scenarios (`whatif.json`) — 80 cases

Plan → what-if → confirm/reject flow across leg pairs and modes.

**Coverage:**
- What-if triggers `proposal_preview`: all 4 modes × ~10 location pairs = ~40 cases
- What-if sets `pending_leg_change`: mode verified in state (~10 cases)
- Confirm with "yes" applies override: all 4 modes × select pairs (~15 cases)
- Reject with "no" clears `pending_leg_change`: select pairs × modes (~15 cases)

### 7. Route Availability (`availability.json`) — 100 cases

Enumerate the graph to know ground truth for each mode × location pair.

**Coverage:**
- Direct edge exists for mode → `available: true`: enumerate all edges per mode (~60 cases)
- Same location pair, mode not in graph → `available: false`: cross-check missing modes (~30 cases)
- Varied natural language: "Is there a {mode} from {A} to {B}?", "Can I take {mode} from {A} to {B}?", "Does a {mode} run between {A} and {B}?" (~10 additional phrasings)

---

## Implementation

**New file:** `eval/generate_fixtures.py`

```
eval/generate_fixtures.py
  imports: data.mumbai_routes (MUMBAI_ROUTES, LOCATION_COORDS)
  writes:  eval/fixtures/*.json (all 7 files)
  run:     python -m eval.generate_fixtures
```

The script overwrites the existing fixture files. After generation, run the eval normally:

```bash
python -m eval.generate_fixtures
python -m eval.run_eval
```

No changes to evaluators or `run_eval.py`.

---

## Constraints

- All `expected` values for route/availability cases are derived from the actual graph at generation time — no hardcoded assumptions about topology.
- Intent cases use only the 12 known location names from `LOCATION_COORDS`.
- IDs follow existing format: `{prefix}_{three-digit-number}` (e.g. `ip_021`, `ro_012`).
- LLM-heavy evals (intent, availability, conversation, whatif) will make significantly more API calls — user has accepted this trade-off.
