/**
 * Entry Scenario Type System - Phase 4.3: Entry Scenario Core (Design-First)
 * 
 * Defines ICT Entry Scenarios as first-class domain objects.
 * Entry Scenarios represent STRUCTURAL MARKET IDEAS, NOT trade decisions.
 * 
 * This file contains ONLY type definitions - no logic, detection, or execution.
 * 
 * HARD CONSTRAINTS:
 * ❌ NO execution logic
 * ❌ NO trade signals (no buy/sell semantics)
 * ❌ NO SL / TP
 * ❌ NO RR
 * ❌ NO scoring, confidence, weights, probabilities
 * ❌ NO strategy decisions
 */

/**
 * ICT Entry Scenario Types
 * 
 * Each type represents a specific structural market pattern based on ICT methodology.
 * These are templates for recognizing market structure, NOT trading signals.
 */
export enum EntryScenarioType {
  /** Liquidity sweep followed by displacement move */
  LiquiditySweepDisplacement = 'LiquiditySweepDisplacement',
  
  /** Breaker block forming a market structure shift */
  BreakerBlockMSS = 'BreakerBlockMSS',
  
  /** Order Block / Fair Value Gap in discount zone */
  OB_FVG_Discount = 'OB_FVG_Discount',
  
  /** Buy side liquidity taken with rejection */
  BuySideTakenRejection = 'BuySideTakenRejection',
  
  /** Sell side sweep with order block reaction */
  SellSideSweepOBReaction = 'SellSideSweepOBReaction'
}

/**
 * Lifecycle states for Entry Scenarios
 * 
 * - 'forming': Required gates are not yet complete (scenario is developing)
 * - 'valid': All required gates are satisfied (scenario is complete)
 * - 'invalidated': Scenario has been invalidated by market conditions
 * 
 * NOTE: 'valid' ≠ tradable, 'valid' ≠ signal
 * A valid scenario is simply a complete structural idea.
 */
export type EntryScenarioStatus = 'forming' | 'valid' | 'invalidated';

/**
 * Required Gates - Minimum structural conditions
 * 
 * These are boolean flags that MUST all be true for a scenario to become 'valid'.
 * Gates represent fundamental structural requirements.
 * 
 * Architecture Decision: Uniform structure across all scenario types
 */
export interface RequiredGates {
  /** Higher timeframe bias aligns with scenario direction */
  htfBiasAligned: boolean;
  
  /** Liquidity event has occurred (sweep, raid, etc.) */
  liquidityEvent: boolean;
  
  /** Structural confirmation is present (MSS, BOS, displacement) */
  structuralConfirmation: boolean;
}

/**
 * Optional Confluences - Additional supporting factors
 * 
 * These are optional boolean flags indicating presence/absence of confluence factors.
 * Confluences do NOT gate validity - they provide additional context.
 * 
 * NOTE: Phase 4.3 ONLY tracks presence/absence (boolean flags).
 * Confluence SCORING is Phase 4.4 (explicitly out of scope here).
 * 
 * Architecture Decision: Explicit flags, no auto-detection
 */
export interface OptionalConfluences {
  /** Order Block is present */
  orderBlock?: boolean;
  
  /** Fair Value Gap is present */
  fairValueGap?: boolean;
  
  /** Breaker Block is present */
  breakerBlock?: boolean;
  
  /** Price is in discount/premium zone */
  discountPremium?: boolean;
  
  /** Buy side or sell side liquidity context */
  buySellLiquidity?: boolean;
  
  /** News risk consideration (inverted: true = risk present) */
  newsRisk?: boolean;
}

/**
 * Entry Scenario - A structural market idea
 * 
 * An Entry Scenario represents a complete structural market pattern at a point in time.
 * It is NOT a trade signal, NOT a buy/sell decision, and NOT an execution instruction.
 * 
 * Key Properties:
 * - Deterministic: Same inputs always produce same output
 * - Immutable: Does not mutate input objects
 * - Time-aware: Evaluated at a fixed timestamp
 * - Context-aware: References LiquidityContext (Phase 4.2)
 * 
 * Lifecycle:
 * 1. Scenario starts as 'forming' (gates not complete)
 * 2. Scenario becomes 'valid' when ALL required gates are true
 * 3. Scenario becomes 'invalidated' if context changes invalidate it
 * 
 * NOTE: A scenario can exist and die silently without ever becoming 'valid'.
 */
export interface EntryScenario {
  /** Unique identifier for the scenario */
  id: string;
  
  /** Type of entry scenario (ICT template) */
  type: EntryScenarioType;
  
  /** Reference to the LiquidityContext (from Phase 4.2) */
  contextId: string;
  
  /** Current lifecycle status of the scenario */
  status: EntryScenarioStatus;
  
  /** Required structural gates (must ALL be true for validity) */
  requiredGates: RequiredGates;
  
  /** Optional confluence factors (presence/absence only) */
  optionalConfluences: OptionalConfluences;
  
  /** Fixed timestamp when this scenario was evaluated (Unix milliseconds) */
  evaluatedAt: number;
}
