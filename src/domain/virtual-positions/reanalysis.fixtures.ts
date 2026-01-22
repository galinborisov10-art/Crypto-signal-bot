/**
 * Re-analysis Test Fixtures - Phase 5.3: Re-analysis & Invalidation Engine
 * 
 * Reusable test fixtures for re-analysis testing.
 * These fixtures support deterministic, replay-safe testing of invalidation logic.
 * 
 * Fixture Categories:
 * 1. Market state fixtures (valid and invalidated states)
 * 2. Position fixtures (from Phase 5.1/5.2)
 * 3. Expected result fixtures
 */

import { MarketState, ReanalysisResult } from './reanalysis.types';
import { VirtualPosition } from './virtualPosition.types';
import {
  T0,
  bullishSLPOI,
  bullishTP1POI,
  bullishTP2POI,
  bullishTP3POI,
  validScore,
  validRisk
} from './virtualPosition.fixtures';
import { EntryScenarioType } from '../entry-scenarios';

// ============================================================
// MARKET STATE FIXTURES
// ============================================================

/**
 * Valid Market State
 * All structural checks pass - position should remain valid
 */
export const validMarketState: MarketState = {
  pois: new Map([
    ['poi-sl-001', bullishSLPOI],
    ['poi-tp1-001', bullishTP1POI],
    ['poi-tp2-001', bullishTP2POI],
    ['poi-tp3-001', bullishTP3POI]
  ]),
  htfBias: 'bullish',
  structureIntact: true,
  counterLiquidityTaken: false,
  invalidatedPOIs: new Set()
};

/**
 * Structure Broken State
 * Market structure no longer supports the scenario
 */
export const structureBrokenState: MarketState = {
  ...validMarketState,
  structureIntact: false
};

/**
 * POI Invalidated State (SL POI)
 * Stop Loss POI has been invalidated/mitigated
 */
export const poiInvalidatedStateSL: MarketState = {
  ...validMarketState,
  invalidatedPOIs: new Set(['poi-sl-001'])
};

/**
 * POI Invalidated State (TP1 POI)
 * Take Profit 1 POI has been invalidated/mitigated
 */
export const poiInvalidatedStateTP1: MarketState = {
  ...validMarketState,
  invalidatedPOIs: new Set(['poi-tp1-001'])
};

/**
 * POI Invalidated State (TP3 POI)
 * Take Profit 3 POI has been invalidated/mitigated
 */
export const poiInvalidatedStateTP3: MarketState = {
  ...validMarketState,
  invalidatedPOIs: new Set(['poi-tp3-001'])
};

/**
 * Counter-Liquidity Taken State
 * Opposing-side liquidity event detected
 */
export const counterLiquidityState: MarketState = {
  ...validMarketState,
  counterLiquidityTaken: true
};

/**
 * HTF Bias Flipped State (Bearish)
 * Higher-timeframe bias has flipped from bullish to bearish
 */
export const htfBiasFlippedState: MarketState = {
  ...validMarketState,
  htfBias: 'bearish' // flipped from bullish
};

/**
 * HTF Bias Neutral State
 * Higher-timeframe bias is neutral (should NOT trigger flip)
 */
export const htfBiasNeutralState: MarketState = {
  ...validMarketState,
  htfBias: 'neutral'
};

// ============================================================
// POSITION FIXTURES
// ============================================================

/**
 * Valid Open Position (from Phase 5.1)
 * Standard open position for testing
 */
export const validOpenPosition: VirtualPosition = {
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
 * Completed Position
 * Position that has reached final TP - should skip re-analysis
 */
export const completedPosition: VirtualPosition = {
  ...validOpenPosition,
  status: 'completed',
  progressPercent: 100,
  reachedTargets: ['TP1', 'TP2', 'TP3']
};

/**
 * Progressing Position
 * Position with some progress - still needs re-analysis
 */
export const progressingPosition: VirtualPosition = {
  ...validOpenPosition,
  status: 'progressing',
  progressPercent: 45,
  reachedTargets: ['TP1'],
  lastEvaluatedAt: T0 + 3600000 // 1 hour later
};

/**
 * Stalled Position
 * Position that has stalled - still needs re-analysis
 */
export const stalledPosition: VirtualPosition = {
  ...validOpenPosition,
  status: 'stalled',
  progressPercent: 30,
  reachedTargets: [],
  lastEvaluatedAt: T0 + 7200000 // 2 hours later
};

// ============================================================
// EXPECTED RESULT FIXTURES
// ============================================================

/**
 * Expected Result: Still Valid
 * All checks passed, position remains valid
 */
export const expectedStillValid: ReanalysisResult = {
  status: 'still_valid',
  checksPassed: [
    'STRUCTURE_INTACT',
    'POI_REMAINS_VALID',
    'NO_COUNTER_LIQUIDITY',
    'HTF_BIAS_ALIGNED'
  ]
};

/**
 * Expected Result: Structure Broken
 */
export const expectedStructureBroken: ReanalysisResult = {
  status: 'invalidated',
  reason: 'STRUCTURE_BROKEN'
};

/**
 * Expected Result: POI Invalidated
 */
export const expectedPOIInvalidated: ReanalysisResult = {
  status: 'invalidated',
  reason: 'POI_INVALIDATED'
};

/**
 * Expected Result: Counter-Liquidity Taken
 */
export const expectedCounterLiquidity: ReanalysisResult = {
  status: 'invalidated',
  reason: 'LIQUIDITY_TAKEN_AGAINST'
};

/**
 * Expected Result: HTF Bias Flipped
 */
export const expectedHTFBiasFlipped: ReanalysisResult = {
  status: 'invalidated',
  reason: 'HTF_BIAS_FLIPPED'
};

/**
 * Expected Result: Time Decay Exceeded
 */
export const expectedTimeDecayExceeded: ReanalysisResult = {
  status: 'invalidated',
  reason: 'TIME_DECAY_EXCEEDED'
};

/**
 * Expected Result: Completed Position (Skip Re-analysis)
 * Completed positions return still_valid with empty checks
 */
export const expectedCompletedSkip: ReanalysisResult = {
  status: 'still_valid',
  checksPassed: []
};

// ============================================================
// TIMESTAMP FIXTURES
// ============================================================

/**
 * Evaluation timestamp: Same as openedAt (0 elapsed)
 */
export const evaluatedAtZero = T0;

/**
 * Evaluation timestamp: 1 hour later
 */
export const evaluatedAt1Hour = T0 + (60 * 60 * 1000);

/**
 * Evaluation timestamp: 23 hours 59 minutes later (within threshold)
 */
export const evaluatedAtAlmost24Hours = T0 + (24 * 60 * 60 * 1000) - (60 * 1000);

/**
 * Evaluation timestamp: Exactly 24 hours later (boundary)
 */
export const evaluatedAtExactly24Hours = T0 + (24 * 60 * 60 * 1000);

/**
 * Evaluation timestamp: 24 hours 1 second later (exceeded)
 */
export const evaluatedAtOver24Hours = T0 + (24 * 60 * 60 * 1000) + 1000;

/**
 * Evaluation timestamp: 48 hours later (far exceeded)
 */
export const evaluatedAt48Hours = T0 + (48 * 60 * 60 * 1000);
