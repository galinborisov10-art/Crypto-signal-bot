/**
 * Virtual Position Contracts - Phase 5.1: Virtual Position Model (Design-First)
 * 
 * Pure, deterministic factory for Virtual Position creation.
 * Implements Virtual Position construction without execution or decision-making.
 * 
 * Contract Rules:
 * 1. ONLY EntryScenario.status === 'valid' can create Virtual Position
 * 2. ONLY RiskContract.status === 'valid' can create Virtual Position
 * 3. scenario.id MUST match score.scenarioId
 * 4. scenario.id MUST match risk.scenarioId
 * 5. Factory returns explicit errors (no throws)
 * 6. Initial state: status='open', progressPercent=0, reachedTargets=[]
 * 
 * Architecture Decisions:
 * - Factory ONLY (no update helpers in PR-5.1)
 * - Deterministic ID generation (scenario.id + openedAt)
 * - Self-contained snapshot (full objects stored)
 * - Immutable design (no input mutation)
 * 
 * Absolute Rules:
 * 1. MUST be deterministic
 * 2. No randomness
 * 3. Same inputs → same output
 * 4. MUST NOT mutate input objects
 * 5. NO execution, signals, or decision logic
 */

import { EntryScenario, isScenarioValid } from '../entry-scenarios';
import { ConfluenceScore } from '../confluence-scoring';
import { RiskContract } from '../risk-contracts';
import {
  VirtualPosition,
  VirtualPositionResult
} from './virtualPosition.types';

/**
 * Create Virtual Position
 * 
 * Pure factory function that creates a Virtual Position from validated Phase 4 inputs.
 * This represents the creation of a "what if this were a trade" observation object.
 * 
 * Implementation Flow:
 * 1. Validate scenario status (must be 'valid')
 * 2. Validate risk status (must be 'valid')
 * 3. Validate scenario-score relationship (scenario.id === score.scenarioId)
 * 4. Validate scenario-risk relationship (scenario.id === risk.scenarioId)
 * 5. Generate deterministic ID
 * 6. Create Virtual Position with initial state
 * 
 * Initial State:
 * - status: 'open'
 * - progressPercent: 0
 * - reachedTargets: []
 * - lastEvaluatedAt: openedAt (same initially)
 * 
 * Validation Errors:
 * - scenario.status !== 'valid' → 'SCENARIO_NOT_VALID'
 * - risk.status !== 'valid' → 'RISK_NOT_VALID'
 * - scenario.id !== score.scenarioId → 'RISK_NOT_VALID'
 * - scenario.id !== risk.scenarioId → 'RISK_NOT_VALID'
 * 
 * @param scenario - EntryScenario to create Virtual Position from (must be status === 'valid')
 * @param score - ConfluenceScore for the scenario (must reference scenario.id)
 * @param risk - RiskContract for the scenario (must be status === 'valid' and reference scenario.id)
 * @param openedAt - Fixed timestamp for Virtual Position creation (Unix milliseconds)
 * @returns VirtualPositionResult with success or explicit error
 * 
 * @remarks
 * - This function is pure and deterministic
 * - Does NOT throw exceptions
 * - Same inputs always produce identical output
 * - Input objects are never mutated
 * - openedAt is a fixed timestamp, not dynamic
 * - ID is deterministic: `vpos-${scenario.id}-${openedAt}`
 */
export function createVirtualPosition(
  scenario: EntryScenario,
  score: ConfluenceScore,
  risk: RiskContract,
  openedAt: number
): VirtualPositionResult {
  // Step 1: Validate scenario status
  if (!isScenarioValid(scenario)) {
    return {
      success: false,
      error: 'SCENARIO_NOT_VALID'
    };
  }

  // Step 2: Validate risk status
  if (risk.status !== 'valid') {
    return {
      success: false,
      error: 'RISK_NOT_VALID'
    };
  }

  // Step 3: Validate scenario-score relationship
  if (scenario.id !== score.scenarioId) {
    return {
      success: false,
      error: 'RISK_NOT_VALID'
    };
  }

  // Step 4: Validate scenario-risk relationship
  if (scenario.id !== risk.scenarioId) {
    return {
      success: false,
      error: 'RISK_NOT_VALID'
    };
  }

  // Step 5: Generate deterministic ID
  // Architecture Decision: Deterministic ID based on scenario.id + openedAt
  const id = `vpos-${scenario.id}-${openedAt}`;

  // Step 6: Create Virtual Position with initial state
  const position: VirtualPosition = {
    id,
    scenarioId: scenario.id,
    scenarioType: scenario.type,
    score: { ...score }, // Defensive copy (self-contained snapshot)
    risk: {
      ...risk,
      stopLoss: { ...risk.stopLoss },
      takeProfits: risk.takeProfits.map(tp => ({ ...tp }))
    }, // Deep defensive copy
    status: 'open',
    progressPercent: 0,
    reachedTargets: [],
    openedAt,
    lastEvaluatedAt: openedAt // Initially same as openedAt
  };

  return {
    success: true,
    position
  };
}

/**
 * Check if Virtual Position is Open
 * 
 * Helper function to check if a Virtual Position is in 'open' state.
 * 
 * @param position - VirtualPosition to check
 * @returns true if position.status === 'open'
 */
export function isVirtualPositionOpen(position: VirtualPosition): boolean {
  return position.status === 'open';
}

/**
 * Check if Virtual Position is Progressing
 * 
 * Helper function to check if a Virtual Position is in 'progressing' state.
 * 
 * @param position - VirtualPosition to check
 * @returns true if position.status === 'progressing'
 */
export function isVirtualPositionProgressing(position: VirtualPosition): boolean {
  return position.status === 'progressing';
}

/**
 * Check if Virtual Position is Completed
 * 
 * Helper function to check if a Virtual Position is in 'completed' state.
 * 
 * @param position - VirtualPosition to check
 * @returns true if position.status === 'completed'
 */
export function isVirtualPositionCompleted(position: VirtualPosition): boolean {
  return position.status === 'completed';
}

/**
 * Check if Virtual Position is Invalidated
 * 
 * Helper function to check if a Virtual Position is in 'invalidated' state.
 * 
 * @param position - VirtualPosition to check
 * @returns true if position.status === 'invalidated'
 */
export function isVirtualPositionInvalidated(position: VirtualPosition): boolean {
  return position.status === 'invalidated';
}
