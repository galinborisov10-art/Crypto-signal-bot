/**
 * Virtual Positions Domain - Entry Point
 * 
 * Phase 5.1: Virtual Position Model (Design-First)
 * Pure data + contract layer for Virtual Positions
 * 
 * Virtual Positions represent "if this were a trade" observation objects.
 * They are NOT real positions, NOT execution instructions, and do NOT involve capital.
 */

// Type definitions
export {
  VirtualPosition,
  VirtualPositionStatus,
  VirtualPositionResult
} from './virtualPosition.types';

// Contracts and functions
export {
  createVirtualPosition,
  isVirtualPositionOpen,
  isVirtualPositionProgressing,
  isVirtualPositionCompleted,
  isVirtualPositionInvalidated
} from './virtualPosition.contracts';

// Phase 5.2: Progress Engine
export {
  updateVirtualPositionProgress
} from './virtualPosition.progress';

// Phase 5.3: Re-analysis & Invalidation Engine
export {
  MarketState,
  InvalidationReason,
  ReanalysisCheck,
  ReanalysisResult
} from './reanalysis.types';

export {
  reanalyzeVirtualPosition,
  inferDirectionFromSLTP
} from './reanalysis.contracts';

// Test fixtures (for testing only)
export {
  T0,
  T1,
  T2,
  validScenario,
  validScore,
  validRisk,
  invalidScenario,
  invalidatedScenario,
  invalidRisk,
  mismatchedScore,
  mismatchedRisk,
  expectedVirtualPosition,
  expectedVirtualPositionT1,
  validBreakerBlockScenario,
  validBreakerBlockScore,
  validBreakerBlockRisk,
  minimalValidScenario,
  minimalValidScore,
  minimalValidRisk,
  boundaryTimestamp,
  largeTimestamp,
  // Phase 5.2 POI fixtures
  bullishSLPOI,
  bullishTP1POI,
  bullishTP2POI,
  bullishTP3POI,
  bearishSLPOI,
  bearishTP1POI,
  bearishTP2POI,
  bearishTP3POI,
  bullishPOIMap,
  bearishPOIMap,
  openBullishPosition,
  progressingBullishPosition
} from './virtualPosition.fixtures';

// Phase 5.3 test fixtures (for testing only)
export {
  validMarketState,
  structureBrokenState,
  poiInvalidatedStateSL,
  poiInvalidatedStateTP1,
  poiInvalidatedStateTP3,
  counterLiquidityState,
  htfBiasFlippedState,
  htfBiasNeutralState,
  validOpenPosition,
  completedPosition,
  progressingPosition,
  stalledPosition,
  expectedStillValid,
  expectedStructureBroken,
  expectedPOIInvalidated,
  expectedCounterLiquidity,
  expectedHTFBiasFlipped,
  expectedTimeDecayExceeded,
  expectedCompletedSkip,
  evaluatedAtZero,
  evaluatedAt1Hour,
  evaluatedAtAlmost24Hours,
  evaluatedAtExactly24Hours,
  evaluatedAtOver24Hours,
  evaluatedAt48Hours
} from './reanalysis.fixtures';
