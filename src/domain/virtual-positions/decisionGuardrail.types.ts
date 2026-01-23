/**
 * Phase 6.3: Decision Guardrail (Types & Semantics)
 * 
 * CRITICAL DISTINCTIONS:
 * 
 * Guardrail ≠ Decision
 * Guardrail ≠ Recommendation
 * Guardrail = Permission gate
 * 
 * Phase 6.3 determines whether decision-making is allowed/blocked
 * for a trading idea based on its policy stance.
 * 
 * This layer has PERMISSION authority but NOT DECISION authority.
 * 
 * Guardrail can be consumed by:
 * - Decision layers (Phase 6.4+)
 * - Manual review systems
 * - Alerting/escalation tools
 * - Compliance monitoring
 * 
 * But Guardrail itself does NOT:
 * - Make decisions
 * - Recommend actions
 * - Execute trades
 * - Analyze market data
 * 
 * Guardrail is the gate before the decision layer.
 * Policy (Phase 6.2) → Guardrail (Phase 6.3) → Decision (Phase 6.4+, future)
 * 
 * VERSIONING:
 * All types in this file are FROZEN for ESB v1.0.
 * Breaking changes require major version bump.
 */

/**
 * Decision permission indicates whether downstream decision layers
 * are allowed to act on this trading idea.
 * 
 * This is a GATE, not a BRAIN.
 * This layer is "permission without action".
 * 
 * Permission does NOT:
 * - Make decisions
 * - Recommend actions
 * - Execute trades
 * 
 * Permission ONLY:
 * - Allows or blocks downstream decision-making
 * 
 * Permission States:
 * 
 * - ALLOWED:
 *   Downstream decision layers may proceed with automated decision-making.
 *   This does NOT mean a decision WILL be made, only that it MAY be considered.
 * 
 * - BLOCKED:
 *   Decision-making is forbidden for this idea.
 *   Automated and manual decisions are both blocked.
 *   Typical for invalidated or insufficient data scenarios.
 * 
 * - MANUAL_REVIEW_ONLY:
 *   Human-in-the-loop is required before any decision.
 *   Automated decision-making is blocked.
 *   Human must review and approve before proceeding.
 *   Typical for high-risk or weakening scenarios.
 * 
 * - ESCALATION_ONLY:
 *   Automated decisions are forbidden.
 *   Idea can be escalated to higher authority/system for review.
 *   Similar to MANUAL_REVIEW_ONLY but allows escalation workflow.
 *   Typical for edge cases or policy conflicts.
 * 
 * CANONICAL SET (FROZEN for ESB v1.0):
 * These 4 states are the complete and closed set.
 * Absence of permission is modeled via BLOCKED + reason.
 */
export type DecisionPermission =
  | 'ALLOWED'
  | 'BLOCKED'
  | 'MANUAL_REVIEW_ONLY'
  | 'ESCALATION_ONLY';

/**
 * Decision guardrail reason explains WHY permission was granted or denied.
 * 
 * Reasons are derived ONLY from Policy Layer (Phase 6.2) stance.
 * 
 * This is a 1:1 mapping to PolicyStance:
 * - STRONG_POLICY ← PolicyStance: STRONG_THESIS
 * - WEAKENING_POLICY ← PolicyStance: WEAKENING_THESIS
 * - HIGH_RISK_POLICY ← PolicyStance: HIGH_RISK_THESIS
 * - INVALID_POLICY ← PolicyStance: INVALID_THESIS
 * - COMPLETED_POLICY ← PolicyStance: COMPLETED_THESIS
 * - INSUFFICIENT_DATA ← PolicyStance: INSUFFICIENT_DATA
 * 
 * Reasons are ONLY policy-derived.
 * 
 * There are NO:
 * - System reasons (technical failures, infrastructure issues)
 * - Regulatory reasons (compliance blocks, risk limits)
 * - External reasons (market conditions, external events)
 * 
 * Such reasons belong to later infrastructure/compliance layers,
 * not ESB core observational runtime.
 * 
 * Guardrail reason reflects the policy stance that led to the permission state.
 */
export type DecisionGuardrailReason =
  | 'STRONG_POLICY'
  | 'WEAKENING_POLICY'
  | 'HIGH_RISK_POLICY'
  | 'INVALID_POLICY'
  | 'COMPLETED_POLICY'
  | 'INSUFFICIENT_DATA';

/**
 * Decision guardrail result represents the permission state for decision-making
 * on a trading idea.
 * 
 * This is NOT a decision.
 * This is NOT a recommendation.
 * 
 * Guardrail result can inform:
 * - Decision layers (Phase 6.4+, if implemented)
 * - Manual review systems (human approval workflows)
 * - Alerting/escalation tools (notification triggers)
 * - Compliance monitoring (audit trails)
 * 
 * But the result itself does NOT cause execution or decision-making.
 * 
 * Fields:
 * 
 * - permission:
 *   Whether decision-making is allowed/blocked/restricted.
 * 
 * - reason:
 *   Policy-derived explanation for the permission state.
 *   Maps 1:1 to the PolicyStance that led to this guardrail result.
 * 
 * Guardrail explains WHY permission is granted or denied,
 * but does NOT carry context or make recommendations.
 */
export interface DecisionGuardrailResult {
  permission: DecisionPermission;
  reason: DecisionGuardrailReason;
}
