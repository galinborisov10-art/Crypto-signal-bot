/**
 * Interpretation Test Fixtures - Phase 6.1: Timeline Interpretation Engine
 * 
 * Provides reusable test data for interpretation pattern recognition.
 * All fixtures are semantic and implementation-agnostic.
 */

import { VirtualPositionTimeline } from './timeline.types';
import { TimelineInterpretation } from './interpretation.types';

// ============================================================
// EMPTY / INSUFFICIENT DATA TIMELINES
// ============================================================

/**
 * Empty timeline (< 2 entries)
 * Expected: trajectory = NO_DATA
 */
export const emptyTimelineForInterpretation: VirtualPositionTimeline = {
  positionId: 'pos-empty',
  entries: []
};

/**
 * Single entry timeline (< 2 entries)
 * Expected: trajectory = NO_DATA
 */
export const singleEntryTimeline: VirtualPositionTimeline = {
  positionId: 'pos-single',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    }
  ]
};

// ============================================================
// TRAJECTORY PATTERNS
// ============================================================

/**
 * Stable progress timeline
 * Deltas: +25, +25, +25 (all positive, majority positive)
 * Expected: trajectory = STABLE_PROGRESS
 */
export const stableProgressTimeline: VirtualPositionTimeline = {
  positionId: 'pos-stable',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 25,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 50,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 4000,
      progressPercent: 75,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

/**
 * Slowing progress timeline
 * Deltas: +30, +20, +10 (all positive but shrinking magnitude)
 * Expected: trajectory = SLOWING_PROGRESS
 */
export const slowingProgressTimeline: VirtualPositionTimeline = {
  positionId: 'pos-slowing',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 30,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 50,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 4000,
      progressPercent: 60,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

/**
 * Stalled trajectory timeline
 * Deltas: 0, 0 (all deltas ≈ 0)
 * Expected: trajectory = STALLED_TRAJECTORY
 */
export const stalledTrajectoryTimeline: VirtualPositionTimeline = {
  positionId: 'pos-stalled-traj',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 25,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 25,
      status: 'stalled',
      validity: 'still_valid',
      guidance: 'THESIS_WEAKENING'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 25,
      status: 'stalled',
      validity: 'still_valid',
      guidance: 'THESIS_WEAKENING'
    }
  ]
};

/**
 * Regressing progress timeline (defensive case, should never happen)
 * Deltas: +25, -10 (has negative delta)
 * Expected: trajectory = REGRESSING_PROGRESS
 */
export const regressingProgressTimeline: VirtualPositionTimeline = {
  positionId: 'pos-regressing',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 25,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 15, // Regression (should never happen)
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

// ============================================================
// STABILITY PATTERNS
// ============================================================

/**
 * Completed timeline (terminal state)
 * Expected: stability = TERMINATED
 */
export const completedTimeline: VirtualPositionTimeline = {
  positionId: 'pos-completed',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 50,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 100,
      status: 'completed',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

/**
 * Invalidated timeline (terminal state)
 * Expected: stability = TERMINATED
 */
export const invalidatedTimeline: VirtualPositionTimeline = {
  positionId: 'pos-invalidated',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 30,
      status: 'progressing',
      validity: 'invalidated',
      invalidationReason: 'STRUCTURE_BROKEN',
      guidance: 'STRUCTURE_AT_RISK'
    }
  ]
};

/**
 * Repeated instability timeline (≥ 2 stalled entries)
 * Expected: stability = REPEATED_INSTABILITY
 */
export const repeatedInstabilityTimeline: VirtualPositionTimeline = {
  positionId: 'pos-repeated',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 25,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 25,
      status: 'stalled',
      validity: 'still_valid',
      guidance: 'THESIS_WEAKENING'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 30,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 4000,
      progressPercent: 30,
      status: 'stalled',
      validity: 'still_valid',
      guidance: 'THESIS_WEAKENING'
    }
  ]
};

/**
 * Early weakening timeline (stalled before 25% progress)
 * Expected: stability = EARLY_WEAKENING
 */
export const earlyWeakeningTimeline: VirtualPositionTimeline = {
  positionId: 'pos-early-weak',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 15,
      status: 'stalled',
      validity: 'still_valid',
      guidance: 'THESIS_WEAKENING'
    }
  ]
};

/**
 * Structurally stable timeline (no issues)
 * Expected: stability = STRUCTURALLY_STABLE
 */
export const structurallyStableTimeline: VirtualPositionTimeline = {
  positionId: 'pos-stable-struct',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 30,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 60,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

// ============================================================
// INVALIDATION PATTERN TESTS
// ============================================================

/**
 * Early invalidation timeline (< 25% progress)
 * Expected: invalidationPattern = EARLY_INVALIDATION
 */
export const earlyInvalidationTimeline: VirtualPositionTimeline = {
  positionId: 'pos-early-inval',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 15,
      status: 'progressing',
      validity: 'invalidated',
      invalidationReason: 'STRUCTURE_BROKEN',
      guidance: 'STRUCTURE_AT_RISK'
    }
  ]
};

/**
 * Mid invalidation timeline (25 ≤ progress < 75)
 * Expected: invalidationPattern = MID_INVALIDATION
 */
export const midInvalidationTimeline: VirtualPositionTimeline = {
  positionId: 'pos-mid-inval',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 50,
      status: 'progressing',
      validity: 'invalidated',
      invalidationReason: 'POI_INVALIDATED',
      guidance: 'STRUCTURE_AT_RISK'
    }
  ]
};

/**
 * Late invalidation timeline (≥ 75% progress)
 * Expected: invalidationPattern = LATE_INVALIDATION
 */
export const lateInvalidationTimeline: VirtualPositionTimeline = {
  positionId: 'pos-late-inval',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 80,
      status: 'progressing',
      validity: 'invalidated',
      invalidationReason: 'TIME_DECAY_EXCEEDED',
      guidance: 'STRUCTURE_AT_RISK'
    }
  ]
};

/**
 * No invalidation timeline
 * Expected: invalidationPattern = undefined
 */
export const noInvalidationTimeline: VirtualPositionTimeline = {
  positionId: 'pos-no-inval',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 50,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

// ============================================================
// GUIDANCE CONSISTENCY PATTERNS
// ============================================================

/**
 * Flip-flop guidance timeline (A → B → A pattern)
 * Pattern: HOLD → WEAK → HOLD
 * Expected: guidanceConsistency = FLIP_FLOP
 */
export const flipFlopGuidanceTimeline: VirtualPositionTimeline = {
  positionId: 'pos-flip-flop',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 20,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 25,
      status: 'stalled',
      validity: 'still_valid',
      guidance: 'THESIS_WEAKENING'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 30,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

/**
 * Degrading guidance timeline (net movement to weaker)
 * Pattern: HOLD → WAIT → WEAK (strength: 4 → 3 → 2, no recovery)
 * Expected: guidanceConsistency = DEGRADING
 */
export const degradingGuidanceTimeline: VirtualPositionTimeline = {
  positionId: 'pos-degrading',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 10,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 20,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 25,
      status: 'stalled',
      validity: 'still_valid',
      guidance: 'THESIS_WEAKENING'
    }
  ]
};

/**
 * Consistent guidance timeline (no flip-flop, no degradation)
 * Pattern: WAIT → HOLD → HOLD (strength: 3 → 4 → 4, improving/stable)
 * Expected: guidanceConsistency = CONSISTENT
 */
export const consistentGuidanceTimeline: VirtualPositionTimeline = {
  positionId: 'pos-consistent',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 20,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 40,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    },
    {
      evaluatedAt: 3000,
      progressPercent: 60,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

/**
 * Insufficient entries for guidance consistency (< 3 entries)
 * Expected: guidanceConsistency = undefined
 */
export const insufficientGuidanceTimeline: VirtualPositionTimeline = {
  positionId: 'pos-insufficient-guidance',
  entries: [
    {
      evaluatedAt: 1000,
      progressPercent: 0,
      status: 'open',
      validity: 'still_valid',
      guidance: 'WAIT_FOR_CONFIRMATION'
    },
    {
      evaluatedAt: 2000,
      progressPercent: 30,
      status: 'progressing',
      validity: 'still_valid',
      guidance: 'HOLD_THESIS'
    }
  ]
};

// ============================================================
// EXPECTED INTERPRETATION RESULTS
// ============================================================

export const expectedEmptyInterpretation: TimelineInterpretation = {
  trajectory: 'NO_DATA',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: undefined
};

export const expectedStableInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

export const expectedSlowingInterpretation: TimelineInterpretation = {
  trajectory: 'SLOWING_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

export const expectedStalledTrajectoryInterpretation: TimelineInterpretation = {
  trajectory: 'STALLED_TRAJECTORY',
  stability: 'REPEATED_INSTABILITY',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

export const expectedRegressingInterpretation: TimelineInterpretation = {
  trajectory: 'REGRESSING_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

export const expectedCompletedInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};

export const expectedInvalidatedInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: 'MID_INVALIDATION',
  guidanceConsistency: undefined
};

export const expectedRepeatedInstabilityInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'REPEATED_INSTABILITY',
  invalidationPattern: undefined,
  guidanceConsistency: 'FLIP_FLOP'
};

export const expectedEarlyWeakeningInterpretation: TimelineInterpretation = {
  trajectory: 'STALLED_TRAJECTORY',
  stability: 'EARLY_WEAKENING',
  invalidationPattern: undefined,
  guidanceConsistency: undefined
};

export const expectedEarlyInvalidationInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: 'EARLY_INVALIDATION',
  guidanceConsistency: undefined
};

export const expectedMidInvalidationInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: 'MID_INVALIDATION',
  guidanceConsistency: undefined
};

export const expectedLateInvalidationInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'TERMINATED',
  invalidationPattern: 'LATE_INVALIDATION',
  guidanceConsistency: undefined
};

export const expectedFlipFlopInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'REPEATED_INSTABILITY',
  invalidationPattern: undefined,
  guidanceConsistency: 'FLIP_FLOP'
};

export const expectedDegradingInterpretation: TimelineInterpretation = {
  trajectory: 'SLOWING_PROGRESS',
  stability: 'EARLY_WEAKENING',
  invalidationPattern: undefined,
  guidanceConsistency: 'DEGRADING'
};

export const expectedConsistentInterpretation: TimelineInterpretation = {
  trajectory: 'STABLE_PROGRESS',
  stability: 'STRUCTURALLY_STABLE',
  invalidationPattern: undefined,
  guidanceConsistency: 'CONSISTENT'
};
