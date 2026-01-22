/**
 * Confluence Score Contracts - Phase 4.4: Confluence Scoring Engine (Design-First)
 * 
 * Pure, deterministic evaluation of Entry Scenario confluence quality.
 * Implements scoring logic without execution or decision-making.
 * 
 * Contract Rules:
 * 1. ONLY EntryScenario.status === 'valid' can be scored
 * 2. Missing confluences add 0
 * 3. Present confluences add their configured weight
 * 4. newsRisk === true subtracts confidence (dampener)
 * 5. Raw score is normalized to 0-100
 * 6. confidence ≡ normalizedScore
 * 7. No hard minimum or maximum enforcement here
 * 
 * Architecture Decisions:
 * - No default weights (explicit configuration only)
 * - Explicit result type (no exceptions)
 * - All factors in contributions (full transparency)
 * - Structured dampeners (extensible)
 * - Linear scaling with clamping
 * 
 * Absolute Rules:
 * 1. Scoring MUST be deterministic
 * 2. No randomness
 * 3. Same inputs → same output
 * 4. MUST NOT mutate input objects
 * 5. NO execution, signals, or decision logic
 */

import { EntryScenario, isScenarioValid } from '../entry-scenarios';
import {
  ConfluenceFactor,
  ConfluenceWeights,
  ConfluenceScore,
  ScoringResult,
  ConfluenceBreakdown,
  DampenerImpact
} from './confluenceScore.types';

/**
 * Evaluate Confluence Score
 * 
 * Pure function that evaluates the quality of an Entry Scenario based on its confluences.
 * 
 * Calculation Steps:
 * 1. Validate scenario status (must be 'valid')
 * 2. Calculate max possible score (sum of positive weights)
 * 3. Calculate raw score (sum of present confluence weights)
 * 4. Apply dampeners (newsRisk subtracts from score)
 * 5. Normalize to 0-100 scale
 * 6. Build comprehensive breakdown
 * 
 * Normalization Formula:
 * ```
 * maxPossibleScore = sum of ALL POSITIVE weights (excludes newsRisk)
 * normalizedScore = clamp((rawScore / maxPossibleScore) * 100, 0, 100)
 * confidence = normalizedScore
 * ```
 * 
 * @param scenario - EntryScenario to evaluate (must be status === 'valid')
 * @param weights - Explicit weight configuration (no defaults)
 * @param evaluatedAt - Fixed timestamp for evaluation (Unix milliseconds)
 * @returns ScoringResult with score or error
 * 
 * @remarks
 * - This function is pure and deterministic
 * - Does NOT throw exceptions
 * - Same inputs always produce identical output
 * - Input objects are never mutated
 * - evaluatedAt is a fixed timestamp, not dynamic
 * - Returns error result if scenario is not valid
 */
export function evaluateConfluenceScore(
  scenario: EntryScenario,
  weights: ConfluenceWeights,
  evaluatedAt: number
): ScoringResult {
  // Step 1: Validate scenario status
  if (!isScenarioValid(scenario)) {
    return {
      success: false,
      error: 'SCENARIO_NOT_VALID'
    };
  }
  
  // Step 2: Calculate max possible score (positive weights only)
  // newsRisk does NOT contribute to maxPossibleScore (it's a dampener)
  const maxPossibleScore =
    weights.orderBlock +
    weights.fairValueGap +
    weights.breakerBlock +
    weights.discountPremium +
    weights.buySellLiquidity;
  
  // Step 3: Calculate raw score from present confluences
  let rawScore = 0;
  const contributions: Record<ConfluenceFactor, number> = {
    orderBlock: 0,
    fairValueGap: 0,
    breakerBlock: 0,
    discountPremium: 0,
    buySellLiquidity: 0,
    newsRisk: 0
  };
  const present: ConfluenceFactor[] = [];
  const missing: ConfluenceFactor[] = [];
  const dampenersApplied: DampenerImpact[] = [];
  
  // Process each confluence factor
  if (scenario.optionalConfluences.orderBlock === true) {
    rawScore += weights.orderBlock;
    contributions.orderBlock = weights.orderBlock;
    present.push('orderBlock');
  } else {
    missing.push('orderBlock');
  }
  
  if (scenario.optionalConfluences.fairValueGap === true) {
    rawScore += weights.fairValueGap;
    contributions.fairValueGap = weights.fairValueGap;
    present.push('fairValueGap');
  } else {
    missing.push('fairValueGap');
  }
  
  if (scenario.optionalConfluences.breakerBlock === true) {
    rawScore += weights.breakerBlock;
    contributions.breakerBlock = weights.breakerBlock;
    present.push('breakerBlock');
  } else {
    missing.push('breakerBlock');
  }
  
  if (scenario.optionalConfluences.discountPremium === true) {
    rawScore += weights.discountPremium;
    contributions.discountPremium = weights.discountPremium;
    present.push('discountPremium');
  } else {
    missing.push('discountPremium');
  }
  
  if (scenario.optionalConfluences.buySellLiquidity === true) {
    rawScore += weights.buySellLiquidity;
    contributions.buySellLiquidity = weights.buySellLiquidity;
    present.push('buySellLiquidity');
  } else {
    missing.push('buySellLiquidity');
  }
  
  // Step 4: Apply dampeners
  // newsRisk is a dampener - when true, it reduces the score
  if (scenario.optionalConfluences.newsRisk === true) {
    rawScore += weights.newsRisk; // newsRisk weight is typically negative
    contributions.newsRisk = weights.newsRisk;
    present.push('newsRisk');
    dampenersApplied.push({
      factor: 'newsRisk',
      impact: weights.newsRisk
    });
  } else {
    missing.push('newsRisk');
  }
  
  // Step 5: Normalize to 0-100 scale
  // Prevent division by zero
  const normalizedScore = maxPossibleScore > 0
    ? Math.max(0, Math.min(100, (rawScore / maxPossibleScore) * 100))
    : 0;
  
  // confidence is an alias of normalizedScore (same value)
  const confidence = normalizedScore;
  
  // Step 6: Build breakdown
  const breakdown: ConfluenceBreakdown = {
    present,
    missing,
    contributions,
    dampenersApplied
  };
  
  // Build final score object
  const score: ConfluenceScore = {
    scenarioId: scenario.id,
    rawScore,
    normalizedScore,
    confidence,
    breakdown,
    evaluatedAt
  };
  
  return {
    success: true,
    score
  };
}
