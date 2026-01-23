/**
 * Re-analysis Type System - Phase 5.3: Re-analysis & Invalidation Engine
 * 
 * Defines types for Virtual Position re-analysis and structural validity checking.
 * This phase answers ONLY: "Is this trading idea still structurally valid?"
 * 
 * This file contains ONLY type definitions - no logic or implementation.
 * 
 * HARD CONSTRAINTS:
 * ❌ NO execution logic
 * ❌ NO trade management suggestions
 * ❌ NO guidance or UX-facing text
 * ❌ NO progress calculation (Phase 5.2)
 * ❌ NO price-based decisions beyond structural checks
 * ❌ NO confidence or ML logic
 */

import { POI } from '../poi';

/**
 * Market State
 * 
 * Architecture Decision: Minimal, observational input
 * 
 * Market state represents the results of upstream market analysis.
 * Phase 5.3 does NOT analyze the market - it only reads analysis results.
 * All heavy lifting (structure/liquidity detection) is done upstream.
 * 
 * This design keeps Phase 5.3 pure and deterministic - it only evaluates
 * structural validity based on pre-computed market observations.
 */
export interface MarketState {
  /** Map of POI objects referenced by the Virtual Position */
  pois: Map<string, POI>;
  
  /** Higher-timeframe bias from upstream analysis */
  htfBias: 'bullish' | 'bearish' | 'neutral';
  
  /** Whether market structure remains intact (provided by upstream) */
  structureIntact: boolean;
  
  /** Whether counter-liquidity has been taken (opposing side liquidity event) */
  counterLiquidityTaken: boolean;
  
  /** Set of POI IDs that have been invalidated/mitigated */
  invalidatedPOIs: Set<string>;
}

/**
 * Invalidation Reason
 * 
 * Architecture Decision: Explicit, machine-readable enums only (NO free-text)
 * 
 * Enumerates all possible reasons why a Virtual Position may be invalidated.
 * Each reason represents a structural violation of the original trading idea.
 * 
 * These reasons are FROZEN for ESB v1.0 after merge.
 */
export type InvalidationReason =
  | 'STRUCTURE_BROKEN'        // Market structure contradicts scenario premise
  | 'POI_INVALIDATED'         // Critical POI (SL/TP anchor) is mitigated
  | 'LIQUIDITY_TAKEN_AGAINST' // Opposing-side liquidity taken after entry
  | 'HTF_BIAS_FLIPPED'        // Higher-timeframe bias flipped against scenario
  | 'TIME_DECAY_EXCEEDED';    // Scenario exceeded 24-hour lifespan without resolution

/**
 * Re-analysis Check
 * 
 * Architecture Decision: Explicit checks for audit-friendly validation
 * 
 * Enumerates all structural checks that pass when a position is still valid.
 * Used in the still_valid result to show which validations succeeded.
 * 
 * These checks are FROZEN for ESB v1.0 after merge.
 */
export type ReanalysisCheck =
  | 'STRUCTURE_INTACT'      // Market structure still supports the scenario
  | 'POI_REMAINS_VALID'     // All critical POIs (SL/TP) remain valid
  | 'NO_COUNTER_LIQUIDITY'  // No opposing liquidity events detected
  | 'HTF_BIAS_ALIGNED';     // Higher-timeframe bias still aligned

/**
 * Re-analysis Result
 * 
 * Architecture Decision: Explicit, machine-readable discriminated union
 * 
 * Represents the outcome of re-analyzing a Virtual Position.
 * - Success case: Position is still structurally valid
 * - Failure case: Position is invalidated with explicit reason
 * 
 * NO free-text. Enums ONLY. This ensures:
 * - Type-safe handling
 * - Machine-readable results
 * - Deterministic behavior
 * - Audit-friendly logging
 */
export type ReanalysisResult =
  | {
      status: 'still_valid';
      checksPassed: ReanalysisCheck[];
    }
  | {
      status: 'invalidated';
      reason: InvalidationReason;
    };
