/**
 * Risk Contract Contracts - Phase 4.5: SL/TP Contracts (Design-First)
 * 
 * Pure, deterministic evaluation of risk structure for entry scenarios.
 * Implements SL/TP contract logic without execution or decision-making.
 * 
 * Contract Rules:
 * 1. ONLY EntryScenario.status === 'valid' can be evaluated
 * 2. SL must be valid type AND correctly positioned
 * 3. At least TP1 must exist
 * 4. RR must be >= 3 (using TP1 only)
 * 5. Early invalidation (no partial contracts)
 * 6. POI-based calculation (NOT execution prices)
 * 
 * Architecture Decisions:
 * - Pre-filtered POI inputs (no discovery here)
 * - TP1-only RR calculation (most conservative)
 * - Fixed TP probabilities (no heuristics)
 * - Early invalidation (fail fast)
 * 
 * Absolute Rules:
 * 1. MUST be deterministic
 * 2. No randomness
 * 3. Same inputs → same output
 * 4. MUST NOT mutate input objects
 * 5. NO execution, signals, or decision logic
 */

import { POIType } from '../poi';
import { EntryScenario, isScenarioValid } from '../entry-scenarios';
import { ConfluenceScore } from '../confluence-scoring';
import {
  RiskContract,
  RiskPOIs,
  StopLossContract,
  TakeProfitContract
} from './riskContract.types';

/**
 * Valid Stop Loss POI Types
 * 
 * Only these POI types can serve as stop loss.
 */
const VALID_SL_POI_TYPES = new Set<POIType>([
  POIType.OrderBlock,
  POIType.PreviousHigh,
  POIType.PreviousLow,
  POIType.BreakerBlock
]);

/**
 * Minimum Risk/Reward Ratio
 * 
 * Minimum acceptable RR for a valid risk contract.
 */
const MIN_RR = 3;

/**
 * Build Risk Contract
 * 
 * Pure function that evaluates the risk structure of an Entry Scenario.
 * Determines if the risk is structurally acceptable and produces SL/TP contracts.
 * 
 * Implementation Flow:
 * 1. Validate scenario status (must be 'valid')
 * 2. Extract entry POI from pois
 * 3. Select Stop Loss (filter, validate position, select best)
 * 4. Select Take Profits (filter, sort by distance, assign TP1-TP3)
 * 5. Calculate RR using POI price ranges (TP1 only)
 * 6. Validate RR >= 3
 * 7. Return valid or invalid contract
 * 
 * Early Invalidation:
 * - No valid SL → return invalid with 'NO_VALID_STOP'
 * - No valid TP → return invalid with 'NO_VALID_TARGETS'
 * - RR < 3 → return invalid with 'RR_TOO_LOW'
 * 
 * @param scenario - EntryScenario to evaluate (must be status === 'valid')
 * @param score - ConfluenceScore for the scenario (for context, not used in calculation)
 * @param pois - Pre-filtered RiskPOIs (entry + SL candidates + TP candidates)
 * @param evaluatedAt - Fixed timestamp for evaluation (Unix milliseconds)
 * @returns RiskContract with status 'valid' or 'invalid'
 * 
 * @remarks
 * - This function is pure and deterministic
 * - Does NOT throw exceptions
 * - Same inputs always produce identical output
 * - Input objects are never mutated
 * - evaluatedAt is a fixed timestamp, not dynamic
 * - Works ONLY for scenario.status === 'valid'
 */
export function buildRiskContract(
  scenario: EntryScenario,
  _score: ConfluenceScore,
  pois: RiskPOIs,
  evaluatedAt: number
): RiskContract {
  // Step 1: Validate scenario status
  // If scenario is not valid, we still need to return a contract (invalid)
  // However, the spec says this should only work for valid scenarios
  // So we'll return an invalid contract if scenario is not valid
  if (!isScenarioValid(scenario)) {
    return {
      scenarioId: scenario.id,
      stopLoss: {
        type: 'structure',
        referencePoiId: '',
        beyondStructure: false
      },
      takeProfits: [],
      rr: 0,
      status: 'invalid',
      invalidationReason: 'NO_VALID_STOP', // Default reason for invalid scenario
      evaluatedAt
    };
  }

  // Step 2: Extract entry POI
  const entryPOI = pois.entryPOI;

  // Determine scenario direction from entry POI direction bias
  const isBullish = entryPOI.directionBias === 'bullish';
  const isBearish = entryPOI.directionBias === 'bearish';

  // Step 3: Select Stop Loss
  const validSLPOIs = pois.stopLossCandidates.filter(poi => {
    // Check valid type
    if (!VALID_SL_POI_TYPES.has(poi.type)) {
      return false;
    }

    // Check position relative to entry
    if (isBullish) {
      // For bullish scenario, SL must be BELOW entry
      return poi.priceRange.high < entryPOI.priceRange.low;
    } else if (isBearish) {
      // For bearish scenario, SL must be ABOVE entry
      return poi.priceRange.low > entryPOI.priceRange.high;
    }

    return false;
  });

  if (validSLPOIs.length === 0) {
    return {
      scenarioId: scenario.id,
      stopLoss: {
        type: 'structure',
        referencePoiId: '',
        beyondStructure: false
      },
      takeProfits: [],
      rr: 0,
      status: 'invalid',
      invalidationReason: 'NO_VALID_STOP',
      evaluatedAt
    };
  }

  // Select the nearest valid SL POI
  const selectedSL = validSLPOIs.reduce((nearest, poi) => {
    const nearestDistance = isBullish
      ? entryPOI.priceRange.low - nearest.priceRange.high
      : nearest.priceRange.low - entryPOI.priceRange.high;

    const poiDistance = isBullish
      ? entryPOI.priceRange.low - poi.priceRange.high
      : poi.priceRange.low - entryPOI.priceRange.high;

    return poiDistance < nearestDistance ? poi : nearest;
  });

  // Build Stop Loss Contract
  const stopLoss: StopLossContract = {
    type: selectedSL.type === POIType.OrderBlock ? 'orderBlock' : 'structure',
    referencePoiId: selectedSL.id,
    // Simplified beyondStructure logic: true for valid SL POIs
    // (can be refined based on structural boundary analysis)
    beyondStructure: true
  };

  // Step 4: Select Take Profits
  const validTPPOIs = pois.takeProfitCandidates.filter(poi => {
    // Check position relative to entry (must be in profit direction)
    if (isBullish) {
      // For bullish scenario, TP must be ABOVE entry
      return poi.priceRange.low > entryPOI.priceRange.high;
    } else if (isBearish) {
      // For bearish scenario, TP must be BELOW entry
      return poi.priceRange.high < entryPOI.priceRange.low;
    }

    return false;
  });

  if (validTPPOIs.length === 0) {
    return {
      scenarioId: scenario.id,
      stopLoss,
      takeProfits: [],
      rr: 0,
      status: 'invalid',
      invalidationReason: 'NO_VALID_TARGETS',
      evaluatedAt
    };
  }

  // Sort TP POIs by distance (nearest to farthest)
  const sortedTPPOIs = [...validTPPOIs].sort((a, b) => {
    const aDistance = isBullish
      ? a.priceRange.low - entryPOI.priceRange.high
      : entryPOI.priceRange.low - a.priceRange.high;

    const bDistance = isBullish
      ? b.priceRange.low - entryPOI.priceRange.high
      : entryPOI.priceRange.low - b.priceRange.high;

    return aDistance - bDistance;
  });

  // Assign TP1, TP2, TP3 with fixed probabilities
  const takeProfits: TakeProfitContract[] = [];

  if (sortedTPPOIs[0]) {
    takeProfits.push({
      level: 'TP1',
      targetPoiId: sortedTPPOIs[0].id,
      probability: 'high'
    });
  }

  if (sortedTPPOIs[1]) {
    takeProfits.push({
      level: 'TP2',
      targetPoiId: sortedTPPOIs[1].id,
      probability: 'medium'
    });
  }

  if (sortedTPPOIs[2]) {
    takeProfits.push({
      level: 'TP3',
      targetPoiId: sortedTPPOIs[2].id,
      probability: 'low'
    });
  }

  // Step 5: Calculate RR using POI price ranges (TP1 only)
  const tp1POI = sortedTPPOIs[0]!; // We know it exists because we checked earlier

  let risk: number;
  let reward: number;

  if (isBullish) {
    // Bullish scenario:
    // risk = entryPOI.priceRange.low - stopLossPOI.priceRange.high
    // reward = takeProfitPOI.priceRange.low - entryPOI.priceRange.high
    risk = entryPOI.priceRange.low - selectedSL.priceRange.high;
    reward = tp1POI.priceRange.low - entryPOI.priceRange.high;
  } else {
    // Bearish scenario:
    // risk = stopLossPOI.priceRange.low - entryPOI.priceRange.high
    // reward = entryPOI.priceRange.low - takeProfitPOI.priceRange.high
    risk = selectedSL.priceRange.low - entryPOI.priceRange.high;
    reward = entryPOI.priceRange.low - tp1POI.priceRange.high;
  }

  const rr = risk > 0 ? reward / risk : 0;

  // Step 6: Validate RR >= 3
  if (rr < MIN_RR) {
    return {
      scenarioId: scenario.id,
      stopLoss,
      takeProfits,
      rr,
      status: 'invalid',
      invalidationReason: 'RR_TOO_LOW',
      evaluatedAt
    };
  }

  // Step 7: Return valid contract
  return {
    scenarioId: scenario.id,
    stopLoss,
    takeProfits,
    rr,
    status: 'valid',
    evaluatedAt
  };
}

/**
 * Check if Risk Contract is Valid
 * 
 * Helper function to check if a risk contract is valid.
 * 
 * @param contract - RiskContract to check
 * @returns true if contract status is 'valid', false otherwise
 */
export function isRiskContractValid(contract: RiskContract): boolean {
  return contract.status === 'valid';
}

/**
 * Check if Risk Contract is Invalid
 * 
 * Helper function to check if a risk contract is invalid.
 * 
 * @param contract - RiskContract to check
 * @returns true if contract status is 'invalid', false otherwise
 */
export function isRiskContractInvalid(contract: RiskContract): boolean {
  return contract.status === 'invalid';
}
