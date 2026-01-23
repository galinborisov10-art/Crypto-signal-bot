/**
 * Phase 6.2: Policy Layer (Types & Semantics)
 * 
 * CRITICAL DISTINCTIONS:
 * 
 * Policy ≠ Decision
 * Policy ≠ Execution
 * Policy = Normative interpretation layer
 * 
 * Phase 6.2 translates pattern recognition (Phase 6.1) into an abstract
 * stance or position toward a trading idea.
 * 
 * This stance has OPINION but NOT ACTION.
 * 
 * Policy can be consumed by:
 * - UI layers (display idea status)
 * - Alerting systems (notify on stance changes)
 * - Reporting tools (aggregate idea quality)
 * - Future automation (Phase 6.3+ decision layers)
 * 
 * But Policy itself does NOT:
 * - Execute trades
 * - Manage positions
 * - Move stops
 * - Provide trading instructions
 * - Analyze market data
 * 
 * Policy is the bridge between observation and (future) decision,
 * but it remains on the observational side of that boundary.
 */

import {
  TrajectorySignal,
  StabilitySignal,
  InvalidationPattern,
  GuidanceConsistency
} from './interpretation.types';

/**
 * Policy stance represents the normative interpretation of a trading idea
 * based on observed patterns and signals.
 * 
 * This is NOT an action or decision.
 * This is an abstract position toward the idea's validity and strength.
 * 
 * Policy stance can be used by:
 * - UI layers
 * - Alerting systems
 * - Reporting tools
 * - Future automation
 * 
 * But the stance itself does NOT execute or manage positions.
 */
export type PolicyStance =
  | 'STRONG_THESIS'        // All signals aligned, high-stability idea
  | 'WEAKENING_THESIS'     // Valid but degrading idea
  | 'HIGH_RISK_THESIS'     // Conflicting/unstable patterns
  | 'INVALID_THESIS'       // Invalidated idea (derived, not execution)
  | 'COMPLETED_THESIS'     // Completed idea (terminal, no further policy)
  | 'INSUFFICIENT_DATA';   // Not enough observations

/**
 * Policy confidence represents the strength of the policy stance
 * based on signal consistency and pattern clarity.
 * 
 * This is NOT a probability.
 * This is NOT a performance metric.
 * 
 * Confidence reflects:
 * - Signal alignment
 * - Pattern consistency
 * - Observation sufficiency
 */
export type PolicyConfidence =
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'UNKNOWN';

/**
 * Policy context is the aggregated interpretation from Phase 6.1.
 * 
 * Policy layer does NOT have direct access to:
 * - Timeline entries
 * - Price data
 * - POIs
 * - Market state
 * 
 * Policy sees only the interpreted patterns, not the raw observations.
 */
export interface PolicyContext {
  trajectory: TrajectorySignal;
  stability: StabilitySignal;
  invalidationPattern?: InvalidationPattern;
  guidanceConsistency?: GuidanceConsistency;
}

/**
 * Policy result represents the normative interpretation of a trading idea.
 * 
 * This is NOT a decision.
 * This is NOT an execution instruction.
 * 
 * Policy result can inform:
 * - User interface displays
 * - Alert generation
 * - Report generation
 * - Future decision layers (Phase 6.3+)
 * 
 * But the result itself does NOT cause execution or position management.
 */
export interface PolicyResult {
  stance: PolicyStance;
  confidence: PolicyConfidence;
}
