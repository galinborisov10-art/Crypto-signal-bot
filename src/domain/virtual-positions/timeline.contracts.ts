/**
 * Timeline Contracts - Phase 5.5: Timeline / Observation History
 * 
 * Pure function for appending timeline entries to Virtual Position timelines.
 * This phase provides ONLY append functionality - no queries or interpretations.
 * 
 * HARD CONSTRAINTS:
 * ❌ NO market analysis
 * ❌ NO decisions
 * ❌ NO recommendations
 * ❌ NO mutations
 * ❌ NO side effects
 * ❌ NO throwing
 * ❌ NO Date.now() or randomness
 * 
 * Timeline is PASSIVE MEMORY ONLY.
 */

import { VirtualPositionTimeline, TimelineEntry } from './timeline.types';

/**
 * Append Timeline Entry
 * 
 * Architecture Decision: Silent no-op on invalid append
 * 
 * Appends a new timeline entry to the Virtual Position timeline.
 * Returns a new VirtualPositionTimeline object (immutable).
 * 
 * Invariant Enforcement:
 * - Chronological order: entry.evaluatedAt >= lastEntry.evaluatedAt
 * - If entry.evaluatedAt < lastEntry.evaluatedAt → returns original timeline unchanged (silent no-op)
 * - Same timestamp allowed: entries with same evaluatedAt preserve insertion order
 * - Always returns NEW timeline object (never mutates input)
 * 
 * Design Decisions:
 * - Deterministic: same inputs → same output
 * - No throwing: invalid append returns original timeline
 * - No validation: trusts upstream phases (5.2, 5.3, 5.4)
 * - No result union: simple function signature
 * 
 * Mental Model:
 * > "Add entry to timeline if timestamp is valid, otherwise do nothing."
 * 
 * @param timeline - The current Virtual Position timeline
 * @param entry - The timeline entry to append
 * @returns New VirtualPositionTimeline with entry appended (or original if invalid)
 * 
 * @example
 * ```typescript
 * // Create empty timeline
 * let timeline: VirtualPositionTimeline = {
 *   positionId: 'pos-1',
 *   entries: []
 * };
 * 
 * // Append first entry
 * const entry1: TimelineEntry = {
 *   evaluatedAt: 1000000,
 *   progressPercent: 0,
 *   status: 'open',
 *   validity: 'still_valid',
 *   guidance: 'WAIT_FOR_CONFIRMATION'
 * };
 * timeline = appendTimelineEntry(timeline, entry1);
 * // timeline.entries.length === 1
 * 
 * // Append second entry (chronological)
 * const entry2: TimelineEntry = {
 *   evaluatedAt: 1000100,
 *   progressPercent: 50,
 *   status: 'progressing',
 *   validity: 'still_valid',
 *   guidance: 'HOLD_THESIS'
 * };
 * timeline = appendTimelineEntry(timeline, entry2);
 * // timeline.entries.length === 2
 * 
 * // Attempt out-of-order append
 * const oldEntry: TimelineEntry = {
 *   evaluatedAt: 999999, // earlier than entry1
 *   progressPercent: 0,
 *   status: 'open',
 *   validity: 'still_valid',
 *   guidance: 'WAIT_FOR_CONFIRMATION'
 * };
 * timeline = appendTimelineEntry(timeline, oldEntry);
 * // timeline unchanged (silent no-op)
 * // timeline.entries.length === 2
 * ```
 */
export function appendTimelineEntry(
  timeline: VirtualPositionTimeline,
  entry: TimelineEntry
): VirtualPositionTimeline {
  // Get the last entry in the timeline (if exists)
  const lastEntry = timeline.entries[timeline.entries.length - 1];
  
  // Invariant check: timestamp must not be earlier than last entry
  // If entry.evaluatedAt < lastEntry.evaluatedAt → silent no-op
  if (lastEntry && entry.evaluatedAt < lastEntry.evaluatedAt) {
    // Return original timeline unchanged (no mutation)
    return timeline;
  }
  
  // Immutable append: create new timeline with new entries array
  // Uses spread operator to create new array with appended entry
  return {
    ...timeline,
    entries: [...timeline.entries, entry]
  };
}
