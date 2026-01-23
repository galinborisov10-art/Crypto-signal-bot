/**
 * Decision Derivation Engine - Phase 6.4.2: Decision Derivation
 * 
 * Implements pure, deterministic action selector layer.
 * Translates DecisionGuardrailResult (Phase 6.3) → DecisionResult (Phase 6.4.1).
 * 
 * CRITICAL DISTINCTIONS:
 * 
 * Decision ≠ Execution
 * Decision ≠ Recommendation
 * Decision = Action selection without effect
 * 
 * This layer selects action intention (WILL) without execution (HANDS).
 * 
 * Decision has WILL but NOT HANDS.
 * 
 * HARD CONSTRAINTS:
 * ❌ NO execution
 * ❌ NO position management
 * ❌ NO guardrail bypass
 * ❌ NO market analysis
 * ❌ NO strategy optimization
 * ❌ NO heuristics or scoring
 * ❌ NO timeline/price/POI/market data access
 * ❌ NO mutation
 * ❌ NO randomness or Date.now()
 * ❌ NO side effects
 * 
 * Decision = Will without hands
 * 
 * Policy has opinion → Guardrail has authority → Decision has will
 */

import { DecisionGuardrailResult } from './decisionGuardrail.types';
import { DecisionResult } from './decision.types';

/**
 * Derives decision action intent from guardrail permission.
 * 
 * This is a pure, deterministic action selector.
 * 
 * Decision = Will without hands
 * 
 * This function does NOT:
 * - Execute trades
 * - Manage positions
 * - Bypass guardrail permissions
 * - Perform market analysis
 * - Introduce strategy heuristics
 * - Access timeline/price/POI/market data
 * 
 * This function ONLY:
 * - Selects action intent based on guardrail permission
 * - Respects guardrail authority
 * - Passes reason through unchanged (1:1 mirror)
 * 
 * Canonical mapping (FROZEN for ESB v1.0):
 * - BLOCKED → NO_ACTION
 * - MANUAL_REVIEW_ONLY → REQUEST_MANUAL_REVIEW
 * - ALLOWED → PREPARE_ENTRY
 * - ESCALATION_ONLY → REQUEST_MANUAL_REVIEW
 * 
 * Reason pass-through (FROZEN for ESB v1.0):
 * - DecisionReason directly mirrors DecisionGuardrailReason
 * - No transformation, remapping, or interpretation
 * - Decision chooses action, NOT explanation
 * - Reason remains policy-based
 * 
 * @param guardrailResult - Guardrail result from Phase 6.3
 * @returns DecisionResult with action intent and reason
 */
export function deriveDecision(
  guardrailResult: DecisionGuardrailResult
): DecisionResult {
  const { permission, reason } = guardrailResult;
  // Note: reason is passed through unchanged (1:1 mirror)

  switch (permission) {
    case 'BLOCKED':
      return {
        action: 'NO_ACTION',
        reason
      };

    case 'MANUAL_REVIEW_ONLY':
      return {
        action: 'REQUEST_MANUAL_REVIEW',
        reason
      };

    case 'ALLOWED':
      return {
        action: 'PREPARE_ENTRY',
        reason
      };

    case 'ESCALATION_ONLY':
      return {
        action: 'REQUEST_MANUAL_REVIEW',
        reason
      };
  }
}
