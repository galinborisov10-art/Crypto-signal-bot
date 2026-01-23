/**
 * Policy Test Fixtures - Phase 6.2.2: Policy Derivation Engine
 * 
 * Reusable fixtures for testing policy derivation logic.
 * All fixtures are semantic and implementation-agnostic.
 * 
 * Coverage:
 * - All 6 policy stances
 * - All 4 confidence levels
 * - Edge cases (undefined guidanceConsistency, multiple risk conditions)
 * - Fallback scenarios
 */

import {
  TimelineInterpretation
} from './interpretation.types';
import {
  PolicyResult
} from './policy.types';

// ============================================================
// STRONG_THESIS FIXTURES
// ============================================================

/**
 * STRONG_THESIS: All signals aligned with guidance consistency
 */
export const strongThesisInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

export const expectedStrongThesis: PolicyResult = {
  stance: 'STRONG_THESIS',
  confidence: 'HIGH'
};

/**
 * STRONG_THESIS with undefined guidance (short timeline < 3 entries)
 * 
 * This tests that undefined guidanceConsistency doesn't penalize STRONG_THESIS.
 */
export const strongThesisShortTimeline: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: undefined // < 3 entries
};

// ============================================================
// WEAKENING_THESIS FIXTURES
// ============================================================

/**
 * WEAKENING_THESIS: Slowing progress variant
 */
export const weakeningThesisSlowing: TimelineInterpretation = {
  trajectory: 'SLOWING_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

/**
 * WEAKENING_THESIS: Degrading guidance variant
 */
export const weakeningThesisDegrading: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'DEGRADING'
};

/**
 * WEAKENING_THESIS: Both slowing AND degrading
 * 
 * Still results in WEAKENING_THESIS with MEDIUM confidence
 * (not escalated to HIGH_RISK).
 */
export const weakeningThesisBoth: TimelineInterpretation = {
  trajectory: 'SLOWING_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'DEGRADING'
};

export const expectedWeakeningThesis: PolicyResult = {
  stance: 'WEAKENING_THESIS',
  confidence: 'MEDIUM'
};

// ============================================================
// HIGH_RISK_THESIS FIXTURES
// ============================================================

/**
 * HIGH_RISK_THESIS: Early weakening variant
 */
export const highRiskEarlyWeakening: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'EARLY_WEAKENING',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

/**
 * HIGH_RISK_THESIS: Repeated instability variant
 */
export const highRiskRepeatedInstability: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'REPEATED_INSTABILITY',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

/**
 * HIGH_RISK_THESIS: Flip-flop guidance variant
 */
export const highRiskFlipFlop: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'FLIP_FLOP'
};

/**
 * HIGH_RISK_THESIS: Stalled trajectory variant
 */
export const highRiskStalled: TimelineInterpretation = {
  trajectory: 'STALLED_TRAJECTORY',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

/**
 * HIGH_RISK_THESIS: Regressing progress variant (defensive case)
 */
export const highRiskRegressing: TimelineInterpretation = {
  trajectory: 'REGRESSING_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

/**
 * HIGH_RISK_THESIS: Multiple risk conditions
 * 
 * Even with multiple HIGH_RISK signals, confidence remains LOW
 * (no escalation beyond HIGH_RISK).
 */
export const highRiskMultipleConditions: TimelineInterpretation = {
  trajectory: 'STALLED_TRAJECTORY',
  stability: 'EARLY_WEAKENING',
  invalidationPattern: undefined,
  guidanceConsistency: 'FLIP_FLOP'
};

export const expectedHighRiskThesis: PolicyResult = {
  stance: 'HIGH_RISK_THESIS',
  confidence: 'LOW'
};

// ============================================================
// INVALID_THESIS FIXTURES
// ============================================================

/**
 * INVALID_THESIS: Terminated with invalidation pattern
 */
export const invalidThesisInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: 'MID_INVALIDATION',
  guidanceConsistency: 'CONSISTENT'
};

/**
 * INVALID_THESIS: Early invalidation variant
 */
export const invalidThesisEarly: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: 'EARLY_INVALIDATION',
  guidanceConsistency: 'CONSISTENT'
};

/**
 * INVALID_THESIS: Late invalidation variant
 */
export const invalidThesisLate: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: 'LATE_INVALIDATION',
  guidanceConsistency: 'CONSISTENT'
};

export const expectedInvalidThesis: PolicyResult = {
  stance: 'INVALID_THESIS',
  confidence: 'HIGH'
};

// ============================================================
// COMPLETED_THESIS FIXTURES
// ============================================================

/**
 * COMPLETED_THESIS: Terminated without invalidation pattern
 */
export const completedThesisInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: undefined, // no invalidation
  guidanceConsistency: 'CONSISTENT'
};

export const expectedCompletedThesis: PolicyResult = {
  stance: 'COMPLETED_THESIS',
  confidence: 'HIGH'
};

// ============================================================
// INSUFFICIENT_DATA FIXTURES
// ============================================================

/**
 * INSUFFICIENT_DATA: NO_DATA trajectory
 */
export const insufficientDataInterpretation: TimelineInterpretation = {
  trajectory: 'NO_DATA',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: undefined
};

export const expectedInsufficientData: PolicyResult = {
  stance: 'INSUFFICIENT_DATA',
  confidence: 'UNKNOWN'
};

// ============================================================
// FALLBACK SCENARIO FIXTURES
// ============================================================

/**
 * Fallback scenario: Mixed signals that don't fit standard patterns
 * 
 * Example reachable scenario:
 * - trajectory = 'STABLE_PROGRESS'
 * - stability = 'STRUCTURALLY_STABLE'
 * - guidanceConsistency = 'FLIP_FLOP'
 * 
 * Analysis:
 * - NOT STRONG (guidance flip-flop violates STRONG requirement)
 * - NOT WEAKENING (not slowing/degrading)
 * - NOT TERMINATED
 * - NOT HIGH_RISK (caught by Priority 5, but this demonstrates fallback logic)
 * 
 * Actually, this would be caught by HIGH_RISK (Priority 5) due to FLIP_FLOP.
 * True fallback would be an edge case we haven't anticipated.
 */
export const fallbackScenario: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'FLIP_FLOP'
};

export const expectedFallback: PolicyResult = {
  stance: 'HIGH_RISK_THESIS',
  confidence: 'LOW'
};

// ============================================================
// EDGE CASE FIXTURES
// ============================================================

/**
 * Edge case: Regressing trajectory (defensive signal, not invalid)
 * 
 * REGRESSING_PROGRESS is defensive (should never happen in practice)
 * but is treated as HIGH_RISK, NOT INVALID_THESIS.
 */
export const regressingTrajectory: TimelineInterpretation = {
  trajectory: 'REGRESSING_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

/**
 * Edge case: Completed with degrading guidance
 * 
 * TERMINATED always dominates, even with degrading signals.
 */
export const completedWithDegrading: TimelineInterpretation = {
  trajectory: 'SLOWING_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: undefined,
  guidanceConsistency: 'DEGRADING'
};

/**
 * Edge case: Invalidated with all good signals
 * 
 * TERMINATED always dominates, even with otherwise positive signals.
 */
export const invalidatedWithGoodSignals: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: 'MID_INVALIDATION',
  guidanceConsistency: 'CONSISTENT'
};

/**
 * Edge case: NO_DATA with other signals present
 * 
 * NO_DATA trajectory always results in INSUFFICIENT_DATA,
 * regardless of other signals.
 */
export const noDataWithOtherSignals: TimelineInterpretation = {
  trajectory: 'NO_DATA',
  stability: 'EARLY_WEAKENING',
  invalidationPattern: undefined,
  guidanceConsistency: 'FLIP_FLOP'
};
