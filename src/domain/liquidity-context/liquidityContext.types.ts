/**
 * Liquidity Context Type System - Phase 4.2: Liquidity Context Layer
 * 
 * Defines time-based interpretation of POIs without detection, scoring, or execution logic.
 * 
 * This layer models how POIs behave over time and across timeframes.
 * It answers:
 * - Is a POI still valid now?
 * - Has it been mitigated?
 * - How do HTF POIs constrain LTF interpretation?
 */

import { Timeframe } from '../poi';

/**
 * Status of a Liquidity Context at a given point in time
 * 
 * - 'active': POI is valid, within time window, and unmitigated
 * - 'expired': POI validity window has ended
 * - 'mitigated': POI has been mitigated (price has reacted to it)
 * - 'invalid': POI is evaluated before its validity window starts
 */
export type LiquidityContextStatus =
  | 'active'
  | 'expired'
  | 'mitigated'
  | 'invalid';

/**
 * Relationship between Higher Timeframe (HTF) and Lower Timeframe (LTF) POI
 * 
 * - 'aligned': LTF and HTF direction bias match
 * - 'counter': LTF and HTF direction bias conflict
 * - 'neutral': Either LTF or HTF has neutral bias
 * - 'undefined': No HTF POI provided for comparison
 */
export type HTFRelation =
  | 'aligned'
  | 'counter'
  | 'neutral'
  | 'undefined';

/**
 * Liquidity Context - A time-based interpretation of a POI
 * 
 * This is a derived, read-only object that interprets a POI at a specific moment in time.
 * It does NOT create or modify POIs.
 * 
 * Key properties:
 * - Deterministic: Same inputs always produce the same output
 * - Immutable: Does not mutate input POIs
 * - Time-aware: Evaluated at a fixed timestamp
 * - HTF-aware: Can model relationship with higher timeframe context
 * 
 * @remarks
 * - `status` is the single source of truth for context state
 * - `isWithinValidityWindow` is derived from status (active or mitigated)
 * - `htfRelation` is only meaningful for active contexts
 */
export interface LiquidityContext {
  /** Reference to the POI being interpreted */
  poiId: string;
  
  /** Timeframe of the POI being interpreted */
  timeframe: Timeframe;
  
  /** Current status of the context (single source of truth) */
  status: LiquidityContextStatus;
  
  /** Whether the POI is within its validity time window (derived from status) */
  isWithinValidityWindow: boolean;
  
  /** Relationship to higher timeframe POI (undefined for non-active contexts) */
  htfRelation: HTFRelation;
  
  /** Fixed timestamp at which this context was evaluated (Unix milliseconds) */
  evaluatedAt: number;
}
