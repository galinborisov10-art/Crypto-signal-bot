/**
 * Confluence Score Type System - Phase 4.4: Confluence Scoring Engine (Design-First)
 * 
 * Defines pure, deterministic evaluation of Entry Scenario confluence quality.
 * This layer answers ONLY: "How good is this structural idea?"
 * 
 * This file contains ONLY type definitions - no logic or implementation.
 * 
 * HARD CONSTRAINTS:
 * ❌ NO execution logic
 * ❌ NO trade signals (no buy/sell semantics)
 * ❌ NO SL / TP
 * ❌ NO RR
 * ❌ NO capital or sizing logic
 * ❌ NO ML, statistics, optimization
 * ❌ NO randomness
 * ❌ NO Date.now()
 * 
 * SCORING MUST BE:
 * ✅ Deterministic
 * ✅ Replay-safe
 * ✅ Pure (no side effects)
 * ✅ Input-driven only
 */

/**
 * Confluence Factors
 * 
 * Mirrors the optional confluences from Phase 4.3 EntryScenario.
 * Each factor can contribute to the overall confluence score.
 * 
 * Architecture Decision: Exact mirror of Phase 4.3 OptionalConfluences keys
 */
export type ConfluenceFactor =
  | 'orderBlock'
  | 'fairValueGap'
  | 'breakerBlock'
  | 'discountPremium'
  | 'buySellLiquidity'
  | 'newsRisk';

/**
 * Weight Configuration for Confluence Factors
 * 
 * Architecture Decision: NO default weights in code
 * - Weights MUST be explicitly provided by caller
 * - Weights are policy, not core semantics
 * - Positive weights add to score
 * - Negative weights (dampeners) subtract from score
 * 
 * Critical Rules:
 * - ❌ NO DEFAULT_WEIGHTS constant in implementation
 * - ❌ NO implicit values
 * - ✅ Explicit configuration only
 * - ✅ newsRisk is typically negative (risk dampener)
 */
export interface ConfluenceWeights {
  /** Weight for Order Block presence */
  orderBlock: number;
  
  /** Weight for Fair Value Gap presence */
  fairValueGap: number;
  
  /** Weight for Breaker Block presence */
  breakerBlock: number;
  
  /** Weight for Discount/Premium zone presence */
  discountPremium: number;
  
  /** Weight for Buy/Sell liquidity context */
  buySellLiquidity: number;
  
  /** Weight for news risk (typically NEGATIVE - dampener) */
  newsRisk: number;
}

/**
 * Dampener Impact Record
 * 
 * Architecture Decision: Structured objects (extensible)
 * 
 * Records the impact of dampeners (e.g., newsRisk) on the score.
 * Provides full auditability of score reduction.
 */
export interface DampenerImpact {
  /** Which confluence factor acted as a dampener */
  factor: ConfluenceFactor;
  
  /** The numerical impact (typically negative) */
  impact: number;
}

/**
 * Score Breakdown
 * 
 * Architecture Decision: ALL factors shown (0 for missing)
 * 
 * Provides complete transparency into how the score was calculated.
 * Every confluence factor appears in contributions, even if 0.
 */
export interface ConfluenceBreakdown {
  /** List of confluence factors that were present (true) */
  present: ConfluenceFactor[];
  
  /** List of confluence factors that were missing (false/undefined) */
  missing: ConfluenceFactor[];
  
  /** Contribution of each factor to raw score (ALL factors, 0 for missing) */
  contributions: Record<ConfluenceFactor, number>;
  
  /** Dampeners that were applied (active dampeners only) */
  dampenersApplied: DampenerImpact[];
}

/**
 * Confluence Score
 * 
 * Architecture Decision: Both confidence and normalizedScore fields (same value)
 * 
 * Represents the evaluated quality of an Entry Scenario based on its confluences.
 * This is a pure evaluation, NOT a trading decision.
 * 
 * Key Properties:
 * - Deterministic: Same inputs always produce same output
 * - Immutable: Does not mutate input objects
 * - Time-aware: Evaluated at a fixed timestamp
 * - Bounded: confidence/normalizedScore always 0-100
 * 
 * NOTE: High confidence ≠ signal
 * NOTE: Confidence = quality, NOT permission to trade
 */
export interface ConfluenceScore {
  /** Reference to the Entry Scenario ID being scored */
  scenarioId: string;
  
  /** Raw score before normalization (can be negative, unbounded) */
  rawScore: number;
  
  /** Normalized score (0-100) */
  normalizedScore: number;
  
  /** Confidence level (0-100) - semantic alias of normalizedScore */
  confidence: number;
  
  /** Detailed breakdown of score calculation */
  breakdown: ConfluenceBreakdown;
  
  /** Fixed timestamp when this score was evaluated (Unix milliseconds) */
  evaluatedAt: number;
}

/**
 * Scoring Result
 * 
 * Architecture Decision: Explicit result type (no throw)
 * 
 * Discriminated union representing the outcome of scoring.
 * - Success case includes the ConfluenceScore
 * - Failure case includes error reason
 * 
 * This design allows for explicit error handling without exceptions.
 */
export type ScoringResult =
  | { success: true; score: ConfluenceScore }
  | { success: false; error: 'SCENARIO_NOT_VALID' };
