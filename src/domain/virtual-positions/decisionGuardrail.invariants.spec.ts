/**
 * Decision Guardrail Invariant Tests - Phase 6.3.2: Decision Guardrail Derivation Engine
 * 
 * Comprehensive invariant tests for decision guardrail derivation logic.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Determinism and immutability
 * 2. All stances reachable
 * 3. Permission exclusivity
 * 4. Reason mapping (1:1 with PolicyStance)
 * 5. Confidence independence
 * 6. ESCALATION_ONLY never returned
 */

import { deriveDecisionGuardrail } from './decisionGuardrail.contracts';
import { PolicyResult } from './policy.types';
import {
  strongThesisPolicyResult,
  strongThesisMediumConfidence,
  strongThesisLowConfidence,
  expectedAllowedGuardrail,
  weakeningThesisPolicyResult,
  weakeningThesisHighConfidence,
  weakeningThesisLowConfidence,
  expectedManualReviewWeakening,
  highRiskThesisPolicyResult,
  highRiskThesisHighConfidence,
  highRiskThesisMediumConfidence,
  expectedManualReviewHighRisk,
  invalidThesisPolicyResult,
  invalidThesisMediumConfidence,
  invalidThesisLowConfidence,
  expectedBlockedInvalid,
  completedThesisPolicyResult,
  completedThesisMediumConfidence,
  completedThesisLowConfidence,
  expectedBlockedCompleted,
  insufficientDataPolicyResult,
  insufficientDataHighConfidence,
  insufficientDataMediumConfidence,
  insufficientDataLowConfidence,
  expectedBlockedInsufficientData
} from './decisionGuardrail.fixtures';

describe('Decision Guardrail Derivation - Invariant Tests', () => {

  // ============================================================
  // DETERMINISM & IMMUTABILITY
  // ============================================================

  describe('Determinism & Immutability', () => {

    test('Same inputs always produce same output', () => {
      // Arrange
      const policyResult = strongThesisPolicyResult;

      // Act: Call twice with same input
      const result1 = deriveDecisionGuardrail(policyResult);
      const result2 = deriveDecisionGuardrail(policyResult);

      // Assert: Results are identical
      expect(result1).toEqual(result2);
      expect(result1.permission).toBe(result2.permission);
      expect(result1.reason).toBe(result2.reason);
    });

    test('No mutation of PolicyResult', () => {
      // Arrange
      const policyResult = strongThesisPolicyResult;
      const originalPolicyResult = JSON.parse(JSON.stringify(policyResult));

      // Act
      deriveDecisionGuardrail(policyResult);

      // Assert: PolicyResult unchanged
      expect(policyResult).toEqual(originalPolicyResult);
    });

    test('Deterministic for all fixtures', () => {
      // Test multiple scenarios for determinism
      const testCases = [
        strongThesisPolicyResult,
        weakeningThesisPolicyResult,
        highRiskThesisPolicyResult,
        invalidThesisPolicyResult,
        completedThesisPolicyResult,
        insufficientDataPolicyResult
      ];

      for (const testCase of testCases) {
        const result1 = deriveDecisionGuardrail(testCase);
        const result2 = deriveDecisionGuardrail(testCase);
        
        expect(result1).toEqual(result2);
      }
    });

  });

  // ============================================================
  // ALL STANCES REACHABLE
  // ============================================================

  describe('All Stances Reachable', () => {

    test('STRONG_THESIS → ALLOWED + STRONG_POLICY', () => {
      // Arrange
      const policyResult = strongThesisPolicyResult;

      // Act
      const result = deriveDecisionGuardrail(policyResult);

      // Assert
      expect(result).toEqual(expectedAllowedGuardrail);
      expect(result.permission).toBe('ALLOWED');
      expect(result.reason).toBe('STRONG_POLICY');
    });

    test('WEAKENING_THESIS → MANUAL_REVIEW_ONLY + WEAKENING_POLICY', () => {
      // Arrange
      const policyResult = weakeningThesisPolicyResult;

      // Act
      const result = deriveDecisionGuardrail(policyResult);

      // Assert
      expect(result).toEqual(expectedManualReviewWeakening);
      expect(result.permission).toBe('MANUAL_REVIEW_ONLY');
      expect(result.reason).toBe('WEAKENING_POLICY');
    });

    test('HIGH_RISK_THESIS → MANUAL_REVIEW_ONLY + HIGH_RISK_POLICY', () => {
      // Arrange
      const policyResult = highRiskThesisPolicyResult;

      // Act
      const result = deriveDecisionGuardrail(policyResult);

      // Assert
      expect(result).toEqual(expectedManualReviewHighRisk);
      expect(result.permission).toBe('MANUAL_REVIEW_ONLY');
      expect(result.reason).toBe('HIGH_RISK_POLICY');
    });

    test('INVALID_THESIS → BLOCKED + INVALID_POLICY', () => {
      // Arrange
      const policyResult = invalidThesisPolicyResult;

      // Act
      const result = deriveDecisionGuardrail(policyResult);

      // Assert
      expect(result).toEqual(expectedBlockedInvalid);
      expect(result.permission).toBe('BLOCKED');
      expect(result.reason).toBe('INVALID_POLICY');
    });

    test('COMPLETED_THESIS → BLOCKED + COMPLETED_POLICY', () => {
      // Arrange
      const policyResult = completedThesisPolicyResult;

      // Act
      const result = deriveDecisionGuardrail(policyResult);

      // Assert
      expect(result).toEqual(expectedBlockedCompleted);
      expect(result.permission).toBe('BLOCKED');
      expect(result.reason).toBe('COMPLETED_POLICY');
    });

    test('INSUFFICIENT_DATA → BLOCKED + INSUFFICIENT_DATA', () => {
      // Arrange
      const policyResult = insufficientDataPolicyResult;

      // Act
      const result = deriveDecisionGuardrail(policyResult);

      // Assert
      expect(result).toEqual(expectedBlockedInsufficientData);
      expect(result.permission).toBe('BLOCKED');
      expect(result.reason).toBe('INSUFFICIENT_DATA');
    });

  });

  // ============================================================
  // PERMISSION EXCLUSIVITY
  // ============================================================

  describe('Permission Exclusivity', () => {

    test('ALLOWED is returned ONLY for STRONG_THESIS', () => {
      // Arrange: All stances
      const allPolicyResults = [
        strongThesisPolicyResult,           // Should be ALLOWED
        weakeningThesisPolicyResult,        // Should NOT be ALLOWED
        highRiskThesisPolicyResult,         // Should NOT be ALLOWED
        invalidThesisPolicyResult,          // Should NOT be ALLOWED
        completedThesisPolicyResult,        // Should NOT be ALLOWED
        insufficientDataPolicyResult        // Should NOT be ALLOWED
      ];

      // Act & Assert
      const results = allPolicyResults.map(pr => deriveDecisionGuardrail(pr));
      
      // Only STRONG_THESIS should return ALLOWED
      expect(results[0]!.permission).toBe('ALLOWED');
      
      // All others should NOT be ALLOWED
      expect(results[1]!.permission).not.toBe('ALLOWED');
      expect(results[2]!.permission).not.toBe('ALLOWED');
      expect(results[3]!.permission).not.toBe('ALLOWED');
      expect(results[4]!.permission).not.toBe('ALLOWED');
      expect(results[5]!.permission).not.toBe('ALLOWED');
    });

    test('BLOCKED is returned ONLY for INVALID_THESIS, COMPLETED_THESIS, INSUFFICIENT_DATA', () => {
      // Arrange: All stances
      const allPolicyResults = [
        strongThesisPolicyResult,           // Should NOT be BLOCKED
        weakeningThesisPolicyResult,        // Should NOT be BLOCKED
        highRiskThesisPolicyResult,         // Should NOT be BLOCKED
        invalidThesisPolicyResult,          // Should be BLOCKED
        completedThesisPolicyResult,        // Should be BLOCKED
        insufficientDataPolicyResult        // Should be BLOCKED
      ];

      // Act & Assert
      const results = allPolicyResults.map(pr => deriveDecisionGuardrail(pr));
      
      // First three should NOT be BLOCKED
      expect(results[0]!.permission).not.toBe('BLOCKED');
      expect(results[1]!.permission).not.toBe('BLOCKED');
      expect(results[2]!.permission).not.toBe('BLOCKED');
      
      // Last three should be BLOCKED
      expect(results[3]!.permission).toBe('BLOCKED');
      expect(results[4]!.permission).toBe('BLOCKED');
      expect(results[5]!.permission).toBe('BLOCKED');
    });

    test('MANUAL_REVIEW_ONLY is returned ONLY for WEAKENING_THESIS and HIGH_RISK_THESIS', () => {
      // Arrange: All stances
      const allPolicyResults = [
        strongThesisPolicyResult,           // Should NOT be MANUAL_REVIEW_ONLY
        weakeningThesisPolicyResult,        // Should be MANUAL_REVIEW_ONLY
        highRiskThesisPolicyResult,         // Should be MANUAL_REVIEW_ONLY
        invalidThesisPolicyResult,          // Should NOT be MANUAL_REVIEW_ONLY
        completedThesisPolicyResult,        // Should NOT be MANUAL_REVIEW_ONLY
        insufficientDataPolicyResult        // Should NOT be MANUAL_REVIEW_ONLY
      ];

      // Act & Assert
      const results = allPolicyResults.map(pr => deriveDecisionGuardrail(pr));
      
      // STRONG_THESIS should NOT be MANUAL_REVIEW_ONLY
      expect(results[0]!.permission).not.toBe('MANUAL_REVIEW_ONLY');
      
      // WEAKENING and HIGH_RISK should be MANUAL_REVIEW_ONLY
      expect(results[1]!.permission).toBe('MANUAL_REVIEW_ONLY');
      expect(results[2]!.permission).toBe('MANUAL_REVIEW_ONLY');
      
      // Terminal states should NOT be MANUAL_REVIEW_ONLY
      expect(results[3]!.permission).not.toBe('MANUAL_REVIEW_ONLY');
      expect(results[4]!.permission).not.toBe('MANUAL_REVIEW_ONLY');
      expect(results[5]!.permission).not.toBe('MANUAL_REVIEW_ONLY');
    });

    test('ESCALATION_ONLY is NEVER returned in v1.0', () => {
      // Arrange: All stances
      const allPolicyResults = [
        strongThesisPolicyResult,
        weakeningThesisPolicyResult,
        highRiskThesisPolicyResult,
        invalidThesisPolicyResult,
        completedThesisPolicyResult,
        insufficientDataPolicyResult
      ];

      // Act & Assert
      const results = allPolicyResults.map(pr => deriveDecisionGuardrail(pr));
      
      // ESCALATION_ONLY should NEVER appear
      for (const result of results) {
        expect(result.permission).not.toBe('ESCALATION_ONLY');
      }
    });

  });

  // ============================================================
  // REASON MAPPING (1:1 with PolicyStance)
  // ============================================================

  describe('Reason Mapping', () => {

    test('STRONG_THESIS always maps to STRONG_POLICY', () => {
      const result = deriveDecisionGuardrail(strongThesisPolicyResult);
      expect(result.reason).toBe('STRONG_POLICY');
    });

    test('WEAKENING_THESIS always maps to WEAKENING_POLICY', () => {
      const result = deriveDecisionGuardrail(weakeningThesisPolicyResult);
      expect(result.reason).toBe('WEAKENING_POLICY');
    });

    test('HIGH_RISK_THESIS always maps to HIGH_RISK_POLICY', () => {
      const result = deriveDecisionGuardrail(highRiskThesisPolicyResult);
      expect(result.reason).toBe('HIGH_RISK_POLICY');
    });

    test('INVALID_THESIS always maps to INVALID_POLICY', () => {
      const result = deriveDecisionGuardrail(invalidThesisPolicyResult);
      expect(result.reason).toBe('INVALID_POLICY');
    });

    test('COMPLETED_THESIS always maps to COMPLETED_POLICY', () => {
      const result = deriveDecisionGuardrail(completedThesisPolicyResult);
      expect(result.reason).toBe('COMPLETED_POLICY');
    });

    test('INSUFFICIENT_DATA always maps to INSUFFICIENT_DATA', () => {
      const result = deriveDecisionGuardrail(insufficientDataPolicyResult);
      expect(result.reason).toBe('INSUFFICIENT_DATA');
    });

  });

  // ============================================================
  // CONFIDENCE INDEPENDENCE
  // ============================================================

  describe('Confidence Independence', () => {

    test('STRONG_THESIS with different confidence → same permission', () => {
      // Arrange: Same stance, different confidence
      const highConf = strongThesisPolicyResult;      // HIGH
      const mediumConf = strongThesisMediumConfidence; // MEDIUM
      const lowConf = strongThesisLowConfidence;       // LOW

      // Act
      const result1 = deriveDecisionGuardrail(highConf);
      const result2 = deriveDecisionGuardrail(mediumConf);
      const result3 = deriveDecisionGuardrail(lowConf);

      // Assert: All return ALLOWED
      expect(result1.permission).toBe('ALLOWED');
      expect(result2.permission).toBe('ALLOWED');
      expect(result3.permission).toBe('ALLOWED');
      
      // Assert: All return STRONG_POLICY
      expect(result1.reason).toBe('STRONG_POLICY');
      expect(result2.reason).toBe('STRONG_POLICY');
      expect(result3.reason).toBe('STRONG_POLICY');
    });

    test('WEAKENING_THESIS with different confidence → same permission', () => {
      // Arrange: Same stance, different confidence
      const mediumConf = weakeningThesisPolicyResult;     // MEDIUM
      const highConf = weakeningThesisHighConfidence;     // HIGH
      const lowConf = weakeningThesisLowConfidence;       // LOW

      // Act
      const result1 = deriveDecisionGuardrail(mediumConf);
      const result2 = deriveDecisionGuardrail(highConf);
      const result3 = deriveDecisionGuardrail(lowConf);

      // Assert: All return MANUAL_REVIEW_ONLY
      expect(result1.permission).toBe('MANUAL_REVIEW_ONLY');
      expect(result2.permission).toBe('MANUAL_REVIEW_ONLY');
      expect(result3.permission).toBe('MANUAL_REVIEW_ONLY');
      
      // Assert: All return WEAKENING_POLICY
      expect(result1.reason).toBe('WEAKENING_POLICY');
      expect(result2.reason).toBe('WEAKENING_POLICY');
      expect(result3.reason).toBe('WEAKENING_POLICY');
    });

    test('HIGH_RISK_THESIS with different confidence → same permission', () => {
      // Arrange: Same stance, different confidence
      const lowConf = highRiskThesisPolicyResult;         // LOW
      const highConf = highRiskThesisHighConfidence;      // HIGH
      const mediumConf = highRiskThesisMediumConfidence;  // MEDIUM

      // Act
      const result1 = deriveDecisionGuardrail(lowConf);
      const result2 = deriveDecisionGuardrail(highConf);
      const result3 = deriveDecisionGuardrail(mediumConf);

      // Assert: All return MANUAL_REVIEW_ONLY
      expect(result1.permission).toBe('MANUAL_REVIEW_ONLY');
      expect(result2.permission).toBe('MANUAL_REVIEW_ONLY');
      expect(result3.permission).toBe('MANUAL_REVIEW_ONLY');
      
      // Assert: All return HIGH_RISK_POLICY
      expect(result1.reason).toBe('HIGH_RISK_POLICY');
      expect(result2.reason).toBe('HIGH_RISK_POLICY');
      expect(result3.reason).toBe('HIGH_RISK_POLICY');
    });

    test('INVALID_THESIS with different confidence → same permission', () => {
      // Arrange: Same stance, different confidence
      const highConf = invalidThesisPolicyResult;         // HIGH
      const mediumConf = invalidThesisMediumConfidence;   // MEDIUM
      const lowConf = invalidThesisLowConfidence;         // LOW

      // Act
      const result1 = deriveDecisionGuardrail(highConf);
      const result2 = deriveDecisionGuardrail(mediumConf);
      const result3 = deriveDecisionGuardrail(lowConf);

      // Assert: All return BLOCKED
      expect(result1.permission).toBe('BLOCKED');
      expect(result2.permission).toBe('BLOCKED');
      expect(result3.permission).toBe('BLOCKED');
      
      // Assert: All return INVALID_POLICY
      expect(result1.reason).toBe('INVALID_POLICY');
      expect(result2.reason).toBe('INVALID_POLICY');
      expect(result3.reason).toBe('INVALID_POLICY');
    });

    test('COMPLETED_THESIS with different confidence → same permission', () => {
      // Arrange: Same stance, different confidence
      const highConf = completedThesisPolicyResult;       // HIGH
      const mediumConf = completedThesisMediumConfidence; // MEDIUM
      const lowConf = completedThesisLowConfidence;       // LOW

      // Act
      const result1 = deriveDecisionGuardrail(highConf);
      const result2 = deriveDecisionGuardrail(mediumConf);
      const result3 = deriveDecisionGuardrail(lowConf);

      // Assert: All return BLOCKED
      expect(result1.permission).toBe('BLOCKED');
      expect(result2.permission).toBe('BLOCKED');
      expect(result3.permission).toBe('BLOCKED');
      
      // Assert: All return COMPLETED_POLICY
      expect(result1.reason).toBe('COMPLETED_POLICY');
      expect(result2.reason).toBe('COMPLETED_POLICY');
      expect(result3.reason).toBe('COMPLETED_POLICY');
    });

    test('INSUFFICIENT_DATA with different confidence → same permission', () => {
      // Arrange: Same stance, different confidence
      const unknownConf = insufficientDataPolicyResult;     // UNKNOWN
      const highConf = insufficientDataHighConfidence;      // HIGH
      const mediumConf = insufficientDataMediumConfidence;  // MEDIUM
      const lowConf = insufficientDataLowConfidence;        // LOW

      // Act
      const result1 = deriveDecisionGuardrail(unknownConf);
      const result2 = deriveDecisionGuardrail(highConf);
      const result3 = deriveDecisionGuardrail(mediumConf);
      const result4 = deriveDecisionGuardrail(lowConf);

      // Assert: All return BLOCKED
      expect(result1.permission).toBe('BLOCKED');
      expect(result2.permission).toBe('BLOCKED');
      expect(result3.permission).toBe('BLOCKED');
      expect(result4.permission).toBe('BLOCKED');
      
      // Assert: All return INSUFFICIENT_DATA
      expect(result1.reason).toBe('INSUFFICIENT_DATA');
      expect(result2.reason).toBe('INSUFFICIENT_DATA');
      expect(result3.reason).toBe('INSUFFICIENT_DATA');
      expect(result4.reason).toBe('INSUFFICIENT_DATA');
    });

    test('Confidence is ignored in permission derivation (documentation test)', () => {
      // This test documents that PolicyConfidence is metadata only
      // and does NOT affect permission logic
      
      // Arrange: Create pairs with same stance, different confidence
      const testPairs: Array<[PolicyResult, PolicyResult]> = [
        [strongThesisPolicyResult, strongThesisMediumConfidence],
        [weakeningThesisPolicyResult, weakeningThesisHighConfidence],
        [highRiskThesisPolicyResult, highRiskThesisHighConfidence],
        [invalidThesisPolicyResult, invalidThesisMediumConfidence],
        [completedThesisPolicyResult, completedThesisMediumConfidence],
        [insufficientDataPolicyResult, insufficientDataHighConfidence]
      ];

      // Act & Assert: Each pair should have identical results
      for (const [first, second] of testPairs) {
        const result1 = deriveDecisionGuardrail(first);
        const result2 = deriveDecisionGuardrail(second);
        
        expect(result1).toEqual(result2);
        expect(result1.permission).toBe(result2.permission);
        expect(result1.reason).toBe(result2.reason);
      }
    });

  });

});
