/**
 * Virtual Position Progress Engine - Phase 5.2: Progress Engine
 * 
 * Pure, deterministic progress calculation for Virtual Positions.
 * Implements progress evolution only - NO execution, invalidation, or re-analysis.
 * 
 * Contract Rules:
 * 1. Deterministic - same inputs → same output
 * 2. No side effects
 * 3. No mutations
 * 4. No randomness
 * 5. No Date.now()
 * 6. Returns NEW VirtualPosition (immutability)
 * 
 * Architecture Decisions:
 * - Direction inferred from SL/TP positioning (Option B)
 * - Linear progress calculation, clamped [0, 100]
 * - Non-decreasing progress (Math.max)
 * - TP skipping allowed (logical sorting)
 * - Hard-coded 1 hour stall threshold
 * - Status priority: completed > stalled > progressing > open
 */

import { VirtualPosition, VirtualPositionStatus } from './virtualPosition.types';
import { POI } from '../poi';

/**
 * Stalling detection threshold (1 hour)
 * Hard-coded as per Phase 5.2 spec
 */
const HOUR_IN_MS = 60 * 60 * 1000;
const STALL_THRESHOLD_MS = HOUR_IN_MS; // 1 hour

/**
 * Update Virtual Position Progress
 * 
 * Pure function that calculates progress toward TP targets and derives lifecycle status.
 * This is the main entry point for the Progress Engine.
 * 
 * What it does:
 * - Calculates progress percent (0-100) based on structural references
 * - Detects which TP levels have been reached
 * - Derives lifecycle status (open/progressing/stalled/completed)
 * - Returns a NEW VirtualPosition snapshot (immutability)
 * 
 * What it does NOT do:
 * - Does NOT invalidate positions (Phase 5.3)
 * - Does NOT re-evaluate scenarios (Phase 5.3)
 * - Does NOT check structural validity (Phase 5.3)
 * - Does NOT execute trades
 * - Does NOT use confidence or scoring logic
 * 
 * @param position - VirtualPosition to update
 * @param currentPrice - Current market price
 * @param pois - Map of POI objects (must include SL and TP POIs)
 * @param evaluatedAt - Fixed timestamp for this evaluation (Unix milliseconds)
 * @returns New VirtualPosition with updated progress
 * 
 * @remarks
 * - This function is pure and deterministic
 * - Same inputs always produce identical output
 * - Input objects are never mutated
 * - evaluatedAt is a fixed timestamp, not dynamic
 */
export function updateVirtualPositionProgress(
  position: VirtualPosition,
  currentPrice: number,
  pois: Map<string, POI>,
  evaluatedAt: number
): VirtualPosition {
  // Step 1: Infer direction from SL/TP positioning
  const direction = inferDirection(position, pois);
  
  // Step 2: Calculate new progress percent
  const calculatedProgress = calculateProgressPercent(position, currentPrice, pois, direction);
  
  // Step 3: Ensure non-decreasing progress
  const newProgress = Math.max(position.progressPercent, calculatedProgress);
  
  // Step 4: Detect reached targets
  const newReachedTargets = detectReachedTargets(position, currentPrice, pois, direction);
  
  // Step 5: Derive new status
  const newStatus = deriveStatus(position, newProgress, newReachedTargets, evaluatedAt);
  
  // Step 6: Return new VirtualPosition (immutability)
  return {
    ...position,
    progressPercent: newProgress,
    reachedTargets: newReachedTargets,
    status: newStatus,
    lastEvaluatedAt: evaluatedAt
  };
}

/**
 * Infer Direction from SL/TP Positioning
 * 
 * Internal helper that determines market direction based on structural positioning.
 * Uses Option B: Inferred from RiskContract + POI positioning.
 * 
 * Logic:
 * - If SL below TP1 → bullish (SL below entry/TP)
 * - If SL above TP1 → bearish (SL above entry/TP)
 * 
 * @param position - VirtualPosition
 * @param pois - Map of POI objects
 * @returns 'bullish' or 'bearish'
 */
function inferDirection(
  position: VirtualPosition,
  pois: Map<string, POI>
): 'bullish' | 'bearish' {
  // Extract SL and TP1 POIs
  const slPOI = pois.get(position.risk.stopLoss.referencePoiId);
  const tp1Contract = position.risk.takeProfits[0];
  const tp1POI = tp1Contract ? pois.get(tp1Contract.targetPoiId) : undefined;
  
  if (!slPOI || !tp1POI) {
    // Defensive fallback: should not happen if RiskContract was valid
    // This represents a configuration error - missing POIs referenced by risk contract
    // Default to bullish to avoid crashes, but this indicates upstream validation failure
    // eslint-disable-next-line no-console
    console.warn(
      '[ProgressEngine] Invariant violation: missing SL or TP1 POI. Defaulting to bullish. ' +
      `Position: ${position.id}, SL POI ID: ${position.risk.stopLoss.referencePoiId}, ` +
      `TP1 POI ID: ${tp1Contract?.targetPoiId || 'N/A'}`
    );
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
    // This should not happen if RiskContract validation was correct
    // Overlapping ranges indicate a structural problem in the risk contract
    // Default to bullish to avoid crashes, but this indicates upstream validation failure
    // eslint-disable-next-line no-console
    console.warn(
      '[ProgressEngine] Invariant violation: overlapping SL and TP1 price ranges. Defaulting to bullish. ' +
      `Position: ${position.id}, SL range: [${slPOI.priceRange.low}, ${slPOI.priceRange.high}], ` +
      `TP1 range: [${tp1POI.priceRange.low}, ${tp1POI.priceRange.high}]`
    );
    return 'bullish';
  }
}

/**
 * Calculate Progress Percent
 * 
 * Internal helper that calculates linear progress toward furthest TP.
 * 
 * Formula (Bullish):
 *   progress = ((currentPrice - entryRef) / (furthestTP - entryRef)) * 100
 * 
 * Formula (Bearish):
 *   progress = ((entryRef - currentPrice) / (entryRef - furthestTP)) * 100
 * 
 * Entry Reference:
 * - Bullish: Midpoint between SL high and TP1 low
 * - Bearish: Midpoint between SL low and TP1 high
 * 
 * Furthest TP:
 * - TP3 if exists, else TP2, else TP1
 * 
 * Clamping:
 * - Result is clamped to [0, 100]
 * 
 * @param position - VirtualPosition
 * @param currentPrice - Current market price
 * @param pois - Map of POI objects
 * @param direction - 'bullish' or 'bearish'
 * @returns Progress percent (0-100)
 */
function calculateProgressPercent(
  position: VirtualPosition,
  currentPrice: number,
  pois: Map<string, POI>,
  direction: 'bullish' | 'bearish'
): number {
  // Get SL and TP1 POIs
  const slPOI = pois.get(position.risk.stopLoss.referencePoiId);
  const tp1Contract = position.risk.takeProfits[0];
  const tp1POI = tp1Contract ? pois.get(tp1Contract.targetPoiId) : undefined;
  
  if (!slPOI || !tp1POI) {
    // Defensive: return 0 if POIs are missing
    return 0;
  }
  
  // Determine entry reference (structural, NOT execution price)
  let entryRef: number;
  if (direction === 'bullish') {
    // Bullish: Midpoint between SL high and TP1 low
    entryRef = (slPOI.priceRange.high + tp1POI.priceRange.low) / 2;
  } else {
    // Bearish: Midpoint between SL low and TP1 high
    entryRef = (slPOI.priceRange.low + tp1POI.priceRange.high) / 2;
  }
  
  // Determine furthest TP (TP3 > TP2 > TP1)
  const furthestTP = getFurthestTP(position, pois, direction);
  
  if (furthestTP === null) {
    // Defensive: no valid TP found
    return 0;
  }
  
  // Calculate progress
  let progress: number;
  if (direction === 'bullish') {
    // Bullish: progress toward higher prices
    progress = ((currentPrice - entryRef) / (furthestTP - entryRef)) * 100;
  } else {
    // Bearish: progress toward lower prices
    progress = ((entryRef - currentPrice) / (entryRef - furthestTP)) * 100;
  }
  
  // Clamp to [0, 100]
  return Math.max(0, Math.min(100, progress));
}

/**
 * Get Furthest TP Price
 * 
 * Internal helper that determines the furthest available TP target.
 * 
 * Priority: TP3 > TP2 > TP1
 * 
 * Returns:
 * - For bullish: low boundary of furthest TP POI
 * - For bearish: high boundary of furthest TP POI
 * 
 * @param position - VirtualPosition
 * @param pois - Map of POI objects
 * @param direction - 'bullish' or 'bearish'
 * @returns Furthest TP price, or null if none found
 */
function getFurthestTP(
  position: VirtualPosition,
  pois: Map<string, POI>,
  direction: 'bullish' | 'bearish'
): number | null {
  // Check for TP3, TP2, TP1 in that order
  const tp3 = position.risk.takeProfits.find(tp => tp.level === 'TP3');
  const tp2 = position.risk.takeProfits.find(tp => tp.level === 'TP2');
  const tp1 = position.risk.takeProfits.find(tp => tp.level === 'TP1');
  
  const furthestTP = tp3 || tp2 || tp1;
  
  if (!furthestTP) {
    return null;
  }
  
  const tpPOI = pois.get(furthestTP.targetPoiId);
  
  if (!tpPOI) {
    return null;
  }
  
  // Return appropriate boundary based on direction
  if (direction === 'bullish') {
    return tpPOI.priceRange.low;
  } else {
    return tpPOI.priceRange.high;
  }
}

/**
 * Detect Reached Targets
 * 
 * Internal helper that determines which TP levels have been reached.
 * 
 * Rules:
 * 1. A TP is reached when currentPrice enters its POI price range
 *    - Bullish: currentPrice >= tpPOI.priceRange.low
 *    - Bearish: currentPrice <= tpPOI.priceRange.high
 * 2. TP levels can only be added once (no duplicates)
 * 3. Skipping is allowed (TP3 can be reached before TP1/TP2)
 * 4. Array is always sorted logically (TP1, TP2, TP3)
 * 
 * @param position - VirtualPosition
 * @param currentPrice - Current market price
 * @param pois - Map of POI objects
 * @param direction - 'bullish' or 'bearish'
 * @returns Sorted array of reached TP levels
 */
function detectReachedTargets(
  position: VirtualPosition,
  currentPrice: number,
  pois: Map<string, POI>,
  direction: 'bullish' | 'bearish'
): ('TP1' | 'TP2' | 'TP3')[] {
  // Start with existing reached targets
  const reached = new Set(position.reachedTargets);
  
  // Check each TP in the risk contract
  for (const tp of position.risk.takeProfits) {
    const tpPOI = pois.get(tp.targetPoiId);
    
    if (!tpPOI) {
      continue;
    }
    
    // Check if TP is reached
    const isReached = isTPReached(currentPrice, tpPOI, direction);
    
    if (isReached) {
      reached.add(tp.level);
    }
  }
  
  // Convert to sorted array (TP1, TP2, TP3 order)
  const sortOrder: { [key: string]: number } = { TP1: 1, TP2: 2, TP3: 3 };
  return Array.from(reached).sort((a, b) => (sortOrder[a] || 0) - (sortOrder[b] || 0));
}

/**
 * Check if TP is Reached
 * 
 * Internal helper that checks if a TP POI has been reached by current price.
 * 
 * @param currentPrice - Current market price
 * @param tpPOI - TP POI object
 * @param direction - 'bullish' or 'bearish'
 * @returns true if TP is reached
 */
function isTPReached(
  currentPrice: number,
  tpPOI: POI,
  direction: 'bullish' | 'bearish'
): boolean {
  if (direction === 'bullish') {
    // Bullish: price reaches TP when it hits or exceeds TP low
    return currentPrice >= tpPOI.priceRange.low;
  } else {
    // Bearish: price reaches TP when it hits or goes below TP high
    return currentPrice <= tpPOI.priceRange.high;
  }
}

/**
 * Derive Status
 * 
 * Internal helper that determines the lifecycle status based on progress and targets.
 * 
 * Status Priority (strict hierarchy):
 * 1. completed - Last TP reached (TP3 or furthest available)
 * 2. stalled - Progress unchanged AND time threshold exceeded
 * 3. progressing - Progress > 0 AND < 100
 * 4. open - Progress === 0
 * 
 * Stalling Detection:
 * - Progress unchanged (newProgress === position.progressPercent)
 * - Time elapsed > STALL_THRESHOLD_MS (1 hour)
 * 
 * @param position - VirtualPosition
 * @param newProgress - New progress percent
 * @param newReachedTargets - New reached targets array
 * @param evaluatedAt - Current evaluation timestamp
 * @returns New status
 */
function deriveStatus(
  position: VirtualPosition,
  newProgress: number,
  newReachedTargets: ('TP1' | 'TP2' | 'TP3')[],
  evaluatedAt: number
): VirtualPositionStatus {
  // Check for completion (highest priority)
  const lastTPLevel = getLastTPLevel(position);
  const lastTPReached = newReachedTargets.includes(lastTPLevel);
  
  if (lastTPReached) {
    return 'completed';
  }
  
  // Check for stalling (second priority)
  const progressUnchanged = (newProgress === position.progressPercent);
  const timeElapsed = (evaluatedAt - position.lastEvaluatedAt);
  const stalled = progressUnchanged && (timeElapsed > STALL_THRESHOLD_MS);
  
  if (stalled) {
    return 'stalled';
  }
  
  // Check for progressing (third priority)
  if (newProgress > 0 && newProgress < 100) {
    return 'progressing';
  }
  
  // Default: open (lowest priority)
  return 'open';
}

/**
 * Get Last TP Level
 * 
 * Internal helper that determines the last (furthest) TP level in the risk contract.
 * 
 * Returns TP3 if exists, else TP2, else TP1.
 * 
 * @param position - VirtualPosition
 * @returns Last TP level
 */
function getLastTPLevel(position: VirtualPosition): 'TP1' | 'TP2' | 'TP3' {
  const hasTP3 = position.risk.takeProfits.some(tp => tp.level === 'TP3');
  const hasTP2 = position.risk.takeProfits.some(tp => tp.level === 'TP2');
  
  if (hasTP3) {
    return 'TP3';
  } else if (hasTP2) {
    return 'TP2';
  } else {
    return 'TP1';
  }
}
