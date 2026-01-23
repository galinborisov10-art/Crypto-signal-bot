/**
 * Decision Derivation Test Fixtures - Phase 6.4.2
 * 
 * Reusable test fixtures for decision derivation engine.
 * 
 * Fixtures demonstrate canonical permission → action mapping
 * and reason pass-through (1:1 mirror).
 */

import { DecisionGuardrailResult } from './decisionGuardrail.types';
import { DecisionResult } from './decision.types';

// ============================================================
// BLOCKED → NO_ACTION
// ============================================================

export const blockedGuardrailResult: DecisionGuardrailResult = {
  permission: 'BLOCKED',
  reason: 'INVALID_POLICY'
};

export const expectedNoActionDecision: DecisionResult = {
  action: 'NO_ACTION',
  reason: 'INVALID_POLICY' // Direct mirror
};

// ============================================================
// MANUAL_REVIEW_ONLY → REQUEST_MANUAL_REVIEW
// ============================================================

export const manualReviewGuardrailResult: DecisionGuardrailResult = {
  permission: 'MANUAL_REVIEW_ONLY',
  reason: 'WEAKENING_POLICY'
};

export const expectedManualReviewDecision: DecisionResult = {
  action: 'REQUEST_MANUAL_REVIEW',
  reason: 'WEAKENING_POLICY' // Direct mirror
};

// ============================================================
// ALLOWED → PREPARE_ENTRY
// ============================================================

export const allowedGuardrailResult: DecisionGuardrailResult = {
  permission: 'ALLOWED',
  reason: 'STRONG_POLICY'
};

export const expectedPrepareEntryDecision: DecisionResult = {
  action: 'PREPARE_ENTRY',
  reason: 'STRONG_POLICY' // Direct mirror
};

// ============================================================
// ESCALATION_ONLY → REQUEST_MANUAL_REVIEW
// ============================================================

export const escalationGuardrailResult: DecisionGuardrailResult = {
  permission: 'ESCALATION_ONLY',
  reason: 'HIGH_RISK_POLICY'
};

export const expectedEscalationDecision: DecisionResult = {
  action: 'REQUEST_MANUAL_REVIEW',
  reason: 'HIGH_RISK_POLICY' // Direct mirror
};

// ============================================================
// DIFFERENT REASONS TO PROVE PASS-THROUGH
// ============================================================

export const blockedCompletedGuardrailResult: DecisionGuardrailResult = {
  permission: 'BLOCKED',
  reason: 'COMPLETED_POLICY'
};

export const expectedNoActionCompletedDecision: DecisionResult = {
  action: 'NO_ACTION',
  reason: 'COMPLETED_POLICY' // Direct mirror
};

export const blockedInsufficientDataGuardrailResult: DecisionGuardrailResult = {
  permission: 'BLOCKED',
  reason: 'INSUFFICIENT_DATA'
};

export const expectedNoActionInsufficientDataDecision: DecisionResult = {
  action: 'NO_ACTION',
  reason: 'INSUFFICIENT_DATA' // Direct mirror
};

export const manualReviewHighRiskGuardrailResult: DecisionGuardrailResult = {
  permission: 'MANUAL_REVIEW_ONLY',
  reason: 'HIGH_RISK_POLICY'
};

export const expectedManualReviewHighRiskDecision: DecisionResult = {
  action: 'REQUEST_MANUAL_REVIEW',
  reason: 'HIGH_RISK_POLICY' // Direct mirror
};
