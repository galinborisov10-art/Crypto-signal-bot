/**
 * Timeline Invariant Tests - Phase 5.5: Timeline / Observation History
 * 
 * Comprehensive invariant tests for timeline mechanics.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Empty Timeline → First Append
 * 2. Sequential Appends
 * 3. Same Timestamp Append
 * 4. Out-of-Order Rejection
 * 5. Immutability
 * 6. Determinism
 */

import { appendTimelineEntry } from './timeline.contracts';
import {
  emptyTimeline,
  earlyEntry,
  midEntry,
  lateEntry,
  invalidatedEntry,
  sameTimeEntry1,
  sameTimeEntry2,
  singleEntryTimeline,
  multiEntryTimeline,
  outOfOrderEntry,
  stalledEntry,
  completedEntry
} from './timeline.fixtures';

describe('Timeline - Invariant Tests', () => {
  
  // ============================================================
  // EMPTY TIMELINE → FIRST APPEND
  // ============================================================
  
  describe('Empty Timeline → First Append', () => {
    
    test('Empty timeline accepts first entry', () => {
      // Act: Append first entry to empty timeline
      const result = appendTimelineEntry(emptyTimeline, earlyEntry);
      
      // Assert: Timeline now has 1 entry
      expect(result.entries.length).toBe(1);
      expect(result.entries[0]).toEqual(earlyEntry);
      expect(result.positionId).toBe(emptyTimeline.positionId);
    });
    
    test('Resulting timeline has exactly 1 entry', () => {
      // Act: Append entry
      const result = appendTimelineEntry(emptyTimeline, earlyEntry);
      
      // Assert: Count is exactly 1
      expect(result.entries).toHaveLength(1);
    });
    
    test('Original empty timeline remains unchanged', () => {
      // Arrange: Capture original state
      const originalEntryCount = emptyTimeline.entries.length;
      
      // Act: Append entry
      appendTimelineEntry(emptyTimeline, earlyEntry);
      
      // Assert: Original timeline unchanged
      expect(emptyTimeline.entries.length).toBe(originalEntryCount);
      expect(emptyTimeline.entries.length).toBe(0);
    });
    
  });
  
  // ============================================================
  // SEQUENTIAL APPENDS
  // ============================================================
  
  describe('Sequential Appends', () => {
    
    test('Append multiple entries in chronological order', () => {
      // Arrange: Start with empty timeline
      let timeline = emptyTimeline;
      
      // Act: Append entries in order
      timeline = appendTimelineEntry(timeline, earlyEntry);
      timeline = appendTimelineEntry(timeline, midEntry);
      timeline = appendTimelineEntry(timeline, lateEntry);
      
      // Assert: All entries present
      expect(timeline.entries.length).toBe(3);
      expect(timeline.entries[0]).toEqual(earlyEntry);
      expect(timeline.entries[1]).toEqual(midEntry);
      expect(timeline.entries[2]).toEqual(lateEntry);
    });
    
    test('Order preserved across multiple appends', () => {
      // Arrange: Start with empty timeline
      let timeline = emptyTimeline;
      
      // Act: Append five entries
      timeline = appendTimelineEntry(timeline, earlyEntry);
      timeline = appendTimelineEntry(timeline, midEntry);
      timeline = appendTimelineEntry(timeline, invalidatedEntry);
      timeline = appendTimelineEntry(timeline, lateEntry);
      timeline = appendTimelineEntry(timeline, stalledEntry);
      
      // Assert: Chronological order maintained
      expect(timeline.entries.length).toBe(5);
      expect(timeline.entries[0]?.evaluatedAt).toBe(1000000);
      expect(timeline.entries[1]?.evaluatedAt).toBe(1000100);
      expect(timeline.entries[2]?.evaluatedAt).toBe(1000150);
      expect(timeline.entries[3]?.evaluatedAt).toBe(1000200);
      expect(timeline.entries[4]?.evaluatedAt).toBe(1000300);
    });
    
    test('Each append returns new timeline object', () => {
      // Arrange: Start with empty timeline
      let timeline = emptyTimeline;
      
      // Act: Append entries and track objects
      const result1 = appendTimelineEntry(timeline, earlyEntry);
      const result2 = appendTimelineEntry(result1, midEntry);
      const result3 = appendTimelineEntry(result2, lateEntry);
      
      // Assert: All different objects
      expect(result1).not.toBe(timeline);
      expect(result2).not.toBe(result1);
      expect(result3).not.toBe(result2);
    });
    
  });
  
  // ============================================================
  // SAME TIMESTAMP APPEND
  // ============================================================
  
  describe('Same Timestamp Append', () => {
    
    test('Two entries with same evaluatedAt both appended', () => {
      // Arrange: Start with timeline containing earlyEntry
      let timeline = singleEntryTimeline;
      
      // Act: Append two entries with same timestamp
      timeline = appendTimelineEntry(timeline, sameTimeEntry1);
      timeline = appendTimelineEntry(timeline, sameTimeEntry2);
      
      // Assert: Both entries present
      expect(timeline.entries.length).toBe(3);
      expect(timeline.entries[1]).toEqual(sameTimeEntry1);
      expect(timeline.entries[2]).toEqual(sameTimeEntry2);
    });
    
    test('Insertion order preserved when timestamps equal', () => {
      // Arrange: Start with empty timeline
      let timeline = emptyTimeline;
      
      // Act: Append entries with same timestamp in specific order
      timeline = appendTimelineEntry(timeline, sameTimeEntry1);
      timeline = appendTimelineEntry(timeline, midEntry); // same timestamp as sameTimeEntry1
      timeline = appendTimelineEntry(timeline, sameTimeEntry2);
      
      // Assert: Order is sameTimeEntry1, midEntry, sameTimeEntry2
      expect(timeline.entries.length).toBe(3);
      expect(timeline.entries[0]).toEqual(sameTimeEntry1);
      expect(timeline.entries[1]).toEqual(midEntry);
      expect(timeline.entries[2]).toEqual(sameTimeEntry2);
      
      // All have same timestamp
      expect(timeline.entries[0]?.evaluatedAt).toBe(1000100);
      expect(timeline.entries[1]?.evaluatedAt).toBe(1000100);
      expect(timeline.entries[2]?.evaluatedAt).toBe(1000100);
    });
    
  });
  
  // ============================================================
  // OUT-OF-ORDER REJECTION
  // ============================================================
  
  describe('Out-of-Order Rejection', () => {
    
    test('Append entry with earlier timestamp returns original timeline unchanged', () => {
      // Arrange: Timeline with entries
      const timeline = multiEntryTimeline;
      const originalLength = timeline.entries.length;
      
      // Act: Attempt to append out-of-order entry
      const result = appendTimelineEntry(timeline, outOfOrderEntry);
      
      // Assert: Timeline unchanged (same object returned)
      expect(result).toBe(timeline);
      expect(result.entries.length).toBe(originalLength);
      expect(result.entries).toBe(timeline.entries);
    });
    
    test('Original timeline not mutated on out-of-order append', () => {
      // Arrange: Timeline with entries
      const timeline = singleEntryTimeline;
      const originalEntries = timeline.entries;
      const originalLength = timeline.entries.length;
      
      // Act: Attempt out-of-order append
      appendTimelineEntry(timeline, outOfOrderEntry);
      
      // Assert: Original timeline completely unchanged
      expect(timeline.entries).toBe(originalEntries);
      expect(timeline.entries.length).toBe(originalLength);
      expect(timeline.entries[0]).toEqual(earlyEntry);
    });
    
    test('No throw on invalid append (silent no-op)', () => {
      // Arrange: Timeline with entries
      const timeline = multiEntryTimeline;
      
      // Act & Assert: No exception thrown
      expect(() => {
        appendTimelineEntry(timeline, outOfOrderEntry);
      }).not.toThrow();
    });
    
    test('Multiple out-of-order attempts all rejected', () => {
      // Arrange: Timeline
      const timeline = multiEntryTimeline;
      const originalLength = timeline.entries.length;
      
      // Act: Attempt multiple out-of-order appends
      let result = timeline;
      result = appendTimelineEntry(result, outOfOrderEntry);
      result = appendTimelineEntry(result, outOfOrderEntry);
      result = appendTimelineEntry(result, outOfOrderEntry);
      
      // Assert: Timeline unchanged (same reference)
      expect(result).toBe(timeline);
      expect(result.entries.length).toBe(originalLength);
    });
    
  });
  
  // ============================================================
  // IMMUTABILITY
  // ============================================================
  
  describe('Immutability', () => {
    
    test('Original timeline never mutated', () => {
      // Arrange: Original timeline
      const original = singleEntryTimeline;
      const originalEntries = original.entries;
      const originalEntryCount = original.entries.length;
      
      // Act: Append new entry
      const result = appendTimelineEntry(original, midEntry);
      
      // Assert: Original unchanged
      expect(original.entries).toBe(originalEntries); // same array reference
      expect(original.entries.length).toBe(originalEntryCount);
      expect(original.entries).toHaveLength(1);
      
      // Result is different
      expect(result.entries).not.toBe(originalEntries);
      expect(result.entries.length).toBe(2);
    });
    
    test('Original entries array never mutated', () => {
      // Arrange: Capture original entries array
      const timeline = singleEntryTimeline;
      const originalEntriesArray = timeline.entries;
      const originalFirstEntry = timeline.entries[0];
      
      // Act: Append entries
      appendTimelineEntry(timeline, midEntry);
      appendTimelineEntry(timeline, lateEntry);
      
      // Assert: Original array completely unchanged
      expect(timeline.entries).toBe(originalEntriesArray);
      expect(timeline.entries.length).toBe(1);
      expect(timeline.entries[0]).toBe(originalFirstEntry);
    });
    
    test('New timeline object returned on successful append', () => {
      // Arrange: Original timeline
      const original = emptyTimeline;
      
      // Act: Append entry
      const result = appendTimelineEntry(original, earlyEntry);
      
      // Assert: Different timeline object
      expect(result).not.toBe(original);
      
      // But same positionId
      expect(result.positionId).toBe(original.positionId);
    });
    
    test('New entries array returned on successful append', () => {
      // Arrange: Original timeline
      const original = singleEntryTimeline;
      const originalEntriesArray = original.entries;
      
      // Act: Append entry
      const result = appendTimelineEntry(original, midEntry);
      
      // Assert: Different entries array
      expect(result.entries).not.toBe(originalEntriesArray);
      
      // But original entry preserved in new array
      expect(result.entries[0]).toBe(originalEntriesArray[0]);
    });
    
  });
  
  // ============================================================
  // DETERMINISM
  // ============================================================
  
  describe('Determinism', () => {
    
    test('Same inputs produce same output', () => {
      // Act: Append same entry twice with same timeline
      const result1 = appendTimelineEntry(emptyTimeline, earlyEntry);
      const result2 = appendTimelineEntry(emptyTimeline, earlyEntry);
      
      // Assert: Results are equal (deep equality)
      expect(result1).toEqual(result2);
      expect(result1.entries).toEqual(result2.entries);
    });
    
    test('Same sequence produces same timeline', () => {
      // Arrange: Define sequence
      const sequence = [earlyEntry, midEntry, lateEntry];
      
      // Act: Apply sequence twice
      let timeline1 = emptyTimeline;
      for (const entry of sequence) {
        timeline1 = appendTimelineEntry(timeline1, entry);
      }
      
      let timeline2 = emptyTimeline;
      for (const entry of sequence) {
        timeline2 = appendTimelineEntry(timeline2, entry);
      }
      
      // Assert: Same result
      expect(timeline1).toEqual(timeline2);
      expect(timeline1.entries.length).toBe(timeline2.entries.length);
    });
    
    test('Out-of-order rejection is deterministic', () => {
      // Act: Attempt out-of-order append twice
      const result1 = appendTimelineEntry(singleEntryTimeline, outOfOrderEntry);
      const result2 = appendTimelineEntry(singleEntryTimeline, outOfOrderEntry);
      
      // Assert: Both return original timeline
      expect(result1).toBe(singleEntryTimeline);
      expect(result2).toBe(singleEntryTimeline);
      expect(result1).toEqual(result2);
    });
    
    test('No randomness in append logic', () => {
      // Act: Append entry multiple times
      const results = [];
      for (let i = 0; i < 10; i++) {
        results.push(appendTimelineEntry(emptyTimeline, earlyEntry));
      }
      
      // Assert: All results identical
      for (let i = 1; i < results.length; i++) {
        expect(results[i]).toEqual(results[0]);
      }
    });
    
  });
  
  // ============================================================
  // EDGE CASES
  // ============================================================
  
  describe('Edge Cases', () => {
    
    test('Append to timeline with same timestamp as last entry', () => {
      // Arrange: Timeline ending with midEntry (timestamp 1000100)
      const timeline = singleEntryTimeline;
      
      // Act: Append entry with exact same timestamp
      const result = appendTimelineEntry(
        appendTimelineEntry(timeline, midEntry),
        sameTimeEntry1 // same timestamp as midEntry
      );
      
      // Assert: Both appended, insertion order preserved
      expect(result.entries.length).toBe(3);
      expect(result.entries[1]).toEqual(midEntry);
      expect(result.entries[2]).toEqual(sameTimeEntry1);
    });
    
    test('Long sequence of appends maintains order', () => {
      // Arrange: Create sequence
      const entries = [
        earlyEntry,
        midEntry,
        invalidatedEntry,
        lateEntry,
        stalledEntry,
        completedEntry
      ];
      
      // Act: Append all
      let timeline = emptyTimeline;
      for (const entry of entries) {
        timeline = appendTimelineEntry(timeline, entry);
      }
      
      // Assert: All present in order
      expect(timeline.entries.length).toBe(6);
      for (let i = 0; i < entries.length; i++) {
        expect(timeline.entries[i]).toEqual(entries[i]);
      }
    });
    
  });
  
});
