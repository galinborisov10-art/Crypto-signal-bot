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

// Phase 5.4: Guidance Layer / Narrative Signals
export {
  GuidanceSignal,
  GuidanceResult
} from './guidance.types';

export {
  deriveGuidance
} from './guidance.contracts';

// Phase 5.5: Timeline / Observation History
export {
  TimelineEntry,
  VirtualPositionTimeline
} from './timeline.types';

export {
  appendTimelineEntry
} from './timeline.contracts';

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

// Phase 5.5 test fixtures (for testing only)
export {
  emptyTimeline,
  earlyEntry,
  midEntry,
  lateEntry,
  invalidatedEntry,
  sameTimeEntry1,
  sameTimeEntry2,
  singleEntryTimeline,
  multiEntryTimeline,
  outOfOrderEntry
} from './timeline.fixtures';

// Phase 6.1: Timeline Interpretation Engine
export {
  TimelineInterpretation,
  TrajectorySignal,
  StabilitySignal,
  InvalidationPattern,
  GuidanceConsistency
} from './interpretation.types';

export {
  interpretTimeline
} from './interpretation.contracts';

// Phase 6.1 test fixtures (for testing only)
export * from './interpretation.fixtures';

// Phase 6.2: Policy types (Phase 6.2.1)
export {
  PolicyStance,
  PolicyConfidence,
  PolicyContext,
  PolicyResult
} from './policy.types';

// Policy derivation (Phase 6.2.2)
export {
  derivePolicy
} from './policy.contracts';

// Phase 6.2 test fixtures (for testing only)
export * from './policy.fixtures';

// Decision Guardrail types (Phase 6.3.1)
export {
  DecisionPermission,
  DecisionGuardrailReason,
  DecisionGuardrailResult
} from './decisionGuardrail.types';

// Decision Guardrail derivation (Phase 6.3.2)
export {
  deriveDecisionGuardrail
} from './decisionGuardrail.contracts';

// Decision Guardrail test fixtures (for testing only)
export * from './decisionGuardrail.fixtures';
