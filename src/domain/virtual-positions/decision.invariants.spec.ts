/**
 * Decision Derivation Invariant Tests - Phase 6.4.2: Decision Derivation Engine
 * 
 * Comprehensive invariant tests for decision derivation logic.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Determinism and immutability
 * 2. All permissions reachable
 * 3. Action exclusivity
 * 4. Reason pass-through
 * 5. Guardrail respect
 */

import { deriveDecision } from './decision.contracts';
import { DecisionGuardrailResult } from './decisionGuardrail.types';
import {
  blockedGuardrailResult,
  expectedNoActionDecision,
  manualReviewGuardrailResult,
  expectedManualReviewDecision,
  allowedGuardrailResult,
  expectedPrepareEntryDecision,
  escalationGuardrailResult,
  expectedEscalationDecision,
  blockedCompletedGuardrailResult,
  blockedInsufficientDataGuardrailResult,
  manualReviewHighRiskGuardrailResult
} from './decision.fixtures';

describe('Decision Derivation - Invariant Tests', () => {

  // ============================================================
  // DETERMINISM & IMMUTABILITY
  // ============================================================

  describe('Determinism & Immutability', () => {

    test('Same inputs always produce same output', () => {
      // Arrange
      const guardrailResult = allowedGuardrailResult;

      // Act: Call twice with same input
      const result1 = deriveDecision(guardrailResult);
      const result2 = deriveDecision(guardrailResult);

      // Assert: Results are identical
      expect(result1).toEqual(result2);
      expect(result1.action).toBe(result2.action);
      expect(result1.reason).toBe(result2.reason);
    });

    test('No mutation of DecisionGuardrailResult', () => {
      // Arrange
      const guardrailResult = allowedGuardrailResult;
      const originalGuardrailResult = JSON.parse(JSON.stringify(guardrailResult));

      // Act
      deriveDecision(guardrailResult);

      // Assert: DecisionGuardrailResult unchanged
      expect(guardrailResult).toEqual(originalGuardrailResult);
    });

    test('Deterministic for all fixtures', () => {
      // Test multiple scenarios for determinism
      const testCases = [
        blockedGuardrailResult,
        manualReviewGuardrailResult,
        allowedGuardrailResult,
        escalationGuardrailResult,
        blockedCompletedGuardrailResult,
        blockedInsufficientDataGuardrailResult,
        manualReviewHighRiskGuardrailResult
      ];

      for (const testCase of testCases) {
        const result1 = deriveDecision(testCase);
        const result2 = deriveDecision(testCase);
        
        expect(result1).toEqual(result2);
      }
    });

  });

  // ============================================================
  // ALL PERMISSIONS REACHABLE
  // ============================================================

  describe('All Permissions Reachable', () => {

    test('BLOCKED permission → NO_ACTION action', () => {
      // Arrange
      const guardrailResult = blockedGuardrailResult;

      // Act
      const result = deriveDecision(guardrailResult);

      // Assert
      expect(result).toEqual(expectedNoActionDecision);
      expect(result.action).toBe('NO_ACTION');
      expect(result.reason).toBe('INVALID_POLICY');
    });

    test('MANUAL_REVIEW_ONLY permission → REQUEST_MANUAL_REVIEW action', () => {
      // Arrange
      const guardrailResult = manualReviewGuardrailResult;

      // Act
      const result = deriveDecision(guardrailResult);

      // Assert
      expect(result).toEqual(expectedManualReviewDecision);
      expect(result.action).toBe('REQUEST_MANUAL_REVIEW');
      expect(result.reason).toBe('WEAKENING_POLICY');
    });

    test('ALLOWED permission → PREPARE_ENTRY action', () => {
      // Arrange
      const guardrailResult = allowedGuardrailResult;

      // Act
      const result = deriveDecision(guardrailResult);

      // Assert
      expect(result).toEqual(expectedPrepareEntryDecision);
      expect(result.action).toBe('PREPARE_ENTRY');
      expect(result.reason).toBe('STRONG_POLICY');
    });

    test('ESCALATION_ONLY permission → REQUEST_MANUAL_REVIEW action', () => {
      // Arrange
      const guardrailResult = escalationGuardrailResult;

      // Act
      const result = deriveDecision(guardrailResult);

      // Assert
      expect(result).toEqual(expectedEscalationDecision);
      expect(result.action).toBe('REQUEST_MANUAL_REVIEW');
      expect(result.reason).toBe('HIGH_RISK_POLICY');
    });

  });

  // ============================================================
  // ACTION EXCLUSIVITY
  // ============================================================

  describe('Action Exclusivity', () => {

    test('NO_ACTION is returned ONLY for BLOCKED permission', () => {
      // Arrange: All permissions
      const permissionCases: Array<{ guardrail: DecisionGuardrailResult; permission: string }> = [
        { guardrail: blockedGuardrailResult, permission: 'BLOCKED' },
        { guardrail: manualReviewGuardrailResult, permission: 'MANUAL_REVIEW_ONLY' },
        { guardrail: allowedGuardrailResult, permission: 'ALLOWED' },
        { guardrail: escalationGuardrailResult, permission: 'ESCALATION_ONLY' }
      ];

      // Act & Assert
      for (const { guardrail, permission } of permissionCases) {
        const result = deriveDecision(guardrail);
        
        if (permission === 'BLOCKED') {
          expect(result.action).toBe('NO_ACTION');
        } else {
          expect(result.action).not.toBe('NO_ACTION');
        }
      }
    });

    test('REQUEST_MANUAL_REVIEW is returned ONLY for MANUAL_REVIEW_ONLY and ESCALATION_ONLY', () => {
      // Arrange: All permissions
      const permissionCases: Array<{ guardrail: DecisionGuardrailResult; permission: string }> = [
        { guardrail: blockedGuardrailResult, permission: 'BLOCKED' },
        { guardrail: manualReviewGuardrailResult, permission: 'MANUAL_REVIEW_ONLY' },
        { guardrail: allowedGuardrailResult, permission: 'ALLOWED' },
        { guardrail: escalationGuardrailResult, permission: 'ESCALATION_ONLY' }
      ];

      // Act & Assert
      for (const { guardrail, permission } of permissionCases) {
        const result = deriveDecision(guardrail);
        
        if (permission === 'MANUAL_REVIEW_ONLY' || permission === 'ESCALATION_ONLY') {
          expect(result.action).toBe('REQUEST_MANUAL_REVIEW');
        } else {
          expect(result.action).not.toBe('REQUEST_MANUAL_REVIEW');
        }
      }
    });

    test('PREPARE_ENTRY is returned ONLY for ALLOWED permission', () => {
      // Arrange: All permissions
      const permissionCases: Array<{ guardrail: DecisionGuardrailResult; permission: string }> = [
        { guardrail: blockedGuardrailResult, permission: 'BLOCKED' },
        { guardrail: manualReviewGuardrailResult, permission: 'MANUAL_REVIEW_ONLY' },
        { guardrail: allowedGuardrailResult, permission: 'ALLOWED' },
        { guardrail: escalationGuardrailResult, permission: 'ESCALATION_ONLY' }
      ];

      // Act & Assert
      for (const { guardrail, permission } of permissionCases) {
        const result = deriveDecision(guardrail);
        
        if (permission === 'ALLOWED') {
          expect(result.action).toBe('PREPARE_ENTRY');
        } else {
          expect(result.action).not.toBe('PREPARE_ENTRY');
        }
      }
    });

  });

  // ============================================================
  // REASON PASS-THROUGH
  // ============================================================

  describe('Reason Pass-Through', () => {

    test('DecisionReason always exactly mirrors DecisionGuardrailReason', () => {
      // Arrange: All guardrail results
      const testCases = [
        { guardrail: blockedGuardrailResult, expectedReason: 'INVALID_POLICY' },
        { guardrail: manualReviewGuardrailResult, expectedReason: 'WEAKENING_POLICY' },
        { guardrail: allowedGuardrailResult, expectedReason: 'STRONG_POLICY' },
        { guardrail: escalationGuardrailResult, expectedReason: 'HIGH_RISK_POLICY' },
        { guardrail: blockedCompletedGuardrailResult, expectedReason: 'COMPLETED_POLICY' },
        { guardrail: blockedInsufficientDataGuardrailResult, expectedReason: 'INSUFFICIENT_DATA' },
        { guardrail: manualReviewHighRiskGuardrailResult, expectedReason: 'HIGH_RISK_POLICY' }
      ];

      // Act & Assert
      for (const { guardrail, expectedReason } of testCases) {
        const result = deriveDecision(guardrail);
        
        // Reason passes through unchanged
        expect(result.reason).toBe(guardrail.reason);
        expect(result.reason).toBe(expectedReason);
      }
    });

    test('All 6 reason variants pass through unchanged', () => {
      // Arrange: Test all 6 reason variants
      const reasonVariants: Array<{ 
        guardrail: DecisionGuardrailResult; 
        reason: string;
      }> = [
        { 
          guardrail: { permission: 'ALLOWED', reason: 'STRONG_POLICY' },
          reason: 'STRONG_POLICY'
        },
        { 
          guardrail: { permission: 'MANUAL_REVIEW_ONLY', reason: 'WEAKENING_POLICY' },
          reason: 'WEAKENING_POLICY'
        },
        { 
          guardrail: { permission: 'MANUAL_REVIEW_ONLY', reason: 'HIGH_RISK_POLICY' },
          reason: 'HIGH_RISK_POLICY'
        },
        { 
          guardrail: { permission: 'BLOCKED', reason: 'INVALID_POLICY' },
          reason: 'INVALID_POLICY'
        },
        { 
          guardrail: { permission: 'BLOCKED', reason: 'COMPLETED_POLICY' },
          reason: 'COMPLETED_POLICY'
        },
        { 
          guardrail: { permission: 'BLOCKED', reason: 'INSUFFICIENT_DATA' },
          reason: 'INSUFFICIENT_DATA'
        }
      ];

      // Act & Assert
      for (const { guardrail, reason } of reasonVariants) {
        const result = deriveDecision(guardrail);
        
        expect(result.reason).toBe(reason);
        expect(result.reason).toBe(guardrail.reason);
      }
    });

    test('No reason transformation or remapping', () => {
      // Arrange: BLOCKED with different reasons
      const blockedVariants: DecisionGuardrailResult[] = [
        blockedGuardrailResult,
        blockedCompletedGuardrailResult,
        blockedInsufficientDataGuardrailResult
      ];

      // Act & Assert
      for (const guardrail of blockedVariants) {
        const result = deriveDecision(guardrail);
        
        // Action is same (NO_ACTION) but reason differs (proves pass-through)
        expect(result.action).toBe('NO_ACTION');
        expect(result.reason).toBe(guardrail.reason);
      }
    });

  });

  // ============================================================
  // GUARDRAIL RESPECT
  // ============================================================

  describe('Guardrail Respect', () => {

    test('Decision never bypasses guardrail permission', () => {
      // Arrange: BLOCKED permission
      const guardrailResult = blockedGuardrailResult;

      // Act
      const result = deriveDecision(guardrailResult);

      // Assert: NEVER returns PREPARE_ENTRY when BLOCKED
      expect(result.action).not.toBe('PREPARE_ENTRY');
      expect(result.action).toBe('NO_ACTION');
    });

    test('BLOCKED always results in NO_ACTION (never PREPARE_ENTRY)', () => {
      // Arrange: All BLOCKED variants
      const blockedVariants = [
        blockedGuardrailResult,
        blockedCompletedGuardrailResult,
        blockedInsufficientDataGuardrailResult
      ];

      // Act & Assert
      for (const guardrail of blockedVariants) {
        const result = deriveDecision(guardrail);
        
        expect(result.action).toBe('NO_ACTION');
        expect(result.action).not.toBe('PREPARE_ENTRY');
      }
    });

    test('MANUAL_REVIEW_ONLY always results in REQUEST_MANUAL_REVIEW (never automated action)', () => {
      // Arrange: MANUAL_REVIEW_ONLY variants
      const manualReviewVariants = [
        manualReviewGuardrailResult,
        manualReviewHighRiskGuardrailResult
      ];

      // Act & Assert
      for (const guardrail of manualReviewVariants) {
        const result = deriveDecision(guardrail);
        
        expect(result.action).toBe('REQUEST_MANUAL_REVIEW');
        expect(result.action).not.toBe('PREPARE_ENTRY');
        expect(result.action).not.toBe('NO_ACTION');
      }
    });

    test('ESCALATION_ONLY always results in REQUEST_MANUAL_REVIEW (never automated action)', () => {
      // Arrange
      const guardrailResult = escalationGuardrailResult;

      // Act
      const result = deriveDecision(guardrailResult);

      // Assert
      expect(result.action).toBe('REQUEST_MANUAL_REVIEW');
      expect(result.action).not.toBe('PREPARE_ENTRY');
      expect(result.action).not.toBe('NO_ACTION');
    });

    test('Only ALLOWED permission can result in PREPARE_ENTRY', () => {
      // Arrange: All permissions
      const allPermissions = [
        blockedGuardrailResult,
        manualReviewGuardrailResult,
        allowedGuardrailResult,
        escalationGuardrailResult
      ];

      // Act & Assert
      for (const guardrail of allPermissions) {
        const result = deriveDecision(guardrail);
        
        if (guardrail.permission === 'ALLOWED') {
          expect(result.action).toBe('PREPARE_ENTRY');
        } else {
          expect(result.action).not.toBe('PREPARE_ENTRY');
        }
      }
    });

  });

});
