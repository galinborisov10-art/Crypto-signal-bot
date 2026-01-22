/**
 * Liquidity Context Contracts - Phase 4.2: Liquidity Context Layer
 * 
 * Contract/validation logic for Liquidity Context interpretation.
 * Enforces deterministic evaluation of POIs without execution or detection logic.
 * 
 * Contract Rules:
 * 1. If evaluatedAt < validFrom → status = 'invalid'
 * 2. If evaluatedAt > validUntil → status = 'expired'
 * 3. If poi.mitigated === true → status = 'mitigated'
 * 4. Only unmitigated + valid POIs can be 'active'
 * 
 * HTF/LTF Rules:
 * 1. HTF bias does not override, only constrains
 * 2. LTF context cannot be 'aligned' if directionBias conflicts with HTF POI
 * 3. If no HTF POI exists → htfRelation = 'undefined'
 * 
 * Absolute Rules:
 * 1. LiquidityContext MUST be derivable deterministically
 * 2. No randomness
 * 3. Same inputs → same output
 * 4. MUST NOT mutate input POI objects
 */

import { POI } from '../poi';
import { LiquidityContext, LiquidityContextStatus, HTFRelation } from './liquidityContext.types';

/**
 * Build a Liquidity Context from a POI at a specific point in time
 * 
 * This function derives a time-based interpretation of a POI without modifying it.
 * 
 * @param poi - The Point of Interest to interpret
 * @param evaluatedAt - Unix timestamp (milliseconds) at which to evaluate the context
 * @param htfPOI - Optional higher timeframe POI for HTF/LTF relationship
 * @returns A deterministic LiquidityContext object
 * 
 * @remarks
 * - This function is pure and deterministic
 * - Same inputs always produce identical output
 * - Input POI objects are never mutated
 * - evaluatedAt is a fixed timestamp, not dynamic
 */
export function buildLiquidityContext(
  poi: POI,
  evaluatedAt: number,
  htfPOI?: POI
): LiquidityContext {
  // Validate inputs are not mutated by creating a read-only reference
  // This ensures contract compliance

  // Determine if within validity window
  const isWithinValidityWindow =
    evaluatedAt >= poi.validFrom &&
    evaluatedAt <= poi.validUntil;

  // Determine mitigation state
  const mitigationState = poi.mitigated ? 'mitigated' : 'unmitigated';

  // Determine status based on contract rules
  let status: LiquidityContextStatus;
  
  if (evaluatedAt < poi.validFrom) {
    // Contract Rule 1: Before validity window
    status = 'invalid';
  } else if (evaluatedAt > poi.validUntil) {
    // Contract Rule 2: After validity window
    status = 'expired';
  } else if (poi.mitigated) {
    // Contract Rule 3: Mitigated
    status = 'mitigated';
  } else {
    // Contract Rule 4: Active (unmitigated + valid)
    status = 'active';
  }

  // Determine HTF relation
  const htfRelation = calculateHTFRelation(poi, htfPOI);

  // Build and return the context
  const context: LiquidityContext = {
    poiId: poi.id,
    timeframe: poi.timeframe,
    status,
    isWithinValidityWindow,
    mitigationState,
    htfRelation,
    evaluatedAt
  };

  return context;
}

/**
 * Calculate HTF/LTF relationship
 * 
 * HTF/LTF Rules:
 * 1. If no HTF POI provided → 'undefined'
 * 2. If LTF directionBias === 'neutral' → 'neutral'
 * 3. If HTF directionBias === 'neutral' → 'neutral'
 * 4. If LTF and HTF directionBias match → 'aligned'
 * 5. If LTF and HTF directionBias conflict → 'counter'
 * 
 * @param ltfPOI - Lower timeframe POI
 * @param htfPOI - Optional higher timeframe POI
 * @returns HTF relation status
 */
function calculateHTFRelation(ltfPOI: POI, htfPOI?: POI): HTFRelation {
  // HTF/LTF Rule 1: No HTF provided
  if (!htfPOI) {
    return 'undefined';
  }

  // HTF/LTF Rule 2: LTF is neutral
  if (ltfPOI.directionBias === 'neutral') {
    return 'neutral';
  }

  // HTF/LTF Rule 3: HTF is neutral
  if (htfPOI.directionBias === 'neutral') {
    return 'neutral';
  }

  // HTF/LTF Rule 4: Direction bias matches
  if (ltfPOI.directionBias === htfPOI.directionBias) {
    return 'aligned';
  }

  // HTF/LTF Rule 5: Direction bias conflicts
  return 'counter';
}

/**
 * Guard: Check if a Liquidity Context is active
 * 
 * Returns true if and only if the context status is 'active'.
 * 
 * @param ctx - The Liquidity Context to check
 * @returns true if context is active, false otherwise
 */
export function isLiquidityContextActive(ctx: LiquidityContext): boolean {
  return ctx.status === 'active';
}

/**
 * Guard: Check if a Liquidity Context is tradable
 * 
 * A context is tradable if:
 * - It is active AND
 * - HTF relation is either 'aligned' or 'neutral'
 * 
 * ⚠️ Important: Tradable ≠ signal
 * This only means "allowed to be considered later" in Phase 4.3 (Entry Scenarios).
 * It does NOT generate signals or make trading decisions.
 * 
 * @param ctx - The Liquidity Context to check
 * @returns true if context is tradable, false otherwise
 */
export function isLiquidityContextTradable(ctx: LiquidityContext): boolean {
  // Must be active first
  if (!isLiquidityContextActive(ctx)) {
    return false;
  }

  // HTF relation must be aligned or neutral
  return ctx.htfRelation === 'aligned' || ctx.htfRelation === 'neutral';
}
