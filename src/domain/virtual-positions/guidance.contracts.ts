/**
 * Guidance Contracts - Phase 5.4: Guidance Layer / Narrative Signals
 * 
 * Core function for deriving guidance signals from Virtual Position state.
 * This phase answers ONLY: "How does this idea currently look from an analytical perspective?"
 * 
 * HARD CONSTRAINTS:
 * ❌ NO decisions
 * ❌ NO position management
 * ❌ NO execution logic
 * ❌ NO trade management suggestions
 * ❌ NO market analysis
 * ❌ NO price logic
 * ❌ NO mutation of VirtualPosition
 * ❌ NO Date.now() or randomness
 * 
 * This function is PURE and DETERMINISTIC.
 * Same inputs ALWAYS produce same output.
 * No side effects. No mutations. Always succeeds.
 */

import { VirtualPosition } from './virtualPosition.types';
import { ReanalysisResult } from './reanalysis.types';
import { GuidanceResult } from './guidance.types';

/**
 * Derive Guidance Signal
 * 
 * Architecture Decision: Strict priority cascade
 * 
 * Aggregates progress, status, and validity into observational context.
 * Returns a guidance signal representing the current analytical posture.
 * 
 * Priority Order (EXACT):
 * 1. Completed positions (terminal state) → HOLD_THESIS
 * 2. Invalidated (always dominates) → STRUCTURE_AT_RISK
 * 3. Stalled (always weakening, regardless of progress) → THESIS_WEAKENING
 * 4. Progress < 25% → WAIT_FOR_CONFIRMATION
 * 5. Default: Healthy thesis → HOLD_THESIS
 * 
 * Progress Thresholds (left-inclusive, right-exclusive):
 * - progress < 25: Early stage → WAIT_FOR_CONFIRMATION
 * - 25 ≤ progress < 75: Healthy progression → HOLD_THESIS
 * - ≥ 75: Near completion → HOLD_THESIS
 * 
 * Status Semantics:
 * - Status does NOT block progress semantics
 * - 'progressing' does NOT override progress thresholds
 * - 'stalled' ALWAYS means weakening (regardless of progress: 30%, 60%, 80%)
 * 
 * @param position - Virtual Position to evaluate (immutable)
 * @param reanalysisResult - Re-analysis result from Phase 5.3 (immutable)
 * @returns GuidanceResult - Aggregated observational context
 * 
 * @invariants
 * - Deterministic: Same inputs → same output
 * - No mutation: Inputs unchanged
 * - No side effects: Pure function
 * - Always succeeds: Inputs pre-validated by Phase 5.1–5.3
 * 
 * @example
 * ```typescript
 * const position = updateVirtualPositionProgress(...);
 * const reanalysisResult = reanalyzeVirtualPosition(...);
 * const guidance = deriveGuidance(position, reanalysisResult);
 * // { signal: 'HOLD_THESIS', progressPercent: 50, status: 'progressing', validity: 'still_valid' }
 * ```
 */
export function deriveGuidance(
  position: VirtualPosition,
  reanalysisResult: ReanalysisResult
): GuidanceResult {
  const progress = position.progressPercent;
  const status = position.status;
  const validity = reanalysisResult.status;
  
  // Priority 1: Completed positions (terminal state)
  // Completed always returns HOLD_THESIS regardless of validity
  if (status === 'completed') {
    return {
      signal: 'HOLD_THESIS',
      progressPercent: progress,
      status,
      validity
    };
  }
  
  // Priority 2: Invalidated (always dominates unless completed)
  // Any invalidation means structure is at risk
  if (validity === 'invalidated') {
    return {
      signal: 'STRUCTURE_AT_RISK',
      progressPercent: progress,
      status,
      validity
    };
  }
  
  // Priority 3: Stalled (always weakening, regardless of progress)
  // Stalled at 30%, 60%, or 80% all return THESIS_WEAKENING
  if (status === 'stalled') {
    return {
      signal: 'THESIS_WEAKENING',
      progressPercent: progress,
      status,
      validity: 'still_valid'
    };
  }
  
  // Priority 4: Progress-based thresholds
  // Early stage positions need more confirmation
  if (progress < 25) {
    return {
      signal: 'WAIT_FOR_CONFIRMATION',
      progressPercent: progress,
      status,
      validity: 'still_valid'
    };
  }
  
  // Default: Healthy thesis
  // Progress >= 25%, not stalled, not invalidated, not completed
  return {
    signal: 'HOLD_THESIS',
    progressPercent: progress,
    status,
    validity: 'still_valid'
  };
}
