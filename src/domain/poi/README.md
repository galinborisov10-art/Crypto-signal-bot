# Points of Interest (POI) Domain Layer

**Phase 4: Strategy Core (Design-First) - ESB v1.0**

## 📌 Overview

This directory contains the **pure data + contract layer** for Points of Interest (POI).

POI represent **liquidity-based contexts**, NOT support/resistance lines.

## 🚫 Hard Constraints

**This implementation strictly forbids:**

- ❌ NO execution logic
- ❌ NO detection algorithms
- ❌ NO strategy scoring
- ❌ NO runtime dependencies (beyond TypeScript/testing libraries)
- ❌ NO support/resistance concepts

## 📁 Files

### Core Files

- **`poi.types.ts`** - Type definitions for POI domain objects
- **`poi.contracts.ts`** - Validation logic and factory functions
- **`poi.fixtures.ts`** - Test fixtures for testing
- **`poi.invariants.spec.ts`** - Comprehensive invariant tests
- **`index.ts`** - Public API entry point

## 🎯 POI Type System

### POI Types (Enum)

```typescript
enum POIType {
  SellSideLiquidity
  BuySideLiquidity
  PreviousHigh
  PreviousLow
  OrderBlock
  FairValueGap
  BreakerBlock
  Accumulation
  Distribution
}
```

### POI Data Model

```typescript
interface POI {
  id: string
  type: POIType
  timeframe: Timeframe  // '1m' | '5m' | '15m' | '1h' | '4h' | '1d'
  priceRange: {
    low: number
    high: number
  }
  directionBias: 'bullish' | 'bearish' | 'neutral'
  validFrom: number  // Unix timestamp (ms)
  validUntil: number  // Unix timestamp (ms)
  mitigated: boolean
  mitigationTimestamp?: number  // Unix timestamp (ms), optional
}
```

## 📜 Contract Rules

The implementation enforces the following invariants:

1. **POI cannot exist without timeframe** - `timeframe` must be defined and valid
2. **POI must declare direction bias** - `directionBias` must be one of `'bullish' | 'bearish' | 'neutral'`
3. **`validUntil` must be > `validFrom`** - Enforces temporal validity
4. **Mitigated POI must not be eligible for entry** - If `mitigated === true`, the POI is invalid for new entries
5. **Support/Resistance must NOT exist** - No references to "support" or "resistance" in types or contracts

## 🧪 Testing

### Run Tests

```bash
npm test
```

### Test Coverage

The test suite (`poi.invariants.spec.ts`) includes:

- **37 passing tests** covering:
  - Invalid POI construction
  - Validity window semantics
  - Mitigation rules
  - Semantic correctness
  - Contract rule enforcement
  - Valid POI creation
  - POI type coverage

All tests are **semantic, not performance-based**.

## 🛠️ Usage

### Import POI Types and Contracts

```typescript
import {
  POI,
  POIType,
  createPOI,
  isPOIValid,
  isPOIEligibleForEntry
} from './domain/poi';
```

### Create a Valid POI

```typescript
const poi = createPOI({
  id: 'poi-ob-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 42000, high: 42500 },
  directionBias: 'bullish',
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000, // +24 hours
  mitigated: false
});

console.log(isPOIValid(poi)); // true
console.log(isPOIEligibleForEntry(poi)); // true
```

### Validation

```typescript
// Will throw POIValidationError if invalid
const poi = createPOI({
  id: 'poi-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 42500, high: 42000 }, // Invalid: low > high
  directionBias: 'bullish',
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000,
  mitigated: false
});
// Throws: POIValidationError: Invalid price range: low (42500) must be <= high (42000)
```

### Check Eligibility

```typescript
// Mitigated POI is not eligible for entry
const mitigatedPOI = createPOI({
  id: 'poi-002',
  type: POIType.BreakerBlock,
  timeframe: '1h',
  priceRange: { low: 42000, high: 42500 },
  directionBias: 'bullish',
  validFrom: Date.now() - 7200000,
  validUntil: Date.now() + 3600000,
  mitigated: true,
  mitigationTimestamp: Date.now()
});

console.log(isPOIEligibleForEntry(mitigatedPOI)); // false
```

## 📊 Build

```bash
npm run build
```

TypeScript compilation outputs to `dist/` directory with:
- Compiled JavaScript (`.js`)
- Type declarations (`.d.ts`)
- Source maps (`.js.map`, `.d.ts.map`)

## ✅ Acceptance Criteria

- [x] `poi.types.ts` defines POIType enum and POI interface
- [x] `poi.contracts.ts` implements validation and factory functions
- [x] `poi.invariants.spec.ts` has comprehensive invariant tests (37 passing)
- [x] `poi.fixtures.ts` provides reusable test data
- [x] All contract rules are enforced via types + tests
- [x] No forbidden logic (execution, detection, scoring, runtime deps)
- [x] No "support" or "resistance" terminology in code
- [x] Code is type-safe and fully tested (TypeScript strict mode)

## 🔒 TypeScript Strict Mode

This project uses **TypeScript strict mode** with all strictness flags enabled:

```json
{
  "strict": true,
  "noImplicitAny": true,
  "strictNullChecks": true,
  "strictFunctionTypes": true,
  "strictBindCallApply": true,
  "strictPropertyInitialization": true,
  "noImplicitThis": true,
  "alwaysStrict": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "noImplicitReturns": true,
  "noFallthroughCasesInSwitch": true
}
```

## 📝 Design Philosophy

This is a **design-first** implementation focused on:

- **Pure data modeling** - POI as first-class domain objects
- **Contract enforcement** - Invariants enforced through types and validation
- **No business logic** - Separation of data layer from execution/detection/strategy
- **Type safety** - Leveraging TypeScript's strict type system
- **Testability** - Comprehensive semantic tests without runtime dependencies

---

**Made with precision for ESB v1.0 - Phase 4**
