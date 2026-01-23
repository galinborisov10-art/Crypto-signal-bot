/**
 * Interpretation Type System - Phase 6.1: Timeline Interpretation Engine
 * 
 * Defines types for timeline pattern recognition and temporal analysis.
 * This phase answers ONLY: "What pattern emerges from this idea over time?"
 * 
 * This file contains ONLY type definitions - no logic or implementation.
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
 * Timeline Interpretation is READ-ONLY PATTERN RECOGNITION ONLY.
 */

/**
 * Trajectory Signal
 * 
 * Architecture Decision: Majority-based delta analysis
 * 
 * Represents the directional pattern of progress over time.
 * Analyzes sequential deltas between progress measurements.
 * 
 * Signal Semantics:
 * - NO_DATA: < 2 entries (cannot compute deltas)
 * - STABLE_PROGRESS: Majority of deltas are positive
 * - SLOWING_PROGRESS: All deltas positive but shrinking magnitude
 * - STALLED_TRAJECTORY: Progress flat (deltas ≈ 0)
 * - REGRESSING_PROGRESS: Progress decreased (defensive, should never happen)
 * 
 * These signals are FROZEN for ESB v1.0 after merge.
 */
export type TrajectorySignal =
  | 'NO_DATA'               // < 2 entries
  | 'STABLE_PROGRESS'       // majority of deltas positive
  | 'SLOWING_PROGRESS'      // positive deltas but shrinking magnitude
  | 'STALLED_TRAJECTORY'    // progress flat (deltas ≈ 0)
  | 'REGRESSING_PROGRESS';  // progress decreasing (defensive, should never happen)

/**
 * Stability Signal
 * 
 * Architecture Decision: Status and guidance pattern analysis
 * 
 * Represents the structural stability of a Virtual Position over time.
 * Analyzes status patterns and early weakening indicators.
 * 
 * Signal Semantics (Priority Cascade):
 * - TERMINATED: Any completed OR invalidated entry (always dominates)
 * - REPEATED_INSTABILITY: ≥ 2 stalled entries (anywhere in timeline)
 * - EARLY_WEAKENING: Stalled or weakening before 25% progress
 * - STRUCTURALLY_STABLE: Default if no other condition met
 * 
 * These signals are FROZEN for ESB v1.0 after merge.
 */
export type StabilitySignal =
  | 'STRUCTURALLY_STABLE'
  | 'EARLY_WEAKENING'        // early stall/weakening (< 25% progress)
  | 'REPEATED_INSTABILITY'   // ≥ 2 stalled entries
  | 'TERMINATED';            // completed OR invalidated

/**
 * Invalidation Pattern
 * 
 * Architecture Decision: First invalidation only
 * 
 * Classifies when invalidation occurred relative to progress.
 * Only present if ANY entry has validity === 'invalidated'.
 * Uses FIRST invalidation only (most semantically important).
 * 
 * Pattern Classification:
 * - EARLY_INVALIDATION: progressPercent < 25
 * - MID_INVALIDATION: 25 ≤ progressPercent < 75
 * - LATE_INVALIDATION: progressPercent ≥ 75
 * 
 * These patterns are FROZEN for ESB v1.0 after merge.
 */
export type InvalidationPattern =
  | 'EARLY_INVALIDATION'   // progressPercent < 25
  | 'MID_INVALIDATION'     // 25 ≤ progressPercent < 75
  | 'LATE_INVALIDATION';   // progressPercent ≥ 75

/**
 * Guidance Consistency
 * 
 * Architecture Decision: Flip-flop pattern and degradation detection
 * 
 * Analyzes how guidance signals change over time.
 * Only present if ≥ 3 entries (need transitions to analyze).
 * 
 * Signal Strength Order (CANONICAL):
 * HOLD_THESIS (strongest)
 *   > WAIT_FOR_CONFIRMATION
 *   > THESIS_WEAKENING
 *   > STRUCTURE_AT_RISK (weakest)
 * 
 * Pattern Semantics:
 * - FLIP_FLOP: Actual oscillation pattern (A → B → A)
 * - DEGRADING: Net movement to weaker signals without recovery
 * - CONSISTENT: No flip-flop, no degradation
 * 
 * These patterns are FROZEN for ESB v1.0 after merge.
 */
export type GuidanceConsistency =
  | 'CONSISTENT'
  | 'FLIP_FLOP'     // oscillation pattern (A → B → A)
  | 'DEGRADING';    // net movement toward weaker signals

/**
 * Timeline Interpretation
 * 
 * Architecture Decision: Machine-readable enums ONLY (no free text)
 * 
 * Aggregates all pattern recognition results for a timeline.
 * All outputs are machine-readable enums for deterministic handling.
 * 
 * Field Presence Rules:
 * - trajectory: Always present
 * - stability: Always present
 * - invalidationPattern: Only present if invalidation occurred
 * - guidanceConsistency: Only present if ≥ 3 entries
 * 
 * This is a pure output type - no logic, just aggregated patterns.
 */
export interface TimelineInterpretation {
  /** Trajectory pattern (based on progress deltas) */
  trajectory: TrajectorySignal;
  
  /** Stability pattern (based on status and guidance) */
  stability: StabilitySignal;
  
  /** Invalidation timing pattern (optional, first invalidation only) */
  invalidationPattern?: InvalidationPattern;
  
  /** Guidance signal consistency pattern (optional, requires ≥ 3 entries) */
  guidanceConsistency?: GuidanceConsistency;
}
