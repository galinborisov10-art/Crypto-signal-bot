/**
 * Risk Contract Type System - Phase 4.5: SL/TP Contracts (Design-First)
 * 
 * Defines pure, deterministic SL/TP risk contracts.
 * This layer answers ONLY: "If we were to trade this idea, is the risk structure valid?"
 * 
 * This file contains ONLY type definitions - no logic or implementation.
 * 
 * HARD CONSTRAINTS:
 * ❌ NO execution logic
 * ❌ NO buy/sell signals
 * ❌ NO order placement
 * ❌ NO position sizing
 * ❌ NO capital logic
 * ❌ NO portfolio logic
 * ❌ NO ML / optimization
 * ❌ NO randomness
 * ❌ NO Date.now()
 * 
 * SL/TP here are CONTRACTS, not execution numbers.
 */

import { POI } from '../poi';

/**
 * Stop Loss Contract
 * 
 * Defines the structural stop loss specification for a risk contract.
 * This is NOT an execution price - it's a structural contract.
 * 
 * Type Determination:
 * - 'orderBlock' if POI type is 'OrderBlock'
 * - 'structure' for all other structural types (PreviousHigh, PreviousLow, BreakerBlock)
 * 
 * beyondStructure Calculation:
 * - Computed: SL POI is beyond last structural boundary (e.g., last swing high/low)
 * - ❌ NOT a POI property
 * - ❌ NOT an external flag
 * - ✅ Determined during SL selection
 */
export interface StopLossContract {
  /** Type of stop loss: order block or structural */
  type: 'structure' | 'orderBlock';
  
  /** Reference to the POI used as stop loss */
  referencePoiId: string;
  
  /** Whether this SL is beyond the last structural boundary */
  beyondStructure: boolean;
}

/**
 * Take Profit Contract
 * 
 * Defines a single take profit target specification.
 * This is NOT an execution price - it's a structural contract.
 * 
 * Probability Assignment (FIXED):
 * - TP1 → 'high'
 * - TP2 → 'medium'
 * - TP3 → 'low'
 * 
 * ❌ NO dynamic probability formulas
 * ❌ NO ML / statistics
 */
export interface TakeProfitContract {
  /** Level identifier for this take profit */
  level: 'TP1' | 'TP2' | 'TP3';
  
  /** Reference to the POI used as take profit target */
  targetPoiId: string;
  
  /** Fixed probability assignment based on level */
  probability: 'high' | 'medium' | 'low';
}

/**
 * Risk Invalidation Reasons
 * 
 * Explicit reasons why a risk contract may be invalid.
 * Early invalidation - no partial contracts allowed.
 */
export type RiskInvalidationReason =
  | 'RR_TOO_LOW'           // Risk/Reward ratio < 3
  | 'NO_VALID_STOP'        // No valid SL POI found
  | 'NO_VALID_TARGETS'     // No valid TP POI found
  | 'SCENARIO_NOT_VALID';  // Entry scenario status is not 'valid' (edge case)

/**
 * Risk Contract
 * 
 * Complete risk specification for an entry scenario.
 * Defines structural acceptability of risk, NOT execution instructions.
 * 
 * Key Properties:
 * - Deterministic: Same inputs always produce same output
 * - Immutable: Does not mutate input objects
 * - Time-aware: Evaluated at a fixed timestamp
 * - POI-based: Uses POI price ranges, NOT execution prices
 * 
 * Validation Rules:
 * - Must have valid SL (correct type + position)
 * - Must have at least TP1
 * - RR must be >= 3 (based on TP1)
 * 
 * Early Invalidation:
 * - No valid SL → STOP
 * - No valid TP → STOP
 * - RR < 3 → STOP
 * - ❌ NO partial contracts
 * - ❌ NO "will fix later"
 * 
 * NOTE: High confidence can still fail risk validation
 * Quality ≠ Acceptable Risk
 */
export interface RiskContract {
  /** Reference to the Entry Scenario ID */
  scenarioId: string;
  
  /** Stop loss contract specification */
  stopLoss: StopLossContract;
  
  /** Take profit contracts (at least TP1, up to TP1-TP3) */
  takeProfits: TakeProfitContract[];
  
  /** Risk/Reward ratio (calculated using TP1 only) */
  rr: number;
  
  /** Validity status of this risk contract */
  status: 'valid' | 'invalid';
  
  /** Reason for invalidation (only present if status === 'invalid') */
  invalidationReason?: RiskInvalidationReason;
  
  /** Fixed timestamp when this contract was evaluated (Unix milliseconds) */
  evaluatedAt: number;
}

/**
 * Risk POIs Input Structure
 * 
 * Architecture Decision: Pre-filtered semantic sets (NOT all POIs)
 * 
 * The caller is responsible for pre-filtering POIs into these semantic sets.
 * This layer does NOT discover or filter POIs - it ONLY validates and selects.
 * 
 * Structure:
 * - entryPOI: The POI representing the entry context (from LiquidityContext)
 * - stopLossCandidates: Pre-filtered POIs that could serve as SL
 * - takeProfitCandidates: Pre-filtered POIs that could serve as TP
 * 
 * Pre-filtering criteria (done by caller):
 * - SL candidates: OrderBlock, PreviousHigh, PreviousLow, BreakerBlock types
 * - TP candidates: Structural targets aligned with scenario direction
 * - Entry POI: Retrieved via scenario.contextId lookup
 */
export interface RiskPOIs {
  /** The entry POI (from scenario.contextId lookup) */
  entryPOI: POI;
  
  /** Pre-filtered POI candidates for stop loss */
  stopLossCandidates: POI[];
  
  /** Pre-filtered POI candidates for take profit targets */
  takeProfitCandidates: POI[];
}
