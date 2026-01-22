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
