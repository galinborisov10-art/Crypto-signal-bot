/**
 * Virtual Position Test Fixtures - Phase 5.1: Virtual Position Model
 * 
 * Reusable test fixtures for Virtual Position testing across all states.
 * These fixtures support deterministic, replay-safe testing.
 * 
 * Fixture Categories:
 * 1. Valid inputs (from Phase 4 fixtures)
 * 2. Invalid inputs (invalid scenario, invalid risk, mismatched relationships)
 * 3. Expected outputs (valid Virtual Positions)
 * 4. Edge cases (boundary timestamps, minimal data)
 */

import { EntryScenario, EntryScenarioType } from '../entry-scenarios';
import { ConfluenceScore } from '../confluence-scoring';
import { RiskContract } from '../risk-contracts';
import { VirtualPosition } from './virtualPosition.types';

/**
 * Fixed reference timestamp for deterministic testing
 * Value: January 1, 2024 00:00:00 UTC (same as Phase 4.5)
 */
export const T0 = 1704067200000;

/**
 * Additional timestamp for testing (1 hour later)
 */
export const T1 = T0 + 3600000;

/**
 * Additional timestamp for testing (1 day later)
 */
export const T2 = T0 + 86400000;

// ============================================================
// VALID INPUTS (FROM PHASE 4)
// ============================================================

/**
 * Valid Entry Scenario
 * All gates true, status = 'valid'
 */
export const validScenario: EntryScenario = {
  id: 'scen-1',
  type: EntryScenarioType.LiquiditySweepDisplacement,
  contextId: 'ctx-1',
  status: 'valid',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: true,
    structuralConfirmation: true
  },
  optionalConfluences: {
    orderBlock: true,
    fairValueGap: true,
    breakerBlock: false,
    discountPremium: true,
    buySellLiquidity: true,
    newsRisk: false
  },
  evaluatedAt: T0
};

/**
 * Valid Confluence Score
 * References validScenario (scenarioId = 'scen-1')
 */
export const validScore: ConfluenceScore = {
  scenarioId: 'scen-1',
  rawScore: 75,
  normalizedScore: 75,
  confidence: 75,
  breakdown: {
    present: ['orderBlock', 'fairValueGap', 'discountPremium', 'buySellLiquidity'],
    missing: ['breakerBlock', 'newsRisk'],
    contributions: {
      orderBlock: 20,
      fairValueGap: 15,
      breakerBlock: 0,
      discountPremium: 20,
      buySellLiquidity: 20,
      newsRisk: 0
    },
    dampenersApplied: []
  },
  evaluatedAt: T0
};

/**
 * Valid Risk Contract
 * References validScenario (scenarioId = 'scen-1')
 * Status = 'valid', RR = 4.5
 */
export const validRisk: RiskContract = {
  scenarioId: 'scen-1',
  stopLoss: {
    type: 'orderBlock',
    referencePoiId: 'poi-sl-001',
    beyondStructure: true
  },
  takeProfits: [
    { level: 'TP1', targetPoiId: 'poi-tp1-001', probability: 'high' },
    { level: 'TP2', targetPoiId: 'poi-tp2-001', probability: 'medium' },
    { level: 'TP3', targetPoiId: 'poi-tp3-001', probability: 'low' }
  ],
  rr: 4.5,
  status: 'valid',
  evaluatedAt: T0
};

// ============================================================
// INVALID INPUTS
// ============================================================

/**
 * Invalid Entry Scenario
 * Status = 'forming' (not valid)
 */
export const invalidScenario: EntryScenario = {
  id: 'scen-2',
  type: EntryScenarioType.BreakerBlockMSS,
  contextId: 'ctx-2',
  status: 'forming', // NOT VALID
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: false,
    structuralConfirmation: true
  },
  optionalConfluences: {
    orderBlock: true
  },
  evaluatedAt: T0
};

/**
 * Invalidated Entry Scenario
 * Status = 'invalidated' (not valid)
 */
export const invalidatedScenario: EntryScenario = {
  id: 'scen-3',
  type: EntryScenarioType.OB_FVG_Discount,
  contextId: 'ctx-3',
  status: 'invalidated', // NOT VALID
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: true,
    structuralConfirmation: true
  },
  optionalConfluences: {},
  evaluatedAt: T0
};

/**
 * Invalid Risk Contract
 * Status = 'invalid', invalidationReason = 'RR_TOO_LOW'
 */
export const invalidRisk: RiskContract = {
  scenarioId: 'scen-1',
  stopLoss: {
    type: 'structure',
    referencePoiId: 'poi-sl-002',
    beyondStructure: true
  },
  takeProfits: [
    { level: 'TP1', targetPoiId: 'poi-tp1-002', probability: 'high' }
  ],
  rr: 2.1, // Below minimum (3.0)
  status: 'invalid', // NOT VALID
  invalidationReason: 'RR_TOO_LOW',
  evaluatedAt: T0
};

/**
 * Mismatched Confluence Score
 * scenarioId does NOT match validScenario.id
 */
export const mismatchedScore: ConfluenceScore = {
  scenarioId: 'different-scenario-id', // MISMATCH
  rawScore: 50,
  normalizedScore: 60,
  confidence: 60,
  breakdown: {
    present: ['orderBlock'],
    missing: ['fairValueGap', 'breakerBlock', 'discountPremium', 'buySellLiquidity', 'newsRisk'],
    contributions: {
      orderBlock: 50,
      fairValueGap: 0,
      breakerBlock: 0,
      discountPremium: 0,
      buySellLiquidity: 0,
      newsRisk: 0
    },
    dampenersApplied: []
  },
  evaluatedAt: T0
};

/**
 * Mismatched Risk Contract
 * scenarioId does NOT match validScenario.id
 */
export const mismatchedRisk: RiskContract = {
  scenarioId: 'different-scenario-id', // MISMATCH
  stopLoss: {
    type: 'structure',
    referencePoiId: 'poi-sl-003',
    beyondStructure: true
  },
  takeProfits: [
    { level: 'TP1', targetPoiId: 'poi-tp1-003', probability: 'high' }
  ],
  rr: 5.0,
  status: 'valid',
  evaluatedAt: T0
};

// ============================================================
// EXPECTED OUTPUTS
// ============================================================

/**
 * Expected Virtual Position (from valid inputs)
 * Created using validScenario, validScore, validRisk at T0
 * 
 * ID is deterministic: `vpos-${scenario.id}-${openedAt}`
 */
export const expectedVirtualPosition: VirtualPosition = {
  id: 'vpos-scen-1-1704067200000',
  scenarioId: 'scen-1',
  scenarioType: EntryScenarioType.LiquiditySweepDisplacement,
  score: validScore,
  risk: validRisk,
  status: 'open',
  progressPercent: 0,
  reachedTargets: [],
  openedAt: T0,
  lastEvaluatedAt: T0
};

/**
 * Expected Virtual Position with different timestamp
 * Same inputs but opened at T1
 */
export const expectedVirtualPositionT1: VirtualPosition = {
  id: 'vpos-scen-1-1704070800000',
  scenarioId: 'scen-1',
  scenarioType: EntryScenarioType.LiquiditySweepDisplacement,
  score: validScore,
  risk: validRisk,
  status: 'open',
  progressPercent: 0,
  reachedTargets: [],
  openedAt: T1,
  lastEvaluatedAt: T1
};

// ============================================================
// ADDITIONAL VALID SCENARIOS (FOR VARIETY)
// ============================================================

/**
 * Valid Breaker Block Scenario
 */
export const validBreakerBlockScenario: EntryScenario = {
  id: 'scen-bb-1',
  type: EntryScenarioType.BreakerBlockMSS,
  contextId: 'ctx-bb-1',
  status: 'valid',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: true,
    structuralConfirmation: true
  },
  optionalConfluences: {
    orderBlock: false,
    fairValueGap: false,
    breakerBlock: true,
    discountPremium: true,
    buySellLiquidity: true,
    newsRisk: false
  },
  evaluatedAt: T0
};

/**
 * Valid Confluence Score for Breaker Block Scenario
 */
export const validBreakerBlockScore: ConfluenceScore = {
  scenarioId: 'scen-bb-1',
  rawScore: 65,
  normalizedScore: 70,
  confidence: 70,
  breakdown: {
    present: ['breakerBlock', 'discountPremium', 'buySellLiquidity'],
    missing: ['orderBlock', 'fairValueGap', 'newsRisk'],
    contributions: {
      orderBlock: 0,
      fairValueGap: 0,
      breakerBlock: 25,
      discountPremium: 20,
      buySellLiquidity: 20,
      newsRisk: 0
    },
    dampenersApplied: []
  },
  evaluatedAt: T0
};

/**
 * Valid Risk Contract for Breaker Block Scenario
 */
export const validBreakerBlockRisk: RiskContract = {
  scenarioId: 'scen-bb-1',
  stopLoss: {
    type: 'structure',
    referencePoiId: 'poi-sl-bb-001',
    beyondStructure: true
  },
  takeProfits: [
    { level: 'TP1', targetPoiId: 'poi-tp1-bb-001', probability: 'high' },
    { level: 'TP2', targetPoiId: 'poi-tp2-bb-001', probability: 'medium' }
  ],
  rr: 3.2,
  status: 'valid',
  evaluatedAt: T0
};

// ============================================================
// EDGE CASES
// ============================================================

/**
 * Boundary timestamp (0)
 */
export const boundaryTimestamp = 0;

/**
 * Large timestamp (far future)
 */
export const largeTimestamp = 9999999999999;

/**
 * Minimal valid scenario (only required fields)
 */
export const minimalValidScenario: EntryScenario = {
  id: 'scen-min-1',
  type: EntryScenarioType.SellSideSweepOBReaction,
  contextId: 'ctx-min-1',
  status: 'valid',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: true,
    structuralConfirmation: true
  },
  optionalConfluences: {},
  evaluatedAt: T0
};

/**
 * Minimal valid score
 */
export const minimalValidScore: ConfluenceScore = {
  scenarioId: 'scen-min-1',
  rawScore: 0,
  normalizedScore: 0,
  confidence: 0,
  breakdown: {
    present: [],
    missing: ['orderBlock', 'fairValueGap', 'breakerBlock', 'discountPremium', 'buySellLiquidity', 'newsRisk'],
    contributions: {
      orderBlock: 0,
      fairValueGap: 0,
      breakerBlock: 0,
      discountPremium: 0,
      buySellLiquidity: 0,
      newsRisk: 0
    },
    dampenersApplied: []
  },
  evaluatedAt: T0
};

/**
 * Minimal valid risk (only TP1)
 */
export const minimalValidRisk: RiskContract = {
  scenarioId: 'scen-min-1',
  stopLoss: {
    type: 'structure',
    referencePoiId: 'poi-sl-min-001',
    beyondStructure: false
  },
  takeProfits: [
    { level: 'TP1', targetPoiId: 'poi-tp1-min-001', probability: 'high' }
  ],
  rr: 3.0, // Exactly at minimum
  status: 'valid',
  evaluatedAt: T0
};
