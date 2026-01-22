/**
 * Entry Scenario Test Fixtures - Phase 4.3: Entry Scenario Core
 * 
 * Reusable test fixtures for Entry Scenarios across all lifecycle states.
 * These fixtures support deterministic, replay-safe testing.
 * 
 * Fixture Categories:
 * 1. Gate Configurations (all true, some false, etc.)
 * 2. Confluence Configurations (all present, none present, mixed)
 * 3. Complete Entry Scenarios (forming, valid, invalidated)
 */

import {
  EntryScenario,
  EntryScenarioType,
  RequiredGates,
  OptionalConfluences
} from './entryScenario.types';

/**
 * Fixed reference timestamp for deterministic testing
 * Value: November 14, 2023 22:13:20 GMT (same as Phase 4.2)
 */
export const T0 = 1700000000000;

// ============================================================
// GATE CONFIGURATIONS
// ============================================================

/**
 * All required gates are true
 * This configuration makes a scenario 'valid'
 */
export const allGatesTrue: RequiredGates = {
  htfBiasAligned: true,
  liquidityEvent: true,
  structuralConfirmation: true
};

/**
 * Some required gates are false
 * This configuration keeps a scenario in 'forming' state
 */
export const someGatesFalse: RequiredGates = {
  htfBiasAligned: true,
  liquidityEvent: false,
  structuralConfirmation: true
};

/**
 * All required gates are false
 * Scenario remains 'forming'
 */
export const allGatesFalse: RequiredGates = {
  htfBiasAligned: false,
  liquidityEvent: false,
  structuralConfirmation: false
};

/**
 * Only HTF bias aligned
 */
export const onlyHTFAligned: RequiredGates = {
  htfBiasAligned: true,
  liquidityEvent: false,
  structuralConfirmation: false
};

/**
 * Only liquidity event occurred
 */
export const onlyLiquidityEvent: RequiredGates = {
  htfBiasAligned: false,
  liquidityEvent: true,
  structuralConfirmation: false
};

/**
 * Only structural confirmation present
 */
export const onlyStructuralConfirmation: RequiredGates = {
  htfBiasAligned: false,
  liquidityEvent: false,
  structuralConfirmation: true
};

// ============================================================
// CONFLUENCE CONFIGURATIONS
// ============================================================

/**
 * All optional confluences are present
 */
export const allConfluencesPresent: OptionalConfluences = {
  orderBlock: true,
  fairValueGap: true,
  breakerBlock: true,
  discountPremium: true,
  buySellLiquidity: true,
  newsRisk: false // Inverted: false = no news risk
};

/**
 * No optional confluences present
 */
export const noConfluences: OptionalConfluences = {};

/**
 * Some confluences present (mixed)
 */
export const mixedConfluences: OptionalConfluences = {
  orderBlock: true,
  fairValueGap: false,
  breakerBlock: true,
  discountPremium: true,
  buySellLiquidity: false,
  newsRisk: true // News risk present
};

/**
 * Only order block present
 */
export const onlyOrderBlock: OptionalConfluences = {
  orderBlock: true
};

/**
 * Only fair value gap present
 */
export const onlyFairValueGap: OptionalConfluences = {
  fairValueGap: true
};

/**
 * High news risk (inverted flag)
 */
export const highNewsRisk: OptionalConfluences = {
  newsRisk: true
};

// ============================================================
// COMPLETE ENTRY SCENARIOS
// ============================================================

/**
 * A scenario in 'forming' state
 * Some required gates are false, so it's not yet valid
 */
export const formingScenario: EntryScenario = {
  id: `${EntryScenarioType.LiquiditySweepDisplacement}_poi-test-001_${T0}`,
  type: EntryScenarioType.LiquiditySweepDisplacement,
  contextId: 'poi-test-001',
  status: 'forming',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: false, // Missing
    structuralConfirmation: true
  },
  optionalConfluences: {
    orderBlock: true,
    fairValueGap: false
  },
  evaluatedAt: T0
};

/**
 * A scenario in 'valid' state
 * All required gates are true
 */
export const validScenario: EntryScenario = {
  id: `${EntryScenarioType.BreakerBlockMSS}_poi-test-002_${T0}`,
  type: EntryScenarioType.BreakerBlockMSS,
  contextId: 'poi-test-002',
  status: 'valid',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: true,
    structuralConfirmation: true
  },
  optionalConfluences: {
    orderBlock: true,
    fairValueGap: true,
    breakerBlock: true
  },
  evaluatedAt: T0
};

/**
 * A scenario in 'invalidated' state
 * Was previously valid but became invalidated
 */
export const invalidatedScenario: EntryScenario = {
  id: `${EntryScenarioType.OB_FVG_Discount}_poi-test-003_${T0}`,
  type: EntryScenarioType.OB_FVG_Discount,
  contextId: 'poi-test-003',
  status: 'invalidated',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: true,
    structuralConfirmation: true
  },
  optionalConfluences: {
    orderBlock: true,
    fairValueGap: true,
    discountPremium: true
  },
  evaluatedAt: T0
};

/**
 * Valid scenario with NO confluences
 * Demonstrates that confluences don't gate validity
 */
export const validScenarioNoConfluences: EntryScenario = {
  id: `${EntryScenarioType.BuySideTakenRejection}_poi-test-004_${T0}`,
  type: EntryScenarioType.BuySideTakenRejection,
  contextId: 'poi-test-004',
  status: 'valid',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: true,
    structuralConfirmation: true
  },
  optionalConfluences: {}, // No confluences
  evaluatedAt: T0
};

/**
 * Forming scenario with ALL confluences
 * Demonstrates that confluences don't make scenario valid
 */
export const formingScenarioAllConfluences: EntryScenario = {
  id: `${EntryScenarioType.SellSideSweepOBReaction}_poi-test-005_${T0}`,
  type: EntryScenarioType.SellSideSweepOBReaction,
  contextId: 'poi-test-005',
  status: 'forming',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: false, // Still missing
    structuralConfirmation: true
  },
  optionalConfluences: {
    orderBlock: true,
    fairValueGap: true,
    breakerBlock: true,
    discountPremium: true,
    buySellLiquidity: true,
    newsRisk: false
  },
  evaluatedAt: T0
};

// ============================================================
// SCENARIO COLLECTIONS
// ============================================================

/**
 * All scenario type examples (all valid)
 */
export const allScenarioTypes: EntryScenario[] = [
  {
    id: `${EntryScenarioType.LiquiditySweepDisplacement}_poi-types-001_${T0}`,
    type: EntryScenarioType.LiquiditySweepDisplacement,
    contextId: 'poi-types-001',
    status: 'valid',
    requiredGates: allGatesTrue,
    optionalConfluences: {},
    evaluatedAt: T0
  },
  {
    id: `${EntryScenarioType.BreakerBlockMSS}_poi-types-002_${T0}`,
    type: EntryScenarioType.BreakerBlockMSS,
    contextId: 'poi-types-002',
    status: 'valid',
    requiredGates: allGatesTrue,
    optionalConfluences: {},
    evaluatedAt: T0
  },
  {
    id: `${EntryScenarioType.OB_FVG_Discount}_poi-types-003_${T0}`,
    type: EntryScenarioType.OB_FVG_Discount,
    contextId: 'poi-types-003',
    status: 'valid',
    requiredGates: allGatesTrue,
    optionalConfluences: {},
    evaluatedAt: T0
  },
  {
    id: `${EntryScenarioType.BuySideTakenRejection}_poi-types-004_${T0}`,
    type: EntryScenarioType.BuySideTakenRejection,
    contextId: 'poi-types-004',
    status: 'valid',
    requiredGates: allGatesTrue,
    optionalConfluences: {},
    evaluatedAt: T0
  },
  {
    id: `${EntryScenarioType.SellSideSweepOBReaction}_poi-types-005_${T0}`,
    type: EntryScenarioType.SellSideSweepOBReaction,
    contextId: 'poi-types-005',
    status: 'valid',
    requiredGates: allGatesTrue,
    optionalConfluences: {},
    evaluatedAt: T0
  }
];

/**
 * All scenarios in different states
 */
export const allScenarioStates: EntryScenario[] = [
  formingScenario,
  validScenario,
  invalidatedScenario
];
