# Entry Scenarios - Phase 4.3

## Overview

Entry Scenarios represent **structural market ideas** in ICT methodology. They are first-class domain objects that model market patterns WITHOUT making trading decisions.

**Critical Distinction:**
- Entry Scenario = "Is there a structural market idea?"
- Trade Signal = "Should I execute a trade?" (Phase 5 - NOT implemented here)

## What is an Entry Scenario?

An Entry Scenario is a **complete structural market pattern** at a point in time. It describes:
- What type of ICT pattern is present
- Which structural gates are satisfied
- What confluence factors are present

### What it is NOT:
❌ NOT a trade signal  
❌ NOT a buy/sell recommendation  
❌ NOT an execution instruction  
❌ NOT a scoring mechanism  
❌ NOT a decision engine  

## Scenario ≠ Signal

This is the most important concept to understand:

```
Entry Scenario: "There is a liquidity sweep + displacement pattern present"
         ≠
Trade Signal: "Buy at this price with this SL/TP"
```

**Why the separation?**
- Entry Scenarios describe WHAT is happening (structural analysis)
- Trade Signals describe WHAT TO DO (execution decisions)
- Conflating them creates brittle, untestable code

## Lifecycle States

Entry Scenarios have three lifecycle states:

### 1. `forming`
**Definition:** Required gates are not yet complete; scenario is developing.

**Example:**
```typescript
{
  status: 'forming',
  requiredGates: {
    htfBiasAligned: true,      // ✅ Complete
    liquidityEvent: false,      // ❌ Missing
    structuralConfirmation: true // ✅ Complete
  }
}
```

**Important:** A scenario in `forming` state may:
- Never become `valid` (gates never complete)
- Become `invalidated` (context changes before completion)
- Eventually become `valid` (all gates become true)

### 2. `valid`
**Definition:** All required gates are satisfied; scenario is structurally complete.

**Example:**
```typescript
{
  status: 'valid',
  requiredGates: {
    htfBiasAligned: true,      // ✅
    liquidityEvent: true,       // ✅
    structuralConfirmation: true // ✅
  }
}
```

**Important:** 
- `valid` ≠ tradable
- `valid` ≠ signal
- A valid scenario is simply a complete structural idea

### 3. `invalidated`
**Definition:** Scenario has been invalidated by market conditions.

**Invalidation triggers:**
- LiquidityContext becomes non-tradable (expired, mitigated, HTF counter)
- Market structure breaks against scenario direction
- Liquidity is taken AGAINST the scenario

## Why Scenarios Can Exist and Die Silently

This is **normal and expected behavior**:

### Scenario 1: Never Valid
```
Time T0: Scenario starts forming (some gates false)
Time T1: Context expires before gates complete
Result: Scenario dies in 'forming' state
```

### Scenario 2: Valid Then Invalidated
```
Time T0: Scenario becomes valid (all gates true)
Time T1: POI gets mitigated
Time T2: Scenario becomes invalidated
Result: Scenario existed briefly, then died
```

### Scenario 3: Multiple Scenarios Compete
```
Time T0: 5 scenarios start forming
Time T1: 3 scenarios become valid
Time T2: 2 scenarios get invalidated
Time T3: 1 scenario remains valid
Result: Only 1 scenario survives
```

**Why this matters:**
- Market generates many potential patterns
- Most patterns fail to complete
- Only a few survive to become trade opportunities
- This layer models ALL patterns, not just the survivors

## How Scenarios Feed Phase 4.4 (Confluence Scoring)

**Clear Separation of Concerns:**

### Phase 4.3 (This Layer)
**Question:** "Is there an entry idea?"

**Responsibilities:**
- Identify structural pattern type
- Track required gate completion
- Record confluence presence/absence (boolean flags)
- Manage scenario lifecycle

**Output:** Entry Scenario objects with status

### Phase 4.4 (Confluence Scoring)
**Question:** "How good is the idea?"

**Responsibilities:**
- Evaluate confluence quality
- Assign scores/weights
- Calculate confidence levels
- Rank scenarios

**Input:** Entry Scenario objects (from Phase 4.3)

### Example Flow:
```typescript
// Phase 4.3: "Is there a scenario?"
const scenario = buildEntryScenario(
  EntryScenarioType.LiquiditySweepDisplacement,
  context,
  { htfBiasAligned: true, liquidityEvent: true, structuralConfirmation: true },
  { orderBlock: true, fairValueGap: true, newsRisk: false },
  timestamp
);
// → scenario.status = 'valid'

// Phase 4.4: "How good is this scenario?"
const score = evaluateConfluence(scenario);
// → score = 8.5/10 (high quality)

// Phase 5: "Should I execute?"
if (score > threshold) {
  const signal = generateSignal(scenario);
}
```

## Why This Layer Contains NO Intelligence

**Design Principle:** Entry Scenarios are **structural models**, not **decision engines**.

### What we model:
✅ Pattern type (LiquiditySweepDisplacement, BreakerBlockMSS, etc.)  
✅ Gate states (true/false)  
✅ Confluence presence (present/absent)  
✅ Lifecycle status (forming/valid/invalidated)  

### What we do NOT model:
❌ How important each gate is (no weights)  
❌ How good a confluence is (no scores)  
❌ Whether to trade (no execution)  
❌ Where to enter (no price targets)  
❌ Risk management (no SL/TP)  

**Rationale:**
- Structural modeling = Phase 4.3 (simple, deterministic, testable)
- Intelligence/scoring = Phase 4.4+ (complex, configurable, domain-specific)
- Execution = Phase 5 (risk-aware, capital-aware, timing-aware)

**Benefit:** Each layer has a single, clear responsibility.

## Architecture Decisions

### Decision 1: Uniform Gate Structure
**Choice:** All scenario types use the same 3 required gates.

**Alternative considered:** Different gates per scenario type.

**Rationale:**
- Simplifies testing and validation
- Ensures consistency across scenario types
- Gates represent fundamental structural requirements (HTF bias, liquidity, confirmation)
- Specific pattern nuances are captured by scenario type, not gate structure

**Example:**
```typescript
// All scenarios use same gates
const gates = {
  htfBiasAligned: boolean,
  liquidityEvent: boolean,
  structuralConfirmation: boolean
};

// Pattern nuance is in the type
type = EntryScenarioType.LiquiditySweepDisplacement // Specific pattern
```

### Decision 2: Explicit Gate + Confluence Inputs (Option C)
**Choice:** Caller explicitly provides gates and confluences.

**Alternatives considered:**
- Option A: Auto-detect gates from context
- Option B: Mixed (some auto, some manual)

**Rationale:**
- Maximum testability (explicit inputs → deterministic outputs)
- Clear separation of concerns (detection logic lives elsewhere)
- Replay-safe (same inputs always produce same scenario)
- Forces caller to be explicit about what they detected

**Example:**
```typescript
// Explicit: Caller provides what they detected
const scenario = buildEntryScenario(
  type,
  context,
  { htfBiasAligned: true, liquidityEvent: true, structuralConfirmation: true },
  { orderBlock: true, fairValueGap: false },
  timestamp
);

// NOT auto-detect:
// const scenario = buildEntryScenario(type, context, marketData);
// ❌ Hidden detection logic = non-deterministic
```

### Decision 3: Separate Invalidation Logic
**Choice:** `invalidateOnContextChange()` is a separate function.

**Alternative considered:** Embed invalidation logic inside `buildEntryScenario()`.

**Rationale:**
- Scenario building = construction logic
- Scenario invalidation = lifecycle management
- Separation makes testing easier
- Allows different invalidation strategies in the future

**Example:**
```typescript
// Build scenario
const scenario = buildEntryScenario(...);

// Later: Check if scenario should be invalidated
const result = invalidateOnContextChange(scenario, newContext);
if (result.invalidated) {
  // Handle invalidation
}
```

## Usage Examples

### Example 1: Basic Scenario Construction
```typescript
import { buildEntryScenario, EntryScenarioType } from './entry-scenarios';
import { buildLiquidityContext } from './liquidity-context';

// Build context from POI
const context = buildLiquidityContext(poi, timestamp);

// Define gates (explicit)
const gates = {
  htfBiasAligned: true,
  liquidityEvent: true,
  structuralConfirmation: true
};

// Define confluences (explicit)
const confluences = {
  orderBlock: true,
  fairValueGap: true,
  discountPremium: true
};

// Build scenario
const scenario = buildEntryScenario(
  EntryScenarioType.OB_FVG_Discount,
  context,
  gates,
  confluences,
  timestamp
);

console.log(scenario.status); // → 'valid' (all gates true)
```

### Example 2: Scenario Lifecycle Tracking
```typescript
// Time T0: Scenario starts forming
const scenario1 = buildEntryScenario(
  type,
  context,
  { htfBiasAligned: true, liquidityEvent: false, structuralConfirmation: true },
  {},
  T0
);
console.log(scenario1.status); // → 'forming'

// Time T1: Liquidity event occurs
const scenario2 = buildEntryScenario(
  type,
  context,
  { htfBiasAligned: true, liquidityEvent: true, structuralConfirmation: true },
  {},
  T1
);
console.log(scenario2.status); // → 'valid'

// Time T2: Context becomes non-tradable
const newContext = buildLiquidityContext(mitigatedPOI, T2);
const result = invalidateOnContextChange(scenario2, newContext);
console.log(result.invalidated); // → true
console.log(result.reason); // → 'context_not_tradable'
```

### Example 3: Confluence Independence
```typescript
// Scenario valid with NO confluences
const scenario1 = buildEntryScenario(
  type,
  context,
  { htfBiasAligned: true, liquidityEvent: true, structuralConfirmation: true },
  {}, // No confluences
  timestamp
);
console.log(scenario1.status); // → 'valid' ✅

// Scenario forming with ALL confluences
const scenario2 = buildEntryScenario(
  type,
  context,
  { htfBiasAligned: true, liquidityEvent: false, structuralConfirmation: true },
  { orderBlock: true, fairValueGap: true, breakerBlock: true }, // All confluences
  timestamp
);
console.log(scenario2.status); // → 'forming' (gates incomplete)
```

## API Reference

### Types

#### `EntryScenarioType` (enum)
ICT entry scenario templates:
- `LiquiditySweepDisplacement`
- `BreakerBlockMSS`
- `OB_FVG_Discount`
- `BuySideTakenRejection`
- `SellSideSweepOBReaction`

#### `EntryScenarioStatus` (type)
Lifecycle states:
- `'forming'` - Gates incomplete
- `'valid'` - All gates complete
- `'invalidated'` - Scenario invalidated

#### `RequiredGates` (interface)
Minimum structural conditions:
- `htfBiasAligned: boolean`
- `liquidityEvent: boolean`
- `structuralConfirmation: boolean`

#### `OptionalConfluences` (interface)
Additional supporting factors (all optional):
- `orderBlock?: boolean`
- `fairValueGap?: boolean`
- `breakerBlock?: boolean`
- `discountPremium?: boolean`
- `buySellLiquidity?: boolean`
- `newsRisk?: boolean`

### Functions

#### `buildEntryScenario()`
Construct an Entry Scenario from explicit inputs.

**Signature:**
```typescript
function buildEntryScenario(
  type: EntryScenarioType,
  liquidityContext: LiquidityContext,
  requiredGates: RequiredGates,
  optionalConfluences: OptionalConfluences,
  evaluatedAt: number
): EntryScenario
```

**Returns:** Deterministic EntryScenario object  
**Side Effects:** None (pure function)

#### `invalidateOnContextChange()`
Check if scenario should be invalidated by context changes.

**Signature:**
```typescript
function invalidateOnContextChange(
  scenario: EntryScenario,
  nextContext: LiquidityContext
): InvalidationResult
```

**Returns:** `{ invalidated: boolean, reason?: string }`  
**Side Effects:** None (pure function)

#### Guard Functions

```typescript
function isScenarioForming(scenario: EntryScenario): boolean
function isScenarioValid(scenario: EntryScenario): boolean
function isScenarioInvalidated(scenario: EntryScenario): boolean
```

## Testing

Comprehensive invariant tests are provided in `entryScenario.invariants.spec.ts`:

### Test Coverage:
1. ✅ Lifecycle transitions (forming → valid, forming → invalidated, valid → invalidated)
2. ✅ Gate logic (all gates true → valid, some gates false → forming)
3. ✅ Confluence independence (confluences don't gate validity)
4. ✅ Determinism & immutability (same inputs → same output, no mutation)
5. ✅ Invalidation logic (context changes → invalidation)
6. ✅ All scenario types supported
7. ✅ Guard functions

### Running Tests:
```bash
npm test -- entryScenario.invariants.spec.ts
```

## Design Principles

### 1. Design-First
**Principle:** Model the domain BEFORE implementing detection/execution.

**Benefit:** Clean separation between "what patterns exist" and "how to detect/trade them".

### 2. Deterministic
**Principle:** Same inputs → same output (always).

**Benefit:** Testable, replay-safe, predictable.

### 3. Replay-Safe
**Principle:** No `Date.now()`, no randomness, no side effects.

**Benefit:** Can replay historical scenarios identically.

### 4. Semantic Clarity > Cleverness
**Principle:** Code should express intent clearly, not be clever.

**Benefit:** Maintainable, understandable, reduces bugs.

## Future Phases

### Phase 4.4: Confluence Scoring (Next)
- Evaluate confluence quality
- Assign scores/weights
- Calculate confidence levels
- **Input:** Entry Scenarios (from this phase)

### Phase 4.5: Stop Loss / Take Profit Contracts (Later)
- Define SL/TP calculation rules
- Model risk/reward contracts
- **Input:** Entry Scenarios + Scores

### Phase 5: Execution & Signals (Later)
- Generate trade signals
- Execute orders
- Manage positions
- **Input:** Entry Scenarios + SL/TP + Risk rules

## Frozen for ESB v1.0

Once merged, **Entry Scenario semantics are FROZEN for ESB v1.0**.

No changes allowed to:
- Core types (EntryScenario, RequiredGates, OptionalConfluences)
- Lifecycle states and transitions
- Gate validation logic
- Public API contracts

This ensures stability for downstream phases (4.4, 4.5, 5).

---

**Version:** Phase 4.3  
**Status:** Implementation Complete  
**Dependencies:** Phase 4.1 (POI), Phase 4.2 (Liquidity Context)  
**Next Phase:** 4.4 (Confluence Scoring)
