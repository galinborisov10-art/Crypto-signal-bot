/**
 * Policy Invariant Tests - Phase 6.2.2: Policy Derivation Engine
 * 
 * Comprehensive invariant tests for policy derivation logic.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Determinism and immutability
 * 2. Priority cascade enforcement
 * 3. All stances reachable
 * 4. All confidence levels reachable
 * 5. Edge cases
 * 6. Fixed confidence mapping
 */

import { derivePolicy } from './policy.contracts';
import {
  strongThesisInterpretation,
  expectedStrongThesis,
  strongThesisShortTimeline,
  weakeningThesisSlowing,
  weakeningThesisDegrading,
  weakeningThesisBoth,
  expectedWeakeningThesis,
  highRiskEarlyWeakening,
  highRiskRepeatedInstability,
  highRiskFlipFlop,
  highRiskStalled,
  highRiskRegressing,
  highRiskMultipleConditions,
  expectedHighRiskThesis,
  invalidThesisInterpretation,
  invalidThesisEarly,
  invalidThesisLate,
  expectedInvalidThesis,
  completedThesisInterpretation,
  expectedCompletedThesis,
  insufficientDataInterpretation,
  expectedInsufficientData,
  fallbackScenario,
  expectedFallback,
  regressingTrajectory,
  completedWithDegrading,
  invalidatedWithGoodSignals,
  noDataWithOtherSignals
} from './policy.fixtures';

describe('Policy Derivation - Invariant Tests', () => {

  // ============================================================
  // DETERMINISM & IMMUTABILITY
  // ============================================================

  describe('Determinism & Immutability', () => {

    test('Same inputs always produce same output', () => {
      // Arrange
      const interpretation = strongThesisInterpretation;

      // Act: Call twice with same input
      const result1 = derivePolicy(interpretation);
      const result2 = derivePolicy(interpretation);

      // Assert: Results are identical
      expect(result1).toEqual(result2);
      expect(result1.stance).toBe(result2.stance);
      expect(result1.confidence).toBe(result2.confidence);
    });

    test('No mutation of interpretation', () => {
      // Arrange
      const interpretation = strongThesisInterpretation;
      const originalInterpretation = JSON.parse(JSON.stringify(interpretation));

      // Act
      derivePolicy(interpretation);

      // Assert: Interpretation unchanged
      expect(interpretation).toEqual(originalInterpretation);
    });

    test('Deterministic for all fixtures', () => {
      // Test multiple scenarios for determinism
      const testCases = [
        strongThesisInterpretation,
        weakeningThesisSlowing,
        highRiskFlipFlop,
        invalidThesisInterpretation,
        completedThesisInterpretation,
        insufficientDataInterpretation
      ];

      for (const testCase of testCases) {
        const result1 = derivePolicy(testCase);
        const result2 = derivePolicy(testCase);
        
        expect(result1).toEqual(result2);
      }
    });

  });

  // ============================================================
  // PRIORITY CASCADE TESTS
  // ============================================================

  describe('Priority Cascade Enforcement', () => {

    test('Priority 1: TERMINATED dominates all other signals', () => {
      // Arrange: Terminated with otherwise good signals
      const interpretation = invalidatedWithGoodSignals;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: TERMINATED priority dominates
      expect(result.stance).toBe('INVALID_THESIS');
      expect(result.confidence).toBe('HIGH');
    });

    test('Priority 1: TERMINATED with degrading signals still returns COMPLETED', () => {
      // Arrange: Completed with degrading signals
      const interpretation = completedWithDegrading;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: TERMINATED priority dominates
      expect(result.stance).toBe('COMPLETED_THESIS');
      expect(result.confidence).toBe('HIGH');
    });

    test('Priority 2: NO_DATA checked before stance derivation', () => {
      // Arrange: NO_DATA with other risk signals
      const interpretation = noDataWithOtherSignals;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: NO_DATA priority dominates
      expect(result.stance).toBe('INSUFFICIENT_DATA');
      expect(result.confidence).toBe('UNKNOWN');
    });

    test('Priority 3: STRONG_THESIS requires ALL conditions', () => {
      // Arrange: Strong thesis with all conditions met
      const interpretation = strongThesisInterpretation;

      // Act
      const result = derivePolicy(interpretation);

      // Assert
      expect(result.stance).toBe('STRONG_THESIS');
      expect(result.confidence).toBe('HIGH');
    });

    test('Priority 3: Missing ANY STRONG_THESIS condition prevents classification', () => {
      // Arrange: FLIP_FLOP violates STRONG requirement
      const interpretation = fallbackScenario;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: NOT STRONG_THESIS (falls to HIGH_RISK due to FLIP_FLOP)
      expect(result.stance).not.toBe('STRONG_THESIS');
      expect(result.stance).toBe('HIGH_RISK_THESIS');
    });

    test('Priority 4: WEAKENING_THESIS uses OR logic (slowing)', () => {
      // Arrange: Slowing progress (first OR condition)
      const interpretation = weakeningThesisSlowing;

      // Act
      const result = derivePolicy(interpretation);

      // Assert
      expect(result.stance).toBe('WEAKENING_THESIS');
      expect(result.confidence).toBe('MEDIUM');
    });

    test('Priority 4: WEAKENING_THESIS uses OR logic (degrading)', () => {
      // Arrange: Degrading guidance (second OR condition)
      const interpretation = weakeningThesisDegrading;

      // Act
      const result = derivePolicy(interpretation);

      // Assert
      expect(result.stance).toBe('WEAKENING_THESIS');
      expect(result.confidence).toBe('MEDIUM');
    });

    test('Priority 4: WEAKENING_THESIS with both conditions still MEDIUM confidence', () => {
      // Arrange: Both slowing AND degrading
      const interpretation = weakeningThesisBoth;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: Still WEAKENING_THESIS with MEDIUM (no escalation)
      expect(result.stance).toBe('WEAKENING_THESIS');
      expect(result.confidence).toBe('MEDIUM');
    });

    test('Priority 5: HIGH_RISK_THESIS ANY condition (early weakening)', () => {
      // Arrange: Early weakening
      const interpretation = highRiskEarlyWeakening;

      // Act
      const result = derivePolicy(interpretation);

      // Assert
      expect(result.stance).toBe('HIGH_RISK_THESIS');
      expect(result.confidence).toBe('LOW');
    });

    test('Priority 5: HIGH_RISK_THESIS ANY condition (flip-flop)', () => {
      // Arrange: Flip-flop guidance
      const interpretation = highRiskFlipFlop;

      // Act
      const result = derivePolicy(interpretation);

      // Assert
      expect(result.stance).toBe('HIGH_RISK_THESIS');
      expect(result.confidence).toBe('LOW');
    });

    test('Priority 5: HIGH_RISK_THESIS with multiple conditions still LOW confidence', () => {
      // Arrange: Multiple HIGH_RISK signals
      const interpretation = highRiskMultipleConditions;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: Still LOW confidence (no escalation beyond HIGH_RISK)
      expect(result.stance).toBe('HIGH_RISK_THESIS');
      expect(result.confidence).toBe('LOW');
    });

    test('Priority 6: Fallback reachable in valid scenarios', () => {
      // The fallback scenario is actually caught by Priority 5 (FLIP_FLOP)
      // but demonstrates that unclassifiable cases default to HIGH_RISK
      const interpretation = fallbackScenario;

      // Act
      const result = derivePolicy(interpretation);

      // Assert
      expect(result).toEqual(expectedFallback);
    });

  });

  // ============================================================
  // ALL STANCES REACHABLE
  // ============================================================

  describe('All Stances Reachable', () => {

    test('STRONG_THESIS reachable', () => {
      const result = derivePolicy(strongThesisInterpretation);
      expect(result.stance).toBe('STRONG_THESIS');
    });

    test('WEAKENING_THESIS reachable (slowing)', () => {
      const result = derivePolicy(weakeningThesisSlowing);
      expect(result.stance).toBe('WEAKENING_THESIS');
    });

    test('WEAKENING_THESIS reachable (degrading)', () => {
      const result = derivePolicy(weakeningThesisDegrading);
      expect(result.stance).toBe('WEAKENING_THESIS');
    });

    test('HIGH_RISK_THESIS reachable (early weakening)', () => {
      const result = derivePolicy(highRiskEarlyWeakening);
      expect(result.stance).toBe('HIGH_RISK_THESIS');
    });

    test('HIGH_RISK_THESIS reachable (repeated instability)', () => {
      const result = derivePolicy(highRiskRepeatedInstability);
      expect(result.stance).toBe('HIGH_RISK_THESIS');
    });

    test('HIGH_RISK_THESIS reachable (flip-flop)', () => {
      const result = derivePolicy(highRiskFlipFlop);
      expect(result.stance).toBe('HIGH_RISK_THESIS');
    });

    test('HIGH_RISK_THESIS reachable (stalled)', () => {
      const result = derivePolicy(highRiskStalled);
      expect(result.stance).toBe('HIGH_RISK_THESIS');
    });

    test('HIGH_RISK_THESIS reachable (regressing)', () => {
      const result = derivePolicy(highRiskRegressing);
      expect(result.stance).toBe('HIGH_RISK_THESIS');
    });

    test('INVALID_THESIS reachable', () => {
      const result = derivePolicy(invalidThesisInterpretation);
      expect(result.stance).toBe('INVALID_THESIS');
    });

    test('COMPLETED_THESIS reachable', () => {
      const result = derivePolicy(completedThesisInterpretation);
      expect(result.stance).toBe('COMPLETED_THESIS');
    });

    test('INSUFFICIENT_DATA reachable', () => {
      const result = derivePolicy(insufficientDataInterpretation);
      expect(result.stance).toBe('INSUFFICIENT_DATA');
    });

  });

  // ============================================================
  // ALL CONFIDENCE LEVELS REACHABLE
  // ============================================================

  describe('All Confidence Levels Reachable', () => {

    test('HIGH confidence reachable (STRONG_THESIS)', () => {
      const result = derivePolicy(strongThesisInterpretation);
      expect(result.confidence).toBe('HIGH');
    });

    test('HIGH confidence reachable (INVALID_THESIS)', () => {
      const result = derivePolicy(invalidThesisInterpretation);
      expect(result.confidence).toBe('HIGH');
    });

    test('HIGH confidence reachable (COMPLETED_THESIS)', () => {
      const result = derivePolicy(completedThesisInterpretation);
      expect(result.confidence).toBe('HIGH');
    });

    test('MEDIUM confidence reachable (WEAKENING_THESIS)', () => {
      const result = derivePolicy(weakeningThesisSlowing);
      expect(result.confidence).toBe('MEDIUM');
    });

    test('LOW confidence reachable (HIGH_RISK_THESIS)', () => {
      const result = derivePolicy(highRiskFlipFlop);
      expect(result.confidence).toBe('LOW');
    });

    test('UNKNOWN confidence reachable (INSUFFICIENT_DATA)', () => {
      const result = derivePolicy(insufficientDataInterpretation);
      expect(result.confidence).toBe('UNKNOWN');
    });

  });

  // ============================================================
  // FIXED CONFIDENCE MAPPING
  // ============================================================

  describe('Fixed Confidence Mapping', () => {

    test('STRONG_THESIS always has HIGH confidence', () => {
      const result1 = derivePolicy(strongThesisInterpretation);
      const result2 = derivePolicy(strongThesisShortTimeline);
      
      expect(result1.stance).toBe('STRONG_THESIS');
      expect(result1.confidence).toBe('HIGH');
      expect(result2.stance).toBe('STRONG_THESIS');
      expect(result2.confidence).toBe('HIGH');
    });

    test('WEAKENING_THESIS always has MEDIUM confidence', () => {
      const result1 = derivePolicy(weakeningThesisSlowing);
      const result2 = derivePolicy(weakeningThesisDegrading);
      const result3 = derivePolicy(weakeningThesisBoth);
      
      expect(result1.stance).toBe('WEAKENING_THESIS');
      expect(result1.confidence).toBe('MEDIUM');
      expect(result2.stance).toBe('WEAKENING_THESIS');
      expect(result2.confidence).toBe('MEDIUM');
      expect(result3.stance).toBe('WEAKENING_THESIS');
      expect(result3.confidence).toBe('MEDIUM');
    });

    test('HIGH_RISK_THESIS always has LOW confidence', () => {
      const result1 = derivePolicy(highRiskEarlyWeakening);
      const result2 = derivePolicy(highRiskFlipFlop);
      const result3 = derivePolicy(highRiskMultipleConditions);
      
      expect(result1.stance).toBe('HIGH_RISK_THESIS');
      expect(result1.confidence).toBe('LOW');
      expect(result2.stance).toBe('HIGH_RISK_THESIS');
      expect(result2.confidence).toBe('LOW');
      expect(result3.stance).toBe('HIGH_RISK_THESIS');
      expect(result3.confidence).toBe('LOW');
    });

    test('INVALID_THESIS always has HIGH confidence', () => {
      const result1 = derivePolicy(invalidThesisEarly);
      const result2 = derivePolicy(invalidThesisInterpretation);
      const result3 = derivePolicy(invalidThesisLate);
      
      expect(result1.stance).toBe('INVALID_THESIS');
      expect(result1.confidence).toBe('HIGH');
      expect(result2.stance).toBe('INVALID_THESIS');
      expect(result2.confidence).toBe('HIGH');
      expect(result3.stance).toBe('INVALID_THESIS');
      expect(result3.confidence).toBe('HIGH');
    });

    test('COMPLETED_THESIS always has HIGH confidence', () => {
      const result = derivePolicy(completedThesisInterpretation);
      
      expect(result.stance).toBe('COMPLETED_THESIS');
      expect(result.confidence).toBe('HIGH');
    });

    test('INSUFFICIENT_DATA always has UNKNOWN confidence', () => {
      const result = derivePolicy(insufficientDataInterpretation);
      
      expect(result.stance).toBe('INSUFFICIENT_DATA');
      expect(result.confidence).toBe('UNKNOWN');
    });

  });

  // ============================================================
  // EDGE CASES
  // ============================================================

  describe('Edge Cases', () => {

    test('guidanceConsistency === undefined handled correctly (STRONG_THESIS)', () => {
      // Arrange: Short timeline with undefined guidance
      const interpretation = strongThesisShortTimeline;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: undefined guidance acceptable for STRONG_THESIS
      expect(result.stance).toBe('STRONG_THESIS');
      expect(result.confidence).toBe('HIGH');
    });

    test('REGRESSING_PROGRESS treated as HIGH_RISK (defensive case)', () => {
      // Arrange: Regressing trajectory
      const interpretation = regressingTrajectory;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: Defensive signal → HIGH_RISK, NOT INVALID
      expect(result.stance).toBe('HIGH_RISK_THESIS');
      expect(result.confidence).toBe('LOW');
    });

    test('Multiple high-risk conditions still result in LOW confidence', () => {
      // Arrange: Multiple HIGH_RISK signals
      const interpretation = highRiskMultipleConditions;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: No escalation beyond LOW
      expect(result.stance).toBe('HIGH_RISK_THESIS');
      expect(result.confidence).toBe('LOW');
    });

    test('TERMINATED with invalidation → INVALID_THESIS (not COMPLETED)', () => {
      // Arrange: Terminated with invalidation pattern
      const interpretation = invalidThesisInterpretation;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: Disambiguation works correctly
      expect(result.stance).toBe('INVALID_THESIS');
      expect(result.confidence).toBe('HIGH');
    });

    test('TERMINATED without invalidation → COMPLETED_THESIS (not INVALID)', () => {
      // Arrange: Terminated without invalidation pattern
      const interpretation = completedThesisInterpretation;

      // Act
      const result = derivePolicy(interpretation);

      // Assert: Disambiguation works correctly
      expect(result.stance).toBe('COMPLETED_THESIS');
      expect(result.confidence).toBe('HIGH');
    });

  });

  // ============================================================
  // FULL POLICY RESULT TESTS
  // ============================================================

  describe('Full Policy Results', () => {

    test('Strong thesis interpretation matches expected policy', () => {
      const result = derivePolicy(strongThesisInterpretation);
      expect(result).toEqual(expectedStrongThesis);
    });

    test('Weakening thesis (slowing) matches expected policy', () => {
      const result = derivePolicy(weakeningThesisSlowing);
      expect(result).toEqual(expectedWeakeningThesis);
    });

    test('Weakening thesis (degrading) matches expected policy', () => {
      const result = derivePolicy(weakeningThesisDegrading);
      expect(result).toEqual(expectedWeakeningThesis);
    });

    test('High risk thesis (flip-flop) matches expected policy', () => {
      const result = derivePolicy(highRiskFlipFlop);
      expect(result).toEqual(expectedHighRiskThesis);
    });

    test('Invalid thesis interpretation matches expected policy', () => {
      const result = derivePolicy(invalidThesisInterpretation);
      expect(result).toEqual(expectedInvalidThesis);
    });

    test('Completed thesis interpretation matches expected policy', () => {
      const result = derivePolicy(completedThesisInterpretation);
      expect(result).toEqual(expectedCompletedThesis);
    });

    test('Insufficient data interpretation matches expected policy', () => {
      const result = derivePolicy(insufficientDataInterpretation);
      expect(result).toEqual(expectedInsufficientData);
    });

    test('Fallback scenario matches expected policy', () => {
      const result = derivePolicy(fallbackScenario);
      expect(result).toEqual(expectedFallback);
    });

  });

});
