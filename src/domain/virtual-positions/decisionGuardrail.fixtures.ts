/**
 * Decision Guardrail Test Fixtures - Phase 6.3.2: Decision Guardrail Derivation Engine
 * 
 * Reusable fixtures for testing decision guardrail derivation logic.
 * All fixtures are semantic and implementation-agnostic.
 * 
 * Coverage:
 * - All 6 policy stances
 * - All 3 permission types (ALLOWED, BLOCKED, MANUAL_REVIEW_ONLY)
 * - Different confidence levels to prove confidence is ignored
 * - 1:1 mapping between PolicyStance and DecisionGuardrailReason
 */

import { PolicyResult } from './policy.types';
import { DecisionGuardrailResult } from './decisionGuardrail.types';

// ============================================================
// STRONG_THESIS → ALLOWED
// ============================================================

/**
 * STRONG_THESIS with HIGH confidence → ALLOWED
 * This is the canonical case for automated decision-making.
 */
export const strongThesisPolicyResult: PolicyResult = {
  stance: 'STRONG_THESIS',
  confidence: 'HIGH'
};

export const expectedAllowedGuardrail: DecisionGuardrailResult = {
  permission: 'ALLOWED',
  reason: 'STRONG_POLICY'
};

/**
 * STRONG_THESIS with different confidence levels
 * Used to test that confidence does NOT affect permission derivation.
 */
export const strongThesisMediumConfidence: PolicyResult = {
  stance: 'STRONG_THESIS',
  confidence: 'MEDIUM'
};

export const strongThesisLowConfidence: PolicyResult = {
  stance: 'STRONG_THESIS',
  confidence: 'LOW'
};

// ============================================================
// WEAKENING_THESIS → MANUAL_REVIEW_ONLY
// ============================================================

/**
 * WEAKENING_THESIS with MEDIUM confidence → MANUAL_REVIEW_ONLY
 * This is the canonical case for controlled degradation.
 */
export const weakeningThesisPolicyResult: PolicyResult = {
  stance: 'WEAKENING_THESIS',
  confidence: 'MEDIUM'
};

export const expectedManualReviewWeakening: DecisionGuardrailResult = {
  permission: 'MANUAL_REVIEW_ONLY',
  reason: 'WEAKENING_POLICY'
};

/**
 * WEAKENING_THESIS with different confidence levels
 * Used to test that confidence does NOT affect permission derivation.
 */
export const weakeningThesisHighConfidence: PolicyResult = {
  stance: 'WEAKENING_THESIS',
  confidence: 'HIGH'
};

export const weakeningThesisLowConfidence: PolicyResult = {
  stance: 'WEAKENING_THESIS',
  confidence: 'LOW'
};

// ============================================================
// HIGH_RISK_THESIS → MANUAL_REVIEW_ONLY
// ============================================================

/**
 * HIGH_RISK_THESIS with LOW confidence → MANUAL_REVIEW_ONLY
 * This is the canonical case for unstable/conflicting patterns.
 */
export const highRiskThesisPolicyResult: PolicyResult = {
  stance: 'HIGH_RISK_THESIS',
  confidence: 'LOW'
};

export const expectedManualReviewHighRisk: DecisionGuardrailResult = {
  permission: 'MANUAL_REVIEW_ONLY',
  reason: 'HIGH_RISK_POLICY'
};

/**
 * HIGH_RISK_THESIS with different confidence levels
 * Used to test that confidence does NOT affect permission derivation.
 */
export const highRiskThesisHighConfidence: PolicyResult = {
  stance: 'HIGH_RISK_THESIS',
  confidence: 'HIGH'
};

export const highRiskThesisMediumConfidence: PolicyResult = {
  stance: 'HIGH_RISK_THESIS',
  confidence: 'MEDIUM'
};

// ============================================================
// INVALID_THESIS → BLOCKED
// ============================================================

/**
 * INVALID_THESIS with HIGH confidence → BLOCKED
 * This is the canonical case for invalidated ideas.
 */
export const invalidThesisPolicyResult: PolicyResult = {
  stance: 'INVALID_THESIS',
  confidence: 'HIGH'
};

export const expectedBlockedInvalid: DecisionGuardrailResult = {
  permission: 'BLOCKED',
  reason: 'INVALID_POLICY'
};

/**
 * INVALID_THESIS with different confidence levels
 * Used to test that confidence does NOT affect permission derivation.
 */
export const invalidThesisMediumConfidence: PolicyResult = {
  stance: 'INVALID_THESIS',
  confidence: 'MEDIUM'
};

export const invalidThesisLowConfidence: PolicyResult = {
  stance: 'INVALID_THESIS',
  confidence: 'LOW'
};

// ============================================================
// COMPLETED_THESIS → BLOCKED
// ============================================================

/**
 * COMPLETED_THESIS with HIGH confidence → BLOCKED
 * This is the canonical case for completed ideas (terminal state).
 */
export const completedThesisPolicyResult: PolicyResult = {
  stance: 'COMPLETED_THESIS',
  confidence: 'HIGH'
};

export const expectedBlockedCompleted: DecisionGuardrailResult = {
  permission: 'BLOCKED',
  reason: 'COMPLETED_POLICY'
};

/**
 * COMPLETED_THESIS with different confidence levels
 * Used to test that confidence does NOT affect permission derivation.
 */
export const completedThesisMediumConfidence: PolicyResult = {
  stance: 'COMPLETED_THESIS',
  confidence: 'MEDIUM'
};

export const completedThesisLowConfidence: PolicyResult = {
  stance: 'COMPLETED_THESIS',
  confidence: 'LOW'
};

// ============================================================
// INSUFFICIENT_DATA → BLOCKED
// ============================================================

/**
 * INSUFFICIENT_DATA with UNKNOWN confidence → BLOCKED
 * This is the canonical case for insufficient observations.
 */
export const insufficientDataPolicyResult: PolicyResult = {
  stance: 'INSUFFICIENT_DATA',
  confidence: 'UNKNOWN'
};

export const expectedBlockedInsufficientData: DecisionGuardrailResult = {
  permission: 'BLOCKED',
  reason: 'INSUFFICIENT_DATA'
};

/**
 * INSUFFICIENT_DATA with different confidence levels
 * Used to test that confidence does NOT affect permission derivation.
 */
export const insufficientDataHighConfidence: PolicyResult = {
  stance: 'INSUFFICIENT_DATA',
  confidence: 'HIGH'
};

export const insufficientDataMediumConfidence: PolicyResult = {
  stance: 'INSUFFICIENT_DATA',
  confidence: 'MEDIUM'
};

export const insufficientDataLowConfidence: PolicyResult = {
  stance: 'INSUFFICIENT_DATA',
  confidence: 'LOW'
};
