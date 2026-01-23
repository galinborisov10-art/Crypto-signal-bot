/**
 * Decision Guardrail Derivation Engine - Phase 6.3.2: Decision Guardrail Derivation
 * 
 * Implements pure, deterministic permission gate layer.
 * Translates PolicyResult (Phase 6.2) → DecisionGuardrailResult (Phase 6.3.1).
 * 
 * CRITICAL DISTINCTIONS:
 * 
 * Guardrail ≠ Decision
 * Guardrail ≠ Recommendation
 * Guardrail = Permission gate
 * 
 * This layer answers ONLY:
 * "Is decision-making allowed at all?"
 * 
 * NOT:
 * "What decision to make?"
 * "How to act?"
 * "Whether to trade?"
 * "How to execute?"
 * 
 * HARD CONSTRAINTS:
 * ❌ NO decisions
 * ❌ NO recommendations
 * ❌ NO execution logic
 * ❌ NO position management
 * ❌ NO timeline/price/POI/market data access
 * ❌ NO mutation
 * ❌ NO randomness or Date.now()
 * ❌ NO side effects
 * 
 * Guardrail = Permission gate without decision authority
 * 
 * Policy has opinion → Guardrail has authority → Decision has will
 */

import { PolicyResult } from './policy.types';
import { DecisionGuardrailResult } from './decisionGuardrail.types';

/**
 * Derives decision guardrail permission from policy result.
 * 
 * This is a pure, deterministic permission gate.
 * 
 * Guardrail = Permission gate without decision authority
 * 
 * This function does NOT:
 * - Make decisions
 * - Provide recommendations
 * - Execute trades
 * - Manage positions
 * - Access timeline/price/POI/market data
 * 
 * This function ONLY:
 * - Determines if decision-making is allowed/blocked/restricted
 * 
 * Permission derivation uses ONLY PolicyStance.
 * PolicyConfidence is metadata and does NOT affect permission logic.
 * 
 * Canonical mapping (FROZEN for ESB v1.0):
 * - STRONG_THESIS → ALLOWED
 * - WEAKENING_THESIS → MANUAL_REVIEW_ONLY
 * - HIGH_RISK_THESIS → MANUAL_REVIEW_ONLY
 * - INVALID_THESIS → BLOCKED
 * - COMPLETED_THESIS → BLOCKED
 * - INSUFFICIENT_DATA → BLOCKED
 * 
 * ESCALATION_ONLY is reserved and NOT used in v1.0.
 * 
 * @param policyResult - Policy result from Phase 6.2
 * @returns DecisionGuardrailResult with permission and reason
 */
export function deriveDecisionGuardrail(
  policyResult: PolicyResult
): DecisionGuardrailResult {
  const { stance } = policyResult;
  // Note: confidence is NOT used in permission derivation

  switch (stance) {
    case 'STRONG_THESIS':
      return {
        permission: 'ALLOWED',
        reason: 'STRONG_POLICY'
      };

    case 'WEAKENING_THESIS':
      return {
        permission: 'MANUAL_REVIEW_ONLY',
        reason: 'WEAKENING_POLICY'
      };

    case 'HIGH_RISK_THESIS':
      return {
        permission: 'MANUAL_REVIEW_ONLY',
        reason: 'HIGH_RISK_POLICY'
      };

    case 'INVALID_THESIS':
      return {
        permission: 'BLOCKED',
        reason: 'INVALID_POLICY'
      };

    case 'COMPLETED_THESIS':
      return {
        permission: 'BLOCKED',
        reason: 'COMPLETED_POLICY'
      };

    case 'INSUFFICIENT_DATA':
      return {
        permission: 'BLOCKED',
        reason: 'INSUFFICIENT_DATA'
      };
  }
}
