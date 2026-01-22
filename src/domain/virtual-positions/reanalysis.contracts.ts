/**
 * Re-analysis Contracts - Phase 5.3: Re-analysis & Invalidation Engine
 * 
 * Pure, deterministic re-analysis for Virtual Positions.
 * Implements structural validity checking only - NO execution or trade management.
 * 
 * Contract Rules:
 * 1. Deterministic - same inputs → same output
 * 2. No side effects
 * 3. No mutations
 * 4. No randomness
 * 5. No Date.now()
 * 6. Short-circuit on first invalidation
 * 
 * Architecture Decisions:
 * - Minimal input (upstream provides analysis results)
 * - Short-circuit validation (return on first invalidation detected)
 * - HTF direction inference (reuses Phase 5.2 logic)
 * - Completed positions skipped (terminal state)
 * - Time decay hard-coded 24 hours (consistency with Phase 5.2)
 */

import { VirtualPosition } from './virtualPosition.types';
import { POI } from '../poi';
import { MarketState, ReanalysisResult } from './reanalysis.types';

/**
 * Time decay threshold (24 hours)
 * Hard-coded as per Phase 5.3 spec for consistency with Phase 5.2 stalling threshold
 */
const MAX_SCENARIO_LIFESPAN_MS = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Infer Direction from SL/TP Positioning
 * 
 * Shared helper that determines market direction based on structural positioning.
 * This is the same logic used in Phase 5.2 Progress Engine.
 * 
 * Logic:
 * - If SL below TP1 → bullish (SL below entry/TP)
 * - If SL above TP1 → bearish (SL above entry/TP)
 * 
 * @param position - VirtualPosition
 * @param pois - Map of POI objects
 * @returns 'bullish' or 'bearish'
 */
export function inferDirectionFromSLTP(
  position: VirtualPosition,
  pois: Map<string, POI>
): 'bullish' | 'bearish' {
  // Extract SL and TP1 POIs
  const slPOI = pois.get(position.risk.stopLoss.referencePoiId);
  const tp1Contract = position.risk.takeProfits[0];
  const tp1POI = tp1Contract ? pois.get(tp1Contract.targetPoiId) : undefined;
  
  if (!slPOI || !tp1POI) {
    // Defensive fallback: should not happen if RiskContract was valid
    // Default to bullish to avoid crashes
    return 'bullish';
  }
  
  // Determine direction based on SL/TP positioning
  if (slPOI.priceRange.high < tp1POI.priceRange.low) {
    // SL below TP1 → bullish
    return 'bullish';
  } else if (slPOI.priceRange.low > tp1POI.priceRange.high) {
    // SL above TP1 → bearish
    return 'bearish';
  } else {
    // Defensive fallback: Invalid structure (overlapping SL and TP1 ranges)
    // Default to bullish to avoid crashes
    return 'bullish';
  }
}

/**
 * Reanalyze Virtual Position
 * 
 * Pure function that re-evaluates structural validity of a Virtual Position.
 * This is the main entry point for the Re-analysis Engine.
 * 
 * What it does:
 * - Re-evaluates structural validity based on market state
 * - Detects invalidation conditions
 * - Returns explicit, typed re-analysis results
 * - Fully deterministic and replay-safe
 * 
 * What it does NOT do:
 * - Does NOT provide guidance or suggestions
 * - Does NOT manage positions
 * - Does NOT execute trades
 * - Does NOT calculate progress (Phase 5.2)
 * - Does NOT communicate with users
 * 
 * Validation checks are executed in strict order with short-circuit behavior:
 * 1. Completed position check (pre-filter)
 * 2. Structure validity
 * 3. POI validity (SL + all TPs)
 * 4. Counter-liquidity
 * 5. HTF bias alignment
 * 6. Time decay
 * 
 * Returns on first invalidation detected.
 * 
 * @param position - VirtualPosition to re-analyze
 * @param marketState - Current market state (from upstream analysis)
 * @param evaluatedAt - Fixed timestamp for this evaluation (Unix milliseconds)
 * @returns ReanalysisResult with status and reason/checks
 * 
 * @remarks
 * - This function is pure and deterministic
 * - Same inputs always produce identical output
 * - Input objects are never mutated
 * - evaluatedAt is a fixed timestamp, not dynamic
 */
export function reanalyzeVirtualPosition(
  position: VirtualPosition,
  marketState: MarketState,
  evaluatedAt: number
): ReanalysisResult {
  // ============================================================
  // CHECK 1: Completed Position (Pre-filter)
  // ============================================================
  // Architecture Decision: Skip re-analysis for completed positions
  // Completion = terminal state for ESB v1.0
  
  if (position.status === 'completed') {
    return {
      status: 'still_valid',
      checksPassed: []
    };
  }
  
  // ============================================================
  // CHECK 2: Structure Validity
  // ============================================================
  // Architecture Decision: Caller-provided flag
  // Avoids duplicating Phase 4 logic - PR-5.3 remains pure re-evaluator
  
  if (!marketState.structureIntact) {
    return {
      status: 'invalidated',
      reason: 'STRUCTURE_BROKEN'
    };
  }
  
  // ============================================================
  // CHECK 3: POI Validity
  // ============================================================
  // Architecture Decision: External validation via MarketState
  // Check if critical POIs (SL and all TPs) are invalidated
  
  // Collect all critical POI IDs (SL + all TPs)
  const criticalPOIs: string[] = [
    position.risk.stopLoss.referencePoiId,
    ...position.risk.takeProfits.map(tp => tp.targetPoiId)
  ];
  
  // Check if any critical POI is invalidated
  for (const poiId of criticalPOIs) {
    if (marketState.invalidatedPOIs.has(poiId)) {
      return {
        status: 'invalidated',
        reason: 'POI_INVALIDATED'
      };
    }
  }
  
  // ============================================================
  // CHECK 4: Liquidity Against Position
  // ============================================================
  // Architecture Decision: Simple flag
  // PR-5.3 does NOT do event analysis - only reacts to detected events
  
  if (marketState.counterLiquidityTaken) {
    return {
      status: 'invalidated',
      reason: 'LIQUIDITY_TAKEN_AGAINST'
    };
  }
  
  // ============================================================
  // CHECK 5: HTF Bias Alignment
  // ============================================================
  // Architecture Decision: Reuse direction inference from PR-5.2
  // Same logic as Progress Engine for consistency
  
  const originalBias = inferDirectionFromSLTP(position, marketState.pois);
  
  // Check if HTF bias has flipped (ignore 'neutral' - not a flip)
  if (marketState.htfBias !== originalBias && marketState.htfBias !== 'neutral') {
    return {
      status: 'invalidated',
      reason: 'HTF_BIAS_FLIPPED'
    };
  }
  
  // ============================================================
  // CHECK 6: Time Decay
  // ============================================================
  // Architecture Decision: Hard-coded 24-hour threshold
  // Consistency with PR-5.2 stalling threshold
  
  const timeElapsed = evaluatedAt - position.openedAt;
  
  if (timeElapsed > MAX_SCENARIO_LIFESPAN_MS) {
    return {
      status: 'invalidated',
      reason: 'TIME_DECAY_EXCEEDED'
    };
  }
  
  // ============================================================
  // ALL CHECKS PASSED
  // ============================================================
  // Architecture Decision: Return all passed checks (audit-friendly)
  
  return {
    status: 'still_valid',
    checksPassed: [
      'STRUCTURE_INTACT',
      'POI_REMAINS_VALID',
      'NO_COUNTER_LIQUIDITY',
      'HTF_BIAS_ALIGNED'
    ]
  };
}
