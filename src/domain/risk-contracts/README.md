# Risk Contracts — Phase 4.5

**Pure, deterministic SL/TP risk structure validation**

---

## Overview

The **Risk Contracts** layer evaluates the structural acceptability of risk for ICT Entry Scenarios. It produces **SL/TP contracts** with risk/reward validation, determining if an idea is structurally tradeable.

**This layer answers ONLY:**

> **"If we were to trade this idea, is the risk structure valid?"**

It does **NOT** answer:
- "Should we execute this trade?"
- "What's the position size?"
- "What's the entry price?"
- "When should we place the order?"

---

## Philosophy: Why SL/TP are Contracts, Not Execution

Understanding the distinction between risk contracts and execution is critical:

### Risk Contracts (Phase 4.5) ← **YOU ARE HERE**

**What they are:**
- Structural specifications
- Validity assessments
- Risk/reward evaluations

**What they represent:**
- "This idea has acceptable risk structure"
- "SL should reference this POI"
- "TP should target these POI zones"

**What they are NOT:**
- Execution prices
- Order parameters
- Trade instructions

### Execution (Phase 5)

**What it does:**
- Translates contracts to execution parameters
- Applies position sizing based on capital management
- Places actual orders with specific prices

**How it uses contracts:**
- Reads SL/TP POI references
- Calculates execution prices from POI price ranges
- Applies capital allocation rules
- Executes orders

**Key principle:**

> **Contracts define WHAT, execution defines WHEN and HOW**
> 
> Separation of concerns = testability + auditability + evolution

---

## Why High Confidence Can Still Fail Risk

The relationship between confluence scoring (Phase 4.4) and risk validation (Phase 4.5) is crucial:

### Confluence Score
- **What it measures:** Quality of structural idea
- **Range:** 0-100 confidence
- **Question:** "How good is this pattern?"

### Risk Contract
- **What it validates:** Structural acceptability of risk
- **Outcome:** valid or invalid
- **Question:** "Is the risk structure acceptable?"

### Quality ≠ Acceptable Risk

A scenario can have excellent confluence quality but fail risk validation:

**Example 1: Perfect Pattern, Bad Risk**
- Confluence Score: 95% (excellent)
- RR: 1.5 (too low)
- **Result:** Idea dies at risk validation ✗

**Example 2: Good Pattern, No Stop**
- Confluence Score: 80% (good)
- Valid SL: None available
- **Result:** Idea dies at risk validation ✗

**Example 3: Decent Pattern, Great Risk**
- Confluence Score: 70% (decent)
- RR: 5.0 (excellent)
- **Result:** Passes risk validation ✓

**The flow:**

```
Entry Scenario (valid)
    ↓
Confluence Score (85%)  ← "Good idea quality"
    ↓
Risk Contract (RR < 3)  ← "Bad risk structure"
    ↓
IDEA DIES  ← Quality doesn't matter if risk is bad
```

**Why this matters:**

> **A great idea with terrible risk MUST die here**
> 
> No amount of confluence quality can compensate for unacceptable risk

---

## Why RR Invalidates Ideas

### The RR >= 3 Rule

The minimum risk/reward ratio of 3:1 is a **structural constraint**, not a preference.

**What it means:**
- For every $1 of risk, we need $3 of potential reward
- This is structural acceptability, not optimization
- RR < 3 means the idea is fundamentally flawed

### Why RR < 3 Kills Ideas

**Scenario:**
- Entry: 120-125
- Stop Loss: 100-105
- Take Profit: 135-140

**Calculation:**
- Risk: 120 - 105 = 15
- Reward: 135 - 125 = 10
- RR: 10 / 15 = 0.67

**Result: Invalid**

Even if confluence score is 90%, this idea dies because:
1. Reward doesn't justify risk
2. Structural constraint violated
3. No amount of confluence can fix it

### Not a Preference, a Constraint

The RR threshold is **architectural**, not discretionary:

❌ "Let's lower the threshold for high-confidence ideas"  
✅ "RR < 3 means the structure is wrong"

❌ "Maybe we can accept RR = 2.5 this time"  
✅ "Fix the structure or abandon the idea"

❌ "But the confluence is so high!"  
✅ "Quality ≠ Acceptable Risk"

---

## How Phase 5 Runtime Will Consume This

Phase 5 (Execution Layer) will receive **valid RiskContract objects** and translate them to execution parameters:

### Input to Phase 5

```typescript
RiskContract {
  scenarioId: "scenario-001",
  stopLoss: {
    type: "orderBlock",
    referencePoiId: "poi-sl-001",
    beyondStructure: true
  },
  takeProfits: [
    { level: "TP1", targetPoiId: "poi-tp-001", probability: "high" },
    { level: "TP2", targetPoiId: "poi-tp-002", probability: "medium" }
  ],
  rr: 4.5,
  status: "valid",
  evaluatedAt: 1704067200000
}
```

### What Phase 5 Does

1. **Lookup POI references:**
   - Retrieve `poi-sl-001` → get price range for SL
   - Retrieve `poi-tp-001` → get price range for TP1
   - Retrieve `poi-tp-002` → get price range for TP2

2. **Calculate execution prices:**
   - SL execution price: based on SL POI price range + buffer
   - TP execution prices: based on TP POI price ranges + targets
   - Entry execution price: based on entry POI price range + strategy

3. **Apply position sizing:**
   - Capital allocation: based on risk management rules
   - Position size: calculated from capital + risk amount
   - Leverage: determined by account settings

4. **Execute orders:**
   - Place entry order with calculated price
   - Place SL order at calculated SL price
   - Place TP orders at calculated TP prices

### Separation of Concerns

**Risk Contracts (Phase 4.5):**
- ✅ Validates risk structure
- ✅ References POIs
- ✅ Calculates structural RR
- ❌ NO execution prices
- ❌ NO position sizing
- ❌ NO order placement

**Execution (Phase 5):**
- ✅ Translates contracts to execution
- ✅ Calculates execution prices
- ✅ Applies position sizing
- ✅ Places orders
- ❌ NO risk validation
- ❌ NO structural assessment

---

## Architecture Decisions

### 1. POI-Based RR Calculation (Not Execution Prices)

**Why:**
- Risk contracts are structural assessments
- Execution prices vary by strategy
- POI price ranges are the structural truth

**How:**
- Use `priceRange.low` and `priceRange.high` from POIs
- Calculate structural risk and reward distances
- RR is a structural metric, not a trade metric

**Example:**
```typescript
// Bullish scenario
risk = entryPOI.priceRange.low - stopLossPOI.priceRange.high
reward = takeProfitPOI.priceRange.low - entryPOI.priceRange.high
rr = reward / risk
```

### 2. Pre-Filtered POI Inputs (No Discovery Here)

**Why:**
- Risk layer should NOT discover POIs
- Risk layer should NOT filter all POIs
- Caller provides semantic sets

**Structure:**
```typescript
RiskPOIs {
  entryPOI: POI;           // The entry context POI
  stopLossCandidates: POI[]; // Pre-filtered SL candidates
  takeProfitCandidates: POI[]; // Pre-filtered TP candidates
}
```

**Responsibility split:**
- Caller: Pre-filter POIs by type, timeframe, direction
- Risk layer: Validate position, select best, calculate RR

### 3. TP1-Only RR (Most Conservative)

**Why:**
- TP1 is highest probability target
- TP2 and TP3 are stretch targets
- Conservative RR protects against over-optimization

**How:**
- RR always uses TP1 for reward calculation
- TP2 and TP3 are documented but not used in RR
- This ensures structural minimum is met

**Example:**
```typescript
// Even if TP2 and TP3 exist, only TP1 is used for RR
rr = rewardToTP1 / risk
```

### 4. Early Invalidation (No Partial Contracts)

**Why:**
- Partial contracts are dangerous
- "Will fix later" is not acceptable
- Fail fast and explicit

**How:**
- No valid SL → STOP immediately
- No valid TP → STOP immediately
- RR < 3 → STOP immediately
- Return invalid contract with reason

**Flow:**
```
Select SL → No valid SL? → STOP (NO_VALID_STOP)
Select TP → No valid TP? → STOP (NO_VALID_TARGETS)
Calculate RR → RR < 3? → STOP (RR_TOO_LOW)
All pass → Return valid contract
```

### 5. Fixed TP Probabilities (No Heuristics)

**Why:**
- Probabilities are policy, not calculation
- No ML, no statistics, no optimization
- Simple, deterministic assignment

**Assignment:**
```typescript
TP1 → 'high'
TP2 → 'medium'
TP3 → 'low'
```

**NOT allowed:**
- Dynamic probability formulas
- Historical hit rates
- ML predictions
- Statistical models

---

## Type System

### StopLossContract

```typescript
interface StopLossContract {
  type: 'structure' | 'orderBlock';
  referencePoiId: string;
  beyondStructure: boolean;
}
```

**Type determination:**
- `'orderBlock'` if POI type is `OrderBlock`
- `'structure'` for all other types (`PreviousHigh`, `PreviousLow`, `BreakerBlock`)

**beyondStructure:**
- Computed: SL POI is beyond last structural boundary
- Currently simplified: `true` for valid SL POIs (ESB v1.0)
- Does NOT participate in RR calculation, gating, or execution
- Serves as a placeholder for future structural boundary analysis (ESB v1.1+)
- Can be refined with more precise structural boundary analysis in future versions

### TakeProfitContract

```typescript
interface TakeProfitContract {
  level: 'TP1' | 'TP2' | 'TP3';
  targetPoiId: string;
  probability: 'high' | 'medium' | 'low';
}
```

**Levels:**
- TP1: Nearest target (highest probability)
- TP2: Mid-range target (medium probability)
- TP3: Stretch target (lowest probability)

**Probabilities:**
- Fixed assignment based on level
- NO dynamic calculation

### RiskContract

```typescript
interface RiskContract {
  scenarioId: string;
  stopLoss: StopLossContract;
  takeProfits: TakeProfitContract[];
  rr: number;
  status: 'valid' | 'invalid';
  invalidationReason?: RiskInvalidationReason;
  evaluatedAt: number;
}
```

**Status:**
- `'valid'`: All validations passed, RR >= 3
- `'invalid'`: At least one validation failed

**Invalidation Reasons:**
- `'RR_TOO_LOW'`: RR < 3
- `'NO_VALID_STOP'`: No valid SL POI found
- `'NO_VALID_TARGETS'`: No valid TP POI found
- `'SCENARIO_NOT_VALID'`: Entry scenario status is not 'valid' (edge case)

### RiskPOIs

```typescript
interface RiskPOIs {
  entryPOI: POI;
  stopLossCandidates: POI[];
  takeProfitCandidates: POI[];
}
```

**Pre-filtering expectations:**
- `entryPOI`: Retrieved via scenario.contextId lookup
- `stopLossCandidates`: OrderBlock, PreviousHigh, PreviousLow, BreakerBlock types
- `takeProfitCandidates`: Structural targets aligned with scenario direction

---

## Core Function

### buildRiskContract

```typescript
function buildRiskContract(
  scenario: EntryScenario,
  score: ConfluenceScore,
  pois: RiskPOIs,
  evaluatedAt: number
): RiskContract
```

**Behavior:**
- Designed to work ONLY for `scenario.status === 'valid'`
- Edge case: If non-valid scenario passed, returns invalid contract with `SCENARIO_NOT_VALID` reason
- Deterministic: same inputs → same output
- Immutable: no mutation of inputs
- No exceptions: returns invalid contract on failure

**Implementation Flow:**
1. Validate scenario status (edge case: non-valid → return invalid with SCENARIO_NOT_VALID)
2. Extract entry POI
3. Select Stop Loss (filter + validate + select best)
4. Select Take Profits (filter + sort + assign)
5. Calculate RR (POI-based, TP1 only)
6. Validate RR >= 3
7. Return valid or invalid contract

---

## Testing

### Invariant Tests

The test suite verifies:

1. **Determinism:**
   - Same inputs → same output
   - Fixed timestamp → consistent results

2. **SL Placement:**
   - Valid types accepted
   - Invalid types rejected
   - Positional validation (below/above entry)
   - `beyondStructure` calculated

3. **TP Selection:**
   - TP1 → TP2 → TP3 ordering
   - Distance-based sorting
   - Fixed probabilities
   - At least TP1 required

4. **RR Enforcement:**
   - Correct POI-based calculation
   - RR >= 3 for valid contracts
   - RR < 3 → invalidation
   - TP1-only calculation

5. **Invalidation:**
   - Correct reasons returned
   - Early invalidation
   - No partial contracts

6. **Immutability:**
   - No input mutation
   - Pure function behavior

7. **No Execution Leakage:**
   - No order placement logic
   - No position sizing
   - No execution prices

---

## Usage Example

```typescript
import { buildRiskContract } from './risk-contracts';

// Given a valid scenario and POIs
const scenario: EntryScenario = { /* valid scenario */ };
const score: ConfluenceScore = { /* confluence score */ };
const pois: RiskPOIs = {
  entryPOI: { /* entry POI */ },
  stopLossCandidates: [/* SL POIs */],
  takeProfitCandidates: [/* TP POIs */]
};

// Build risk contract
const contract = buildRiskContract(scenario, score, pois, Date.now());

if (contract.status === 'valid') {
  console.log('Risk structure is acceptable');
  console.log('RR:', contract.rr);
  console.log('SL POI:', contract.stopLoss.referencePoiId);
  console.log('TP1 POI:', contract.takeProfits[0]?.targetPoiId);
  
  // Pass to Phase 5 for execution
} else {
  console.log('Risk structure is invalid');
  console.log('Reason:', contract.invalidationReason);
  
  // Idea dies here
}
```

---

## Integration with Other Phases

### Inputs (Read-Only)

**Phase 4.1 - POI:**
- POI type definitions
- POI price ranges
- POI references

**Phase 4.2 - Liquidity Context:**
- Entry POI lookup (via scenario.contextId)

**Phase 4.3 - Entry Scenarios:**
- Entry scenario validation
- Scenario status
- Scenario ID

**Phase 4.4 - Confluence Scoring:**
- Confluence score (for context, not used in calculation)

### Outputs

**Phase 5 - Execution:**
- Valid risk contracts
- SL/TP POI references
- RR metrics
- Validity status

### Constraints

**MUST consume read-only:**
- ❌ NO modification of POIs
- ❌ NO modification of scenarios
- ❌ NO modification of scores
- ✅ Pure evaluation only

**MUST NOT include:**
- ❌ Execution logic
- ❌ Order placement
- ❌ Position sizing
- ❌ Capital management
- ❌ ML / optimization

---

## Post-Merge Freeze

Once merged, risk contract semantics are **FROZEN for ESB v1.0**.

No ad-hoc SL/TP tweaks allowed.

---

## Summary

**Risk Contracts define structural risk acceptability, not trade execution.**

**Key Principles:**
1. Contracts, not prices
2. Quality ≠ Acceptable Risk
3. RR >= 3 is a constraint, not a preference
4. Early invalidation, no partial contracts
5. POI-based calculation, not execution-based

**A great idea with bad risk MUST die here.**
