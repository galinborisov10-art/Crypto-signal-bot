/**
 * Guidance Invariant Tests - Phase 5.4: Guidance Layer / Narrative Signals
 * 
 * Comprehensive invariant tests for guidance signal derivation.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Determinism
 * 2. Priority Cascade (completed > invalidated > stalled > progress)
 * 3. Progress Thresholds (< 25%, ≥ 25%)
 * 4. Status Interaction (status informs, progress leads)
 * 5. Invalidation Dominance
 * 6. Immutability
 */

import { deriveGuidance } from './guidance.contracts';
import {
  earlyPosition,
  lowProgressPosition,
  boundaryLowPosition,
  thresholdPosition,
  midProgressPosition,
  highProgressPosition,
  stalledLowPosition,
  stalledMidPosition,
  stalledHighPosition,
  completedPosition,
  openWithProgressPosition,
  progressingLowPosition,
  progressingMidPosition,
  validReanalysis,
  invalidatedReanalysisStructure,
  invalidatedReanalysisPOI,
  invalidatedReanalysisLiquidity,
  invalidatedReanalysisHTF,
  invalidatedReanalysisTimeDecay,
  expectedWaitForConfirmationEarly,
  expectedWaitForConfirmationLow,
  expectedWaitForConfirmationBoundary,
  expectedHoldThesisThreshold,
  expectedHoldThesisMid,
  expectedHoldThesisHigh,
  expectedHoldThesisCompleted,
  expectedHoldThesisOpenWithProgress,
  expectedThesisWeakeningStalledLow,
  expectedThesisWeakeningStalledMid,
  expectedThesisWeakeningStalledHigh,
  expectedStructureAtRiskOpen,
  expectedStructureAtRiskProgressing,
  expectedStructureAtRiskStalled,
  expectedHoldThesisCompletedInvalidated,
  expectedWaitForConfirmationProgressingLow,
  expectedHoldThesisProgressingMid
} from './guidance.fixtures';

describe('Guidance - Invariant Tests', () => {
  
  // ============================================================
  // DETERMINISM
  // ============================================================
  
  describe('Determinism', () => {
    
    test('Same inputs always produce same output', () => {
      // Act: Derive guidance twice with identical inputs
      const result1 = deriveGuidance(midProgressPosition, validReanalysis);
      const result2 = deriveGuidance(midProgressPosition, validReanalysis);
      
      // Assert: Results are identical
      expect(result1).toEqual(result2);
      expect(result1.signal).toBe(result2.signal);
      expect(result1.progressPercent).toBe(result2.progressPercent);
      expect(result1.status).toBe(result2.status);
      expect(result1.validity).toBe(result2.validity);
    });
    
    test('Deterministic for all signal types', () => {
      // Test each signal type for determinism
      const testCases = [
        { position: earlyPosition, reanalysis: validReanalysis, expectedSignal: 'WAIT_FOR_CONFIRMATION' },
        { position: midProgressPosition, reanalysis: validReanalysis, expectedSignal: 'HOLD_THESIS' },
        { position: stalledMidPosition, reanalysis: validReanalysis, expectedSignal: 'THESIS_WEAKENING' },
        { position: midProgressPosition, reanalysis: invalidatedReanalysisStructure, expectedSignal: 'STRUCTURE_AT_RISK' },
        { position: completedPosition, reanalysis: validReanalysis, expectedSignal: 'HOLD_THESIS' }
      ];
      
      for (const testCase of testCases) {
        const result1 = deriveGuidance(testCase.position, testCase.reanalysis);
        const result2 = deriveGuidance(testCase.position, testCase.reanalysis);
        
        expect(result1).toEqual(result2);
        expect(result1.signal).toBe(testCase.expectedSignal);
        expect(result2.signal).toBe(testCase.expectedSignal);
      }
    });
    
  });
  
  // ============================================================
  // PRIORITY CASCADE
  // ============================================================
  
  describe('Priority Cascade', () => {
    
    test('Priority 1: Completed always returns HOLD_THESIS', () => {
      // Completed position with valid reanalysis
      const result = deriveGuidance(completedPosition, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.status).toBe('completed');
      expect(result.validity).toBe('still_valid');
      expect(result.progressPercent).toBe(100);
    });
    
    test('Priority 1: Completed overrides invalidation', () => {
      // Completed position even if invalidated should return HOLD_THESIS
      const result = deriveGuidance(completedPosition, invalidatedReanalysisStructure);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.status).toBe('completed');
      expect(result.validity).toBe('invalidated'); // validity passed through
      expect(result.progressPercent).toBe(100);
      expect(result).toEqual(expectedHoldThesisCompletedInvalidated);
    });
    
    test('Priority 2: Invalidated always returns STRUCTURE_AT_RISK (unless completed)', () => {
      // Invalidated with open status
      const result1 = deriveGuidance(earlyPosition, invalidatedReanalysisStructure);
      expect(result1.signal).toBe('STRUCTURE_AT_RISK');
      expect(result1.validity).toBe('invalidated');
      expect(result1).toEqual(expectedStructureAtRiskOpen);
      
      // Invalidated with progressing status
      const result2 = deriveGuidance(midProgressPosition, invalidatedReanalysisPOI);
      expect(result2.signal).toBe('STRUCTURE_AT_RISK');
      expect(result2.validity).toBe('invalidated');
      expect(result2).toEqual(expectedStructureAtRiskProgressing);
      
      // Invalidated with stalled status
      const result3 = deriveGuidance(stalledMidPosition, invalidatedReanalysisLiquidity);
      expect(result3.signal).toBe('STRUCTURE_AT_RISK');
      expect(result3.validity).toBe('invalidated');
      expect(result3).toEqual(expectedStructureAtRiskStalled);
    });
    
    test('Priority 3: Stalled always returns THESIS_WEAKENING (unless completed/invalidated)', () => {
      // Stalled at 30%
      const result1 = deriveGuidance(stalledLowPosition, validReanalysis);
      expect(result1.signal).toBe('THESIS_WEAKENING');
      expect(result1.status).toBe('stalled');
      expect(result1).toEqual(expectedThesisWeakeningStalledLow);
      
      // Stalled at 60%
      const result2 = deriveGuidance(stalledMidPosition, validReanalysis);
      expect(result2.signal).toBe('THESIS_WEAKENING');
      expect(result2.status).toBe('stalled');
      expect(result2).toEqual(expectedThesisWeakeningStalledMid);
      
      // Stalled at 80%
      const result3 = deriveGuidance(stalledHighPosition, validReanalysis);
      expect(result3.signal).toBe('THESIS_WEAKENING');
      expect(result3.status).toBe('stalled');
      expect(result3).toEqual(expectedThesisWeakeningStalledHigh);
    });
    
    test('Priority 4: Progress thresholds apply after higher priorities', () => {
      // Early position (< 25%)
      const result1 = deriveGuidance(lowProgressPosition, validReanalysis);
      expect(result1.signal).toBe('WAIT_FOR_CONFIRMATION');
      expect(result1).toEqual(expectedWaitForConfirmationLow);
      
      // Mid progress (>= 25%)
      const result2 = deriveGuidance(midProgressPosition, validReanalysis);
      expect(result2.signal).toBe('HOLD_THESIS');
      expect(result2).toEqual(expectedHoldThesisMid);
    });
    
  });
  
  // ============================================================
  // PROGRESS THRESHOLDS
  // ============================================================
  
  describe('Progress Thresholds', () => {
    
    test('Progress = 0% → WAIT_FOR_CONFIRMATION', () => {
      const result = deriveGuidance(earlyPosition, validReanalysis);
      
      expect(result.signal).toBe('WAIT_FOR_CONFIRMATION');
      expect(result.progressPercent).toBe(0);
      expect(result).toEqual(expectedWaitForConfirmationEarly);
    });
    
    test('Progress = 10% → WAIT_FOR_CONFIRMATION', () => {
      const result = deriveGuidance(lowProgressPosition, validReanalysis);
      
      expect(result.signal).toBe('WAIT_FOR_CONFIRMATION');
      expect(result.progressPercent).toBe(10);
      expect(result).toEqual(expectedWaitForConfirmationLow);
    });
    
    test('Progress = 24.9% → WAIT_FOR_CONFIRMATION (boundary, right-exclusive)', () => {
      const result = deriveGuidance(boundaryLowPosition, validReanalysis);
      
      expect(result.signal).toBe('WAIT_FOR_CONFIRMATION');
      expect(result.progressPercent).toBe(24.9);
      expect(result).toEqual(expectedWaitForConfirmationBoundary);
    });
    
    test('Progress = 25% → HOLD_THESIS (threshold, left-inclusive)', () => {
      const result = deriveGuidance(thresholdPosition, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.progressPercent).toBe(25);
      expect(result).toEqual(expectedHoldThesisThreshold);
    });
    
    test('Progress = 50% → HOLD_THESIS', () => {
      const result = deriveGuidance(midProgressPosition, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.progressPercent).toBe(50);
      expect(result).toEqual(expectedHoldThesisMid);
    });
    
    test('Progress = 74.9% → HOLD_THESIS', () => {
      // Create position with 74.9% progress
      const position = { ...midProgressPosition, progressPercent: 74.9 };
      const result = deriveGuidance(position, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.progressPercent).toBe(74.9);
    });
    
    test('Progress = 75% → HOLD_THESIS (unless stalled)', () => {
      // Create position with 75% progress
      const position = { ...midProgressPosition, progressPercent: 75 };
      const result = deriveGuidance(position, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.progressPercent).toBe(75);
    });
    
    test('Progress = 80% → HOLD_THESIS', () => {
      const result = deriveGuidance(highProgressPosition, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.progressPercent).toBe(80);
      expect(result).toEqual(expectedHoldThesisHigh);
    });
    
    test('Progress = 100% → HOLD_THESIS', () => {
      const result = deriveGuidance(completedPosition, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.progressPercent).toBe(100);
      expect(result).toEqual(expectedHoldThesisCompleted);
    });
    
  });
  
  // ============================================================
  // STATUS INTERACTION
  // ============================================================
  
  describe('Status Interaction', () => {
    
    test('open + 10% → WAIT_FOR_CONFIRMATION', () => {
      const result = deriveGuidance(lowProgressPosition, validReanalysis);
      
      expect(result.signal).toBe('WAIT_FOR_CONFIRMATION');
      expect(result.status).toBe('open');
      expect(result.progressPercent).toBe(10);
    });
    
    test('open + 30% → HOLD_THESIS', () => {
      const result = deriveGuidance(openWithProgressPosition, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.status).toBe('open');
      expect(result.progressPercent).toBe(30);
      expect(result).toEqual(expectedHoldThesisOpenWithProgress);
    });
    
    test('progressing + 10% → WAIT_FOR_CONFIRMATION', () => {
      const result = deriveGuidance(progressingLowPosition, validReanalysis);
      
      expect(result.signal).toBe('WAIT_FOR_CONFIRMATION');
      expect(result.status).toBe('progressing');
      expect(result.progressPercent).toBe(10);
      expect(result).toEqual(expectedWaitForConfirmationProgressingLow);
    });
    
    test('progressing + 40% → HOLD_THESIS', () => {
      const result = deriveGuidance(progressingMidPosition, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.status).toBe('progressing');
      expect(result.progressPercent).toBe(40);
      expect(result).toEqual(expectedHoldThesisProgressingMid);
    });
    
    test('stalled + 30% → THESIS_WEAKENING', () => {
      const result = deriveGuidance(stalledLowPosition, validReanalysis);
      
      expect(result.signal).toBe('THESIS_WEAKENING');
      expect(result.status).toBe('stalled');
      expect(result.progressPercent).toBe(30);
      expect(result).toEqual(expectedThesisWeakeningStalledLow);
    });
    
    test('stalled + 60% → THESIS_WEAKENING', () => {
      const result = deriveGuidance(stalledMidPosition, validReanalysis);
      
      expect(result.signal).toBe('THESIS_WEAKENING');
      expect(result.status).toBe('stalled');
      expect(result.progressPercent).toBe(60);
      expect(result).toEqual(expectedThesisWeakeningStalledMid);
    });
    
    test('stalled + 80% → THESIS_WEAKENING', () => {
      const result = deriveGuidance(stalledHighPosition, validReanalysis);
      
      expect(result.signal).toBe('THESIS_WEAKENING');
      expect(result.status).toBe('stalled');
      expect(result.progressPercent).toBe(80);
      expect(result).toEqual(expectedThesisWeakeningStalledHigh);
    });
    
  });
  
  // ============================================================
  // INVALIDATION DOMINANCE
  // ============================================================
  
  describe('Invalidation Dominance', () => {
    
    test('invalidated + open → STRUCTURE_AT_RISK', () => {
      const result = deriveGuidance(earlyPosition, invalidatedReanalysisStructure);
      
      expect(result.signal).toBe('STRUCTURE_AT_RISK');
      expect(result.status).toBe('open');
      expect(result.validity).toBe('invalidated');
      expect(result).toEqual(expectedStructureAtRiskOpen);
    });
    
    test('invalidated + progressing → STRUCTURE_AT_RISK', () => {
      const result = deriveGuidance(midProgressPosition, invalidatedReanalysisHTF);
      
      expect(result.signal).toBe('STRUCTURE_AT_RISK');
      expect(result.status).toBe('progressing');
      expect(result.validity).toBe('invalidated');
      expect(result).toEqual(expectedStructureAtRiskProgressing);
    });
    
    test('invalidated + stalled → STRUCTURE_AT_RISK', () => {
      const result = deriveGuidance(stalledMidPosition, invalidatedReanalysisTimeDecay);
      
      expect(result.signal).toBe('STRUCTURE_AT_RISK');
      expect(result.status).toBe('stalled');
      expect(result.validity).toBe('invalidated');
      expect(result).toEqual(expectedStructureAtRiskStalled);
    });
    
    test('invalidated + completed → HOLD_THESIS (completed dominates)', () => {
      const result = deriveGuidance(completedPosition, invalidatedReanalysisStructure);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.status).toBe('completed');
      expect(result.validity).toBe('invalidated'); // validity passed through
      expect(result).toEqual(expectedHoldThesisCompletedInvalidated);
    });
    
    test('All invalidation reasons return STRUCTURE_AT_RISK', () => {
      const invalidationReasons = [
        invalidatedReanalysisStructure,
        invalidatedReanalysisPOI,
        invalidatedReanalysisLiquidity,
        invalidatedReanalysisHTF,
        invalidatedReanalysisTimeDecay
      ];
      
      for (const reanalysis of invalidationReasons) {
        const result = deriveGuidance(midProgressPosition, reanalysis);
        expect(result.signal).toBe('STRUCTURE_AT_RISK');
        expect(result.validity).toBe('invalidated');
      }
    });
    
  });
  
  // ============================================================
  // IMMUTABILITY
  // ============================================================
  
  describe('Immutability', () => {
    
    test('No mutation of position', () => {
      const originalPosition = { ...midProgressPosition };
      const originalReanalysis = { ...validReanalysis };
      
      // Act: Derive guidance
      deriveGuidance(midProgressPosition, validReanalysis);
      
      // Assert: Inputs unchanged
      expect(midProgressPosition).toEqual(originalPosition);
      expect(validReanalysis).toEqual(originalReanalysis);
    });
    
    test('No mutation of reanalysisResult', () => {
      const originalReanalysis = { ...validReanalysis };
      
      // Act: Derive guidance multiple times
      deriveGuidance(earlyPosition, validReanalysis);
      deriveGuidance(midProgressPosition, validReanalysis);
      deriveGuidance(completedPosition, validReanalysis);
      
      // Assert: Reanalysis unchanged
      expect(validReanalysis).toEqual(originalReanalysis);
    });
    
    test('Multiple calls with same inputs do not mutate', () => {
      const position1 = { ...stalledMidPosition };
      const position2 = { ...stalledMidPosition };
      const reanalysis1 = { ...validReanalysis };
      const reanalysis2 = { ...validReanalysis };
      
      // Act: Derive guidance twice
      const result1 = deriveGuidance(stalledMidPosition, validReanalysis);
      const result2 = deriveGuidance(stalledMidPosition, validReanalysis);
      
      // Assert: Inputs unchanged, results identical
      expect(stalledMidPosition).toEqual(position1);
      expect(stalledMidPosition).toEqual(position2);
      expect(validReanalysis).toEqual(reanalysis1);
      expect(validReanalysis).toEqual(reanalysis2);
      expect(result1).toEqual(result2);
    });
    
  });
  
  // ============================================================
  // EDGE CASES & COMPREHENSIVE COVERAGE
  // ============================================================
  
  describe('Edge Cases & Comprehensive Coverage', () => {
    
    test('All four guidance signals are reachable', () => {
      // WAIT_FOR_CONFIRMATION
      const result1 = deriveGuidance(earlyPosition, validReanalysis);
      expect(result1.signal).toBe('WAIT_FOR_CONFIRMATION');
      
      // HOLD_THESIS
      const result2 = deriveGuidance(midProgressPosition, validReanalysis);
      expect(result2.signal).toBe('HOLD_THESIS');
      
      // THESIS_WEAKENING
      const result3 = deriveGuidance(stalledMidPosition, validReanalysis);
      expect(result3.signal).toBe('THESIS_WEAKENING');
      
      // STRUCTURE_AT_RISK
      const result4 = deriveGuidance(midProgressPosition, invalidatedReanalysisStructure);
      expect(result4.signal).toBe('STRUCTURE_AT_RISK');
    });
    
    test('Boundary case: exactly 25% triggers HOLD_THESIS', () => {
      const result = deriveGuidance(thresholdPosition, validReanalysis);
      
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.progressPercent).toBe(25);
    });
    
    test('Boundary case: 24.9% triggers WAIT_FOR_CONFIRMATION', () => {
      const result = deriveGuidance(boundaryLowPosition, validReanalysis);
      
      expect(result.signal).toBe('WAIT_FOR_CONFIRMATION');
      expect(result.progressPercent).toBe(24.9);
    });
    
    test('Status does NOT override progress semantics', () => {
      // progressing status with low progress still returns WAIT_FOR_CONFIRMATION
      const result = deriveGuidance(progressingLowPosition, validReanalysis);
      expect(result.signal).toBe('WAIT_FOR_CONFIRMATION');
      expect(result.status).toBe('progressing');
      expect(result.progressPercent).toBe(10);
    });
    
    test('Stalled status ALWAYS dominates progress', () => {
      // Even at 80% progress, stalled returns THESIS_WEAKENING
      const result = deriveGuidance(stalledHighPosition, validReanalysis);
      expect(result.signal).toBe('THESIS_WEAKENING');
      expect(result.progressPercent).toBe(80);
    });
    
    test('Completed status ALWAYS dominates invalidation', () => {
      // Even if invalidated, completed returns HOLD_THESIS
      const result = deriveGuidance(completedPosition, invalidatedReanalysisStructure);
      expect(result.signal).toBe('HOLD_THESIS');
      expect(result.validity).toBe('invalidated');
    });
    
  });
  
});
