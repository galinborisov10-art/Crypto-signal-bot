# Liquidity Context Layer

**Phase 4.2: ESB v1.0 — Strategy Core (Design-First)**

This module provides a **time-based interpretation layer** for Points of Interest (POI) without adding detection, scoring, or execution logic.

---

## 📌 Core Concept

### What is a Liquidity Context?

A **Liquidity Context** is a derived, read-only interpretation of a POI at a specific moment in time.

It answers three key questions:

1. ✅ **Is a POI still valid now?**
2. ✅ **Has it been mitigated?**
3. ✅ **How do HTF POIs constrain LTF interpretation?**

### Key Distinction: POI vs Liquidity Context

| Aspect | POI (Phase 4.1) | Liquidity Context (Phase 4.2) |
|--------|----------------|-------------------------------|
| **Nature** | Static liquidity object | Time-based interpretation |
| **Created when** | When detected in market | When evaluating a POI at a specific time |
| **Mutability** | Frozen (immutable) | Derived (read-only) |
| **Timeframe awareness** | Has a timeframe | Evaluates validity at a timestamp |
| **HTF/LTF** | No relationship | Models HTF/LTF constraints |
| **Validity** | Has validFrom/validUntil | Evaluates if currently valid |
| **Purpose** | "What exists" | "What's relevant now" |

**Example:**

```typescript
// POI (static object created in Phase 4.1)
const poi: POI = {
  id: 'poi-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 42000, high: 42500 },
  directionBias: 'bullish',
  validFrom: 1700000000000,
  validUntil: 1700086400000,
  mitigated: false
};

// Liquidity Context (interpretation of POI at T0)
const context = buildLiquidityContext(poi, 1700000000000);
// context.status = 'active' (because T0 is within validity window)

// Same POI, different time
const laterContext = buildLiquidityContext(poi, 1700100000000);
// laterContext.status = 'expired' (because evaluated after validUntil)
```

---

## 🎯 Why This Layer Exists

### Separation of Concerns

**Liquidity Context** separates two distinct responsibilities:

1. **POI Layer (Phase 4.1)**: Models "what liquidity zones exist"
2. **Context Layer (Phase 4.2)**: Models "what's relevant at this moment"

This enables:

- ✅ **Deterministic evaluation**: Same inputs → same output
- ✅ **Time-based filtering**: Distinguish active, expired, and mitigated POIs
- ✅ **HTF/LTF modeling**: Understand alignment/conflict without strategy logic
- ✅ **Replay safety**: Fixed timestamps for audit and testing

### Foundation for Phase 4.3 (Entry Scenarios)

Liquidity Context provides the **foundation** for entry scenario evaluation:

- Filters out expired and mitigated POIs
- Establishes HTF/LTF constraints
- Identifies tradable contexts
- Does NOT generate signals or make trading decisions

---

## 🧱 Type System

### LiquidityContextStatus

```typescript
type LiquidityContextStatus =
  | 'active'      // POI is valid, within time window, and unmitigated
  | 'expired'     // POI validity window has ended
  | 'mitigated'   // POI has been mitigated
  | 'invalid';    // POI evaluated before validity window
```

### HTFRelation

```typescript
type HTFRelation =
  | 'aligned'     // LTF and HTF direction bias match
  | 'counter'     // LTF and HTF direction bias conflict
  | 'neutral'     // Either LTF or HTF has neutral bias
  | 'undefined';  // No HTF POI provided
```

### LiquidityContext

```typescript
interface LiquidityContext {
  poiId: string;                          // Reference to POI
  timeframe: Timeframe;                   // Timeframe of POI
  status: LiquidityContextStatus;         // Current status
  isWithinValidityWindow: boolean;        // Time window check
  mitigationState: 'unmitigated' | 'mitigated';
  htfRelation: HTFRelation;               // HTF/LTF relationship
  evaluatedAt: number;                    // Fixed timestamp (Unix ms)
}
```

---

## 📜 Contract Rules

### Validity Rules

1. If `evaluatedAt < validFrom` → `status = 'invalid'`
2. If `evaluatedAt > validUntil` → `status = 'expired'`
3. If `poi.mitigated === true` → `status = 'mitigated'`
4. Only unmitigated + valid POIs can be `'active'`

### HTF/LTF Rules

1. HTF bias does not override, only constrains
2. LTF context cannot be `'aligned'` if `directionBias` conflicts with HTF POI
3. If no HTF POI exists → `htfRelation = 'undefined'`

### Absolute Rules

1. `LiquidityContext` MUST be derivable deterministically
2. No randomness
3. Same inputs → same output
4. Input POI objects are NEVER mutated

---

## 🧠 Core Functions

### buildLiquidityContext

```typescript
function buildLiquidityContext(
  poi: POI,
  evaluatedAt: number,
  htfPOI?: POI
): LiquidityContext
```

**Purpose**: Derive a time-based interpretation of a POI.

**Parameters**:
- `poi`: The Point of Interest to interpret
- `evaluatedAt`: Unix timestamp (milliseconds) for evaluation
- `htfPOI`: Optional higher timeframe POI for HTF/LTF relationship

**Returns**: A deterministic `LiquidityContext` object

**Guarantees**:
- ✅ Pure function (no side effects)
- ✅ Deterministic (same inputs → same output)
- ✅ Does NOT mutate input POIs
- ✅ Uses fixed timestamp (not dynamic)

**Example**:

```typescript
import { buildLiquidityContext } from '@/domain/liquidity-context';
import { createPOI, POIType } from '@/domain/poi';

const poi = createPOI({
  id: 'poi-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 42000, high: 42500 },
  directionBias: 'bullish',
  validFrom: 1700000000000,
  validUntil: 1700086400000,
  mitigated: false
});

const context = buildLiquidityContext(poi, 1700043200000);
// context.status = 'active'
// context.isWithinValidityWindow = true
// context.htfRelation = 'undefined'
```

---

### Guard Functions

#### isLiquidityContextActive

```typescript
function isLiquidityContextActive(ctx: LiquidityContext): boolean
```

Returns `true` if and only if `ctx.status === 'active'`.

**Example**:

```typescript
if (isLiquidityContextActive(context)) {
  // Context is active (unmitigated + within validity window)
}
```

---

#### isLiquidityContextTradable

```typescript
function isLiquidityContextTradable(ctx: LiquidityContext): boolean
```

Returns `true` if context is **active** AND (`htfRelation === 'aligned'` OR `htfRelation === 'neutral'`).

⚠️ **Important**: Tradable ≠ signal

This guard only filters contexts that are "allowed to be considered" by Phase 4.3 (Entry Scenarios).
It does NOT generate signals or make trading decisions.

**Example**:

```typescript
if (isLiquidityContextTradable(context)) {
  // Context is tradable (active + aligned/neutral HTF)
  // Can be passed to Entry Scenarios layer (Phase 4.3)
}
```

---

## 🚫 What This Layer Does NOT Do

This is a **pure context + contracts layer**. It deliberately does NOT:

- ❌ Generate signals
- ❌ Score or rank contexts
- ❌ Detect new POIs
- ❌ Make trading decisions
- ❌ Calculate entry/exit prices
- ❌ Manage risk or capital
- ❌ Execute trades
- ❌ Use machine learning
- ❌ Modify POI types or contracts from Phase 4.1

**This layer is environmental awareness, NOT intelligence.**

Intelligence starts in **Phase 4.3 (Entry Scenarios)**.

---

## 🧪 Testing

All behavior is covered by comprehensive invariant tests:

```bash
npm test
```

Test coverage includes:

- ✅ Validity scenarios (active, invalid, expired, mitigated)
- ✅ HTF/LTF scenarios (aligned, counter, neutral, undefined)
- ✅ Determinism & immutability
- ✅ Guard function behavior
- ✅ Boundary conditions

---

## 📦 Exports

Public API exported from `index.ts`:

```typescript
// Types
export {
  LiquidityContext,
  LiquidityContextStatus,
  HTFRelation
} from './liquidityContext.types';

// Contracts
export {
  buildLiquidityContext,
  isLiquidityContextActive,
  isLiquidityContextTradable
} from './liquidityContext.contracts';

// Fixtures (for testing)
export * from './liquidityContext.fixtures';
```

---

## 🔒 Post-Merge Freeze

Once merged:  
👉 **Liquidity Context semantics are FROZEN for ESB v1.0**

---

## 📚 Related Documentation

- **Phase 4.1**: Points of Interest (POI) — `/src/domain/poi/README.md`
- **Phase 4.3**: Entry Scenarios — (To be implemented)

---

## 🏗️ Architecture Note

**Liquidity Context Layer** sits between:

1. **POI Layer (Phase 4.1)** ← Upstream (provides static POI objects)
2. **Entry Scenarios Layer (Phase 4.3)** ← Downstream (consumes tradable contexts)

```
┌─────────────────┐
│   POI Layer     │  ← What exists
│   (Phase 4.1)   │
└────────┬────────┘
         │
         │ POI objects
         ▼
┌─────────────────┐
│ Context Layer   │  ← What's relevant now
│  (Phase 4.2)    │
└────────┬────────┘
         │
         │ Tradable contexts
         ▼
┌─────────────────┐
│ Entry Scenarios │  ← What to do about it
│  (Phase 4.3)    │
└─────────────────┘
```

---

## 💡 Usage Examples

### Basic Context Evaluation

```typescript
import { buildLiquidityContext } from '@/domain/liquidity-context';
import { createPOI, POIType } from '@/domain/poi';

const poi = createPOI({
  id: 'ob-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 42000, high: 42500 },
  directionBias: 'bullish',
  validFrom: 1700000000000,
  validUntil: 1700086400000,
  mitigated: false
});

const now = Date.now();
const context = buildLiquidityContext(poi, now);

console.log(context.status); // 'active', 'expired', 'mitigated', or 'invalid'
```

### HTF/LTF Evaluation

```typescript
import { buildLiquidityContext, isLiquidityContextTradable } from '@/domain/liquidity-context';

// LTF POI (15m timeframe)
const ltfPOI = createPOI({
  id: 'ltf-001',
  type: POIType.OrderBlock,
  timeframe: '15m',
  priceRange: { low: 42000, high: 42500 },
  directionBias: 'bullish',
  validFrom: 1700000000000,
  validUntil: 1700086400000,
  mitigated: false
});

// HTF POI (4h timeframe)
const htfPOI = createPOI({
  id: 'htf-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 41500, high: 42000 },
  directionBias: 'bullish',
  validFrom: 1700000000000,
  validUntil: 1700172800000,
  mitigated: false
});

const now = Date.now();
const context = buildLiquidityContext(ltfPOI, now, htfPOI);

console.log(context.htfRelation); // 'aligned'

if (isLiquidityContextTradable(context)) {
  // Pass to Entry Scenarios layer
  console.log('Context is tradable');
}
```

### Filtering Active Contexts

```typescript
import { buildLiquidityContext, isLiquidityContextActive } from '@/domain/liquidity-context';

const pois: POI[] = [...]; // Array of POIs
const now = Date.now();

const activeContexts = pois
  .map(poi => buildLiquidityContext(poi, now))
  .filter(isLiquidityContextActive);

console.log(`Found ${activeContexts.length} active contexts`);
```

---

## 🔍 Design Rationale

### Why Not Add This to POI?

POI represents a **static liquidity object** — it's what exists in the market.

Liquidity Context represents a **time-based interpretation** — it's what's relevant now.

Mixing these concerns would:
- ❌ Violate single responsibility principle
- ❌ Make POI objects mutable (breaking Phase 4.1 freeze)
- ❌ Couple detection logic with interpretation logic
- ❌ Prevent deterministic replay (POI would need current time)

### Why Fixed Timestamps?

Using `Date.now()` internally would:
- ❌ Break determinism (same POI → different contexts over time)
- ❌ Make testing unreliable
- ❌ Prevent replay/audit
- ❌ Introduce non-deterministic behavior

Fixed timestamps ensure:
- ✅ Deterministic evaluation
- ✅ Replay safety
- ✅ Audit trails
- ✅ Consistent testing

---

**ESB v1.0 — Phase 4.2: Liquidity Context Layer**  
*Environmental Awareness for Strategy Execution*
