# Virtual Positions Domain

**Phase 5.1: Virtual Position Model (Design-First)**

## Overview

Virtual Positions represent **"if this were a trade"** observation objects in the ESB v1.0 Dry-Run Runtime. They are **NOT** real positions, **NOT** execution instructions, and do **NOT** involve capital, sizing, or PnL tracking.

This domain layer provides the foundational state model for observing structural market ideas over time without risk.

---

## 🔑 Key Philosophy

### Virtual Position ≠ Trade

A **Virtual Position** is a **state model**, not a trade:

- ✅ **IS**: A snapshot of "what would happen if we entered this idea"
- ✅ **IS**: A container for observing progress toward structural targets
- ✅ **IS**: A lifecycle state machine for dry-run observation
- ✅ **IS**: Foundation for paper trading / dry-run runtime

- ❌ **NOT**: A real position with capital at risk
- ❌ **NOT**: Execution instructions (no buy/sell semantics)
- ❌ **NOT**: Size, balance, capital allocation
- ❌ **NOT**: PnL tracking (no profit/loss calculation)

### Runtime Observation ≠ Decision

Virtual Positions **observe**, they do **NOT** decide:

- ✅ Tracks lifecycle state (`open`, `progressing`, `stalled`, `invalidated`, `completed`)
- ✅ Records progress toward TP targets (0-100%)
- ✅ Notes which targets have been reached
- ✅ Monitors structural validity over time

- ❌ Does NOT decide entry/exit
- ❌ Does NOT execute orders
- ❌ Does NOT calculate optimal size
- ❌ Does NOT optimize parameters

---

## 📦 What's in Phase 5.1?

### PR-5.1 Implements: Model + Creation

**PR-5.1 provides:**

1. **Type System**: `VirtualPosition` interface, `VirtualPositionStatus` type
2. **Factory Function**: `createVirtualPosition()` - creates initial state
3. **Validation**: Enforces Phase 4 relationships (scenario ↔ score ↔ risk)
4. **Immutability**: Defensive copies, no input mutation
5. **Determinism**: Same inputs always produce same output

**PR-5.1 does NOT include:**

- ❌ Progress calculation (PR-5.2 Progress Engine)
- ❌ Status transitions (PR-5.2 Progress Engine)
- ❌ Target tracking logic (PR-5.2 Progress Engine)
- ❌ Re-analysis triggers (PR-5.3 Re-analysis Logic)
- ❌ Invalidation detection (PR-5.3 Re-analysis Logic)
- ❌ Decision-making of any kind

---

## 🏗️ Architecture Decisions

### 1. Self-Contained Snapshot

**Decision**: Virtual Position stores **full objects** (not just IDs)

```typescript
interface VirtualPosition {
  score: ConfluenceScore;  // Full object
  risk: RiskContract;      // Full object
  // ... other fields
}
```

**Rationale:**
- Enables replay without external lookups
- Supports event sourcing (future)
- Complete state snapshot at creation time
- No coupling to external storage

### 2. Factory-Only (PR-5.1)

**Decision**: Only `createVirtualPosition()` factory in PR-5.1 - no update helpers

**Rationale:**
- PR-5.1 = creation + validation
- PR-5.2 = evolution (progress, transitions)
- Clean separation of concerns
- Update logic belongs with progress engine

### 3. Explicit Result Type

**Decision**: No exceptions - return `VirtualPositionResult` discriminated union

```typescript
type VirtualPositionResult =
  | { success: true; position: VirtualPosition }
  | { success: false; error: 'SCENARIO_NOT_VALID' | 'RISK_NOT_VALID' };
```

**Rationale:**
- Explicit error handling (no hidden control flow)
- Type-safe error checking
- Consistent with Phase 4 patterns
- No try/catch needed

### 4. Immutable Design

**Decision**: Every change creates a new Virtual Position

**Rationale:**
- Deterministic replay (same inputs → same output)
- Event sourcing friendly (future)
- Prevents accidental mutations
- Clear state transitions (future PRs)

### 5. Deterministic ID Generation

**Decision**: ID = `vpos-${scenario.id}-${openedAt}`

**Rationale:**
- Reproducible for tests
- No randomness (replay-safe)
- Encodes relationship (scenario + time)
- Human-readable for debugging

### 6. Two Error Types Only

**Decision**: Only `SCENARIO_NOT_VALID` and `RISK_NOT_VALID`

**Rationale:**
- Phase 4 already validated inputs thoroughly
- Relationship validation = risk validation
- Minimal error surface
- Additional errors indicate hidden behavior

---

## 🎯 How Virtual Position Will Be Used

### In PR-5.2 (Progress Engine)

**Progress Engine will:**

1. **Calculate** `progressPercent` based on price movement toward TP targets
2. **Update** `reachedTargets` array when price hits TP1, TP2, TP3
3. **Transition** `status` from `open` → `progressing` → `completed`
4. **Detect** stalling (no progress over time)
5. **Create** new Virtual Position snapshots on each update (immutability)

**Example:**
```typescript
// PR-5.2 (not in PR-5.1)
function updateProgress(
  position: VirtualPosition,
  currentPrice: number,
  evaluatedAt: number
): VirtualPosition {
  // Calculate new progress
  const newProgress = calculateProgressPercent(position.risk, currentPrice);
  
  // Check for TP hits
  const newReachedTargets = detectReachedTargets(position, currentPrice);
  
  // Determine new status
  const newStatus = deriveStatus(newProgress, newReachedTargets);
  
  // Return NEW Virtual Position (immutable)
  return {
    ...position,
    progressPercent: newProgress,
    reachedTargets: newReachedTargets,
    status: newStatus,
    lastEvaluatedAt: evaluatedAt
  };
}
```

### In PR-5.3 (Re-analysis Triggers)

**Re-analysis Logic will:**

1. **Detect** when to re-evaluate scenarios (time-based, event-based)
2. **Trigger** invalidation when structure breaks
3. **Compare** Virtual Position state with market reality
4. **Decide** if scenario needs re-assessment

**Example:**
```typescript
// PR-5.3 (not in PR-5.1)
function shouldReanalyze(
  position: VirtualPosition,
  marketData: MarketData
): boolean {
  // Check if structure still valid
  if (structureViolated(position, marketData)) {
    return true;
  }
  
  // Check time-based triggers
  if (timeSinceLastEval(position) > THRESHOLD) {
    return true;
  }
  
  return false;
}
```

---

## 🔐 Validation Rules

Virtual Position creation validates:

1. **Scenario Status**: `scenario.status === 'valid'`
   - Rejects `'forming'` or `'invalidated'` scenarios
   - Error: `SCENARIO_NOT_VALID`

2. **Risk Status**: `risk.status === 'valid'`
   - Rejects invalid risk contracts
   - Error: `RISK_NOT_VALID`

3. **Scenario-Score Relationship**: `scenario.id === score.scenarioId`
   - Ensures score references correct scenario
   - Error: `RISK_NOT_VALID`

4. **Scenario-Risk Relationship**: `scenario.id === risk.scenarioId`
   - Ensures risk references correct scenario
   - Error: `RISK_NOT_VALID`

**Phase 4 already validated** individual inputs - Virtual Position only validates **relationships**.

---

## 📊 Initial State Specification

When `createVirtualPosition()` succeeds, the Virtual Position has:

| Field | Initial Value | Notes |
|-------|---------------|-------|
| `id` | `vpos-${scenario.id}-${openedAt}` | Deterministic |
| `scenarioId` | `scenario.id` | Extracted |
| `scenarioType` | `scenario.type` | Extracted |
| `score` | Full `ConfluenceScore` object | Defensive copy |
| `risk` | Full `RiskContract` object | Deep defensive copy |
| `status` | `'open'` | Always starts open |
| `progressPercent` | `0` | No progress yet |
| `reachedTargets` | `[]` | No targets hit yet |
| `openedAt` | Provided timestamp | Fixed point in time |
| `lastEvaluatedAt` | Same as `openedAt` | Initially same |

**No logic, no calculation, no decisions** - just initial state.

---

## 🚫 What Phase 5.1 Does NOT Do

### NO Progress Calculation
- `progressPercent` is **always 0** in PR-5.1
- Calculation logic = PR-5.2

### NO Target Tracking
- `reachedTargets` is **always []** in PR-5.1
- Tracking logic = PR-5.2

### NO Status Transitions
- `status` is **always 'open'** in PR-5.1
- Transition logic = PR-5.2

### NO Re-analysis
- No invalidation detection
- No structural break monitoring
- Re-analysis = PR-5.3

### NO Execution
- No buy/sell
- No SL/TP execution
- No capital management
- **Never** in ESB v1.0

---

## 💡 Why Immutability?

**Benefits:**

1. **Deterministic Replay**
   - Same inputs always produce same output
   - Critical for testing and debugging
   - Enables time-travel debugging

2. **Event Sourcing Ready**
   - Each Virtual Position is a complete snapshot
   - Can reconstruct state history
   - Future-proof for audit trails

3. **Prevents Bugs**
   - No accidental mutations
   - Clear ownership of state
   - Easier to reason about

4. **Clear State Transitions**
   - Old state → New state (explicit)
   - No hidden side effects
   - Each transition is a new object

**Trade-off:**
- More memory (storing full objects)
- Acceptable for observation-only runtime

---

## 📝 Usage Examples

### Creating a Virtual Position

```typescript
import { createVirtualPosition } from './virtual-positions';

// Inputs from Phase 4
const scenario = /* EntryScenario with status='valid' */;
const score = /* ConfluenceScore referencing scenario */;
const risk = /* RiskContract with status='valid' referencing scenario */;
const timestamp = Date.now(); // Fixed timestamp (NOT dynamic)

// Create Virtual Position
const result = createVirtualPosition(scenario, score, risk, timestamp);

if (result.success) {
  console.log('Virtual Position created:', result.position);
  // {
  //   id: 'vpos-scen-1-1704067200000',
  //   scenarioId: 'scen-1',
  //   scenarioType: 'LiquiditySweepDisplacement',
  //   score: { ... },
  //   risk: { ... },
  //   status: 'open',
  //   progressPercent: 0,
  //   reachedTargets: [],
  //   openedAt: 1704067200000,
  //   lastEvaluatedAt: 1704067200000
  // }
} else {
  console.error('Failed to create Virtual Position:', result.error);
  // 'SCENARIO_NOT_VALID' or 'RISK_NOT_VALID'
}
```

### Error Handling

```typescript
// Invalid scenario
const result1 = createVirtualPosition(formingScenario, score, risk, timestamp);
// result1 = { success: false, error: 'SCENARIO_NOT_VALID' }

// Invalid risk
const result2 = createVirtualPosition(scenario, score, invalidRisk, timestamp);
// result2 = { success: false, error: 'RISK_NOT_VALID' }

// Mismatched relationships
const result3 = createVirtualPosition(scenario, mismatchedScore, risk, timestamp);
// result3 = { success: false, error: 'RISK_NOT_VALID' }
```

---

## 🧪 Testing

Virtual Position tests verify:

1. **Determinism**: Same inputs → same output
2. **Immutability**: No input mutation
3. **Initial State**: All fields correct
4. **Validation**: Correct error codes
5. **No Logic**: No calculations performed

Run tests:
```bash
npm test -- virtualPosition.invariants.spec.ts
```

---

## 🔮 Future Evolution

### PR-5.2: Progress Engine
- Calculate `progressPercent`
- Update `reachedTargets`
- Transition `status`
- Create updated snapshots

### PR-5.3: Re-analysis Triggers
- Detect invalidation conditions
- Trigger re-evaluation
- Monitor structural breaks

### Future Phases
- Event sourcing (state history)
- Replay capabilities
- Audit trails
- Performance analytics

---

## 🔄 Phase 5.2: Progress Engine

**What it does:**
- Calculates structural progress toward TP targets (0% → 100%)
- Detects when TP levels are reached
- Derives lifecycle status (`open`, `progressing`, `stalled`, `completed`)
- Returns updated immutable snapshots

**What it does NOT do:**
- Does NOT invalidate positions (Phase 5.3)
- Does NOT re-evaluate scenarios (Phase 5.3)
- Does NOT check structural validity (Phase 5.3)
- Does NOT execute trades
- Does NOT use confidence or scoring logic

### Key Design Decisions

1. **Direction inference:** Derived from SL/TP positioning (no EntryScenario dependency)
   - If SL below TP1 → bullish
   - If SL above TP1 → bearish
   - Purely structural, deterministic

2. **Progress calculation:** Linear, structural, clamped [0, 100]
   - Entry reference: Midpoint between SL and TP1 boundaries
   - **Entry Reference Clarification (ESB v1.0 Semantic Lock):**
     * Entry reference is defined as the **structural midpoint** between the Stop Loss POI boundary and the nearest Take Profit (TP1) boundary
     * This is a **deterministic structural approximation**, NOT an execution price
     * NOT stored state, NOT derived from `openedAt`
     * This definition is **frozen for ESB v1.0** to ensure replay safety and deterministic behavior
   - Furthest TP: TP3 if exists, else TP2, else TP1
   - Formula (Bullish): `((currentPrice - entryRef) / (furthestTP - entryRef)) * 100`
   - Formula (Bearish): `((entryRef - currentPrice) / (entryRef - furthestTP)) * 100`

3. **Non-decreasing progress:** `Math.max()` ensures monotonicity
   - Progress can only increase or stay the same
   - No new field needed - history = immutable snapshots

4. **TP skipping allowed:** Price can reach TP3 before TP1/TP2
   - Logical sorting always maintained: `['TP1', 'TP2', 'TP3']`
   - No duplicates in `reachedTargets`

5. **Stalling threshold:** Hard-coded 1 hour
   - Progress unchanged AND time elapsed > 1 hour → `stalled`
   - Uses `lastEvaluatedAt` from existing VirtualPosition

6. **Status priority:** `completed` > `stalled` > `progressing` > `open`
   - Strict hierarchy ensures predictable transitions
   - `invalidated` NOT used in Phase 5.2 (reserved for Phase 5.3)

### Function Signature

```typescript
function updateVirtualPositionProgress(
  position: VirtualPosition,
  currentPrice: number,
  pois: Map<string, POI>,
  evaluatedAt: number
): VirtualPosition
```

### Mental Model

> Phase 5.2 answers: "How is this idea progressing over time if price moves?"
> 
> NO decisions. NO execution. NO risk logic.

### Usage Example

```typescript
// Initial position (from PR-5.1)
let position = createVirtualPosition(scenario, score, risk, 1000000);
// status: 'open', progressPercent: 0

// Market moves, price = 125 (toward TP1)
position = updateVirtualPositionProgress(
  position,
  125,
  poiMap,
  1000100
);
// status: 'progressing', progressPercent: 30 (example)

// Price reaches TP1 (130)
position = updateVirtualPositionProgress(
  position,
  130,
  poiMap,
  1000200
);
// status: 'progressing', progressPercent: 50, reachedTargets: ['TP1']

// Price stalls for 1 hour
position = updateVirtualPositionProgress(
  position,
  130,
  poiMap,
  1000200 + 3700000 // > 1 hour later
);
// status: 'stalled', progressPercent: 50 (unchanged)

// Price eventually reaches TP3
position = updateVirtualPositionProgress(
  position,
  180,
  poiMap,
  1005000
);
// status: 'completed', progressPercent: 100, reachedTargets: ['TP1', 'TP2', 'TP3']
```

### Testing

Run progress engine tests:
```bash
npm test -- virtualPosition.progress.spec.ts
```

**Test Coverage:**
- ✅ Progress monotonicity (never decreases)
- ✅ Correct TP detection (with skipping)
- ✅ Status transitions
- ✅ Determinism
- ✅ Immutability
- ✅ Boundary cases (31 tests, all passing)

---

## ⚠️ Constraints

**Absolute Constraints (NEVER violate):**

- ❌ NO `Date.now()` calls (timestamps must be provided)
- ❌ NO randomness (determinism required)
- ❌ NO execution logic (observation only)
- ❌ NO mutations (immutability required)
- ❌ NO hidden behavior (explicit errors only)

**Phase 5.1 Constraints:**

- ❌ NO progress calculation (moved to Phase 5.2)
- ❌ NO status transitions (moved to Phase 5.2)
- ❌ NO target tracking (moved to Phase 5.2)
- ❌ NO decision logic

**Phase 5.2 Constraints:**

- ❌ NO invalidation logic (Phase 5.3)
- ❌ NO re-evaluation logic (Phase 5.3)
- ❌ NO structural validity checks (Phase 5.3)
- ❌ NO execution logic
- ❌ NO confidence or score logic

---

## 📚 Related Phases

- **Phase 4.3**: Entry Scenarios → Provides `EntryScenario` type
- **Phase 4.4**: Confluence Scoring → Provides `ConfluenceScore` type
- **Phase 4.5**: Risk Contracts → Provides `RiskContract` type
- **Phase 5.1**: Virtual Position Model → Provides `VirtualPosition` type and `createVirtualPosition()` factory
- **Phase 5.2**: Progress Engine → Provides `updateVirtualPositionProgress()` (CURRENT)
- **Phase 5.3**: Re-analysis Logic → Will trigger re-evaluation (future)

---

## 🔒 Semantic Lock

Once merged:
- **Phase 5.1 semantics FROZEN** (VirtualPosition model)
- **Phase 5.2 semantics FROZEN** (Progress calculation logic)

Changes to field names, type definitions, validation rules, or error codes require major version bump and migration plan.

**Reason**: Virtual Positions and progress semantics are the runtime foundation - breaking changes cascade through the entire system.

Phase 5.3 MUST NOT modify progress logic.

---

## 🔄 Phase 5.3: Re-analysis & Invalidation Engine

**What it does:**
- Re-evaluates structural validity of Virtual Positions
- Detects invalidation conditions
- Returns explicit, machine-readable results
- Fully deterministic and replay-safe

**What it does NOT do:**
- Does NOT provide guidance or suggestions
- Does NOT manage positions
- Does NOT execute trades
- Does NOT calculate progress (Phase 5.2)
- Does NOT communicate with users

### Invalidation Reasons

| Reason | Meaning |
|--------|---------|
| `STRUCTURE_BROKEN` | Market structure contradicts scenario premise |
| `POI_INVALIDATED` | Critical POI (SL/TP anchor) is mitigated |
| `LIQUIDITY_TAKEN_AGAINST` | Opposing-side liquidity taken after entry |
| `HTF_BIAS_FLIPPED` | Higher-timeframe bias flipped against scenario |
| `TIME_DECAY_EXCEEDED` | Scenario exceeded 24-hour lifespan without resolution |

### Key Design Decisions

1. **Minimal input:** Upstream provides analysis results (no market analysis in Phase 5.3)
2. **Short-circuit validation:** Returns on first invalidation detected
3. **HTF direction inference:** Reuses Phase 5.2 logic (SL/TP positioning)
4. **Completed positions:** Skipped (terminal state)
5. **Time decay:** Hard-coded 24 hours (consistency with Phase 5.2)

### Mental Model

> **Phase 5.2:** "How is this idea progressing?"  
> **Phase 5.3:** "Is this idea still valid?"  
> 
> **NOT:** "What should we do?"

### Function Signature

```typescript
function reanalyzeVirtualPosition(
  position: VirtualPosition,
  marketState: MarketState,
  evaluatedAt: number
): ReanalysisResult
```

### Market State

```typescript
interface MarketState {
  pois: Map<string, POI>;
  htfBias: 'bullish' | 'bearish' | 'neutral';
  structureIntact: boolean;
  counterLiquidityTaken: boolean;
  invalidatedPOIs: Set<string>;
}
```

**Architecture Decision:** Minimal, observational input. Phase 5.3 does NOT analyze market - it only reads analysis results from upstream.

### Re-analysis Result

```typescript
type ReanalysisResult =
  | {
      status: 'still_valid';
      checksPassed: ReanalysisCheck[];
    }
  | {
      status: 'invalidated';
      reason: InvalidationReason;
    };
```

**Architecture Decision:** Explicit, machine-readable enums only (NO free-text).

### Validation Checks (Ordered, Short-Circuit)

Execute in this exact order, return immediately on first failure:

1. **Completed Position Check (Pre-filter):** Skip re-analysis for completed positions
2. **Structure Validity:** Check `marketState.structureIntact`
3. **POI Validity:** Check if critical POIs (SL + all TPs) are invalidated
4. **Liquidity Against Position:** Check `marketState.counterLiquidityTaken`
5. **HTF Bias Alignment:** Check if HTF bias has flipped
6. **Time Decay:** Check if elapsed time > 24 hours
7. **All Checks Passed:** Return all passed checks (audit-friendly)

### Usage Example

```typescript
// Position from Phase 5.1/5.2
const position = updateVirtualPositionProgress(
  virtualPosition,
  currentPrice,
  pois,
  1000100
);

// Market state (provided by upstream analysis)
const marketState: MarketState = {
  pois: poiMap,
  htfBias: 'bullish',
  structureIntact: true,
  counterLiquidityTaken: false,
  invalidatedPOIs: new Set()
};

// Re-analyze
const result = reanalyzeVirtualPosition(
  position,
  marketState,
  1000200
);

if (result.status === 'still_valid') {
  console.log('Position still valid');
  console.log('Checks passed:', result.checksPassed);
  // ['STRUCTURE_INTACT', 'POI_REMAINS_VALID', 'NO_COUNTER_LIQUIDITY', 'HTF_BIAS_ALIGNED']
} else {
  console.log('Position invalidated');
  console.log('Reason:', result.reason);
  // e.g., 'STRUCTURE_BROKEN'
}
```

### Testing

Run re-analysis tests:
```bash
npm test -- reanalysis.invariants.spec.ts
```

**Test Coverage:**
- ✅ Determinism (same inputs → same output)
- ✅ No mutation (inputs unchanged)
- ✅ Each invalidation reason (5 scenarios)
- ✅ Still-valid path
- ✅ Boundary cases (24 hours, neutral HTF, completed position)
- ✅ Isolation from Phase 5.2

### Future Guidance Layer (Phase 5.4+)

Everything like "hold", "move stop", "partial close", "wait" belongs to a future Guidance Layer, NOT Phase 5.3.

**Phase 5.3 ONLY answers: "Is this still valid?"**

---

## 📖 Summary

**Virtual Position = State Model for Dry-Run Observation**

- Created from validated Phase 4 inputs
- Immutable snapshots
- Deterministic behavior
- Foundation for paper trading
- No execution, no capital, no risk

**Phase 5.1 = Model + Creation** ✅

**Phase 5.2 = Evolution + Progress** ✅

**Phase 5.3 = Re-analysis + Invalidation** ✅

**Dry-Run Runtime Complete!** 🎉

Clean, simple, safe. ✅

---

## 🔄 Phase 5.4: Guidance Layer / Narrative Signals

**What it does:**
- Provides observational context for Virtual Positions
- Aggregates progress, status, and validity into analytical posture
- Returns machine-readable guidance signals
- Fully deterministic and replay-safe

**What it does NOT do:**
- Does NOT make decisions
- Does NOT manage positions
- Does NOT execute trades
- Does NOT provide trading instructions
- Does NOT perform market analysis

### Guidance Signals

| Signal | Meaning |
|--------|---------|
| `HOLD_THESIS` | Thesis intact, structure & progress healthy |
| `THESIS_WEAKENING` | Valid, but momentum/progress degraded (stalled) |
| `STRUCTURE_AT_RISK` | Invalidated (re-analysis flagged failure) |
| `WAIT_FOR_CONFIRMATION` | Early stage / low progress / neutral state |

### Key Design Decisions

1. **Priority cascade:** `completed` > `invalidated` > `stalled` > progress thresholds
2. **Progress thresholds:** `< 25%` = wait, `≥ 25%` = hold (if not stalled)
3. **Stalling dominance:** ANY `stalled` status → `THESIS_WEAKENING`
4. **Status informs, progress leads:** `open` or `progressing` don't override progress checks
5. **No invalidation reason:** Phase 5.3 already carries it, no duplication

### Mental Model

> **Phase 5.2:** "How is it progressing?"  
> **Phase 5.3:** "Is it still valid?"  
> **Phase 5.4:** "What is the current analytical posture?"

**NOT:**
> "What should I do?"

### Critical Distinction

Phase 5.4 is **context**, NOT **decision**.

Guidance signals are **observational**, NOT **instructional**.

### Function Signature

```typescript
function deriveGuidance(
  position: VirtualPosition,
  reanalysisResult: ReanalysisResult
): GuidanceResult
```

### Guidance Result

```typescript
interface GuidanceResult {
  signal: GuidanceSignal;
  progressPercent: number;
  status: VirtualPositionStatus;
  validity: 'still_valid' | 'invalidated';
}
```

### Priority Order (EXACT)

Execute in this exact order:

1. **Completed positions (terminal state):** Always return `HOLD_THESIS`
2. **Invalidated (always dominates):** Return `STRUCTURE_AT_RISK` (unless completed)
3. **Stalled (always weakening):** Return `THESIS_WEAKENING` (regardless of progress: 30%, 60%, 80%)
4. **Progress < 25%:** Return `WAIT_FOR_CONFIRMATION`
5. **Default:** Return `HOLD_THESIS` (healthy thesis)

### Progress Thresholds (Left-Inclusive, Right-Exclusive)

| Progress Range | Condition | Guidance Signal |
|----------------|-----------|-----------------|
| `progress < 25` | Early stage | `WAIT_FOR_CONFIRMATION` |
| `25 ≤ progress < 75` | Healthy progression | `HOLD_THESIS` |
| `≥ 75` | Near completion | `HOLD_THESIS` |

**Stalling Override:**
- ANY `stalled` status → `THESIS_WEAKENING` (regardless of progress)

### Status Semantics

| Status | Progress | Result |
|--------|----------|--------|
| `open` | `< 25%` | `WAIT_FOR_CONFIRMATION` |
| `open` | `≥ 25%` | `HOLD_THESIS` |
| `progressing` | `< 25%` | `WAIT_FOR_CONFIRMATION` |
| `progressing` | `≥ 25%` | `HOLD_THESIS` |
| `stalled` | ANY | `THESIS_WEAKENING` |
| `completed` | ANY | `HOLD_THESIS` |
| ANY | (invalidated) | `STRUCTURE_AT_RISK` |

**Rules:**
- Status does NOT block progress semantics
- `progressing` does NOT override progress thresholds
- `stalled` ALWAYS means weakening

### Usage Example

```typescript
// Position from PR-5.2
const position = updateVirtualPositionProgress(
  virtualPosition,
  currentPrice,
  pois,
  1000100
);

// Re-analysis from PR-5.3
const reanalysisResult = reanalyzeVirtualPosition(
  position,
  marketState,
  1000100
);

// Derive guidance
const guidance = deriveGuidance(position, reanalysisResult);

console.log(guidance);
// {
//   signal: 'HOLD_THESIS',
//   progressPercent: 50,
//   status: 'progressing',
//   validity: 'still_valid'
// }
```

### Testing

Run guidance tests:
```bash
npm test -- guidance.invariants.spec.ts
```

**Test Coverage:**
- ✅ Determinism (same inputs → same output)
- ✅ Priority cascade (completed > invalidated > stalled > progress)
- ✅ Progress thresholds (< 25%, ≥ 25%)
- ✅ Status interaction (status informs, progress leads)
- ✅ Invalidation dominance
- ✅ Immutability (no mutation of inputs)
- ✅ All four guidance signals reachable
- ✅ Boundary cases (25%, 24.9%)

### Key Philosophy

> **Phase 5.4 DOES NOT TELL THE USER WHAT TO DO**  
> It only says "how the idea currently looks."

**Guidance ≠ Advice**  
**Guidance = Context**

---

## 🔄 Phase 5.5: Timeline / Observation History

**What it does:**
- Records how Virtual Position analytical state evolves over time
- Stores ordered snapshots as append-only log
- Aggregates outputs from Phases 5.2, 5.3, 5.4
- Fully deterministic and replay-safe

**What it does NOT do:**
- Does NOT analyze market data
- Does NOT make decisions
- Does NOT provide recommendations
- Does NOT influence progress, re-analysis, or guidance logic
- Does NOT reorder or reinterpret past data

### Timeline Structure

```typescript
interface TimelineEntry {
  evaluatedAt: number;
  
  // From Phase 5.2
  progressPercent: number;
  status: VirtualPositionStatus;
  
  // From Phase 5.3
  validity: 'still_valid' | 'invalidated';
  invalidationReason?: InvalidationReason;
  
  // From Phase 5.4
  guidance: GuidanceSignal;
}
```

### Key Design Decisions

1. **Append-only log:** Entries can only be added, never removed or modified
2. **Chronological order:** Entries sorted by `evaluatedAt` (append order if same timestamp)
3. **Silent no-op on invalid append:** Earlier timestamps ignored (returns original timeline)
4. **No validation:** Trusts upstream phases (5.2, 5.3, 5.4)
5. **No query helpers:** Phase 5.5 = memory, Phase 6 = interpretation
6. **Manual construction:** No factory functions or aggregation helpers

### Invariants

- ✅ Entries ordered by `evaluatedAt`
- ✅ `entry.evaluatedAt >= lastEntry.evaluatedAt` (or silent no-op)
- ✅ Timeline immutable (always returns new object)
- ✅ Deterministic (same inputs → same output)

### Mental Model

> **Phase 5.5 is MEMORY, NOT INTELLIGENCE.**
> 
> - No interpretation
> - No optimization
> - No inference
> - Just record

### Function Signature

```typescript
function appendTimelineEntry(
  timeline: VirtualPositionTimeline,
  entry: TimelineEntry
): VirtualPositionTimeline
```

### Usage Example

```typescript
// Create empty timeline
let timeline: VirtualPositionTimeline = {
  positionId: 'pos-1',
  entries: []
};

// Position evolves (Phase 5.2)
const position1 = updateVirtualPositionProgress(position, 120, pois, 1000000);
const reanalysis1 = reanalyzeVirtualPosition(position1, marketState, 1000000);
const guidance1 = deriveGuidance(position1, reanalysis1);

// Record first observation
const entry1: TimelineEntry = {
  evaluatedAt: 1000000,
  progressPercent: position1.progressPercent,
  status: position1.status,
  validity: reanalysis1.status,
  invalidationReason: reanalysis1.status === 'invalidated' ? reanalysis1.reason : undefined,
  guidance: guidance1.signal
};

timeline = appendTimelineEntry(timeline, entry1);
// timeline.entries.length === 1

// Position evolves again
const position2 = updateVirtualPositionProgress(position1, 130, pois, 1000100);
const reanalysis2 = reanalyzeVirtualPosition(position2, marketState, 1000100);
const guidance2 = deriveGuidance(position2, reanalysis2);

// Record second observation
const entry2: TimelineEntry = {
  evaluatedAt: 1000100,
  progressPercent: position2.progressPercent,
  status: position2.status,
  validity: reanalysis2.status,
  invalidationReason: reanalysis2.status === 'invalidated' ? reanalysis2.reason : undefined,
  guidance: guidance2.signal
};

timeline = appendTimelineEntry(timeline, entry2);
// timeline.entries.length === 2

// Attempt to append out-of-order entry
const oldEntry: TimelineEntry = {
  evaluatedAt: 999999, // earlier than entry1
  // ...
};

timeline = appendTimelineEntry(timeline, oldEntry);
// timeline unchanged (silent no-op)
// timeline.entries.length === 2
```

### Testing

Run timeline tests:
```bash
npm test -- timeline.invariants.spec.ts
```

**Test Coverage:**
- ✅ Empty timeline → first append
- ✅ Sequential appends
- ✅ Same timestamp handling (insertion order preserved)
- ✅ Out-of-order rejection (silent no-op)
- ✅ Immutability (no mutation)
- ✅ Determinism (same inputs → same output)

### Future Phase 6 (Policy / Interpretation Layer)

Phase 6 MAY interpret timeline history for:
- Pattern detection
- Trend analysis
- Policy decisions

Phase 5.5 does NOT interpret history.

---

## 📖 Summary

**Virtual Position = State Model for Dry-Run Observation**

- Created from validated Phase 4 inputs
- Immutable snapshots
- Deterministic behavior
- Foundation for paper trading
- No execution, no capital, no risk

**Phase 5.1 = Model + Creation** ✅

**Phase 5.2 = Evolution + Progress** ✅

**Phase 5.3 = Re-analysis + Invalidation** ✅

**Phase 5.4 = Guidance Layer / Narrative Signals** ✅

**Phase 5.5 = Timeline / Observation History** ✅

**ESB v1.0 Dry-Run Runtime COMPLETE!** 🎉

Clean, simple, safe. ✅
