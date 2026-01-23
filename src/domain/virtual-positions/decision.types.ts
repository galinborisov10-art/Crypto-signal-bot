/**
 * Phase 6.4: Decision Layer (Types & Semantics)
 * 
 * CRITICAL DISTINCTIONS:
 * 
 * Decision ≠ Execution
 * Decision ≠ Recommendation
 * Decision = Action selection without effect
 * 
 * Phase 6.4 selects an action intention for a trading idea
 * based on its guardrail permission.
 * 
 * This layer has WILL but NOT HANDS.
 * 
 * Decision can be consumed by:
 * - Execution layers (Phase 7+, if implemented)
 * - Manual review systems
 * - UI displays
 * - Audit/logging systems
 * 
 * But Decision itself does NOT:
 * - Execute trades
 * - Manage positions
 * - Access timeline/price/POI data
 * - Bypass guardrail permissions
 * - Perform market analysis
 * - Mutate state
 * 
 * Decision is the first layer with intent (will),
 * but remains on the planning side of the execution boundary.
 * 
 * Policy (Phase 6.2) → Guardrail (Phase 6.3) → Decision (Phase 6.4) → Execution (Phase 7+, future)
 * 
 * VERSIONING:
 * All types in this file are FROZEN for ESB v1.0.
 * Breaking changes require major version bump.
 */

/**
 * Decision action represents the selected intent for a trading idea.
 * 
 * Actions are intentions, NOT operations.
 * 
 * Decision has WILL (intent) but NOT HANDS (execution).
 * 
 * Action States:
 * 
 * - NO_ACTION:
 *   Idea doesn't require attention right now.
 *   Passive "we do nothing".
 *   NOT the same as MONITOR (which is active observation).
 *   NOT the same as ABORT_IDEA (which is explicit termination).
 *   Used when: not enough reason for activity, idea is not "alive" but not terminated.
 * 
 * - PREPARE_ENTRY:
 *   Signal readiness for potential entry (NO execution).
 *   Expresses intention: "idea is strong enough to consider entry".
 *   Does NOT calculate entry parameters (price, size, etc.).
 *   Does NOT change internal state.
 *   This is planning, NOT configuration.
 *   Future execution layer (Phase 7+) may act on this intent.
 * 
 * - MONITOR:
 *   Continue active observation of this idea.
 *   Idea is active and deserves ongoing attention.
 *   NOT the same as NO_ACTION (which is passive).
 *   Used when: idea warrants tracking but no immediate action.
 * 
 * - REQUEST_MANUAL_REVIEW:
 *   Explicit human review is required before proceeding.
 *   Automated decision-making stops here.
 *   Commonly used when guardrail permission is MANUAL_REVIEW_ONLY.
 *   But can also be used when permission is ALLOWED (decision chooses to escalate).
 * 
 * - ABORT_IDEA:
 *   Explicitly abandon this idea.
 *   This is a DECISION, not a consequence of guardrail blocking.
 *   Can be returned even when permission is ALLOWED or MANUAL_REVIEW_ONLY.
 *   Decision layer chooses to terminate the idea (e.g., policy invalidation, completion).
 *   NOT the same as guardrail BLOCKED (which prevents decision-making entirely).
 * 
 * CANONICAL SET (FROZEN for ESB v1.0):
 * These 5 actions are the complete and closed set.
 * 
 * NO_ACTION ≠ MONITOR ≠ ABORT_IDEA (distinct semantics, documented above)
 */
export type DecisionAction =
  | 'NO_ACTION'
  | 'PREPARE_ENTRY'
  | 'MONITOR'
  | 'REQUEST_MANUAL_REVIEW'
  | 'ABORT_IDEA';

/**
 * Decision reason explains WHY an action was selected.
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
 * - Decision-specific reasons (e.g., "strategic abort", "resource constraint")
 * - System reasons (technical failures, infrastructure issues)
 * - Regulatory reasons (compliance blocks, risk limits)
 * - Market reasons (volatility, liquidity, external events)
 * 
 * Decision selects action, but does NOT explain why beyond policy.
 * 
 * Decision reason reflects the policy stance that informed the action selection.
 */
export type DecisionReason =
  | 'STRONG_POLICY'
  | 'WEAKENING_POLICY'
  | 'HIGH_RISK_POLICY'
  | 'INVALID_POLICY'
  | 'COMPLETED_POLICY'
  | 'INSUFFICIENT_DATA';

/**
 * Decision result represents the selected action intention for a trading idea.
 * 
 * This is NOT execution.
 * This is NOT a recommendation.
 * 
 * Decision result is an intent (will) without effect (hands).
 * 
 * Decision result can inform:
 * - Execution layers (Phase 7+, if implemented)
 * - Manual review systems (human approval workflows)
 * - UI displays (show current intent)
 * - Audit/logging systems (track decision history)
 * 
 * But the result itself does NOT cause execution, position management, or state mutation.
 * 
 * Fields:
 * 
 * - action:
 *   The selected action intention.
 *   Represents WILL (what we intend to do).
 * 
 * - reason:
 *   Policy-derived explanation for the action selection.
 *   Maps 1:1 to the PolicyStance that informed this decision.
 * 
 * Decision explains WHAT intent was selected and WHY (based on policy),
 * but does NOT execute, manage, or mutate.
 */
export interface DecisionResult {
  action: DecisionAction;
  reason: DecisionReason;
}
