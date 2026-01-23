/**
 * Interpretation Contracts - Phase 6.1: Timeline Interpretation Engine
 * 
 * Implements pure, deterministic pattern recognition over timeline data.
 * This phase answers ONLY: "What pattern emerges from this idea over time?"
 * 
 * HARD CONSTRAINTS:
 * ❌ NO decisions
 * ❌ NO recommendations
 * ❌ NO position management
 * ❌ NO market analysis
 * ❌ NO mutation of timeline or entries
 * ❌ NO randomness or Date.now()
 * ❌ NO side effects
 * 
 * All functions are pure and deterministic.
 */

import { VirtualPositionTimeline } from './timeline.types';
import { GuidanceSignal } from './guidance.types';
import {
  TrajectorySignal,
  StabilitySignal,
  InvalidationPattern,
  GuidanceConsistency,
  TimelineInterpretation
} from './interpretation.types';

/**
 * Analyze Trajectory
 * 
 * Architecture Decision: Majority-based delta analysis
 * 
 * Analyzes progress trajectory by examining sequential deltas.
 * Uses majority voting for stable vs stalled detection.
 * 
 * Logic:
 * 1. < 2 entries → NO_DATA
 * 2. Any negative delta → REGRESSING_PROGRESS (defensive)
 * 3. All deltas ≈ 0 → STALLED_TRAJECTORY
 * 4. All positive but shrinking → SLOWING_PROGRESS
 * 5. Majority positive → STABLE_PROGRESS
 * 6. Default → STALLED_TRAJECTORY
 * 
 * @param entries - Timeline entries (readonly)
 * @returns Trajectory signal
 */
function analyzeTrajectory(entries: readonly TimelineEntry[]): TrajectorySignal {
  // Need at least 2 entries to compute deltas
  if (entries.length < 2) {
    return 'NO_DATA';
  }

  // Calculate deltas between sequential entries
  const deltas: number[] = [];
  for (let i = 1; i < entries.length; i++) {
    deltas.push(entries[i].progressPercent - entries[i - 1].progressPercent);
  }

  // Check for regression (should never happen if Phase 5.2 invariants hold)
  if (deltas.some(d => d < 0)) {
    // Should never happen if Phase 5.2 invariants hold
    return 'REGRESSING_PROGRESS';
  }

  // Define stall threshold (small epsilon for floating point comparison)
  const STALL_THRESHOLD = 0.1;

  // Check for stalled (all deltas ≈ 0)
  if (deltas.every(d => Math.abs(d) < STALL_THRESHOLD)) {
    return 'STALLED_TRAJECTORY';
  }

  // Check for slowing (all positive but shrinking magnitude)
  const allPositive = deltas.every(d => d > STALL_THRESHOLD);
  if (allPositive) {
    let hasShrinking = false;
    for (let i = 1; i < deltas.length; i++) {
      if (deltas[i] < deltas[i - 1]) {
        hasShrinking = true;
        break;
      }
    }
    if (hasShrinking) {
      return 'SLOWING_PROGRESS';
    }
  }

  // Majority positive → stable progress
  const positiveCount = deltas.filter(d => d > STALL_THRESHOLD).length;
  if (positiveCount > deltas.length / 2) {
    return 'STABLE_PROGRESS';
  }

  // Default: stalled
  return 'STALLED_TRAJECTORY';
}

/**
 * Analyze Stability
 * 
 * Architecture Decision: Status and guidance pattern analysis
 * 
 * Analyzes structural stability using priority cascade.
 * Priority: TERMINATED > REPEATED_INSTABILITY > EARLY_WEAKENING > STABLE
 * 
 * Logic:
 * 1. Any completed or invalidated → TERMINATED
 * 2. ≥ 2 stalled entries → REPEATED_INSTABILITY
 * 3. Any stalled or weakening before 25% → EARLY_WEAKENING
 * 4. Default → STRUCTURALLY_STABLE
 * 
 * @param entries - Timeline entries (readonly)
 * @returns Stability signal
 */
function analyzeStability(entries: readonly TimelineEntry[]): StabilitySignal {
  // Need at least 2 entries for meaningful stability analysis
  if (entries.length < 2) {
    return 'STRUCTURALLY_STABLE'; // not enough data, assume stable
  }

  // Priority 1: TERMINATED (completed OR invalidated)
  const hasCompleted = entries.some(e => e.status === 'completed');
  const hasInvalidated = entries.some(e => e.validity === 'invalidated');
  if (hasCompleted || hasInvalidated) {
    return 'TERMINATED';
  }

  // Priority 2: REPEATED_INSTABILITY (≥ 2 stalled)
  const stalledCount = entries.filter(e => e.status === 'stalled').length;
  if (stalledCount >= 2) {
    return 'REPEATED_INSTABILITY';
  }

  // Priority 3: EARLY_WEAKENING (stalled or weakening before 25%)
  const hasEarlyWeakening = entries.some(
    e =>
      e.progressPercent < 25 &&
      (e.status === 'stalled' || e.guidance === 'THESIS_WEAKENING')
  );
  if (hasEarlyWeakening) {
    return 'EARLY_WEAKENING';
  }

  // Default: stable
  return 'STRUCTURALLY_STABLE';
}

/**
 * Analyze Invalidation Pattern
 * 
 * Architecture Decision: First invalidation only
 * 
 * Classifies when invalidation occurred based on progress.
 * Only returns value if invalidation exists.
 * Uses first invalidation (most semantically important).
 * 
 * Logic:
 * 1. No invalidation → undefined
 * 2. First invalidation < 25% → EARLY_INVALIDATION
 * 3. First invalidation < 75% → MID_INVALIDATION
 * 4. First invalidation ≥ 75% → LATE_INVALIDATION
 * 
 * @param entries - Timeline entries (readonly)
 * @returns Invalidation pattern or undefined
 */
function analyzeInvalidationPattern(
  entries: readonly TimelineEntry[]
): InvalidationPattern | undefined {
  // Find FIRST invalidation
  const invalidatedEntry = entries.find(e => e.validity === 'invalidated');

  if (!invalidatedEntry) {
    return undefined;
  }

  const progress = invalidatedEntry.progressPercent;

  if (progress < 25) return 'EARLY_INVALIDATION';
  if (progress < 75) return 'MID_INVALIDATION';
  return 'LATE_INVALIDATION';
}

/**
 * Analyze Guidance Consistency
 * 
 * Architecture Decision: Flip-flop pattern and degradation detection
 * 
 * Analyzes how guidance signals change over time.
 * Detects oscillation patterns and net degradation.
 * 
 * Signal Strength Order:
 * HOLD_THESIS (4) > WAIT_FOR_CONFIRMATION (3) > THESIS_WEAKENING (2) > STRUCTURE_AT_RISK (1)
 * 
 * Logic:
 * 1. < 3 entries → undefined (need transitions)
 * 2. Flip-flop pattern (A → B → A) → FLIP_FLOP
 * 3. Net movement to weaker without recovery → DEGRADING
 * 4. Default → CONSISTENT
 * 
 * @param entries - Timeline entries (readonly)
 * @returns Guidance consistency or undefined
 */
function analyzeGuidanceConsistency(
  entries: readonly TimelineEntry[]
): GuidanceConsistency | undefined {
  // Need ≥ 3 entries to analyze transitions
  if (entries.length < 3) {
    return undefined;
  }

  const signals = entries.map(e => e.guidance);

  // Check for flip-flop (A → B → A pattern)
  let hasFlipFlop = false;
  for (let i = 2; i < signals.length; i++) {
    if (signals[i] === signals[i - 2] && signals[i] !== signals[i - 1]) {
      hasFlipFlop = true;
      break;
    }
  }
  if (hasFlipFlop) {
    return 'FLIP_FLOP';
  }

  // Check for degradation (net movement to weaker)
  const signalStrength: Record<GuidanceSignal, number> = {
    HOLD_THESIS: 4,
    WAIT_FOR_CONFIRMATION: 3,
    THESIS_WEAKENING: 2,
    STRUCTURE_AT_RISK: 1
  };

  const firstStrength = signalStrength[signals[0]];
  const lastStrength = signalStrength[signals[signals.length - 1]];

  // Check if net movement is downward
  if (lastStrength < firstStrength) {
    // Check if there's no recovery (flip-flop back up)
    let hasRecovery = false;
    for (let i = 1; i < signals.length; i++) {
      if (signalStrength[signals[i]] > signalStrength[signals[i - 1]]) {
        hasRecovery = true;
        break;
      }
    }
    if (!hasRecovery) {
      return 'DEGRADING';
    }
  }

  return 'CONSISTENT';
}

/**
 * Interpret Timeline
 * 
 * Architecture Decision: Pure, deterministic pattern recognition
 * 
 * Main entry point for timeline interpretation.
 * Aggregates all pattern recognition results.
 * 
 * Function Semantics:
 * - Pure (no side effects)
 * - Deterministic (same inputs → same output)
 * - Read-only (no mutations)
 * - Always succeeds (uses NO_DATA for insufficient data)
 * 
 * Mental Model:
 * > "Brain without will"
 * > Observes patterns, does NOT act on them.
 * 
 * @param timeline - Virtual Position timeline to interpret
 * @returns Timeline interpretation with all recognized patterns
 */
export function interpretTimeline(
  timeline: VirtualPositionTimeline
): TimelineInterpretation {
  const entries = timeline.entries;

  return {
    trajectory: analyzeTrajectory(entries),
    stability: analyzeStability(entries),
    invalidationPattern: analyzeInvalidationPattern(entries),
    guidanceConsistency: analyzeGuidanceConsistency(entries)
  };
}

// Re-export TimelineEntry for convenience (used in helper functions)
import { TimelineEntry } from './timeline.types';
