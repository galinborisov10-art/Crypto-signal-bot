/**
 * Re-analysis Invariant Tests - Phase 5.3: Re-analysis & Invalidation Engine
 * 
 * Comprehensive invariant tests for re-analysis behavior.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Determinism
 * 2. No Mutation
 * 3. Each Invalidation Reason (5 scenarios)
 * 4. Still-Valid Path
 * 5. Boundary Cases
 * 6. Isolation from Phase 5.2
 */

import { reanalyzeVirtualPosition } from './reanalysis.contracts';
import {
  validMarketState,
  structureBrokenState,
  poiInvalidatedStateSL,
  poiInvalidatedStateTP1,
  poiInvalidatedStateTP3,
  counterLiquidityState,
  htfBiasFlippedState,
  htfBiasNeutralState,
  validOpenPosition,
  completedPosition,
  progressingPosition,
  stalledPosition,
  expectedStillValid,
  expectedStructureBroken,
  expectedPOIInvalidated,
  expectedCounterLiquidity,
  expectedHTFBiasFlipped,
  expectedTimeDecayExceeded,
  expectedCompletedSkip,
  evaluatedAt1Hour,
  evaluatedAtAlmost24Hours,
  evaluatedAtExactly24Hours,
  evaluatedAtOver24Hours,
  evaluatedAt48Hours
} from './reanalysis.fixtures';

describe('Re-analysis - Invariant Tests', () => {
  
  // ============================================================
  // DETERMINISM
  // ============================================================
  
  describe('Determinism', () => {
    
    test('Same inputs always produce same output', () => {
      // Act: Re-analyze twice with identical inputs
      const result1 = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      const result2 = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Results are identical
      expect(result1).toEqual(result2);
      expect(result1.status).toBe(result2.status);
      
      if (result1.status === 'still_valid' && result2.status === 'still_valid') {
        expect(result1.checksPassed).toEqual(result2.checksPassed);
      }
    });
    
    test('Deterministic for all invalidation paths', () => {
      // Test each invalidation reason for determinism
      const testCases = [
        { state: structureBrokenState, expectedReason: 'STRUCTURE_BROKEN' },
        { state: poiInvalidatedStateSL, expectedReason: 'POI_INVALIDATED' },
        { state: counterLiquidityState, expectedReason: 'LIQUIDITY_TAKEN_AGAINST' },
        { state: htfBiasFlippedState, expectedReason: 'HTF_BIAS_FLIPPED' }
      ];
      
      for (const testCase of testCases) {
        const result1 = reanalyzeVirtualPosition(
          validOpenPosition,
          testCase.state,
          evaluatedAt1Hour
        );
        const result2 = reanalyzeVirtualPosition(
          validOpenPosition,
          testCase.state,
          evaluatedAt1Hour
        );
        
        expect(result1).toEqual(result2);
        expect(result1.status).toBe('invalidated');
        expect(result2.status).toBe('invalidated');
        
        if (result1.status === 'invalidated' && result2.status === 'invalidated') {
          expect(result1.reason).toBe(testCase.expectedReason);
          expect(result2.reason).toBe(testCase.expectedReason);
        }
      }
    });
    
    test('Fixed timestamps produce consistent results', () => {
      // Act: Re-analyze at different fixed timestamps
      const resultEarly = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      const resultLater = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAtAlmost24Hours
      );
      
      // Assert: Both should be valid (within 24-hour threshold)
      expect(resultEarly.status).toBe('still_valid');
      expect(resultLater.status).toBe('still_valid');
    });
    
  });
  
  // ============================================================
  // NO MUTATION
  // ============================================================
  
  describe('No Mutation', () => {
    
    test('Original position unchanged after re-analysis', () => {
      // Arrange: Clone original for comparison
      const originalPosition = { ...validOpenPosition };
      const originalStatus = validOpenPosition.status;
      const originalProgress = validOpenPosition.progressPercent;
      
      // Act: Re-analyze
      reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Original unchanged
      expect(validOpenPosition.status).toBe(originalStatus);
      expect(validOpenPosition.progressPercent).toBe(originalProgress);
      expect(validOpenPosition).toEqual(originalPosition);
    });
    
    test('Market state unchanged after re-analysis', () => {
      // Arrange: Clone original for comparison
      const originalBias = validMarketState.htfBias;
      const originalStructure = validMarketState.structureIntact;
      const originalPOISize = validMarketState.pois.size;
      const originalInvalidatedSize = validMarketState.invalidatedPOIs.size;
      
      // Act: Re-analyze
      reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Market state unchanged
      expect(validMarketState.htfBias).toBe(originalBias);
      expect(validMarketState.structureIntact).toBe(originalStructure);
      expect(validMarketState.pois.size).toBe(originalPOISize);
      expect(validMarketState.invalidatedPOIs.size).toBe(originalInvalidatedSize);
    });
    
    test('No mutation across multiple invalidation scenarios', () => {
      // Test that re-analysis doesn't mutate inputs even when invalidated
      const originalPosition = { ...validOpenPosition };
      
      // Run multiple re-analyses with different states
      reanalyzeVirtualPosition(validOpenPosition, structureBrokenState, evaluatedAt1Hour);
      reanalyzeVirtualPosition(validOpenPosition, poiInvalidatedStateSL, evaluatedAt1Hour);
      reanalyzeVirtualPosition(validOpenPosition, counterLiquidityState, evaluatedAt1Hour);
      
      // Assert: Position still unchanged
      expect(validOpenPosition).toEqual(originalPosition);
    });
    
  });
  
  // ============================================================
  // INVALIDATION REASON: STRUCTURE_BROKEN
  // ============================================================
  
  describe('Invalidation Reason: STRUCTURE_BROKEN', () => {
    
    test('Triggers when structureIntact is false', () => {
      // Act: Re-analyze with broken structure
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        structureBrokenState,
        evaluatedAt1Hour
      );
      
      // Assert: Invalidated with correct reason
      expect(result).toEqual(expectedStructureBroken);
      expect(result.status).toBe('invalidated');
      
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('STRUCTURE_BROKEN');
      }
    });
    
    test('Structure check happens first (short-circuit)', () => {
      // Arrange: State with both structure broken AND other issues
      const multipleIssuesState = {
        ...structureBrokenState,
        counterLiquidityTaken: true,
        invalidatedPOIs: new Set(['poi-sl-001'])
      };
      
      // Act: Re-analyze
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        multipleIssuesState,
        evaluatedAt1Hour
      );
      
      // Assert: Returns STRUCTURE_BROKEN first (short-circuit)
      expect(result.status).toBe('invalidated');
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('STRUCTURE_BROKEN');
      }
    });
    
  });
  
  // ============================================================
  // INVALIDATION REASON: POI_INVALIDATED
  // ============================================================
  
  describe('Invalidation Reason: POI_INVALIDATED', () => {
    
    test('Triggers when SL POI is invalidated', () => {
      // Act: Re-analyze with SL POI invalidated
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        poiInvalidatedStateSL,
        evaluatedAt1Hour
      );
      
      // Assert: Invalidated with correct reason
      expect(result).toEqual(expectedPOIInvalidated);
      expect(result.status).toBe('invalidated');
      
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('POI_INVALIDATED');
      }
    });
    
    test('Triggers when TP1 POI is invalidated', () => {
      // Act: Re-analyze with TP1 POI invalidated
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        poiInvalidatedStateTP1,
        evaluatedAt1Hour
      );
      
      // Assert: Invalidated with correct reason
      expect(result.status).toBe('invalidated');
      
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('POI_INVALIDATED');
      }
    });
    
    test('Triggers when TP3 POI is invalidated', () => {
      // Act: Re-analyze with TP3 POI invalidated
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        poiInvalidatedStateTP3,
        evaluatedAt1Hour
      );
      
      // Assert: Invalidated with correct reason
      expect(result.status).toBe('invalidated');
      
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('POI_INVALIDATED');
      }
    });
    
    test('POI check happens after structure check', () => {
      // Arrange: State with structure intact but POI invalidated
      const poiOnlyState = {
        ...validMarketState,
        invalidatedPOIs: new Set(['poi-sl-001'])
      };
      
      // Act: Re-analyze
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        poiOnlyState,
        evaluatedAt1Hour
      );
      
      // Assert: POI invalidation is detected
      expect(result.status).toBe('invalidated');
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('POI_INVALIDATED');
      }
    });
    
  });
  
  // ============================================================
  // INVALIDATION REASON: LIQUIDITY_TAKEN_AGAINST
  // ============================================================
  
  describe('Invalidation Reason: LIQUIDITY_TAKEN_AGAINST', () => {
    
    test('Triggers when counterLiquidityTaken is true', () => {
      // Act: Re-analyze with counter-liquidity taken
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        counterLiquidityState,
        evaluatedAt1Hour
      );
      
      // Assert: Invalidated with correct reason
      expect(result).toEqual(expectedCounterLiquidity);
      expect(result.status).toBe('invalidated');
      
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('LIQUIDITY_TAKEN_AGAINST');
      }
    });
    
    test('Liquidity check happens after POI check', () => {
      // Arrange: State with valid structure, valid POIs, but counter-liquidity
      const liquidityOnlyState = {
        ...validMarketState,
        counterLiquidityTaken: true
      };
      
      // Act: Re-analyze
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        liquidityOnlyState,
        evaluatedAt1Hour
      );
      
      // Assert: Counter-liquidity is detected
      expect(result.status).toBe('invalidated');
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('LIQUIDITY_TAKEN_AGAINST');
      }
    });
    
  });
  
  // ============================================================
  // INVALIDATION REASON: HTF_BIAS_FLIPPED
  // ============================================================
  
  describe('Invalidation Reason: HTF_BIAS_FLIPPED', () => {
    
    test('Triggers when HTF bias flips from bullish to bearish', () => {
      // Act: Re-analyze with HTF bias flipped
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        htfBiasFlippedState,
        evaluatedAt1Hour
      );
      
      // Assert: Invalidated with correct reason
      expect(result).toEqual(expectedHTFBiasFlipped);
      expect(result.status).toBe('invalidated');
      
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('HTF_BIAS_FLIPPED');
      }
    });
    
    test('Does NOT trigger when HTF bias is neutral', () => {
      // Act: Re-analyze with HTF bias neutral (not a flip)
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        htfBiasNeutralState,
        evaluatedAt1Hour
      );
      
      // Assert: Should remain valid (neutral is not a flip)
      expect(result.status).toBe('still_valid');
    });
    
    test('HTF bias check happens after liquidity check', () => {
      // Arrange: State with everything valid except HTF bias
      const htfOnlyState = {
        ...validMarketState,
        htfBias: 'bearish' as const
      };
      
      // Act: Re-analyze
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        htfOnlyState,
        evaluatedAt1Hour
      );
      
      // Assert: HTF bias flip is detected
      expect(result.status).toBe('invalidated');
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('HTF_BIAS_FLIPPED');
      }
    });
    
  });
  
  // ============================================================
  // INVALIDATION REASON: TIME_DECAY_EXCEEDED
  // ============================================================
  
  describe('Invalidation Reason: TIME_DECAY_EXCEEDED', () => {
    
    test('Triggers when time elapsed exceeds 24 hours', () => {
      // Act: Re-analyze at 24 hours + 1 second
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAtOver24Hours
      );
      
      // Assert: Invalidated with correct reason
      expect(result).toEqual(expectedTimeDecayExceeded);
      expect(result.status).toBe('invalidated');
      
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('TIME_DECAY_EXCEEDED');
      }
    });
    
    test('Triggers when far exceeding 24 hours', () => {
      // Act: Re-analyze at 48 hours
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAt48Hours
      );
      
      // Assert: Invalidated
      expect(result.status).toBe('invalidated');
      if (result.status === 'invalidated') {
        expect(result.reason).toBe('TIME_DECAY_EXCEEDED');
      }
    });
    
    test('Does NOT trigger at exactly 24 hours', () => {
      // Act: Re-analyze at exactly 24 hours
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAtExactly24Hours
      );
      
      // Assert: Should remain valid (not exceeded, just at boundary)
      expect(result.status).toBe('still_valid');
    });
    
    test('Does NOT trigger within 24 hours', () => {
      // Act: Re-analyze at 23:59
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAtAlmost24Hours
      );
      
      // Assert: Should remain valid
      expect(result.status).toBe('still_valid');
    });
    
  });
  
  // ============================================================
  // STILL-VALID PATH
  // ============================================================
  
  describe('Still-Valid Path', () => {
    
    test('All checks passed returns still_valid with correct checksPassed array', () => {
      // Act: Re-analyze with all valid conditions
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Still valid with all checks passed
      expect(result).toEqual(expectedStillValid);
      expect(result.status).toBe('still_valid');
      
      if (result.status === 'still_valid') {
        expect(result.checksPassed).toHaveLength(4);
        expect(result.checksPassed).toContain('STRUCTURE_INTACT');
        expect(result.checksPassed).toContain('POI_REMAINS_VALID');
        expect(result.checksPassed).toContain('NO_COUNTER_LIQUIDITY');
        expect(result.checksPassed).toContain('HTF_BIAS_ALIGNED');
      }
    });
    
    test('Still valid for progressing position', () => {
      // Act: Re-analyze progressing position
      const result = reanalyzeVirtualPosition(
        progressingPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Still valid
      expect(result.status).toBe('still_valid');
    });
    
    test('Still valid for stalled position', () => {
      // Act: Re-analyze stalled position
      const result = reanalyzeVirtualPosition(
        stalledPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Still valid (stalling is status from Phase 5.2, not invalidation)
      expect(result.status).toBe('still_valid');
    });
    
  });
  
  // ============================================================
  // BOUNDARY CASES
  // ============================================================
  
  describe('Boundary Cases', () => {
    
    test('Completed position skips re-analysis', () => {
      // Act: Re-analyze completed position (should skip)
      const result = reanalyzeVirtualPosition(
        completedPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Returns still_valid with empty checks (skip signal)
      expect(result).toEqual(expectedCompletedSkip);
      expect(result.status).toBe('still_valid');
      
      if (result.status === 'still_valid') {
        expect(result.checksPassed).toHaveLength(0);
      }
    });
    
    test('Completed position skips even with broken structure', () => {
      // Act: Re-analyze completed position with broken structure
      const result = reanalyzeVirtualPosition(
        completedPosition,
        structureBrokenState,
        evaluatedAt1Hour
      );
      
      // Assert: Still returns completed skip (no checks run)
      expect(result.status).toBe('still_valid');
      if (result.status === 'still_valid') {
        expect(result.checksPassed).toHaveLength(0);
      }
    });
    
    test('Exactly at 24-hour boundary (inclusive)', () => {
      // Act: Re-analyze at exactly 24 hours
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        validMarketState,
        evaluatedAtExactly24Hours
      );
      
      // Assert: Should still be valid (threshold is exclusive)
      expect(result.status).toBe('still_valid');
    });
    
    test('HTF bias neutral does not trigger flip', () => {
      // Act: Re-analyze with neutral HTF bias
      const result = reanalyzeVirtualPosition(
        validOpenPosition,
        htfBiasNeutralState,
        evaluatedAt1Hour
      );
      
      // Assert: Still valid (neutral is not a flip)
      expect(result.status).toBe('still_valid');
    });
    
  });
  
  // ============================================================
  // ISOLATION FROM PHASE 5.2
  // ============================================================
  
  describe('Isolation from Phase 5.2', () => {
    
    test('Re-analysis does not affect progress calculation', () => {
      // Arrange: Position with specific progress
      const positionWithProgress = {
        ...validOpenPosition,
        progressPercent: 45
      };
      
      // Act: Re-analyze
      const result = reanalyzeVirtualPosition(
        positionWithProgress,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Progress unchanged
      expect(positionWithProgress.progressPercent).toBe(45);
      expect(result.status).toBe('still_valid');
    });
    
    test('Re-analysis does not affect reachedTargets', () => {
      // Arrange: Position with reached targets
      const positionWithTargets = {
        ...validOpenPosition,
        reachedTargets: ['TP1' as const, 'TP2' as const]
      };
      
      // Act: Re-analyze
      reanalyzeVirtualPosition(
        positionWithTargets,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Targets unchanged
      expect(positionWithTargets.reachedTargets).toEqual(['TP1', 'TP2']);
    });
    
    test('Re-analysis does not affect status', () => {
      // Act: Re-analyze progressing position
      const originalStatus = progressingPosition.status;
      
      reanalyzeVirtualPosition(
        progressingPosition,
        validMarketState,
        evaluatedAt1Hour
      );
      
      // Assert: Status unchanged (Phase 5.3 is observational only)
      expect(progressingPosition.status).toBe(originalStatus);
    });
    
    test('Phase 5.3 is purely observational', () => {
      // Arrange: Clone position
      const originalPosition = JSON.parse(JSON.stringify(validOpenPosition));
      
      // Act: Multiple re-analyses
      reanalyzeVirtualPosition(validOpenPosition, validMarketState, evaluatedAt1Hour);
      reanalyzeVirtualPosition(validOpenPosition, structureBrokenState, evaluatedAt1Hour);
      reanalyzeVirtualPosition(validOpenPosition, counterLiquidityState, evaluatedAt1Hour);
      
      // Assert: Position completely unchanged
      expect(validOpenPosition).toEqual(originalPosition);
    });
    
  });
  
});
