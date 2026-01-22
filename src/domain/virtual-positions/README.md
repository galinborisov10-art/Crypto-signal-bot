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

## 📖 Summary

**Virtual Position = State Model for Dry-Run Observation**

- Created from validated Phase 4 inputs
- Immutable snapshots
- Deterministic behavior
- Foundation for paper trading
- No execution, no capital, no risk

**Phase 5.1 = Model + Creation**

**Phase 5.2 = Evolution + Progress** ✅

**Phase 5.3 = Re-analysis + Invalidation** (future)

Clean, simple, safe. ✅
