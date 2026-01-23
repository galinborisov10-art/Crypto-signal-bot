/**
 * Interpretation Invariant Tests - Phase 6.1: Timeline Interpretation Engine
 * 
 * Comprehensive invariant tests for timeline pattern recognition.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Trajectory Tests (NO_DATA, STABLE, SLOWING, STALLED, REGRESSING)
 * 2. Stability Tests (TERMINATED, REPEATED_INSTABILITY, EARLY_WEAKENING, STABLE)
 * 3. Invalidation Pattern Tests (EARLY, MID, LATE, undefined)
 * 4. Guidance Consistency Tests (FLIP_FLOP, DEGRADING, CONSISTENT, undefined)
 * 5. Determinism and Immutability
 * 6. Edge Cases
 */

import { interpretTimeline } from './interpretation.contracts';
import {
  emptyTimelineForInterpretation,
  singleEntryTimeline,
  stableProgressTimeline,
  slowingProgressTimeline,
  stalledTrajectoryTimeline,
  regressingProgressTimeline,
  completedTimeline,
  invalidatedTimeline,
  repeatedInstabilityTimeline,
  earlyWeakeningTimeline,
  structurallyStableTimeline,
  earlyInvalidationTimeline,
  midInvalidationTimeline,
  lateInvalidationTimeline,
  noInvalidationTimeline,
  flipFlopGuidanceTimeline,
  degradingGuidanceTimeline,
  consistentGuidanceTimeline,
  insufficientGuidanceTimeline,
  expectedEmptyInterpretation,
  expectedStableInterpretation,
  expectedSlowingInterpretation,
  expectedStalledTrajectoryInterpretation,
  expectedRegressingInterpretation,
  expectedCompletedInterpretation,
  expectedInvalidatedInterpretation,
  expectedRepeatedInstabilityInterpretation,
  expectedEarlyWeakeningInterpretation,
  expectedEarlyInvalidationInterpretation,
  expectedMidInvalidationInterpretation,
  expectedLateInvalidationInterpretation,
  expectedFlipFlopInterpretation,
  expectedDegradingInterpretation,
  expectedConsistentInterpretation
} from './interpretation.fixtures';

describe('Interpretation - Invariant Tests', () => {

  // ============================================================
  // TRAJECTORY TESTS
  // ============================================================

  describe('Trajectory Signal', () => {

    test('Empty timeline (< 2 entries) → NO_DATA', () => {
      // Act
      const result = interpretTimeline(emptyTimelineForInterpretation);

      // Assert
      expect(result.trajectory).toBe('NO_DATA');
    });

    test('Single entry timeline (< 2 entries) → NO_DATA', () => {
      // Act
      const result = interpretTimeline(singleEntryTimeline);

      // Assert
      expect(result.trajectory).toBe('NO_DATA');
    });

    test('Stable increasing progress (majority positive deltas) → STABLE_PROGRESS', () => {
      // Act
      const result = interpretTimeline(stableProgressTimeline);

      // Assert
      expect(result.trajectory).toBe('STABLE_PROGRESS');
    });

    test('Slowing progress (positive but shrinking magnitude) → SLOWING_PROGRESS', () => {
      // Act
      const result = interpretTimeline(slowingProgressTimeline);

      // Assert
      expect(result.trajectory).toBe('SLOWING_PROGRESS');
    });

    test('Flat progress (stalled trajectory) → STALLED_TRAJECTORY', () => {
      // Act
      const result = interpretTimeline(stalledTrajectoryTimeline);

      // Assert
      expect(result.trajectory).toBe('STALLED_TRAJECTORY');
    });

    test('Regressing progress (defensive case) → REGRESSING_PROGRESS', () => {
      // Act
      const result = interpretTimeline(regressingProgressTimeline);

      // Assert
      expect(result.trajectory).toBe('REGRESSING_PROGRESS');
    });

  });

  // ============================================================
  // STABILITY TESTS
  // ============================================================

  describe('Stability Signal', () => {

    test('Completed position → TERMINATED', () => {
      // Act
      const result = interpretTimeline(completedTimeline);

      // Assert
      expect(result.stability).toBe('TERMINATED');
    });

    test('Invalidated position → TERMINATED', () => {
      // Act
      const result = interpretTimeline(invalidatedTimeline);

      // Assert
      expect(result.stability).toBe('TERMINATED');
    });

    test('≥ 2 stalled entries → REPEATED_INSTABILITY', () => {
      // Act
      const result = interpretTimeline(repeatedInstabilityTimeline);

      // Assert
      expect(result.stability).toBe('REPEATED_INSTABILITY');
    });

    test('Early weakening (< 25% progress) → EARLY_WEAKENING', () => {
      // Act
      const result = interpretTimeline(earlyWeakeningTimeline);

      // Assert
      expect(result.stability).toBe('EARLY_WEAKENING');
    });

    test('No issues → STRUCTURALLY_STABLE', () => {
      // Act
      const result = interpretTimeline(structurallyStableTimeline);

      // Assert
      expect(result.stability).toBe('STRUCTURALLY_STABLE');
    });

    test('Priority: TERMINATED dominates REPEATED_INSTABILITY', () => {
      // Arrange: Timeline with both completed AND ≥ 2 stalled entries
      const timeline = {
        positionId: 'pos-priority-test',
        entries: [
          {
            evaluatedAt: 1000,
            progressPercent: 20,
            status: 'stalled' as const,
            validity: 'still_valid' as const,
            guidance: 'THESIS_WEAKENING' as const
          },
          {
            evaluatedAt: 2000,
            progressPercent: 20,
            status: 'stalled' as const,
            validity: 'still_valid' as const,
            guidance: 'THESIS_WEAKENING' as const
          },
          {
            evaluatedAt: 3000,
            progressPercent: 100,
            status: 'completed' as const,
            validity: 'still_valid' as const,
            guidance: 'HOLD_THESIS' as const
          }
        ]
      };

      // Act
      const result = interpretTimeline(timeline);

      // Assert: TERMINATED should dominate
      expect(result.stability).toBe('TERMINATED');
    });

  });

  // ============================================================
  // INVALIDATION PATTERN TESTS
  // ============================================================

  describe('Invalidation Pattern', () => {

    test('Early invalidation (< 25% progress) → EARLY_INVALIDATION', () => {
      // Act
      const result = interpretTimeline(earlyInvalidationTimeline);

      // Assert
      expect(result.invalidationPattern).toBe('EARLY_INVALIDATION');
    });

    test('Mid invalidation (25 ≤ progress < 75) → MID_INVALIDATION', () => {
      // Act
      const result = interpretTimeline(midInvalidationTimeline);

      // Assert
      expect(result.invalidationPattern).toBe('MID_INVALIDATION');
    });

    test('Late invalidation (≥ 75% progress) → LATE_INVALIDATION', () => {
      // Act
      const result = interpretTimeline(lateInvalidationTimeline);

      // Assert
      expect(result.invalidationPattern).toBe('LATE_INVALIDATION');
    });

    test('No invalidation → undefined', () => {
      // Act
      const result = interpretTimeline(noInvalidationTimeline);

      // Assert
      expect(result.invalidationPattern).toBeUndefined();
    });

    test('First invalidation used (not last)', () => {
      // Arrange: Timeline with multiple invalidations
      const timeline = {
        positionId: 'pos-multi-inval',
        entries: [
          {
            evaluatedAt: 1000,
            progressPercent: 0,
            status: 'open' as const,
            validity: 'still_valid' as const,
            guidance: 'WAIT_FOR_CONFIRMATION' as const
          },
          {
            evaluatedAt: 2000,
            progressPercent: 20,
            status: 'progressing' as const,
            validity: 'invalidated' as const,
            invalidationReason: 'STRUCTURE_BROKEN' as const,
            guidance: 'STRUCTURE_AT_RISK' as const
          },
          {
            evaluatedAt: 3000,
            progressPercent: 80,
            status: 'progressing' as const,
            validity: 'invalidated' as const,
            invalidationReason: 'TIME_DECAY_EXCEEDED' as const,
            guidance: 'STRUCTURE_AT_RISK' as const
          }
        ]
      };

      // Act
      const result = interpretTimeline(timeline);

      // Assert: Should use first invalidation (20% = EARLY)
      expect(result.invalidationPattern).toBe('EARLY_INVALIDATION');
    });

  });

  // ============================================================
  // GUIDANCE CONSISTENCY TESTS
  // ============================================================

  describe('Guidance Consistency', () => {

    test('< 3 entries → undefined', () => {
      // Act
      const result = interpretTimeline(insufficientGuidanceTimeline);

      // Assert
      expect(result.guidanceConsistency).toBeUndefined();
    });

    test('Flip-flop pattern (A → B → A) → FLIP_FLOP', () => {
      // Act
      const result = interpretTimeline(flipFlopGuidanceTimeline);

      // Assert
      expect(result.guidanceConsistency).toBe('FLIP_FLOP');
    });

    test('Degrading pattern (net movement to weaker) → DEGRADING', () => {
      // Act
      const result = interpretTimeline(degradingGuidanceTimeline);

      // Assert
      expect(result.guidanceConsistency).toBe('DEGRADING');
    });

    test('Consistent (stable signals) → CONSISTENT', () => {
      // Act
      const result = interpretTimeline(consistentGuidanceTimeline);

      // Assert
      expect(result.guidanceConsistency).toBe('CONSISTENT');
    });

    test('All same guidance signals → CONSISTENT', () => {
      // Arrange: Timeline with all same guidance
      const timeline = {
        positionId: 'pos-same-guidance',
        entries: [
          {
            evaluatedAt: 1000,
            progressPercent: 30,
            status: 'progressing' as const,
            validity: 'still_valid' as const,
            guidance: 'HOLD_THESIS' as const
          },
          {
            evaluatedAt: 2000,
            progressPercent: 50,
            status: 'progressing' as const,
            validity: 'still_valid' as const,
            guidance: 'HOLD_THESIS' as const
          },
          {
            evaluatedAt: 3000,
            progressPercent: 70,
            status: 'progressing' as const,
            validity: 'still_valid' as const,
            guidance: 'HOLD_THESIS' as const
          }
        ]
      };

      // Act
      const result = interpretTimeline(timeline);

      // Assert
      expect(result.guidanceConsistency).toBe('CONSISTENT');
    });

    test('Multiple flip-flops detected', () => {
      // Arrange: Timeline with WAIT → HOLD → WAIT → HOLD pattern
      const timeline = {
        positionId: 'pos-multi-flip',
        entries: [
          {
            evaluatedAt: 1000,
            progressPercent: 20,
            status: 'progressing' as const,
            validity: 'still_valid' as const,
            guidance: 'WAIT_FOR_CONFIRMATION' as const
          },
          {
            evaluatedAt: 2000,
            progressPercent: 30,
            status: 'progressing' as const,
            validity: 'still_valid' as const,
            guidance: 'HOLD_THESIS' as const
          },
          {
            evaluatedAt: 3000,
            progressPercent: 20,
            status: 'progressing' as const,
            validity: 'still_valid' as const,
            guidance: 'WAIT_FOR_CONFIRMATION' as const
          },
          {
            evaluatedAt: 4000,
            progressPercent: 30,
            status: 'progressing' as const,
            validity: 'still_valid' as const,
            guidance: 'HOLD_THESIS' as const
          }
        ]
      };

      // Act
      const result = interpretTimeline(timeline);

      // Assert: First flip-flop should be detected
      expect(result.guidanceConsistency).toBe('FLIP_FLOP');
    });

  });

  // ============================================================
  // DETERMINISM & IMMUTABILITY
  // ============================================================

  describe('Determinism & Immutability', () => {

    test('Same inputs always produce same output', () => {
      // Arrange
      const timeline = stableProgressTimeline;

      // Act: Call twice with same input
      const result1 = interpretTimeline(timeline);
      const result2 = interpretTimeline(timeline);

      // Assert: Results are identical
      expect(result1).toEqual(result2);
      expect(result1.trajectory).toBe(result2.trajectory);
      expect(result1.stability).toBe(result2.stability);
      expect(result1.invalidationPattern).toBe(result2.invalidationPattern);
      expect(result1.guidanceConsistency).toBe(result2.guidanceConsistency);
    });

    test('No mutation of timeline', () => {
      // Arrange
      const timeline = {
        positionId: 'pos-immutable',
        entries: [
          {
            evaluatedAt: 1000,
            progressPercent: 0,
            status: 'open' as const,
            validity: 'still_valid' as const,
            guidance: 'WAIT_FOR_CONFIRMATION' as const
          },
          {
            evaluatedAt: 2000,
            progressPercent: 50,
            status: 'progressing' as const,
            validity: 'still_valid' as const,
            guidance: 'HOLD_THESIS' as const
          }
        ]
      };
      
      const originalTimeline = JSON.parse(JSON.stringify(timeline));

      // Act
      interpretTimeline(timeline);

      // Assert: Timeline unchanged
      expect(timeline).toEqual(originalTimeline);
    });

    test('No mutation of entries', () => {
      // Arrange
      const timeline = stableProgressTimeline;
      const originalEntries = JSON.parse(JSON.stringify(timeline.entries));

      // Act
      interpretTimeline(timeline);

      // Assert: Entries unchanged
      expect(timeline.entries).toEqual(originalEntries);
    });

    test('Deterministic for all signal combinations', () => {
      // Test multiple scenarios for determinism
      const testCases = [
        emptyTimelineForInterpretation,
        stableProgressTimeline,
        slowingProgressTimeline,
        stalledTrajectoryTimeline,
        completedTimeline,
        invalidatedTimeline,
        flipFlopGuidanceTimeline,
        degradingGuidanceTimeline
      ];

      for (const testCase of testCases) {
        const result1 = interpretTimeline(testCase);
        const result2 = interpretTimeline(testCase);
        
        expect(result1).toEqual(result2);
      }
    });

  });

  // ============================================================
  // EDGE CASES
  // ============================================================

  describe('Edge Cases', () => {

    test('Empty timeline returns valid interpretation', () => {
      // Act
      const result = interpretTimeline(emptyTimelineForInterpretation);

      // Assert
      expect(result).toEqual(expectedEmptyInterpretation);
    });

    test('Completed timeline analyzes deltas normally', () => {
      // Act
      const result = interpretTimeline(completedTimeline);

      // Assert: Should still analyze trajectory (STABLE_PROGRESS)
      expect(result.trajectory).toBe('STABLE_PROGRESS');
      expect(result.stability).toBe('TERMINATED');
    });

    test('Invalidated timeline analyzes deltas normally', () => {
      // Act
      const result = interpretTimeline(invalidatedTimeline);

      // Assert: Should still analyze trajectory
      expect(result.trajectory).toBe('STABLE_PROGRESS');
      expect(result.stability).toBe('TERMINATED');
    });

    test('Timeline with exactly 2 entries (minimum for deltas)', () => {
      // Arrange
      const timeline = {
        positionId: 'pos-two-entries',
        entries: [
          {
            evaluatedAt: 1000,
            progressPercent: 0,
            status: 'open' as const,
            validity: 'still_valid' as const,
            guidance: 'WAIT_FOR_CONFIRMATION' as const
          },
          {
            evaluatedAt: 2000,
            progressPercent: 25,
            status: 'progressing' as const,
            validity: 'still_valid' as const,
            guidance: 'HOLD_THESIS' as const
          }
        ]
      };

      // Act
      const result = interpretTimeline(timeline);

      // Assert: Should have trajectory (STABLE_PROGRESS)
      expect(result.trajectory).toBe('STABLE_PROGRESS');
      // But no guidance consistency (< 3 entries)
      expect(result.guidanceConsistency).toBeUndefined();
    });

    test('Timeline with exactly 3 entries (minimum for guidance)', () => {
      // Arrange
      const timeline = consistentGuidanceTimeline;

      // Act
      const result = interpretTimeline(timeline);

      // Assert: Should have guidance consistency
      expect(result.guidanceConsistency).toBe('CONSISTENT');
    });

    test('Boundary case: exactly 25% progress for invalidation', () => {
      // Arrange: Invalidation at exactly 25% (should be MID, not EARLY)
      const timeline = {
        positionId: 'pos-boundary-25',
        entries: [
          {
            evaluatedAt: 1000,
            progressPercent: 0,
            status: 'open' as const,
            validity: 'still_valid' as const,
            guidance: 'WAIT_FOR_CONFIRMATION' as const
          },
          {
            evaluatedAt: 2000,
            progressPercent: 25,
            status: 'progressing' as const,
            validity: 'invalidated' as const,
            invalidationReason: 'STRUCTURE_BROKEN' as const,
            guidance: 'STRUCTURE_AT_RISK' as const
          }
        ]
      };

      // Act
      const result = interpretTimeline(timeline);

      // Assert: 25 is NOT < 25, so should be MID
      expect(result.invalidationPattern).toBe('MID_INVALIDATION');
    });

    test('Boundary case: exactly 75% progress for invalidation', () => {
      // Arrange: Invalidation at exactly 75% (should be LATE, not MID)
      const timeline = {
        positionId: 'pos-boundary-75',
        entries: [
          {
            evaluatedAt: 1000,
            progressPercent: 0,
            status: 'open' as const,
            validity: 'still_valid' as const,
            guidance: 'WAIT_FOR_CONFIRMATION' as const
          },
          {
            evaluatedAt: 2000,
            progressPercent: 75,
            status: 'progressing' as const,
            validity: 'invalidated' as const,
            invalidationReason: 'STRUCTURE_BROKEN' as const,
            guidance: 'STRUCTURE_AT_RISK' as const
          }
        ]
      };

      // Act
      const result = interpretTimeline(timeline);

      // Assert: 75 is ≥ 75, so should be LATE
      expect(result.invalidationPattern).toBe('LATE_INVALIDATION');
    });

    test('Boundary case: exactly 25% progress for early weakening', () => {
      // Arrange: Stalled at exactly 25% (should NOT be EARLY_WEAKENING)
      const timeline = {
        positionId: 'pos-boundary-25-weak',
        entries: [
          {
            evaluatedAt: 1000,
            progressPercent: 0,
            status: 'open' as const,
            validity: 'still_valid' as const,
            guidance: 'WAIT_FOR_CONFIRMATION' as const
          },
          {
            evaluatedAt: 2000,
            progressPercent: 25,
            status: 'stalled' as const,
            validity: 'still_valid' as const,
            guidance: 'THESIS_WEAKENING' as const
          }
        ]
      };

      // Act
      const result = interpretTimeline(timeline);

      // Assert: 25 is NOT < 25, so should NOT be EARLY_WEAKENING
      expect(result.stability).not.toBe('EARLY_WEAKENING');
    });

  });

  // ============================================================
  // INTEGRATION TESTS (Full Interpretation Results)
  // ============================================================

  describe('Full Interpretation Results', () => {

    test('Stable progress timeline matches expected interpretation', () => {
      const result = interpretTimeline(stableProgressTimeline);
      expect(result).toEqual(expectedStableInterpretation);
    });

    test('Slowing progress timeline matches expected interpretation', () => {
      const result = interpretTimeline(slowingProgressTimeline);
      expect(result).toEqual(expectedSlowingInterpretation);
    });

    test('Stalled trajectory timeline matches expected interpretation', () => {
      const result = interpretTimeline(stalledTrajectoryTimeline);
      expect(result).toEqual(expectedStalledTrajectoryInterpretation);
    });

    test('Regressing progress timeline matches expected interpretation', () => {
      const result = interpretTimeline(regressingProgressTimeline);
      expect(result).toEqual(expectedRegressingInterpretation);
    });

    test('Completed timeline matches expected interpretation', () => {
      const result = interpretTimeline(completedTimeline);
      expect(result).toEqual(expectedCompletedInterpretation);
    });

    test('Early invalidation timeline matches expected interpretation', () => {
      const result = interpretTimeline(earlyInvalidationTimeline);
      expect(result).toEqual(expectedEarlyInvalidationInterpretation);
    });

    test('Flip-flop guidance timeline matches expected interpretation', () => {
      const result = interpretTimeline(flipFlopGuidanceTimeline);
      expect(result).toEqual(expectedFlipFlopInterpretation);
    });

    test('Degrading guidance timeline matches expected interpretation', () => {
      const result = interpretTimeline(degradingGuidanceTimeline);
      expect(result).toEqual(expectedDegradingInterpretation);
    });

  });

});
