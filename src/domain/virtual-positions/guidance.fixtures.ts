/**
 * Guidance Test Fixtures - Phase 5.4: Guidance Layer / Narrative Signals
 * 
 * Reusable test fixtures for guidance testing.
 * These fixtures support deterministic, replay-safe testing of guidance signals.
 * 
 * Fixture Categories:
 * 1. Position fixtures at various progress levels
 * 2. Re-analysis result fixtures (valid and invalidated)
 * 3. Expected guidance result fixtures
 */

import { VirtualPosition } from './virtualPosition.types';
import { ReanalysisResult } from './reanalysis.types';
import { GuidanceResult } from './guidance.types';
import {
  T0,
  validScore,
  validRisk
} from './virtualPosition.fixtures';
import { EntryScenarioType } from '../entry-scenarios';

// ============================================================
// POSITION FIXTURES AT VARIOUS PROGRESS LEVELS
// ============================================================

/**
 * Early Position (0% progress)
 * Status: open, no progress yet
 */
export const earlyPosition: VirtualPosition = {
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
 * Low Progress Position (10% progress)
 * Status: open, minimal progress
 */
export const lowProgressPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'open',
  progressPercent: 10,
  lastEvaluatedAt: T0 + 600000 // 10 minutes later
};

/**
 * Boundary Position (24.9% progress)
 * Status: progressing, just below 25% threshold
 */
export const boundaryLowPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'progressing',
  progressPercent: 24.9,
  lastEvaluatedAt: T0 + 1200000 // 20 minutes later
};

/**
 * Threshold Position (25% progress - EXACT)
 * Status: progressing, exactly at 25% threshold (left-inclusive)
 */
export const thresholdPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'progressing',
  progressPercent: 25,
  reachedTargets: [],
  lastEvaluatedAt: T0 + 1800000 // 30 minutes later
};

/**
 * Mid Progress Position (50% progress)
 * Status: progressing, healthy progress
 */
export const midProgressPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'progressing',
  progressPercent: 50,
  reachedTargets: ['TP1'],
  lastEvaluatedAt: T0 + 3600000 // 1 hour later
};

/**
 * High Progress Position (80% progress)
 * Status: progressing, near completion
 */
export const highProgressPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'progressing',
  progressPercent: 80,
  reachedTargets: ['TP1', 'TP2'],
  lastEvaluatedAt: T0 + 7200000 // 2 hours later
};

/**
 * Stalled Position (30% progress)
 * Status: stalled, progress degraded
 */
export const stalledLowPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'stalled',
  progressPercent: 30,
  reachedTargets: [],
  lastEvaluatedAt: T0 + 7200000 // 2 hours later
};

/**
 * Stalled Position (60% progress)
 * Status: stalled, mid progress but momentum lost
 */
export const stalledMidPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'stalled',
  progressPercent: 60,
  reachedTargets: ['TP1'],
  lastEvaluatedAt: T0 + 10800000 // 3 hours later
};

/**
 * Stalled Position (80% progress)
 * Status: stalled, high progress but stalled
 */
export const stalledHighPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'stalled',
  progressPercent: 80,
  reachedTargets: ['TP1', 'TP2'],
  lastEvaluatedAt: T0 + 14400000 // 4 hours later
};

/**
 * Completed Position (100% progress)
 * Status: completed, all targets reached (terminal state)
 */
export const completedPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'completed',
  progressPercent: 100,
  reachedTargets: ['TP1', 'TP2', 'TP3'],
  lastEvaluatedAt: T0 + 18000000 // 5 hours later
};

/**
 * Open Position with Progress (30% progress)
 * Status: open, has progress but not yet 'progressing' status
 */
export const openWithProgressPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'open',
  progressPercent: 30,
  reachedTargets: [],
  lastEvaluatedAt: T0 + 1800000 // 30 minutes later
};

/**
 * Progressing Position with Low Progress (10% progress)
 * Status: progressing, but progress is still low
 */
export const progressingLowPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'progressing',
  progressPercent: 10,
  reachedTargets: [],
  lastEvaluatedAt: T0 + 900000 // 15 minutes later
};

/**
 * Progressing Position with Mid Progress (40% progress)
 * Status: progressing, healthy progress
 */
export const progressingMidPosition: VirtualPosition = {
  ...earlyPosition,
  status: 'progressing',
  progressPercent: 40,
  reachedTargets: [],
  lastEvaluatedAt: T0 + 2400000 // 40 minutes later
};

// ============================================================
// RE-ANALYSIS RESULT FIXTURES
// ============================================================

/**
 * Valid Re-analysis Result
 * All checks passed, position still structurally valid
 */
export const validReanalysis: ReanalysisResult = {
  status: 'still_valid',
  checksPassed: [
    'STRUCTURE_INTACT',
    'POI_REMAINS_VALID',
    'NO_COUNTER_LIQUIDITY',
    'HTF_BIAS_ALIGNED'
  ]
};

/**
 * Invalidated Re-analysis Result (Structure Broken)
 * Position invalidated due to structure violation
 */
export const invalidatedReanalysisStructure: ReanalysisResult = {
  status: 'invalidated',
  reason: 'STRUCTURE_BROKEN'
};

/**
 * Invalidated Re-analysis Result (POI Invalidated)
 * Position invalidated due to POI mitigation
 */
export const invalidatedReanalysisPOI: ReanalysisResult = {
  status: 'invalidated',
  reason: 'POI_INVALIDATED'
};

/**
 * Invalidated Re-analysis Result (Liquidity Taken Against)
 * Position invalidated due to counter-liquidity event
 */
export const invalidatedReanalysisLiquidity: ReanalysisResult = {
  status: 'invalidated',
  reason: 'LIQUIDITY_TAKEN_AGAINST'
};

/**
 * Invalidated Re-analysis Result (HTF Bias Flipped)
 * Position invalidated due to HTF bias flip
 */
export const invalidatedReanalysisHTF: ReanalysisResult = {
  status: 'invalidated',
  reason: 'HTF_BIAS_FLIPPED'
};

/**
 * Invalidated Re-analysis Result (Time Decay)
 * Position invalidated due to time decay
 */
export const invalidatedReanalysisTimeDecay: ReanalysisResult = {
  status: 'invalidated',
  reason: 'TIME_DECAY_EXCEEDED'
};

// ============================================================
// EXPECTED GUIDANCE RESULT FIXTURES
// ============================================================

/**
 * Expected: WAIT_FOR_CONFIRMATION
 * Early stage, low progress (0%)
 */
export const expectedWaitForConfirmationEarly: GuidanceResult = {
  signal: 'WAIT_FOR_CONFIRMATION',
  progressPercent: 0,
  status: 'open',
  validity: 'still_valid'
};

/**
 * Expected: WAIT_FOR_CONFIRMATION
 * Low progress (10%)
 */
export const expectedWaitForConfirmationLow: GuidanceResult = {
  signal: 'WAIT_FOR_CONFIRMATION',
  progressPercent: 10,
  status: 'open',
  validity: 'still_valid'
};

/**
 * Expected: WAIT_FOR_CONFIRMATION
 * Boundary progress (24.9%)
 */
export const expectedWaitForConfirmationBoundary: GuidanceResult = {
  signal: 'WAIT_FOR_CONFIRMATION',
  progressPercent: 24.9,
  status: 'progressing',
  validity: 'still_valid'
};

/**
 * Expected: HOLD_THESIS
 * Threshold progress (25% - left-inclusive)
 */
export const expectedHoldThesisThreshold: GuidanceResult = {
  signal: 'HOLD_THESIS',
  progressPercent: 25,
  status: 'progressing',
  validity: 'still_valid'
};

/**
 * Expected: HOLD_THESIS
 * Mid progress (50%)
 */
export const expectedHoldThesisMid: GuidanceResult = {
  signal: 'HOLD_THESIS',
  progressPercent: 50,
  status: 'progressing',
  validity: 'still_valid'
};

/**
 * Expected: HOLD_THESIS
 * High progress (80%)
 */
export const expectedHoldThesisHigh: GuidanceResult = {
  signal: 'HOLD_THESIS',
  progressPercent: 80,
  status: 'progressing',
  validity: 'still_valid'
};

/**
 * Expected: HOLD_THESIS
 * Completed (100%)
 */
export const expectedHoldThesisCompleted: GuidanceResult = {
  signal: 'HOLD_THESIS',
  progressPercent: 100,
  status: 'completed',
  validity: 'still_valid'
};

/**
 * Expected: HOLD_THESIS
 * Open with progress (30%)
 */
export const expectedHoldThesisOpenWithProgress: GuidanceResult = {
  signal: 'HOLD_THESIS',
  progressPercent: 30,
  status: 'open',
  validity: 'still_valid'
};

/**
 * Expected: THESIS_WEAKENING
 * Stalled with low progress (30%)
 */
export const expectedThesisWeakeningStalledLow: GuidanceResult = {
  signal: 'THESIS_WEAKENING',
  progressPercent: 30,
  status: 'stalled',
  validity: 'still_valid'
};

/**
 * Expected: THESIS_WEAKENING
 * Stalled with mid progress (60%)
 */
export const expectedThesisWeakeningStalledMid: GuidanceResult = {
  signal: 'THESIS_WEAKENING',
  progressPercent: 60,
  status: 'stalled',
  validity: 'still_valid'
};

/**
 * Expected: THESIS_WEAKENING
 * Stalled with high progress (80%)
 */
export const expectedThesisWeakeningStalledHigh: GuidanceResult = {
  signal: 'THESIS_WEAKENING',
  progressPercent: 80,
  status: 'stalled',
  validity: 'still_valid'
};

/**
 * Expected: STRUCTURE_AT_RISK
 * Invalidated with open status
 */
export const expectedStructureAtRiskOpen: GuidanceResult = {
  signal: 'STRUCTURE_AT_RISK',
  progressPercent: 0,
  status: 'open',
  validity: 'invalidated'
};

/**
 * Expected: STRUCTURE_AT_RISK
 * Invalidated with progressing status
 */
export const expectedStructureAtRiskProgressing: GuidanceResult = {
  signal: 'STRUCTURE_AT_RISK',
  progressPercent: 50,
  status: 'progressing',
  validity: 'invalidated'
};

/**
 * Expected: STRUCTURE_AT_RISK
 * Invalidated with stalled status
 */
export const expectedStructureAtRiskStalled: GuidanceResult = {
  signal: 'STRUCTURE_AT_RISK',
  progressPercent: 60,
  status: 'stalled',
  validity: 'invalidated'
};

/**
 * Expected: HOLD_THESIS
 * Completed overrides invalidation
 */
export const expectedHoldThesisCompletedInvalidated: GuidanceResult = {
  signal: 'HOLD_THESIS',
  progressPercent: 100,
  status: 'completed',
  validity: 'invalidated'
};

/**
 * Expected: WAIT_FOR_CONFIRMATION
 * Progressing but low progress (10%)
 */
export const expectedWaitForConfirmationProgressingLow: GuidanceResult = {
  signal: 'WAIT_FOR_CONFIRMATION',
  progressPercent: 10,
  status: 'progressing',
  validity: 'still_valid'
};

/**
 * Expected: HOLD_THESIS
 * Progressing with mid progress (40%)
 */
export const expectedHoldThesisProgressingMid: GuidanceResult = {
  signal: 'HOLD_THESIS',
  progressPercent: 40,
  status: 'progressing',
  validity: 'still_valid'
};
