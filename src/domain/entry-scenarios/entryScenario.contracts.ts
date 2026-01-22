/**
 * Entry Scenario Contracts - Phase 4.3: Entry Scenario Core (Design-First)
 * 
 * Contract/validation logic for Entry Scenario construction and lifecycle.
 * Enforces deterministic scenario building without execution or scoring logic.
 * 
 * Contract Rules:
 * 1. Scenario starts as 'forming' if ANY required gate is false
 * 2. Scenario becomes 'valid' ONLY if ALL required gates are true
 * 3. Optional confluences do NOT gate validity
 * 4. Scenarios can be invalidated by context changes
 * 
 * Architecture Decisions:
 * - Explicit gates + confluences (Option C from spec)
 * - Separate invalidation function (not in builder)
 * - Uniform gate structure across all scenario types
 * 
 * Absolute Rules:
 * 1. Entry Scenario MUST be derivable deterministically
 * 2. No randomness
 * 3. Same inputs → same output
 * 4. MUST NOT mutate input objects
 * 5. NO scoring, execution, or decision logic
 */

import { LiquidityContext, isLiquidityContextTradable } from '../liquidity-context';
import {
  EntryScenario,
  EntryScenarioType,
  EntryScenarioStatus,
  RequiredGates,
  OptionalConfluences
} from './entryScenario.types';

/**
 * Build an Entry Scenario from explicit inputs
 * 
 * Architecture Decision: Option C - Explicit gates + confluences
 * 
 * This function constructs a deterministic Entry Scenario without auto-detection.
 * All gates and confluences must be explicitly provided.
 * 
 * Status determination:
 * - If ALL required gates are true → status = 'valid'
 * - Otherwise → status = 'forming'
 * 
 * @param type - Type of entry scenario (ICT template)
 * @param liquidityContext - LiquidityContext from Phase 4.2 (read-only)
 * @param requiredGates - Required structural gates (explicit boolean flags)
 * @param optionalConfluences - Optional confluence factors (explicit boolean flags)
 * @param evaluatedAt - Fixed timestamp for scenario evaluation (Unix milliseconds)
 * @returns A deterministic EntryScenario object
 * 
 * @remarks
 * - This function is pure and deterministic
 * - Same inputs always produce identical output
 * - Input objects are never mutated
 * - evaluatedAt is a fixed timestamp, not dynamic
 * - Optional confluences do NOT affect validity status
 */
export function buildEntryScenario(
  type: EntryScenarioType,
  liquidityContext: LiquidityContext,
  requiredGates: RequiredGates,
  optionalConfluences: OptionalConfluences,
  evaluatedAt: number
): EntryScenario {
  // Generate unique ID (deterministic based on type + contextId + timestamp)
  const id = `${type}_${liquidityContext.poiId}_${evaluatedAt}`;
  
  // Extract context reference (NOT the context object itself)
  const contextId = liquidityContext.poiId;
  
  // Determine initial status based on required gates
  // ALL gates must be true for scenario to be 'valid'
  const allGatesTrue =
    requiredGates.htfBiasAligned &&
    requiredGates.liquidityEvent &&
    requiredGates.structuralConfirmation;
  
  const status: EntryScenarioStatus = allGatesTrue ? 'valid' : 'forming';
  
  // Build and return the scenario
  // NOTE: We do NOT mutate any input objects
  const scenario: EntryScenario = {
    id,
    type,
    contextId,
    status,
    requiredGates: { ...requiredGates }, // Defensive copy
    optionalConfluences: { ...optionalConfluences }, // Defensive copy
    evaluatedAt
  };
  
  return scenario;
}

/**
 * Guard: Check if a scenario is in 'forming' state
 * 
 * A scenario is forming when required gates are not yet complete.
 * 
 * @param scenario - The EntryScenario to check
 * @returns true if scenario.status === 'forming'
 */
export function isScenarioForming(scenario: EntryScenario): boolean {
  return scenario.status === 'forming';
}

/**
 * Guard: Check if a scenario is in 'valid' state
 * 
 * A scenario is valid when ALL required gates are satisfied.
 * 
 * NOTE: 'valid' ≠ tradable
 * NOTE: 'valid' ≠ signal
 * 
 * A valid scenario is simply a complete structural idea.
 * 
 * @param scenario - The EntryScenario to check
 * @returns true if scenario.status === 'valid'
 */
export function isScenarioValid(scenario: EntryScenario): boolean {
  return scenario.status === 'valid';
}

/**
 * Guard: Check if a scenario is in 'invalidated' state
 * 
 * A scenario is invalidated when market conditions have broken the scenario.
 * 
 * @param scenario - The EntryScenario to check
 * @returns true if scenario.status === 'invalidated'
 */
export function isScenarioInvalidated(scenario: EntryScenario): boolean {
  return scenario.status === 'invalidated';
}

/**
 * Invalidation result with reason
 */
export type InvalidationResult = {
  /** Whether the scenario should be invalidated */
  invalidated: boolean;
  
  /** Reason for invalidation (if invalidated) */
  reason?: 'context_not_tradable' | 'structure_break' | 'liquidity_against';
};

/**
 * Check if a scenario should be invalidated based on context changes
 * 
 * Architecture Decision: Separate validation function (NOT inside buildEntryScenario)
 * 
 * This function evaluates whether a scenario should be invalidated by comparing
 * the scenario's original context with a new/updated context.
 * 
 * Invalidation conditions:
 * 1. If nextContext is not tradable → invalidate with reason 'context_not_tradable'
 * 2. Structure breaks / liquidity against logic (basic implementation)
 * 
 * @param scenario - The EntryScenario to validate
 * @param nextContext - Updated LiquidityContext to check against
 * @returns InvalidationResult indicating if scenario should be invalidated
 * 
 * @remarks
 * - This function is pure and deterministic
 * - Works ONLY with LiquidityContext (status, directionBias, lifecycle)
 * - NO additional market data
 * - Input objects are never mutated
 * - Returns result object; does NOT modify scenario
 */
export function invalidateOnContextChange(
  scenario: EntryScenario,
  nextContext: LiquidityContext
): InvalidationResult {
  // Check if nextContext is tradable using Phase 4.2 contract
  if (!isLiquidityContextTradable(nextContext)) {
    return {
      invalidated: true,
      reason: 'context_not_tradable'
    };
  }
  
  // Additional structural checks could be implemented here
  // For now, basic invalidation logic:
  // - If context becomes non-tradable, invalidate
  // - More detailed structural break logic can be added in future iterations
  
  // If context is still tradable, scenario remains valid
  return {
    invalidated: false
  };
}
