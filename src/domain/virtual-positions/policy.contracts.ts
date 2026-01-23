/**
 * Policy Derivation Engine - Phase 6.2.2: Policy Derivation
 * 
 * Implements pure, deterministic normative interpretation layer.
 * Translates TimelineInterpretation (Phase 6.1) → PolicyResult (Phase 6.2.1).
 * 
 * CRITICAL DISTINCTIONS:
 * 
 * Policy ≠ Decision
 * Policy ≠ Execution
 * Policy = Opinion without will
 * 
 * This layer answers ONLY:
 * "What is the normative stance toward this idea?"
 * 
 * NOT:
 * "What should we do?"
 * 
 * HARD CONSTRAINTS:
 * ❌ NO decisions
 * ❌ NO recommendations
 * ❌ NO position management
 * ❌ NO timeline/price/POI access
 * ❌ NO mutation
 * ❌ NO randomness or Date.now()
 * ❌ NO side effects
 * ❌ NO string literals outside enums
 * 
 * Policy can inform:
 * - UI displays
 * - Alerting systems
 * - Reporting tools
 * - Future decision layers (Phase 6.3+)
 * 
 * But policy itself does NOT cause execution or position management.
 */

import { TimelineInterpretation } from './interpretation.types';
import { PolicyResult } from './policy.types';

/**
 * Derives policy stance and confidence from timeline interpretation.
 * 
 * This is a pure, deterministic normative interpretation layer.
 * 
 * Policy = Opinion without will
 * 
 * This function does NOT:
 * - Make decisions
 * - Provide recommendations
 * - Manage positions
 * - Access raw timeline data
 * - Access price/POI/market data
 * 
 * Policy can inform:
 * - UI displays
 * - Alerting systems
 * - Reporting tools
 * - Future decision layers (Phase 6.3+)
 * 
 * But policy itself does NOT cause execution or position management.
 * 
 * CANONICAL POLICY LOGIC (FROZEN FOR ESB v1.0):
 * 
 * Priority Cascade (STRICT ORDER):
 * 1. TERMINATED (invalidated vs completed)
 * 2. NO_DATA (insufficient observations)
 * 3. STRONG_THESIS (all signals aligned)
 * 4. WEAKENING_THESIS (controlled degradation)
 * 5. HIGH_RISK_THESIS (instability signals)
 * 6. Fallback (unclassifiable → HIGH_RISK_THESIS)
 * 
 * Fixed Confidence Mapping:
 * - STRONG_THESIS → HIGH
 * - WEAKENING_THESIS → MEDIUM
 * - HIGH_RISK_THESIS → LOW
 * - INVALID_THESIS → HIGH
 * - COMPLETED_THESIS → HIGH
 * - INSUFFICIENT_DATA → UNKNOWN
 * 
 * @param interpretation - Timeline interpretation from Phase 6.1
 * @returns PolicyResult with stance and confidence
 */
export function derivePolicy(
  interpretation: TimelineInterpretation
): PolicyResult {
  
  // ============================================================
  // Priority 1: TERMINATED (completed or invalidated)
  // ============================================================
  
  if (interpretation.stability === 'TERMINATED') {
    // Disambiguate: invalidated vs completed
    if (interpretation.invalidationPattern !== undefined) {
      return {
        stance: 'INVALID_THESIS',
        confidence: 'HIGH'
      };
    }
    return {
      stance: 'COMPLETED_THESIS',
      confidence: 'HIGH'
    };
  }
  
  // ============================================================
  // Priority 2: NO_DATA (insufficient observations)
  // ============================================================
  
  if (interpretation.trajectory === 'NO_DATA') {
    return {
      stance: 'INSUFFICIENT_DATA',
      confidence: 'UNKNOWN'
    };
  }
  
  // ============================================================
  // Priority 3: STRONG_THESIS (all signals aligned)
  // ============================================================
  
  // Strict AND logic: ALL conditions required
  if (
    interpretation.trajectory === 'STABLE_PROGRESS' &&
    interpretation.stability === 'STRUCTURALLY_STABLE' &&
    (interpretation.guidanceConsistency === 'CONSISTENT' || 
     interpretation.guidanceConsistency === undefined) &&
    interpretation.invalidationPattern === undefined
  ) {
    return {
      stance: 'STRONG_THESIS',
      confidence: 'HIGH'
    };
  }
  
  // ============================================================
  // Priority 4: WEAKENING_THESIS (controlled degradation)
  // ============================================================
  
  // OR logic: EITHER condition triggers
  if (
    interpretation.trajectory === 'SLOWING_PROGRESS' ||
    interpretation.guidanceConsistency === 'DEGRADING'
  ) {
    return {
      stance: 'WEAKENING_THESIS',
      confidence: 'MEDIUM'
    };
  }
  
  // ============================================================
  // Priority 5: HIGH_RISK_THESIS (instability signals)
  // ============================================================
  
  // ANY condition triggers HIGH_RISK
  if (
    interpretation.stability === 'EARLY_WEAKENING' ||
    interpretation.stability === 'REPEATED_INSTABILITY' ||
    interpretation.guidanceConsistency === 'FLIP_FLOP' ||
    interpretation.trajectory === 'STALLED_TRAJECTORY' ||
    interpretation.trajectory === 'REGRESSING_PROGRESS'
  ) {
    return {
      stance: 'HIGH_RISK_THESIS',
      confidence: 'LOW'
    };
  }
  
  // ============================================================
  // Priority 6: Fallback (unclassifiable but valid risk)
  // ============================================================
  
  // Fallback ≠ error
  // Fallback = unclassifiable, but valid risk
  // Example reachable scenario:
  //   trajectory = 'STABLE_PROGRESS'
  //   stability = 'STRUCTURALLY_STABLE'
  //   guidanceConsistency = 'FLIP_FLOP'
  //   → NOT STRONG (guidance flip-flop violates requirement)
  //   → NOT WEAKENING (not slowing/degrading)
  //   → NOT TERMINATED
  //   → Fallback → HIGH_RISK_THESIS
  return {
    stance: 'HIGH_RISK_THESIS',
    confidence: 'LOW'
  };
}
