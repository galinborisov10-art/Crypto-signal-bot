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

**Phase 6.1 = Timeline Interpretation Engine** ✅

**ESB v1.0 Dry-Run Runtime COMPLETE!** 🎉

Clean, simple, safe. ✅

---

## 🔄 Phase 6.1: Timeline Interpretation Engine

**What it does:**
- Pure, read-only pattern recognition over timeline
- Detects trajectory patterns (stable, slowing, stalled, regressing)
- Analyzes stability (early weakening, repeated instability, termination)
- Classifies invalidation timing (early, mid, late)
- Tracks guidance consistency (flip-flop, degrading, consistent)
- Fully deterministic and replay-safe

**What it does NOT do:**
- Does NOT make decisions
- Does NOT provide recommendations
- Does NOT manage positions
- Does NOT analyze market data
- Does NOT mutate timeline or entries

**Key Design Decisions:**

1. **Trajectory:** Majority-based delta analysis (not just last delta)
   - Calculates sequential deltas between progress measurements
   - Uses majority voting: if most deltas positive → STABLE_PROGRESS
   - Detects slowing: all positive but shrinking magnitude
   - Defensive regressing detection (should never happen with Phase 5.2 invariants)

2. **Slowing:** Positive deltas with shrinking magnitude
   - All deltas > 0 (positive progress)
   - At least one consecutive pair where `|delta[i+1]| < |delta[i]|`
   - Example: deltas [+30, +20, +10] → SLOWING_PROGRESS

3. **Regressing:** Defensive (should never happen with Phase 5.2 invariants)
   - Any delta < 0 (progress decreased)
   - Comment in code: "Should never happen if Phase 5.2 invariants hold"

4. **Stability priority:** `TERMINATED` > `REPEATED_INSTABILITY` > `EARLY_WEAKENING` > `STABLE`
   - Strict cascade ensures predictable results
   - TERMINATED: ANY completed OR invalidated entry (always dominates)
   - REPEATED_INSTABILITY: ≥ 2 stalled entries (anywhere, not necessarily consecutive)
   - EARLY_WEAKENING: Stalled or weakening WHILE progress < 25%

5. **Invalidation:** First invalidation only (most semantically important)
   - Ignores subsequent invalidations
   - Classifies based on progress: < 25% (EARLY), < 75% (MID), ≥ 75% (LATE)
   - Only present if invalidation exists, otherwise undefined

6. **Guidance consistency:** Real flip-flop pattern (A → B → A), not just changes
   - Detects actual oscillation: signal returns to previous value
   - Examples: HOLD → WEAK → HOLD, WAIT → HOLD → WAIT
   - NOT just "many changes" - specific return pattern

7. **Degrading:** Net movement to weaker signals without recovery
   - Compares first and last signal strength
   - Checks for any upward movement (recovery)
   - If lastStrength < firstStrength AND no recovery → DEGRADING

8. **Minimum entries:** Different thresholds
   - Trajectory: 2 entries (need deltas)
   - Stability: 2 entries (meaningful stability analysis)
   - Guidance consistency: 3 entries (need transitions)
   - Invalidation pattern: 1 invalidation event

**Signal Strength Order:**
```
HOLD_THESIS (strongest, value: 4)
  > WAIT_FOR_CONFIRMATION (value: 3)
  > THESIS_WEAKENING (value: 2)
  > STRUCTURE_AT_RISK (weakest, value: 1)
```

**Mental Model:**

> **"Brain without will"**
> 
> Phase 6.1 observes patterns, does NOT act on them.

**This is the last observational layer.**

Phase 6.2+ (if implemented) would add policy, but Phase 6.1 is complete pattern recognition without decisions.

### Function Signature

```typescript
export function interpretTimeline(
  timeline: VirtualPositionTimeline
): TimelineInterpretation
```

**Function Semantics:**
- Pure (no side effects)
- Deterministic (same inputs → same output)
- Read-only (no mutations)
- Always succeeds (uses NO_DATA for insufficient data)

### Timeline Interpretation Type

```typescript
interface TimelineInterpretation {
  trajectory: TrajectorySignal;
  stability: StabilitySignal;
  invalidationPattern?: InvalidationPattern;
  guidanceConsistency?: GuidanceConsistency;
}
```

**All outputs are machine-readable enums (NO free text).**

### Usage Example

```typescript
// Timeline from Phase 5.5
const timeline: VirtualPositionTimeline = {
  positionId: 'pos-1',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 25,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 50,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

// Interpret timeline
const interpretation = interpretTimeline(timeline);

console.log(interpretation);
// {
//   trajectory: 'STABLE_PROGRESS',
//   stability: 'STRUCTURALLY_STABLE',
//   invalidationPattern: undefined,
//   guidanceConsistency: 'CONSISTENT'
// }
```

### Testing

Run interpretation tests:
```bash
npm test -- interpretation.invariants.spec.ts
```

**Test Coverage:**
- ✅ Trajectory patterns (NO_DATA, STABLE, SLOWING, STALLED, REGRESSING)
- ✅ Stability patterns (TERMINATED, REPEATED_INSTABILITY, EARLY_WEAKENING, STABLE)
- ✅ Invalidation patterns (EARLY, MID, LATE, undefined)
- ✅ Guidance consistency (FLIP_FLOP, DEGRADING, CONSISTENT, undefined)
- ✅ Determinism (same inputs → same output)
- ✅ Immutability (no mutations)
- ✅ Edge cases (boundaries, empty timeline, single entry)

### Key Philosophy

> **All signals are observational.**
> 
> - No policy
> - No recommendations
> - This is the last "brain without will" layer

Phase 6.1 completes the pattern recognition foundation for ESB v1.0.

---

## 🧭 Phase 6.2: Policy Layer (Normative Interpretation)

**Phase 6.2 is COMPLETE and FROZEN for ESB v1.0.**

This layer translates pattern recognition (Phase 6.1) into normative stance — opinion without action.

### What Policy IS

Policy is the **normative interpretation** of observed patterns. It translates timeline interpretation outputs into an abstract stance toward an apparent trading idea.

**Key characteristics:**

Policy has **opinion** but NOT **action**.

- **Normative interpretation:** Provides a judgment or stance on pattern quality
- **Opinion without will:** Can assess and classify, but cannot execute or decide
- **Abstract stance:** Takes a position on the idea itself, not on what to do about it
- **Bridge layer:** Sits between observation (Phase 5–6.1) and future decision layers (Phase 6.3+)

Policy translates pattern recognition (Phase 6.1) into a normative stance.

### What Policy IS NOT

Policy is explicitly **NOT** any of the following:

- ❌ NOT a decision
- ❌ NOT execution
- ❌ NOT position management
- ❌ NOT recommendations
- ❌ NOT trade advice
- ❌ NOT market analysis

**Policy provides stance. It does not provide instructions.**

### Inputs to Policy

Policy consumes **ONLY** outputs of Phase 6.1 (`TimelineInterpretation`).

**Policy has access to:**
- ✅ Trajectory signals (STABLE_PROGRESS, SLOWING_PROGRESS, etc.)
- ✅ Stability signals (STRUCTURALLY_STABLE, EARLY_WEAKENING, etc.)
- ✅ Invalidation patterns (EARLY, MID, LATE)
- ✅ Guidance consistency (CONSISTENT, DEGRADING, FLIP_FLOP)

**Policy has NO access to:**
- ❌ Timeline entries
- ❌ Price data
- ❌ POIs (Points of Interest)
- ❌ Market state
- ❌ Virtual position details

**Architectural boundary:**

Policy operates on **interpreted patterns**, NOT raw observations.

This prevents policy from re-implementing interpretation logic and ensures clean separation of concerns.

### Outputs of Policy

Policy produces a `PolicyResult` containing a stance and confidence level.

#### PolicyResult

**Stance (`PolicyStance`):**

- `STRONG_THESIS` — All signals aligned, high-stability idea
- `WEAKENING_THESIS` — Valid but degrading idea
- `HIGH_RISK_THESIS` — Conflicting/unstable patterns
- `INVALID_THESIS` — Invalidated idea (derived, not execution)
- `COMPLETED_THESIS` — Completed idea (terminal state)
- `INSUFFICIENT_DATA` — Not enough observations to form stance

**Confidence (`PolicyConfidence`):**

- `HIGH` — Strong alignment and stability
- `MEDIUM` — Moderate alignment or some degradation
- `LOW` — Conflicts or instability present
- `UNKNOWN` — Insufficient data

**Stance is a normative position, NOT an instruction.**

Policy tells you what it thinks about the pattern, not what to do about it.

### Confidence Semantics

**Confidence is NOT:**

- ❌ Probability
- ❌ Expected performance
- ❌ Win rate
- ❌ Statistical measure

**Confidence reflects:**

- ✅ Signal alignment (do trajectory, stability, guidance agree?)
- ✅ Pattern consistency (are signals stable or flip-flopping?)
- ✅ Observation sufficiency (enough data to form stance?)

**Fixed mapping:**

| Stance | Confidence |
|--------|-----------|
| `STRONG_THESIS` | `HIGH` |
| `WEAKENING_THESIS` | `MEDIUM` |
| `HIGH_RISK_THESIS` | `LOW` |
| `INVALID_THESIS` | `HIGH` |
| `COMPLETED_THESIS` | `HIGH` |
| `INSUFFICIENT_DATA` | `UNKNOWN` |

Confidence is determined by stance, NOT adjusted dynamically.

### Priority Model

Policy derivation follows strict priority cascade:

**1. TERMINATED (highest priority)**
   - If invalidated → `INVALID_THESIS`
   - If completed → `COMPLETED_THESIS`

**2. NO_DATA**
   - → `INSUFFICIENT_DATA`

**3. STRONG_THESIS**
   - Requires ALL:
     - Stable progress
     - Structurally stable
     - Consistent guidance (or undefined for short timeline)
     - No invalidation

**4. WEAKENING_THESIS**
   - Slowing progress OR degrading guidance

**5. HIGH_RISK_THESIS**
   - Any of:
     - Early weakening
     - Repeated instability
     - Flip-flop guidance
     - Stalled trajectory
     - Regressing progress (defensive)

**6. Fallback**
   - → `HIGH_RISK_THESIS` (unclassifiable but valid risk)

**This cascade is FROZEN for ESB v1.0.**

---

> ⚠️ **ARCHITECTURAL BOUNDARY**
> 
> **Policy is the LAST layer allowed to have opinion.**
> 
> All subsequent layers (Phase 6.3+) MUST be **explicit decision layers**
> and MUST NOT be merged into Policy.
> 
> Policy provides stance. Decision provides action.
> 
> These are separate architectural concerns and must remain decoupled.

---

### Mental Model

> **"Policy is a brain without hands."**

Policy can:
- ✅ Form opinions
- ✅ Assess patterns
- ✅ Express stance

Policy cannot:
- ❌ Execute
- ❌ Manage
- ❌ Decide

**Policy = Normative interpretation**  
**Decision = Action selection** (Phase 6.3+, if implemented)

### Versioning & Stability

**Policy semantics are FROZEN for ESB v1.0.**

This includes:
- Stance definitions
- Priority cascade order
- Confidence mapping
- Input/output contracts

**Any future change to Policy semantics requires a major version bump.**

Policy is a foundational layer. Breaking changes affect all downstream consumers.

---

## 🚪 Phase 6.3: Decision Guardrail (Permission Gate)

**Phase 6.3 is COMPLETE and FROZEN for ESB v1.0.**

Decision Guardrail is the permission gate layer.

Guardrail has **authority** but NOT **will**.

Guardrail answers ONLY:
> "Is decision-making allowed at all for this idea?"

NOT:
> "What decision should be made?"
> "How should we act?"
> "What trade should be executed?"

**Permission without decision**  
**Gate, not brain**  
**Authority without action**

### What Decision Guardrail IS

Decision Guardrail is the **permission gate** that determines whether downstream decision layers are allowed to proceed with automated decision-making.

**Key characteristics:**

- **Permission authority:** Has the power to allow or block decision-making
- **Authority without will:** Can permit or deny, but cannot choose what action to take
- **Binary gate:** Either allows, requires review, or blocks — no complex reasoning
- **Policy consumer:** Operates exclusively on Policy stance (Phase 6.2 output)
- **Decision precursor:** Sits between policy interpretation (Phase 6.2) and future decision execution (Phase 6.4+)

Guardrail translates normative stance (Policy) into permission state.

### What Decision Guardrail IS NOT

Decision Guardrail is explicitly **NOT** any of the following:

- ❌ NOT a decision
- ❌ NOT a recommendation
- ❌ NOT execution
- ❌ NOT position management
- ❌ NOT market analysis
- ❌ Does NOT analyze price, timeline, or POIs

**Guardrail never chooses an action.**

Guardrail only determines whether downstream decision layers are permitted to act.

### Inputs to Decision Guardrail

Decision Guardrail consumes **ONLY** `PolicyResult` from Phase 6.2.

**Guardrail has access to:**
- ✅ Policy stance (via `PolicyStance`)

**Guardrail has NO access to:**
- ❌ Timeline entries
- ❌ Price data
- ❌ POIs (Points of Interest)
- ❌ Market state
- ❌ Interpretation logic

#### Input Processing

Decision Guardrail uses **ONLY** `PolicyStance` from `PolicyResult`.

**`PolicyConfidence` is NOT used in permission derivation.**

Rationale:
- Phase 6.2 enforces a fixed invariant: `PolicyStance → PolicyConfidence`
- Confidence is metadata for UI, reporting, and analytics
- Guardrail is a permission gate, NOT a validator
- Permission authority derives from stance alone

**Architectural boundary:**

Guardrail operates on **policy stance**, NOT raw observations or interpretations.

This prevents guardrail from re-implementing policy logic.

### Outputs of Decision Guardrail

Decision Guardrail produces a `DecisionGuardrailResult` containing a permission state and reason.

#### DecisionGuardrailResult

**Permission (`DecisionPermission`):**

- `ALLOWED`
  - Downstream decision layers MAY proceed with automated decision-making
  - Does NOT mean a decision WILL be made, only that it MAY be considered
  
- `MANUAL_REVIEW_ONLY`
  - Human-in-the-loop is required before any decision
  - Automated decision-making is blocked
  
- `BLOCKED`
  - Decision-making is forbidden for this idea
  - Both automated and manual decisions are blocked
  
- `ESCALATION_ONLY` (reserved, NOT used in ESB v1.0)
  - Type exists for future multi-policy or conflict scenarios
  - NOT used in current implementation

**Reason (`DecisionGuardrailReason`):**

- 1:1 mapping to `PolicyStance`
- ONLY policy-derived reasons
- NO system, regulatory, or technical reasons

**Permission is a gate state, NOT an instruction.**

### Canonical Permission Mapping

**This mapping is FROZEN for ESB v1.0.**

| PolicyStance | Permission | Reason |
|--------------|-----------|--------|
| `STRONG_THESIS` | `ALLOWED` | `STRONG_POLICY` |
| `WEAKENING_THESIS` | `MANUAL_REVIEW_ONLY` | `WEAKENING_POLICY` |
| `HIGH_RISK_THESIS` | `MANUAL_REVIEW_ONLY` | `HIGH_RISK_POLICY` |
| `INVALID_THESIS` | `BLOCKED` | `INVALID_POLICY` |
| `COMPLETED_THESIS` | `BLOCKED` | `COMPLETED_POLICY` |
| `INSUFFICIENT_DATA` | `BLOCKED` | `INSUFFICIENT_DATA` |

**Key rules:**

- `ALLOWED` is returned ONLY for `STRONG_THESIS`
- `MANUAL_REVIEW_ONLY` is returned for `WEAKENING_THESIS` and `HIGH_RISK_THESIS`
- `BLOCKED` is returned for `INVALID_THESIS`, `COMPLETED_THESIS`, and `INSUFFICIENT_DATA`
- `ESCALATION_ONLY` is NOT used in ESB v1.0 (reserved for future)

### Layered Architecture

```
Observation (Phase 5) → Interpretation (Phase 6.1) → Policy (Phase 6.2) → Guardrail (Phase 6.3) → Decision (Phase 6.4+, future)
```

**Or:**

```
Opinion → Permission → Action
```

**Clear rules:**

- **Policy (Phase 6.2)** is the LAST layer with **opinion**
- **Guardrail (Phase 6.3)** is the FIRST layer with **authority**
- **Decision (Phase 6.4+)** is the FIRST layer with **will**

These are distinct architectural concerns and must remain decoupled.

---

> ⚠️ **ARCHITECTURAL BOUNDARY**
> 
> **Guardrail MUST NOT contain:**
> 
> - ❌ Decision logic
> - ❌ Heuristics
> - ❌ Scoring mechanisms
> - ❌ Market reasoning
> - ❌ Trade recommendations
> 
> **Guardrail ONLY determines permission state based on policy stance.**
> 
> Violating this boundary requires a MAJOR version bump.
> 
> **Guardrail is a gate, not a brain.**

---

### Mental Model

> **"Gate, not brain."**

Guardrail can:
- ✅ Grant permission
- ✅ Require review
- ✅ Block access

Guardrail cannot:
- ❌ Make decisions
- ❌ Recommend actions
- ❌ Execute trades

**Guardrail = Permission gate**  
**Decision = Action selection** (Phase 6.4+, if implemented)

### Versioning & Stability

**Phase 6.3 (Decision Guardrail) is FROZEN for ESB v1.0.**

This includes:
- Permission states (`ALLOWED`, `MANUAL_REVIEW_ONLY`, `BLOCKED`)
- Canonical mapping from `PolicyStance` to permission
- Reason derivation (1:1 policy mapping)
- Input processing (stance-only, confidence ignored)
- Architectural boundaries

**Any future change to Guardrail semantics requires a major version bump.**

Guardrail is a foundational gate layer. Breaking changes affect all downstream consumers.

---

## 🧠 Phase 6.4: Decision Layer (Action Selection)

**Phase 6.4 is COMPLETE and FROZEN for ESB v1.0.**

Decision is the action selection layer.

Decision is the first layer with **WILL** (intent).

Decision selects action intention, NOT execution.

Decision has **will** but NOT **hands**.

Decision answers:
> "What do I intend to do for this idea?"

NOT:
> "Execute this action"  
> "Manage this position"  
> "Override guardrail"

**Will without hands**  
**Action selection without effect**  
**Intent, not operation**

### What Decision IS

Decision is the **action selection layer** that determines the intended action based on guardrail permission.

**Key characteristics:**

- **First layer with will (intent):** Has the capacity to select an action intention
- **Will without hands:** Can choose intent, but cannot execute or cause effect
- **Intent selection, not execution:** Chooses what to intend to do, not what to actually do
- **Guardrail consumer:** Operates strictly after Guardrail (Phase 6.3) and respects permission
- **Permission-based selection:** Selects action intention based exclusively on permission state

Decision translates permission state (Guardrail) into action intent.

### What Decision IS NOT

Decision is explicitly **NOT** any of the following:

- ❌ NOT execution
- ❌ NOT recommendation
- ❌ NOT strategy optimization
- ❌ NOT position management
- ❌ NOT market analysis
- ❌ NOT guardrail bypass
- ❌ NOT state mutation

**Decision never:**

- Touches price data
- Touches timeline entries
- Touches POIs
- Executes trades
- Manages positions
- Overrides guardrail permissions
- Mutates system state

Decision only selects intent based on guardrail permission.

### Inputs to Decision

Decision consumes **ONLY** `DecisionGuardrailResult` from Phase 6.3.

**Decision has access to:**
- ✅ `DecisionPermission`
- ✅ `DecisionGuardrailReason`

**Decision has NO access to:**
- ❌ Policy logic
- ❌ Timeline entries
- ❌ Price data
- ❌ POIs
- ❌ Market state
- ❌ Interpretation logic

#### Input Processing

Decision uses **ONLY** `DecisionGuardrailResult` from Phase 6.3.

Decision operates on **permission**, NOT raw observations or policy.

This prevents Decision from re-implementing guardrail or policy logic.

### Outputs of Decision

Decision produces a `DecisionResult` containing an action intent and reason.

#### DecisionResult

**Action (`DecisionAction`):**

Decision selects from **5 canonical action intentions** (closed set for ESB v1.0):

- `NO_ACTION`
  - Passive "do nothing"
  - Idea doesn't require attention right now
  - NOT the same as MONITOR (which is active observation)
  - NOT the same as ABORT_IDEA (which is explicit termination)
  - Used when: not enough reason for activity, idea is not "alive" but not terminated
  
- `PREPARE_ENTRY`
  - Signal readiness for potential entry (NO execution)
  - Expresses intent: "idea is strong enough to consider entry"
  - Does NOT calculate entry parameters (price, size, etc.)
  - Does NOT change internal state
  - This is planning, NOT configuration
  - Future execution layer (Phase 7+) may act on this intent
  - Returned ONLY when guardrail permission is `ALLOWED`
  
- `MONITOR`
  - Continue active observation of this idea
  - Idea is active and deserves ongoing attention
  - NOT the same as NO_ACTION (which is passive)
  - Used when: idea warrants tracking but no immediate action
  
- `REQUEST_MANUAL_REVIEW`
  - Explicit human review is required before proceeding
  - Automated decision-making stops here
  - Commonly used when guardrail permission is `MANUAL_REVIEW_ONLY`
  - Can also be used when permission is `ESCALATION_ONLY`
  
- `ABORT_IDEA`
  - Explicitly abandon this idea
  - This is a DECISION choice, not a consequence of guardrail blocking
  - Can be returned even when permission is `ALLOWED` (decision chooses to terminate)
  - NOT the same as guardrail `BLOCKED` (which prevents decision-making entirely)

**These 5 actions form a closed set for ESB v1.0.**

NO_ACTION ≠ MONITOR ≠ ABORT_IDEA (distinct semantics)

**Action is an intent (will), NOT an instruction.**

**Reason (`DecisionReason`):**

- Direct 1:1 mirror of `DecisionGuardrailReason`
- ONLY policy-derived reasons
- NO decision-specific reasoning
- NO transformation or remapping

### Canonical Permission → Action Mapping

**This mapping is FROZEN for ESB v1.0.**

| Guardrail Permission | Decision Action |
|---------------------|-----------------|
| `BLOCKED` | `NO_ACTION` |
| `MANUAL_REVIEW_ONLY` | `REQUEST_MANUAL_REVIEW` |
| `ALLOWED` | `PREPARE_ENTRY` |
| `ESCALATION_ONLY` | `REQUEST_MANUAL_REVIEW` |

**Key rules:**

- `PREPARE_ENTRY` is returned ONLY when guardrail permission is `ALLOWED`
- `NO_ACTION` is returned when permission is `BLOCKED`
- `REQUEST_MANUAL_REVIEW` is returned when permission is `MANUAL_REVIEW_ONLY` or `ESCALATION_ONLY`
- Decision NEVER bypasses guardrail authority
- Decision respects permission without exception

### DecisionReason Semantics

**`DecisionReason` is a direct 1:1 mirror of policy-derived reason.**

Decision does NOT:
- Transform reasons
- Add decision-specific reasoning
- Invent new explanations

**Reason lineage is preserved:**

```
Policy (Phase 6.2) → Guardrail (Phase 6.3) → Decision (Phase 6.4)
```

**Decision explains WHAT intent was selected.**  
**WHY remains policy-based.**

This design ensures:
- 🔗 Full traceability from policy to action
- 🧠 Decision chooses action, NOT explanation
- 🧱 Reason remains policy-based, NOT "decision-based"
- 🔒 Prevents future creep ("let's add decision reasons...")

**This is NOT a shortcut, this is DESIGN.**

---

> ⚠️ **ARCHITECTURAL BOUNDARY**
> 
> **Decision MUST NOT:**
> 
> - ❌ Execute trades
> - ❌ Contain heuristics
> - ❌ Perform strategy optimization
> - ❌ Override guardrail permissions
> - ❌ Mutate system state
> - ❌ Access market data, price, timeline, or POIs
> 
> **Decision ONLY selects action intent based on guardrail permission.**
> 
> **Decision = WILL, not HANDS.**
> 
> Violating this boundary requires a MAJOR version bump.
> 
> **Decision is intent selection, not execution.**

---

### Mental Model

**Decision chooses intent.**  
**Execution (future) performs action.**

Or:

```
Guardrail says: "May I act?"
Decision says: "What do I intend to do?"
Execution says: "Do it."
```

**Layered Architecture:**

```
Policy → Guardrail → Decision → Execution (future)
Opinion → Authority → Will → Hands
```

**Clear roles:**

- **Guardrail (Phase 6.3)** has **authority** (permission)
- **Decision (Phase 6.4)** has **will** (intent)
- **Execution (Phase 7+)** has **hands** (effect)

These are distinct architectural concerns and must remain decoupled.

### Versioning & Stability

**Phase 6.4 (Decision Layer) is FROZEN for ESB v1.0.**

This includes:
- Decision actions (`NO_ACTION`, `PREPARE_ENTRY`, `MONITOR`, `REQUEST_MANUAL_REVIEW`, `ABORT_IDEA`)
- Canonical mapping from guardrail permission to action
- Reason pass-through (1:1 mirror, no transformation)
- Architectural boundaries (no execution, no guardrail bypass)

**Any future change to Decision semantics requires a major version bump.**

Decision is a foundational intent selection layer. Breaking changes affect all downstream consumers.

---
