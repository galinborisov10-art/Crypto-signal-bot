/**
 * Timeline Type System - Phase 5.5: Timeline / Observation History
 * 
 * Defines types for Virtual Position observation history and temporal tracking.
 * This phase answers ONLY: "How has this idea changed over time?"
 * 
 * This file contains ONLY type definitions - no logic or implementation.
 * 
 * HARD CONSTRAINTS:
 * ❌ NO market analysis
 * ❌ NO decisions
 * ❌ NO recommendations or advice
 * ❌ NO influence on progress, re-analysis, or guidance logic
 * ❌ NO mutation
 * ❌ NO randomness or Date.now()
 * ❌ NO reordering or reinterpretation
 * 
 * Timeline is PASSIVE MEMORY ONLY.
 */

import { VirtualPositionStatus } from './virtualPosition.types';
import { InvalidationReason } from './reanalysis.types';
import { GuidanceSignal } from './guidance.types';

/**
 * Timeline Entry
 * 
 * Architecture Decision: Aggregates outputs from Phases 5.2, 5.3, 5.4
 * 
 * Represents a single observation point in a Virtual Position's timeline.
 * This is a simple aggregation of prior phase outputs with no new analytical fields.
 * 
 * Timeline entries are immutable snapshots that record how a Virtual Position's
 * analytical state appeared at a specific point in time.
 * 
 * Design Rules:
 * - Simple aggregation only (no new analysis)
 * - Optional invalidationReason (present when validity === 'invalidated')
 * - No position ID (timeline already has positionId)
 * - Purely observational (no decisions)
 */
export interface TimelineEntry {
  /** Fixed timestamp when this observation was made (Unix milliseconds) */
  evaluatedAt: number;
  
  // Phase 5.2 (Progress Engine) outputs
  /** Progress toward TP targets (0-100) */
  progressPercent: number;
  /** Current lifecycle status of Virtual Position */
  status: VirtualPositionStatus;
  
  // Phase 5.3 (Re-analysis & Invalidation) outputs
  /** Structural validity from re-analysis */
  validity: 'still_valid' | 'invalidated';
  /** Reason for invalidation (only present when validity === 'invalidated') */
  invalidationReason?: InvalidationReason;
  
  // Phase 5.4 (Guidance Layer) output
  /** Machine-readable guidance signal */
  guidance: GuidanceSignal;
}

/**
 * Virtual Position Timeline
 * 
 * Architecture Decision: Append-only log with readonly array
 * 
 * Represents the complete observation history for a single Virtual Position.
 * Timeline is a passive storage layer that records how analytical state evolves.
 * 
 * Design Rules:
 * - Append-only (entries can only be added, never removed)
 * - Chronologically ordered by evaluatedAt (append order if same timestamp)
 * - Readonly entries array (immutability enforced structurally)
 * - No deep readonly on TimelineEntry fields (shallow immutability)
 * 
 * Invariants (enforced by appendTimelineEntry):
 * - Entries MUST be sorted by evaluatedAt
 * - entry.evaluatedAt >= lastEntry.evaluatedAt (if timeline not empty)
 * - Timeline itself is immutable (always returns new object)
 * 
 * This is MEMORY, NOT INTELLIGENCE:
 * - No interpretation
 * - No optimization
 * - No inference
 * - Just record
 */
export interface VirtualPositionTimeline {
  /** Unique identifier of the Virtual Position this timeline belongs to */
  positionId: string;
  
  /** Ordered history of observations (readonly, append-only) */
  readonly entries: readonly TimelineEntry[];
}
