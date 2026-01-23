/**
 * Timeline Test Fixtures - Phase 5.5: Timeline / Observation History
 * 
 * Reusable test fixtures for timeline testing.
 * These fixtures support deterministic, replay-safe testing of timeline mechanics.
 * 
 * Fixture Categories:
 * 1. Empty timeline
 * 2. Sample timeline entries (various states)
 * 3. Timelines with entries (single and multiple)
 * 4. Out-of-order entries for testing rejection
 */

import { VirtualPositionTimeline, TimelineEntry } from './timeline.types';

// ============================================================
// EMPTY TIMELINE
// ============================================================

/**
 * Empty Timeline
 * No entries, ready for first append
 */
export const emptyTimeline: VirtualPositionTimeline = {
  positionId: 'pos-1',
  entries: []
};

// ============================================================
// SAMPLE TIMELINE ENTRIES
// ============================================================

/**
 * Early Entry (timestamp: 1000000)
 * Status: open, no progress, still valid
 */
export const earlyEntry: TimelineEntry = {
  evaluatedAt: 1000000,
  progressPercent: 0,
  status: 'open',
  validity: 'still_valid',
  guidance: 'WAIT_FOR_CONFIRMATION'
};

/**
 * Mid Entry (timestamp: 1000100)
 * Status: progressing, 50% progress, still valid
 */
export const midEntry: TimelineEntry = {
  evaluatedAt: 1000100,
  progressPercent: 50,
  status: 'progressing',
  validity: 'still_valid',
  guidance: 'HOLD_THESIS'
};

/**
 * Late Entry (timestamp: 1000200)
 * Status: progressing, 80% progress, still valid
 */
export const lateEntry: TimelineEntry = {
  evaluatedAt: 1000200,
  progressPercent: 80,
  status: 'progressing',
  validity: 'still_valid',
  guidance: 'HOLD_THESIS'
};

/**
 * Invalidated Entry (timestamp: 1000150)
 * Status: progressing, 60% progress, invalidated (structure broken)
 */
export const invalidatedEntry: TimelineEntry = {
  evaluatedAt: 1000150,
  progressPercent: 60,
  status: 'progressing',
  validity: 'invalidated',
  invalidationReason: 'STRUCTURE_BROKEN',
  guidance: 'STRUCTURE_AT_RISK'
};

/**
 * Same Time Entry 1 (timestamp: 1000100)
 * Status: progressing, 40% progress, still valid
 * Same timestamp as midEntry for testing insertion order
 */
export const sameTimeEntry1: TimelineEntry = {
  evaluatedAt: 1000100,
  progressPercent: 40,
  status: 'progressing',
  validity: 'still_valid',
  guidance: 'HOLD_THESIS'
};

/**
 * Same Time Entry 2 (timestamp: 1000100)
 * Status: progressing, 45% progress, still valid
 * Same timestamp as midEntry for testing insertion order
 */
export const sameTimeEntry2: TimelineEntry = {
  evaluatedAt: 1000100,
  progressPercent: 45,
  status: 'progressing',
  validity: 'still_valid',
  guidance: 'HOLD_THESIS'
};

/**
 * Out-of-Order Entry (timestamp: 999999)
 * Status: open, 0% progress, still valid
 * Earlier than earlyEntry - should be rejected
 */
export const outOfOrderEntry: TimelineEntry = {
  evaluatedAt: 999999, // before earlyEntry
  progressPercent: 0,
  status: 'open',
  validity: 'still_valid',
  guidance: 'WAIT_FOR_CONFIRMATION'
};

/**
 * Stalled Entry (timestamp: 1000300)
 * Status: stalled, 50% progress, still valid
 */
export const stalledEntry: TimelineEntry = {
  evaluatedAt: 1000300,
  progressPercent: 50,
  status: 'stalled',
  validity: 'still_valid',
  guidance: 'THESIS_WEAKENING'
};

/**
 * Completed Entry (timestamp: 1000400)
 * Status: completed, 100% progress, still valid
 */
export const completedEntry: TimelineEntry = {
  evaluatedAt: 1000400,
  progressPercent: 100,
  status: 'completed',
  validity: 'still_valid',
  guidance: 'HOLD_THESIS'
};

// ============================================================
// TIMELINES WITH ENTRIES
// ============================================================

/**
 * Single Entry Timeline
 * Timeline with one entry (earlyEntry)
 */
export const singleEntryTimeline: VirtualPositionTimeline = {
  positionId: 'pos-1',
  entries: [earlyEntry]
};

/**
 * Multi Entry Timeline
 * Timeline with three entries in chronological order
 */
export const multiEntryTimeline: VirtualPositionTimeline = {
  positionId: 'pos-1',
  entries: [earlyEntry, midEntry, lateEntry]
};

/**
 * Timeline with Same Timestamp Entries
 * Timeline demonstrating insertion order preservation
 */
export const sameTimestampTimeline: VirtualPositionTimeline = {
  positionId: 'pos-2',
  entries: [earlyEntry, sameTimeEntry1, sameTimeEntry2]
};

/**
 * Full Lifecycle Timeline
 * Timeline showing complete position lifecycle
 */
export const fullLifecycleTimeline: VirtualPositionTimeline = {
  positionId: 'pos-3',
  entries: [earlyEntry, midEntry, lateEntry, stalledEntry, completedEntry]
};

/**
 * Timeline with Invalidation
 * Timeline showing a position that became invalidated
 */
export const invalidatedTimeline: VirtualPositionTimeline = {
  positionId: 'pos-4',
  entries: [earlyEntry, midEntry, invalidatedEntry]
};
