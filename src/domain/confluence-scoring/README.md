# Confluence Scoring Engine — Phase 4.4

**Pure, deterministic evaluation of Entry Scenario quality**

---

## Overview

The **Confluence Scoring Engine** evaluates the quality of ICT Entry Scenarios by analyzing their optional confluence factors. It produces a **confidence score (0–100)** with full breakdown for auditability.

**This layer answers ONLY:**

> **"How good is this structural idea?"**

It does **NOT** answer:
- "Should we trade this?"
- "What's the position size?"
- "Where's the stop loss?"

---

## Philosophy: Scenario ≠ Score ≠ Signal

Understanding the boundaries between layers is critical:

### 1. Entry Scenario (Phase 4.3)
- **What it is:** A structural market idea
- **What it represents:** "Here's a complete ICT pattern"
- **Status:** `forming` → `valid` → `invalidated`
- **Decision:** None (it's just a structural observation)

### 2. Confluence Score (Phase 4.4) ← **YOU ARE HERE**
- **What it is:** A quality evaluation
- **What it represents:** "This idea has X% confluence quality"
- **Range:** 0–100 confidence
- **Decision:** None (it's just an assessment)

### 3. Trade Signal (Phase 5)
- **What it is:** A trading decision
- **What it represents:** "We should take this trade"
- **Inputs:** Scenario + Score + Risk + Context + ...
- **Decision:** YES — this is where execution happens

**Key principle:**

> **70% confidence ≠ signal**
> 
> Confidence = quality, NOT permission

A scenario can have 95% confluence quality and still not be tradable (e.g., wrong market conditions, conflicting signals, risk limits).

---

## Why Scoring is Isolated from Execution

The scoring engine is **pure evaluation logic** with zero side effects:

### Determinism
- Same inputs → same output (always)
- No `Date.now()`, no randomness, no external state
- Replay-safe for backtesting and audits

### Separation of Concerns
- Scoring evaluates structure quality
- Execution (Phase 5) makes trading decisions
- Clean boundaries = easier testing, debugging, evolution

### Auditability
- Full breakdown of every score
- Every confluence factor shown (even if 0)
- Dampeners explicitly tracked
- Complete transparency

---

## How Confidence is Derived

### Inputs

1. **Entry Scenario** (from Phase 4.3)
   - Must be `status === 'valid'`
   - Contains `optionalConfluences` (boolean flags)

2. **Weight Configuration**
   - Explicit weights for each confluence factor
   - **NO defaults** — caller must provide weights
   - Positive weights add to score
   - Negative weights (dampeners) subtract

3. **Evaluated At**
   - Fixed timestamp (Unix milliseconds)
   - Replay-safe, deterministic

### Calculation

```typescript
// Step 1: Calculate max possible score (positive weights only)
maxPossibleScore = 
  weights.orderBlock +
  weights.fairValueGap +
  weights.breakerBlock +
  weights.discountPremium +
  weights.buySellLiquidity;
// newsRisk NOT included (it's a dampener)

// Step 2: Calculate raw score from present confluences
rawScore = 0;

if (scenario.optionalConfluences.orderBlock) rawScore += weights.orderBlock;
if (scenario.optionalConfluences.fairValueGap) rawScore += weights.fairValueGap;
if (scenario.optionalConfluences.breakerBlock) rawScore += weights.breakerBlock;
if (scenario.optionalConfluences.discountPremium) rawScore += weights.discountPremium;
if (scenario.optionalConfluences.buySellLiquidity) rawScore += weights.buySellLiquidity;

// Step 3: Apply dampeners
if (scenario.optionalConfluences.newsRisk) rawScore += weights.newsRisk; // negative

// Step 4: Normalize to 0-100
normalizedScore = clamp((rawScore / maxPossibleScore) * 100, 0, 100);
confidence = normalizedScore; // semantic alias
```

### Output

```typescript
{
  scenarioId: string;
  rawScore: number;           // e.g., 60
  normalizedScore: number;    // e.g., 60 (0-100)
  confidence: number;         // e.g., 60 (same as normalizedScore)
  breakdown: {
    present: ['orderBlock', 'breakerBlock', ...],
    missing: ['fairValueGap', ...],
    contributions: {
      orderBlock: 20,
      fairValueGap: 0,
      breakerBlock: 25,
      // ... all 6 factors shown
    },
    dampenersApplied: [
      { factor: 'newsRisk', impact: -20 }
    ]
  },
  evaluatedAt: number;
}
```

---

## Why Dampeners Exist

### newsRisk Dampener

- **Purpose:** Reduce confidence when high-impact news is scheduled
- **Mechanism:** Negative weight subtracts from raw score
- **Key insight:** Dampeners are NOT gates

A scenario with `newsRisk === true` is still **valid** (gates passed), but has **lower confidence** (quality reduced).

### Design Extensibility

Dampeners use structured objects:

```typescript
interface DampenerImpact {
  factor: ConfluenceFactor;
  impact: number;
}
```

This allows future dampeners (e.g., volatility risk, correlation risk) to be added without breaking the scoring contract.

### Dampeners vs. Gates

| **Gates (Phase 4.3)** | **Dampeners (Phase 4.4)** |
|-----------------------|---------------------------|
| Binary (pass/fail)    | Continuous (reduce score) |
| Block validity        | Reduce confidence         |
| Required for "valid"  | Optional risk awareness   |

---

## How Phase 4.5 and Phase 5 Will Consume This

### Phase 4.5: SL/TP Contracts (Planned)

- May use confidence thresholds
  - e.g., "Only calculate TP if confidence > 60%"
- Does NOT modify scoring logic
- Reads confidence as input

### Phase 5: Execution Layer (Planned)

- Combines multiple factors:
  ```
  Signal Decision = 
    Scenario (valid?) +
    Score (confidence ≥ threshold?) +
    Risk Management (position size OK?) +
    Market Conditions (volatility, spread, liquidity) +
    Portfolio State (open positions, correlation)
  ```

- Scoring layer remains pure and isolated
- Execution layer makes final "go/no-go" decision

---

## Architecture Decisions

### 1. No Default Weights

**Decision:** Weights MUST be explicitly provided by caller

**Rationale:**
- Weights are **policy**, not semantics
- Different strategies need different weights
- Defaults hide assumptions and create hidden coupling
- Explicit configuration = clear intent

**Anti-pattern:**
```typescript
// ❌ BAD: Hidden defaults
const DEFAULT_WEIGHTS = { ... };
function evaluate(scenario, weights = DEFAULT_WEIGHTS) { ... }
```

**Correct pattern:**
```typescript
// ✅ GOOD: Explicit configuration
function evaluate(scenario, weights: ConfluenceWeights, evaluatedAt) { ... }
// Caller MUST provide weights
```

### 2. Explicit Result Type (No Exceptions)

**Decision:** Return `ScoringResult` discriminated union

**Rationale:**
- Explicit error handling
- Type-safe error checking
- No try/catch overhead
- Easier to reason about

**Pattern:**
```typescript
type ScoringResult =
  | { success: true; score: ConfluenceScore }
  | { success: false; error: 'SCENARIO_NOT_VALID' };

const result = evaluateConfluenceScore(scenario, weights, timestamp);

if (result.success) {
  console.log(result.score.confidence);
} else {
  console.log(result.error); // 'SCENARIO_NOT_VALID'
}
```

### 3. All Factors in Contributions (Full Transparency)

**Decision:** `contributions` shows ALL 6 factors (0 for missing)

**Rationale:**
- Complete auditability
- Consistent structure (no guessing what's missing)
- Easier debugging and analysis
- Clear signal-to-noise ratio

**Example:**
```typescript
contributions: {
  orderBlock: 20,       // present
  fairValueGap: 0,      // missing
  breakerBlock: 25,     // present
  discountPremium: 0,   // missing
  buySellLiquidity: 0,  // missing
  newsRisk: 0           // missing (no dampener)
}
```

### 4. Structured Dampeners (Extensible)

**Decision:** Dampeners are objects with `{ factor, impact }`

**Rationale:**
- Extensible for future dampeners
- Clear audit trail
- Type-safe
- Self-documenting

**Example:**
```typescript
dampenersApplied: [
  { factor: 'newsRisk', impact: -20 }
]
```

### 5. `confidence === normalizedScore` (Semantic Clarity)

**Decision:** Both fields exist with same value

**Rationale:**
- `normalizedScore` = technical term (0-100 normalization)
- `confidence` = semantic term (quality assessment)
- Different consumers prefer different terminology
- No performance cost (same value)

---

## Usage Examples

### Example 1: Basic Scoring

```typescript
import { evaluateConfluenceScore } from './confluenceScore.contracts';
import { buildEntryScenario } from '../entry-scenarios';

// Build a valid scenario (Phase 4.3)
const scenario = buildEntryScenario(
  EntryScenarioType.OB_FVG_Discount,
  liquidityContext,
  allGatesTrue,
  { orderBlock: true, fairValueGap: true, newsRisk: false },
  timestamp
);

// Define weights (explicit configuration)
const weights = {
  orderBlock: 20,
  fairValueGap: 15,
  breakerBlock: 25,
  discountPremium: 15,
  buySellLiquidity: 25,
  newsRisk: -20
};

// Evaluate score
const result = evaluateConfluenceScore(scenario, weights, timestamp);

if (result.success) {
  console.log(`Confidence: ${result.score.confidence}%`);
  console.log(`Raw score: ${result.score.rawScore}`);
  console.log(`Present: ${result.score.breakdown.present.join(', ')}`);
}
```

### Example 2: Handling Non-Valid Scenarios

```typescript
const formingScenario = buildEntryScenario(
  EntryScenarioType.LiquiditySweepDisplacement,
  context,
  someGatesFalse, // Not all gates true
  confluences,
  timestamp
);

const result = evaluateConfluenceScore(formingScenario, weights, timestamp);

if (!result.success) {
  console.log(result.error); // 'SCENARIO_NOT_VALID'
  // Scenario is still forming, can't score yet
}
```

### Example 3: Analyzing Dampener Impact

```typescript
const scenarioWithRisk = buildEntryScenario(
  type,
  context,
  allGatesTrue,
  { orderBlock: true, fairValueGap: true, newsRisk: true }, // Risk present
  timestamp
);

const result = evaluateConfluenceScore(scenarioWithRisk, weights, timestamp);

if (result.success) {
  const dampeners = result.score.breakdown.dampenersApplied;
  
  dampeners.forEach(d => {
    console.log(`${d.factor}: ${d.impact}`); // newsRisk: -20
  });
  
  console.log(`Final confidence: ${result.score.confidence}%`); // Reduced by dampener
}
```

---

## Testing

All scoring behavior is verified through invariant tests in `confluenceScore.invariants.spec.ts`.

### Test Categories

1. **Determinism & Replay Safety**
   - Same inputs → same outputs
   - Fixed timestamps produce consistent results

2. **Scoring Correctness**
   - All confluences = 100%
   - No confluences = 0%
   - Partial confluences = correct weighted score
   - `confidence === normalizedScore`

3. **Dampener Behavior**
   - `newsRisk === true` reduces score
   - Dampener impact correctly recorded
   - `newsRisk` NOT in `maxPossibleScore`

4. **Normalization Boundaries**
   - Score never exceeds 100
   - Score never goes below 0
   - Correct clamping with strong dampeners

5. **Validation**
   - Non-valid scenarios return error
   - No exceptions thrown

6. **Immutability**
   - No mutation of scenario
   - No mutation of weights

7. **Breakdown Transparency**
   - All factors in `contributions`
   - Correct `present` and `missing` arrays
   - Full breakdown always present

---

## Public API

The public API is exported from `index.ts`:

```typescript
// Types
export {
  ConfluenceFactor,
  ConfluenceWeights,
  DampenerImpact,
  ConfluenceBreakdown,
  ConfluenceScore,
  ScoringResult
} from './confluenceScore.types';

// Contracts
export {
  evaluateConfluenceScore
} from './confluenceScore.contracts';

// Test fixtures (for testing only)
export {
  testWeights,
  equalWeights,
  allConfluencesPresent,
  withNewsRisk,
  // ... etc
} from './confluenceScore.fixtures';
```

---

## Constraints

This module strictly adheres to the following constraints:

### ❌ FORBIDDEN

- Execution logic
- Trade signals
- Buy/sell semantics
- SL / TP
- RR logic
- Capital or sizing logic
- ML, statistics, optimization
- Randomness
- `Date.now()`

### ✅ REQUIRED

- Deterministic
- Replay-safe
- Pure (no side effects)
- Input-driven only

---

## Integration with ESB v1.0

```
Phase 4.1: POI
    ↓
Phase 4.2: Liquidity Context
    ↓
Phase 4.3: Entry Scenarios
    ↓
Phase 4.4: Confluence Scoring ← YOU ARE HERE
    ↓
Phase 4.5: SL/TP Contracts (planned)
    ↓
Phase 5: Execution Layer (planned)
```

**Post-merge:** Confluence scoring semantics are **FROZEN** for ESB v1.0. Future changes only via ESB v1.1.

---

## Summary

The Confluence Scoring Engine is a **pure quality evaluator** that:

- ✅ Evaluates scenario quality (0-100 confidence)
- ✅ Provides full transparency (breakdown)
- ✅ Handles dampeners (risk awareness)
- ✅ Is deterministic and replay-safe
- ❌ Does NOT make trading decisions
- ❌ Does NOT execute trades
- ❌ Does NOT calculate SL/TP

**Remember:** High confidence ≠ signal. Confidence = quality, NOT permission.

---

## See Also

- **Phase 4.3 README:** Understanding Entry Scenarios
- **Phase 4.2 README:** Liquidity Context
- **Phase 4.1 README:** POI fundamentals

---

**Version:** ESB v1.0 Phase 4.4
**Status:** Design-First Implementation
**License:** MIT
