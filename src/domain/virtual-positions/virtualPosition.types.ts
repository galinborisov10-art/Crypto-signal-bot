/**
 * Virtual Position Type System - Phase 5.1: Virtual Position Model (Design-First)
 * 
 * Defines Virtual Position as a first-class runtime object.
 * Virtual Positions represent "if this were a trade" - NOT real positions.
 * 
 * This file contains ONLY type definitions - no logic or implementation.
 * 
 * HARD CONSTRAINTS:
 * ❌ NO execution logic
 * ❌ NO buy/sell signals
 * ❌ NO SL/TP execution
 * ❌ NO capital, balance, sizing
 * ❌ NO PnL, profit, loss
 * ❌ NO optimization
 * ❌ NO ML
 * ❌ NO randomness
 * ❌ NO Date.now()
 * 
 * Virtual Position is a STATE MODEL, NOT execution instructions.
 */

import { EntryScenarioType } from '../entry-scenarios';
import { ConfluenceScore } from '../confluence-scoring';
import { RiskContract } from '../risk-contracts';

/**
 * Virtual Position Status
 * 
 * Architecture Decision: Named type for consistency with Phase 4 patterns
 * 
 * Represents the lifecycle state of a Virtual Position during observation.
 * Status transitions will be implemented in PR-5.2 (Progress Engine).
 * 
 * PR-5.1 ONLY defines semantics - NO transition logic yet.
 */
export type VirtualPositionStatus =
  | 'open'          // Position created, no movement yet
  | 'progressing'   // Progress toward TP
  | 'stalled'       // No progress, but structure still valid
  | 'invalidated'   // Structure violated
  | 'completed';    // TP3 / stretch target reached

/**
 * Virtual Position
 * 
 * Architecture Decision: Self-contained snapshot (full objects stored)
 * 
 * Represents a "what if this were a trade" observation object.
 * This is NOT a real position - it's a state machine for observing an idea over time.
 * 
 * Key Properties:
 * - Immutable: Every change creates a new Virtual Position
 * - Deterministic: Same inputs always produce same output
 * - Self-contained: Stores full score and risk objects (not just IDs)
 * - Time-aware: Tracks when opened and last evaluated
 * 
 * What Virtual Position is NOT:
 * - ❌ NOT a real trade
 * - ❌ NOT execution instructions
 * - ❌ NOT capital allocation
 * - ❌ NOT PnL tracking
 * 
 * What Virtual Position IS:
 * - ✅ State snapshot of an idea
 * - ✅ Progress observation container
 * - ✅ Structural validity tracker
 * - ✅ Foundation for dry-run runtime
 */
export interface VirtualPosition {
  /** Unique identifier for this Virtual Position */
  id: string;
  
  /** Reference to the Entry Scenario ID */
  scenarioId: string;
  
  /** Type of entry scenario (for quick access without lookup) */
  scenarioType: EntryScenarioType;
  
  /** Full Confluence Score object (self-contained snapshot) */
  score: ConfluenceScore;
  
  /** Full Risk Contract object (self-contained snapshot) */
  risk: RiskContract;
  
  /** Current lifecycle status of this Virtual Position */
  status: VirtualPositionStatus;
  
  /** Progress toward TP targets (0-100) */
  progressPercent: number;
  
  /** Which TP targets have been reached */
  reachedTargets: ('TP1' | 'TP2' | 'TP3')[];
  
  /** Fixed timestamp when this Virtual Position was opened (Unix milliseconds) */
  openedAt: number;
  
  /** Fixed timestamp when this Virtual Position was last evaluated (Unix milliseconds) */
  lastEvaluatedAt: number;
}

/**
 * Virtual Position Result
 * 
 * Architecture Decision: Explicit result type (no exceptions)
 * 
 * Discriminated union representing the outcome of Virtual Position creation.
 * - Success case includes the VirtualPosition
 * - Failure case includes error reason
 * 
 * Error Types (ONLY TWO - Phase 4 already validated):
 * - SCENARIO_NOT_VALID: scenario.status !== 'valid'
 * - RISK_NOT_VALID: risk.status !== 'valid' OR relationship mismatch
 * 
 * This design allows for explicit error handling without exceptions.
 */
export type VirtualPositionResult =
  | { success: true; position: VirtualPosition }
  | { success: false; error: 'SCENARIO_NOT_VALID' | 'RISK_NOT_VALID' };
