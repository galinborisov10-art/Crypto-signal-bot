/**
 * Guidance Type System - Phase 5.4: Guidance Layer / Narrative Signals
 * 
 * Defines types for Virtual Position guidance signals and observational context.
 * This phase answers ONLY: "How does this idea currently look from an analytical perspective?"
 * 
 * This file contains ONLY type definitions - no logic or implementation.
 * 
 * HARD CONSTRAINTS:
 * ❌ NO decisions
 * ❌ NO position management
 * ❌ NO execution logic
 * ❌ NO trade management suggestions
 * ❌ NO market analysis
 * ❌ NO price logic
 * ❌ NO guidance or UX-facing text
 * ❌ NO mutation of VirtualPosition
 * ❌ NO Date.now() or randomness
 * 
 * Guidance is CONTEXT, NOT decision.
 * Guidance is OBSERVATIONAL, NOT instructional.
 */

import { VirtualPositionStatus } from './virtualPosition.types';

/**
 * Guidance Signal
 * 
 * Architecture Decision: Machine-readable enums ONLY (no free text)
 * 
 * Represents the current analytical posture of a Virtual Position.
 * Signals are derived from aggregating progress, status, and validity.
 * 
 * These signals answer: "How does this idea currently look?"
 * They do NOT answer: "What should I do?"
 * 
 * Signals are FROZEN for ESB v1.0 after merge.
 */
export type GuidanceSignal =
  | 'HOLD_THESIS'          // Thesis intact, structure & progress healthy
  | 'THESIS_WEAKENING'     // Valid, but momentum/progress degraded
  | 'STRUCTURE_AT_RISK'    // Invalidated (re-analysis flagged failure)
  | 'WAIT_FOR_CONFIRMATION'; // Early / low progress / neutral state

/**
 * Guidance Result
 * 
 * Architecture Decision: No invalidation reason field (Phase 5.3 already carries it)
 * 
 * Represents the aggregated observational context for a Virtual Position.
 * Combines guidance signal with supporting context (progress, status, validity).
 * 
 * Rationale for no invalidation reason:
 * - Phase 5.3 already carries the invalidation reason
 * - Phase 5.4 is aggregated, non-duplicating layer
 * - Guidance signal is sufficient (STRUCTURE_AT_RISK)
 * 
 * This is a pure output type - no complex logic, just context aggregation.
 */
export interface GuidanceResult {
  /** Machine-readable guidance signal */
  signal: GuidanceSignal;
  
  /** Progress toward TP targets (0-100) */
  progressPercent: number;
  
  /** Current lifecycle status from Phase 5.2 */
  status: VirtualPositionStatus;
  
  /** Structural validity from Phase 5.3 */
  validity: 'still_valid' | 'invalidated';
}
