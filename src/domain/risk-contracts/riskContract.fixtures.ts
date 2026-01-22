/**
 * Risk Contract Test Fixtures - Phase 4.5: SL/TP Contracts
 * 
 * Reusable test fixtures for risk contract testing.
 * Provides POI fixtures, RiskPOIs fixtures, and RiskContract fixtures.
 */

import { POI, POIType } from '../poi';
import { EntryScenario, EntryScenarioType } from '../entry-scenarios';
import { ConfluenceScore } from '../confluence-scoring';
import {
  RiskPOIs,
  RiskContract
} from './riskContract.types';

/**
 * Fixed timestamp for testing (T0)
 */
export const T0 = 1704067200000; // 2024-01-01 00:00:00 UTC

/**
 * Bullish Entry POI Fixture
 */
export const bullishEntryPOI: POI = {
  id: 'entry-bullish-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 120, high: 125 },
  directionBias: 'bullish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Bearish Entry POI Fixture
 */
export const bearishEntryPOI: POI = {
  id: 'entry-bearish-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 120, high: 125 },
  directionBias: 'bearish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Valid Bullish Stop Loss POI
 * Below entry (100-105 vs entry 120-125)
 */
export const validBullishSLPOI: POI = {
  id: 'sl-bullish-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 100, high: 105 },
  directionBias: 'bullish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Valid Bearish Stop Loss POI
 * Above entry (140-145 vs entry 120-125)
 */
export const validBearishSLPOI: POI = {
  id: 'sl-bearish-001',
  type: POIType.PreviousHigh,
  timeframe: '4h',
  priceRange: { low: 140, high: 145 },
  directionBias: 'bearish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Large Bullish Stop Loss POI (for low RR testing)
 * Far below entry (60-65 vs entry 120-125)
 * This creates high risk, leading to low RR
 */
export const largeBullishSLPOI: POI = {
  id: 'sl-bullish-large-001',
  type: POIType.PreviousLow,
  timeframe: '4h',
  priceRange: { low: 60, high: 65 },
  directionBias: 'bullish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Valid Bullish TP1 POI
 * Above entry (180-185 vs entry 120-125)
 */
export const validBullishTP1POI: POI = {
  id: 'tp-bullish-001',
  type: POIType.PreviousHigh,
  timeframe: '4h',
  priceRange: { low: 180, high: 185 },
  directionBias: 'bullish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Valid Bullish TP2 POI
 * Further above entry (220-225 vs entry 120-125)
 */
export const validBullishTP2POI: POI = {
  id: 'tp-bullish-002',
  type: POIType.BuySideLiquidity,
  timeframe: '1d',
  priceRange: { low: 220, high: 225 },
  directionBias: 'bullish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Valid Bullish TP3 POI
 * Even further above entry (280-285 vs entry 120-125)
 */
export const validBullishTP3POI: POI = {
  id: 'tp-bullish-003',
  type: POIType.Distribution,
  timeframe: '1d',
  priceRange: { low: 280, high: 285 },
  directionBias: 'bullish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Near Bullish TP1 POI (for low RR testing)
 * Just above entry (135-140 vs entry 120-125)
 * This creates low reward, leading to low RR when combined with large SL
 */
export const nearBullishTP1POI: POI = {
  id: 'tp-bullish-near-001',
  type: POIType.PreviousHigh,
  timeframe: '1h',
  priceRange: { low: 135, high: 140 },
  directionBias: 'bullish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Valid Bearish TP1 POI
 * Below entry (60-65 vs entry 120-125)
 */
export const validBearishTP1POI: POI = {
  id: 'tp-bearish-001',
  type: POIType.PreviousLow,
  timeframe: '4h',
  priceRange: { low: 60, high: 65 },
  directionBias: 'bearish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Valid Bearish TP2 POI
 * Further below entry (30-35 vs entry 120-125)
 */
export const validBearishTP2POI: POI = {
  id: 'tp-bearish-002',
  type: POIType.SellSideLiquidity,
  timeframe: '1d',
  priceRange: { low: 30, high: 35 },
  directionBias: 'bearish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Valid Bearish TP3 POI
 * Even further below entry (10-15 vs entry 120-125)
 */
export const validBearishTP3POI: POI = {
  id: 'tp-bearish-003',
  type: POIType.Accumulation,
  timeframe: '1d',
  priceRange: { low: 10, high: 15 },
  directionBias: 'bearish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Invalid SL POI (wrong type)
 * FairValueGap is not a valid SL type
 */
export const invalidSLTypePOI: POI = {
  id: 'sl-invalid-type-001',
  type: POIType.FairValueGap,
  timeframe: '4h',
  priceRange: { low: 100, high: 105 },
  directionBias: 'bullish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Invalid Bullish SL POI (wrong position - above entry)
 * Should be below for bullish, but is above
 */
export const invalidBullishSLPositionPOI: POI = {
  id: 'sl-bullish-wrong-position-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: { low: 140, high: 145 }, // Above entry (should be below)
  directionBias: 'bullish',
  validFrom: T0,
  validUntil: T0 + 86400000,
  mitigated: false
};

/**
 * Valid Bullish RiskPOIs
 * Contains valid entry, SL, and TP POIs for bullish scenario
 * RR calculation: risk = 120 - 105 = 15, reward = 180 - 125 = 55, RR = 55/15 = 3.67
 */
export const validBullishRiskPOIs: RiskPOIs = {
  entryPOI: bullishEntryPOI,
  stopLossCandidates: [validBullishSLPOI],
  takeProfitCandidates: [validBullishTP1POI, validBullishTP2POI, validBullishTP3POI]
};

/**
 * Valid Bearish RiskPOIs
 * Contains valid entry, SL, and TP POIs for bearish scenario
 * RR calculation: risk = 140 - 125 = 15, reward = 120 - 65 = 55, RR = 55/15 = 3.67
 */
export const validBearishRiskPOIs: RiskPOIs = {
  entryPOI: bearishEntryPOI,
  stopLossCandidates: [validBearishSLPOI],
  takeProfitCandidates: [validBearishTP1POI, validBearishTP2POI, validBearishTP3POI]
};

/**
 * No Valid Stop RiskPOIs
 * Contains no valid SL candidates (empty array)
 */
export const noValidStopRiskPOIs: RiskPOIs = {
  entryPOI: bullishEntryPOI,
  stopLossCandidates: [],
  takeProfitCandidates: [validBullishTP1POI]
};

/**
 * No Valid Targets RiskPOIs
 * Contains no valid TP candidates (empty array)
 */
export const noValidTargetsRiskPOIs: RiskPOIs = {
  entryPOI: bullishEntryPOI,
  stopLossCandidates: [validBullishSLPOI],
  takeProfitCandidates: []
};

/**
 * Low RR RiskPOIs
 * Contains large SL and near TP1, resulting in RR < 3
 * RR calculation: risk = 120 - 65 = 55, reward = 135 - 125 = 10, RR = 10/55 = 0.18
 */
export const lowRRRiskPOIs: RiskPOIs = {
  entryPOI: bullishEntryPOI,
  stopLossCandidates: [largeBullishSLPOI],
  takeProfitCandidates: [nearBullishTP1POI]
};

/**
 * Invalid SL Type RiskPOIs
 * Contains only invalid SL type (FairValueGap)
 */
export const invalidSLTypeRiskPOIs: RiskPOIs = {
  entryPOI: bullishEntryPOI,
  stopLossCandidates: [invalidSLTypePOI],
  takeProfitCandidates: [validBullishTP1POI]
};

/**
 * Invalid SL Position RiskPOIs
 * Contains SL in wrong position (above entry for bullish)
 */
export const invalidSLPositionRiskPOIs: RiskPOIs = {
  entryPOI: bullishEntryPOI,
  stopLossCandidates: [invalidBullishSLPositionPOI],
  takeProfitCandidates: [validBullishTP1POI]
};

/**
 * Valid Bullish Entry Scenario
 */
export const validBullishScenario: EntryScenario = {
  id: 'scenario-bullish-001',
  type: EntryScenarioType.OB_FVG_Discount,
  contextId: 'context-001',
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
 * Valid Bearish Entry Scenario
 */
export const validBearishScenario: EntryScenario = {
  id: 'scenario-bearish-001',
  type: EntryScenarioType.BuySideTakenRejection,
  contextId: 'context-002',
  status: 'valid',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: true,
    structuralConfirmation: true
  },
  optionalConfluences: {
    orderBlock: true,
    fairValueGap: false,
    breakerBlock: true,
    discountPremium: true,
    buySellLiquidity: true,
    newsRisk: false
  },
  evaluatedAt: T0
};

/**
 * Forming Entry Scenario (not valid yet)
 */
export const formingScenario: EntryScenario = {
  id: 'scenario-forming-001',
  type: EntryScenarioType.LiquiditySweepDisplacement,
  contextId: 'context-003',
  status: 'forming',
  requiredGates: {
    htfBiasAligned: true,
    liquidityEvent: false, // Not complete yet
    structuralConfirmation: false
  },
  optionalConfluences: {
    orderBlock: true
  },
  evaluatedAt: T0
};

/**
 * Mock Confluence Score (for valid scenario)
 */
export const validConfluenceScore: ConfluenceScore = {
  scenarioId: 'scenario-bullish-001',
  rawScore: 50,
  normalizedScore: 85,
  confidence: 85,
  breakdown: {
    present: ['orderBlock', 'fairValueGap', 'discountPremium', 'buySellLiquidity'],
    missing: ['breakerBlock', 'newsRisk'],
    contributions: {
      orderBlock: 15,
      fairValueGap: 10,
      breakerBlock: 0,
      discountPremium: 15,
      buySellLiquidity: 10,
      newsRisk: 0
    },
    dampenersApplied: []
  },
  evaluatedAt: T0
};

/**
 * Valid Risk Contract (Bullish)
 */
export const validBullishRiskContract: RiskContract = {
  scenarioId: 'scenario-bullish-001',
  stopLoss: {
    type: 'orderBlock',
    referencePoiId: 'sl-bullish-001',
    beyondStructure: true
  },
  takeProfits: [
    { level: 'TP1', targetPoiId: 'tp-bullish-001', probability: 'high' },
    { level: 'TP2', targetPoiId: 'tp-bullish-002', probability: 'medium' },
    { level: 'TP3', targetPoiId: 'tp-bullish-003', probability: 'low' }
  ],
  rr: 3.67,
  status: 'valid',
  evaluatedAt: T0
};

/**
 * Invalid Risk Contract (No Valid Stop)
 */
export const invalidRiskContract_NoStop: RiskContract = {
  scenarioId: 'scenario-bullish-001',
  stopLoss: {
    type: 'structure',
    referencePoiId: '',
    beyondStructure: false
  },
  takeProfits: [],
  rr: 0,
  status: 'invalid',
  invalidationReason: 'NO_VALID_STOP',
  evaluatedAt: T0
};

/**
 * Invalid Risk Contract (No Valid Targets)
 */
export const invalidRiskContract_NoTargets: RiskContract = {
  scenarioId: 'scenario-bullish-001',
  stopLoss: {
    type: 'orderBlock',
    referencePoiId: 'sl-bullish-001',
    beyondStructure: true
  },
  takeProfits: [],
  rr: 0,
  status: 'invalid',
  invalidationReason: 'NO_VALID_TARGETS',
  evaluatedAt: T0
};

/**
 * Invalid Risk Contract (RR Too Low)
 */
export const invalidRiskContract_LowRR: RiskContract = {
  scenarioId: 'scenario-bullish-001',
  stopLoss: {
    type: 'structure',
    referencePoiId: 'sl-bullish-large-001',
    beyondStructure: true
  },
  takeProfits: [
    { level: 'TP1', targetPoiId: 'tp-bullish-near-001', probability: 'high' }
  ],
  rr: 0.18,
  status: 'invalid',
  invalidationReason: 'RR_TOO_LOW',
  evaluatedAt: T0
};

/**
 * Invalid Risk Contract (Scenario Not Valid - Edge Case)
 */
export const invalidRiskContract_ScenarioNotValid: RiskContract = {
  scenarioId: 'scenario-forming-001',
  stopLoss: {
    type: 'structure',
    referencePoiId: '',
    beyondStructure: false
  },
  takeProfits: [],
  rr: 0,
  status: 'invalid',
  invalidationReason: 'SCENARIO_NOT_VALID',
  evaluatedAt: T0
};
