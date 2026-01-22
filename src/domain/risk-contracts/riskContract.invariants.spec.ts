/**
 * Risk Contract Invariant Tests - Phase 4.5: SL/TP Contracts
 * 
 * Comprehensive tests for risk contract invariants.
 * Tests are semantic, not implementation-specific.
 * 
 * Test Coverage:
 * 1. Determinism
 * 2. SL Placement Rules
 * 3. TP Selection Order
 * 4. RR Enforcement
 * 5. Invalidation Reasons
 * 6. Immutability
 * 7. No Execution Logic Leakage
 */

import {
  buildRiskContract,
  isRiskContractValid,
  isRiskContractInvalid
} from './riskContract.contracts';

import {
  RiskPOIs
} from './riskContract.types';

import {
  T0,
  validBullishScenario,
  validBearishScenario,
  formingScenario,
  validConfluenceScore,
  validBullishRiskPOIs,
  validBearishRiskPOIs,
  noValidStopRiskPOIs,
  noValidTargetsRiskPOIs,
  lowRRRiskPOIs,
  invalidSLTypeRiskPOIs,
  invalidSLPositionRiskPOIs,
  bullishEntryPOI,
  validBullishSLPOI,
  validBullishTP1POI,
  validBullishTP2POI
} from './riskContract.fixtures';

describe('Risk Contract Invariant Tests - Phase 4.5', () => {
  
  describe('1. Determinism', () => {
    
    test('same inputs produce same output (deterministic replay)', () => {
      const result1 = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      const result2 = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result1).toEqual(result2);
    });

    test('fixed evaluatedAt produces consistent results', () => {
      const result1 = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      const result2 = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result1.evaluatedAt).toBe(T0);
      expect(result2.evaluatedAt).toBe(T0);
      expect(result1.evaluatedAt).toBe(result2.evaluatedAt);
    });

    test('different timestamps produce different evaluatedAt but same logic', () => {
      const T1 = T0 + 1000;

      const result1 = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      const result2 = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T1
      );

      expect(result1.evaluatedAt).toBe(T0);
      expect(result2.evaluatedAt).toBe(T1);
      
      // Same logic results, different timestamps
      expect(result1.status).toBe(result2.status);
      expect(result1.rr).toBe(result2.rr);
      expect(result1.stopLoss).toEqual(result2.stopLoss);
      expect(result1.takeProfits).toEqual(result2.takeProfits);
    });
  });

  describe('2. SL Placement Rules', () => {
    
    test('valid SL POI types accepted (OrderBlock)', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      expect(result.stopLoss.type).toBe('orderBlock');
    });

    test('valid SL POI types accepted (PreviousHigh, PreviousLow, BreakerBlock)', () => {
      const result = buildRiskContract(
        validBearishScenario,
        validConfluenceScore,
        validBearishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      expect(result.stopLoss.type).toBe('structure');
    });

    test('invalid SL POI types rejected (FairValueGap)', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        invalidSLTypeRiskPOIs,
        T0
      );

      expect(result.status).toBe('invalid');
      expect(result.invalidationReason).toBe('NO_VALID_STOP');
    });

    test('bullish scenario: SL POI must be BELOW entry', () => {
      // Valid case: SL below entry
      const validResult = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(validResult.status).toBe('valid');

      // Invalid case: SL above entry
      const invalidResult = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        invalidSLPositionRiskPOIs,
        T0
      );

      expect(invalidResult.status).toBe('invalid');
      expect(invalidResult.invalidationReason).toBe('NO_VALID_STOP');
    });

    test('bearish scenario: SL POI must be ABOVE entry', () => {
      const result = buildRiskContract(
        validBearishScenario,
        validConfluenceScore,
        validBearishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      expect(result.stopLoss.referencePoiId).toBe('sl-bearish-001');
    });

    test('beyondStructure correctly calculated', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      expect(result.stopLoss.beyondStructure).toBe(true);
    });

    test('no valid SL candidates → invalidation', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        noValidStopRiskPOIs,
        T0
      );

      expect(result.status).toBe('invalid');
      expect(result.invalidationReason).toBe('NO_VALID_STOP');
    });
  });

  describe('3. TP Selection Order', () => {
    
    test('TP1 → TP2 → TP3 assignment correct', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      expect(result.takeProfits).toHaveLength(3);
      
      expect(result.takeProfits[0]?.level).toBe('TP1');
      expect(result.takeProfits[1]?.level).toBe('TP2');
      expect(result.takeProfits[2]?.level).toBe('TP3');
    });

    test('distance-based ordering (nearest → farthest)', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      
      // TP1 should be the nearest (tp-bullish-001 at 180-185)
      expect(result.takeProfits[0]?.targetPoiId).toBe('tp-bullish-001');
      
      // TP2 should be next (tp-bullish-002 at 220-225)
      expect(result.takeProfits[1]?.targetPoiId).toBe('tp-bullish-002');
      
      // TP3 should be farthest (tp-bullish-003 at 280-285)
      expect(result.takeProfits[2]?.targetPoiId).toBe('tp-bullish-003');
    });

    test('fixed probability assignment (high → medium → low)', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      
      expect(result.takeProfits[0]?.probability).toBe('high');
      expect(result.takeProfits[1]?.probability).toBe('medium');
      expect(result.takeProfits[2]?.probability).toBe('low');
    });

    test('at least TP1 must exist', () => {
      const singleTPPOIs: RiskPOIs = {
        entryPOI: bullishEntryPOI,
        stopLossCandidates: [validBullishSLPOI],
        takeProfitCandidates: [validBullishTP1POI] // Only TP1
      };

      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        singleTPPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      expect(result.takeProfits).toHaveLength(1);
      expect(result.takeProfits[0]?.level).toBe('TP1');
      expect(result.takeProfits[0]?.probability).toBe('high');
    });

    test('TP2 and TP3 are optional', () => {
      const twoTPPOIs: RiskPOIs = {
        entryPOI: bullishEntryPOI,
        stopLossCandidates: [validBullishSLPOI],
        takeProfitCandidates: [validBullishTP1POI, validBullishTP2POI] // Only TP1 and TP2
      };

      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        twoTPPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      expect(result.takeProfits).toHaveLength(2);
      expect(result.takeProfits[0]?.level).toBe('TP1');
      expect(result.takeProfits[1]?.level).toBe('TP2');
    });

    test('no valid TP candidates → invalidation', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        noValidTargetsRiskPOIs,
        T0
      );

      expect(result.status).toBe('invalid');
      expect(result.invalidationReason).toBe('NO_VALID_TARGETS');
    });
  });

  describe('4. RR Enforcement', () => {
    
    test('RR calculated correctly using POI price ranges (bullish)', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      
      // Expected calculation:
      // risk = entryPOI.priceRange.low - stopLossPOI.priceRange.high
      //      = 120 - 105 = 15
      // reward = takeProfitPOI.priceRange.low - entryPOI.priceRange.high
      //        = 180 - 125 = 55
      // rr = 55 / 15 = 3.67
      expect(result.rr).toBeCloseTo(3.67, 2);
    });

    test('RR calculated correctly using POI price ranges (bearish)', () => {
      const result = buildRiskContract(
        validBearishScenario,
        validConfluenceScore,
        validBearishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      
      // Expected calculation:
      // risk = stopLossPOI.priceRange.low - entryPOI.priceRange.high
      //      = 140 - 125 = 15
      // reward = entryPOI.priceRange.low - takeProfitPOI.priceRange.high
      //        = 120 - 65 = 55
      // rr = 55 / 15 = 3.67
      expect(result.rr).toBeCloseTo(3.67, 2);
    });

    test('RR >= 3 for valid contracts', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      expect(result.rr).toBeGreaterThanOrEqual(3);
    });

    test('RR < 3 → invalidation with RR_TOO_LOW', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        lowRRRiskPOIs,
        T0
      );

      expect(result.status).toBe('invalid');
      expect(result.invalidationReason).toBe('RR_TOO_LOW');
      expect(result.rr).toBeLessThan(3);
    });

    test('RR uses TP1 only (not TP2 or TP3)', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      
      // RR should be based on TP1 (180-185), not TP2 (220-225) or TP3 (280-285)
      // If it used TP2 or TP3, RR would be much higher
      expect(result.rr).toBeCloseTo(3.67, 2);
      expect(result.rr).toBeLessThan(5); // Sanity check that it's not using TP2 or TP3
    });
  });

  describe('5. Invalidation Reasons', () => {
    
    test('NO_VALID_STOP when no SL candidates qualify', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        noValidStopRiskPOIs,
        T0
      );

      expect(result.status).toBe('invalid');
      expect(result.invalidationReason).toBe('NO_VALID_STOP');
    });

    test('NO_VALID_TARGETS when no TP candidates qualify', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        noValidTargetsRiskPOIs,
        T0
      );

      expect(result.status).toBe('invalid');
      expect(result.invalidationReason).toBe('NO_VALID_TARGETS');
    });

    test('RR_TOO_LOW when RR < 3', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        lowRRRiskPOIs,
        T0
      );

      expect(result.status).toBe('invalid');
      expect(result.invalidationReason).toBe('RR_TOO_LOW');
    });

    test('correct invalidation reason returned', () => {
      const noStopResult = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        noValidStopRiskPOIs,
        T0
      );

      const noTargetsResult = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        noValidTargetsRiskPOIs,
        T0
      );

      const lowRRResult = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        lowRRRiskPOIs,
        T0
      );

      expect(noStopResult.invalidationReason).toBe('NO_VALID_STOP');
      expect(noTargetsResult.invalidationReason).toBe('NO_VALID_TARGETS');
      expect(lowRRResult.invalidationReason).toBe('RR_TOO_LOW');
    });

    test('no invalidation reason for valid contracts', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('valid');
      expect(result.invalidationReason).toBeUndefined();
    });

    test('forming scenario produces invalid contract', () => {
      const result = buildRiskContract(
        formingScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result.status).toBe('invalid');
      expect(result.invalidationReason).toBeDefined();
    });
  });

  describe('6. Immutability', () => {
    
    test('no mutation of input scenario object', () => {
      const scenarioCopy = { ...validBullishScenario };
      
      buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(validBullishScenario).toEqual(scenarioCopy);
    });

    test('no mutation of input score object', () => {
      const scoreCopy = { ...validConfluenceScore };
      
      buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(validConfluenceScore).toEqual(scoreCopy);
    });

    test('no mutation of input pois objects', () => {
      const poisCopy = {
        entryPOI: { ...validBullishRiskPOIs.entryPOI },
        stopLossCandidates: [...validBullishRiskPOIs.stopLossCandidates],
        takeProfitCandidates: [...validBullishRiskPOIs.takeProfitCandidates]
      };
      
      buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(validBullishRiskPOIs.entryPOI).toEqual(poisCopy.entryPOI);
      expect(validBullishRiskPOIs.stopLossCandidates).toEqual(poisCopy.stopLossCandidates);
      expect(validBullishRiskPOIs.takeProfitCandidates).toEqual(poisCopy.takeProfitCandidates);
    });
  });

  describe('7. No Execution Logic Leakage', () => {
    
    test('no order placement logic', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      // Check that result only contains contract fields, no execution fields
      expect(result).not.toHaveProperty('orderType');
      expect(result).not.toHaveProperty('orderPrice');
      expect(result).not.toHaveProperty('quantity');
      expect(result).not.toHaveProperty('leverage');
    });

    test('no position sizing', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result).not.toHaveProperty('positionSize');
      expect(result).not.toHaveProperty('capitalAllocation');
      expect(result).not.toHaveProperty('riskAmount');
    });

    test('no execution prices', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(result).not.toHaveProperty('entryPrice');
      expect(result).not.toHaveProperty('stopLossPrice');
      expect(result).not.toHaveProperty('takeProfitPrice');
      
      // Only POI references should exist
      expect(result.stopLoss.referencePoiId).toBeDefined();
      expect(result.takeProfits[0]?.targetPoiId).toBeDefined();
    });
  });

  describe('8. Helper Functions', () => {
    
    test('isRiskContractValid returns true for valid contracts', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(isRiskContractValid(result)).toBe(true);
    });

    test('isRiskContractValid returns false for invalid contracts', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        noValidStopRiskPOIs,
        T0
      );

      expect(isRiskContractValid(result)).toBe(false);
    });

    test('isRiskContractInvalid returns true for invalid contracts', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        lowRRRiskPOIs,
        T0
      );

      expect(isRiskContractInvalid(result)).toBe(true);
    });

    test('isRiskContractInvalid returns false for valid contracts', () => {
      const result = buildRiskContract(
        validBullishScenario,
        validConfluenceScore,
        validBullishRiskPOIs,
        T0
      );

      expect(isRiskContractInvalid(result)).toBe(false);
    });
  });
});
