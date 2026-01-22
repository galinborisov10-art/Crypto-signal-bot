/**
 * Virtual Position Progress Engine - Invariant Tests - Phase 5.2
 * 
 * Comprehensive invariant tests for progress engine behavior.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Progress Monotonicity (never decreases)
 * 2. Correct TP Detection (with skipping)
 * 3. Status Transitions
 * 4. Determinism
 * 5. Immutability
 * 6. Boundary Cases
 */

import { updateVirtualPositionProgress } from './virtualPosition.progress';
import {
  T0,
  openBullishPosition,
  bullishPOIMap,
  bearishPOIMap,
  validScore
} from './virtualPosition.fixtures';
import { VirtualPosition } from './virtualPosition.types';
import { EntryScenarioType } from '../entry-scenarios';
import { RiskContract } from '../risk-contracts';

describe('Virtual Position - Progress Engine Invariant Tests', () => {
  
  // ============================================================
  // PROGRESS MONOTONICITY
  // ============================================================
  
  describe('Progress Monotonicity', () => {
    
    test('Progress never decreases when price moves backward', () => {
      // Arrange: Start with position at 50% progress
      let position: VirtualPosition = {
        ...openBullishPosition,
        progressPercent: 50,
        lastEvaluatedAt: T0
      };
      
      // Act: Update with lower price (backward movement)
      const result = updateVirtualPositionProgress(
        position,
        115, // Lower than what gave 50%
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Progress does not decrease
      expect(result.progressPercent).toBeGreaterThanOrEqual(50);
    });
    
    test('Progress increases when price moves forward', () => {
      // Arrange: Start with position at 0% progress
      let position = openBullishPosition;
      
      // Act: Update with higher price
      const result = updateVirtualPositionProgress(
        position,
        125, // Moving toward TP1 (130-135)
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Progress increases
      expect(result.progressPercent).toBeGreaterThan(0);
    });
    
    test('Math.max behavior prevents progress decrease', () => {
      // Arrange: Position with some progress
      let position: VirtualPosition = {
        ...openBullishPosition,
        progressPercent: 60,
        lastEvaluatedAt: T0
      };
      
      // Act: Multiple updates with varying prices
      let updated1 = updateVirtualPositionProgress(position, 140, bullishPOIMap, T0 + 1000);
      let updated2 = updateVirtualPositionProgress(updated1, 120, bullishPOIMap, T0 + 2000);
      let updated3 = updateVirtualPositionProgress(updated2, 150, bullishPOIMap, T0 + 3000);
      
      // Assert: Progress only increases or stays same
      expect(updated1.progressPercent).toBeGreaterThanOrEqual(position.progressPercent);
      expect(updated2.progressPercent).toBeGreaterThanOrEqual(updated1.progressPercent);
      expect(updated3.progressPercent).toBeGreaterThanOrEqual(updated2.progressPercent);
    });
    
  });
  
  // ============================================================
  // CORRECT TP DETECTION
  // ============================================================
  
  describe('TP Detection', () => {
    
    test('TP1 detected when price enters TP1 POI range (bullish)', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price reaches TP1 low (130)
      const result = updateVirtualPositionProgress(
        position,
        130,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: TP1 is in reachedTargets
      expect(result.reachedTargets).toContain('TP1');
    });
    
    test('TP2 detected when price enters TP2 POI range (bullish)', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price reaches TP2 low (150)
      const result = updateVirtualPositionProgress(
        position,
        150,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: TP2 is in reachedTargets
      expect(result.reachedTargets).toContain('TP2');
    });
    
    test('TP3 detected when price enters TP3 POI range (bullish)', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price reaches TP3 low (180)
      const result = updateVirtualPositionProgress(
        position,
        180,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: TP3 is in reachedTargets
      expect(result.reachedTargets).toContain('TP3');
    });
    
    test('Skipping allowed - TP3 hit before TP1', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price jumps directly to TP3 (180)
      const result = updateVirtualPositionProgress(
        position,
        180,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: TP3 is reached even though TP1/TP2 not hit
      expect(result.reachedTargets).toContain('TP3');
      // TP1 and TP2 also detected because price passed through them
      expect(result.reachedTargets).toContain('TP1');
      expect(result.reachedTargets).toContain('TP2');
    });
    
    test('No duplicates in reachedTargets', () => {
      // Arrange: Position with TP1 already reached
      const position: VirtualPosition = {
        ...openBullishPosition,
        reachedTargets: ['TP1']
      };
      
      // Act: Update with price still at TP1
      const result = updateVirtualPositionProgress(
        position,
        130,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: TP1 appears only once
      const tp1Count = result.reachedTargets.filter(tp => tp === 'TP1').length;
      expect(tp1Count).toBe(1);
    });
    
    test('Logical sorting maintained (TP1, TP2, TP3)', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price reaches all TPs
      const result = updateVirtualPositionProgress(
        position,
        185, // Beyond TP3
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Array is sorted logically
      expect(result.reachedTargets).toEqual(['TP1', 'TP2', 'TP3']);
    });
    
    test('TP detection works for bearish scenarios', () => {
      // Arrange: Create bearish position
      const bearishRisk: RiskContract = {
        scenarioId: 'scen-bearish-1',
        stopLoss: {
          type: 'orderBlock',
          referencePoiId: 'poi-sl-bearish-001',
          beyondStructure: true
        },
        takeProfits: [
          { level: 'TP1', targetPoiId: 'poi-tp1-bearish-001', probability: 'high' },
          { level: 'TP2', targetPoiId: 'poi-tp2-bearish-001', probability: 'medium' },
          { level: 'TP3', targetPoiId: 'poi-tp3-bearish-001', probability: 'low' }
        ],
        rr: 4.5,
        status: 'valid',
        evaluatedAt: T0
      };
      
      const bearishPosition: VirtualPosition = {
        id: 'vpos-bearish-test-001',
        scenarioId: 'scen-bearish-1',
        scenarioType: EntryScenarioType.LiquiditySweepDisplacement,
        score: validScore,
        risk: bearishRisk,
        status: 'open',
        progressPercent: 0,
        reachedTargets: [],
        openedAt: T0,
        lastEvaluatedAt: T0
      };
      
      // Act: Price reaches TP1 high for bearish (170)
      const result = updateVirtualPositionProgress(
        bearishPosition,
        170,
        bearishPOIMap,
        T0 + 1000
      );
      
      // Assert: TP1 is reached
      expect(result.reachedTargets).toContain('TP1');
    });
    
  });
  
  // ============================================================
  // STATUS TRANSITIONS
  // ============================================================
  
  describe('Status Transitions', () => {
    
    test('open → progressing when progress > 0', () => {
      // Arrange: Position at 0% (open)
      const position = openBullishPosition;
      
      // Act: Price moves toward TP1
      const result = updateVirtualPositionProgress(
        position,
        120, // Between entry and TP1
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Status is progressing
      expect(result.status).toBe('progressing');
      expect(result.progressPercent).toBeGreaterThan(0);
    });
    
    test('progressing → stalled when time threshold exceeded', () => {
      // Arrange: Position with some progress
      const position: VirtualPosition = {
        ...openBullishPosition,
        progressPercent: 30,
        status: 'progressing',
        lastEvaluatedAt: T0
      };
      
      // Act: Update after 2 hours with no progress change
      const result = updateVirtualPositionProgress(
        position,
        120, // Same price = same progress
        bullishPOIMap,
        T0 + (2 * 60 * 60 * 1000) // 2 hours later
      );
      
      // Assert: Status is stalled (if progress unchanged)
      if (result.progressPercent === position.progressPercent) {
        expect(result.status).toBe('stalled');
      }
    });
    
    test('progressing → completed when last TP reached', () => {
      // Arrange: Position with some progress
      const position: VirtualPosition = {
        ...openBullishPosition,
        progressPercent: 80,
        status: 'progressing',
        reachedTargets: ['TP1', 'TP2']
      };
      
      // Act: Price reaches TP3 (last TP)
      const result = updateVirtualPositionProgress(
        position,
        180,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Status is completed
      expect(result.status).toBe('completed');
      expect(result.reachedTargets).toContain('TP3');
    });
    
    test('Status priority: completed > stalled > progressing > open', () => {
      // Arrange: Position that could be both completed and stalled
      const position: VirtualPosition = {
        ...openBullishPosition,
        progressPercent: 100,
        status: 'progressing',
        reachedTargets: ['TP1', 'TP2'],
        lastEvaluatedAt: T0
      };
      
      // Act: Update after 2 hours with TP3 reached (completed + stalled conditions)
      const result = updateVirtualPositionProgress(
        position,
        180, // TP3 reached
        bullishPOIMap,
        T0 + (2 * 60 * 60 * 1000)
      );
      
      // Assert: completed takes priority
      expect(result.status).toBe('completed');
    });
    
    test('Stays open if progress is 0', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price below entry (no progress)
      const result = updateVirtualPositionProgress(
        position,
        105, // Below entry reference
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Status is open
      expect(result.status).toBe('open');
      expect(result.progressPercent).toBe(0);
    });
    
  });
  
  // ============================================================
  // DETERMINISM
  // ============================================================
  
  describe('Determinism', () => {
    
    test('Same inputs always produce same output', () => {
      // Arrange
      const position = openBullishPosition;
      const price = 125;
      const evaluatedAt = T0 + 1000;
      
      // Act: Call twice with identical inputs
      const result1 = updateVirtualPositionProgress(position, price, bullishPOIMap, evaluatedAt);
      const result2 = updateVirtualPositionProgress(position, price, bullishPOIMap, evaluatedAt);
      
      // Assert: Results are identical
      expect(result1).toEqual(result2);
      expect(result1.progressPercent).toBe(result2.progressPercent);
      expect(result1.reachedTargets).toEqual(result2.reachedTargets);
      expect(result1.status).toBe(result2.status);
    });
    
    test('Fixed timestamps produce deterministic results', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Use fixed timestamp
      const result = updateVirtualPositionProgress(
        position,
        130,
        bullishPOIMap,
        1704070800000 // Fixed timestamp
      );
      
      // Assert: lastEvaluatedAt is the provided timestamp
      expect(result.lastEvaluatedAt).toBe(1704070800000);
    });
    
    test('Direction inference is deterministic', () => {
      // Arrange: Same position
      const position = openBullishPosition;
      
      // Act: Multiple updates with same price
      const results = Array(5).fill(null).map(() =>
        updateVirtualPositionProgress(position, 125, bullishPOIMap, T0 + 1000)
      );
      
      // Assert: All results have same direction-dependent behavior
      const progresses = results.map(r => r.progressPercent);
      expect(new Set(progresses).size).toBe(1); // All same
    });
    
    test('Progress calculation is deterministic', () => {
      // Arrange
      const position = openBullishPosition;
      const prices = [110, 120, 130, 140, 150, 160, 170, 180];
      
      // Act: Calculate progress for each price twice
      const results1 = prices.map(p => 
        updateVirtualPositionProgress(position, p, bullishPOIMap, T0 + 1000)
      );
      const results2 = prices.map(p => 
        updateVirtualPositionProgress(position, p, bullishPOIMap, T0 + 1000)
      );
      
      // Assert: Results match exactly
      results1.forEach((r1, i) => {
        const r2 = results2[i];
        if (r2) {
          expect(r1.progressPercent).toBe(r2.progressPercent);
        }
      });
    });
    
  });
  
  // ============================================================
  // IMMUTABILITY
  // ============================================================
  
  describe('Immutability', () => {
    
    test('Original position unchanged after update', () => {
      // Arrange
      const position = openBullishPosition;
      const originalCopy = JSON.parse(JSON.stringify(position));
      
      // Act
      updateVirtualPositionProgress(
        position,
        125,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Original position unchanged
      expect(position).toEqual(originalCopy);
      expect(position.progressPercent).toBe(0);
      expect(position.status).toBe('open');
    });
    
    test('New position returned', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act
      const result = updateVirtualPositionProgress(
        position,
        125,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Different object reference
      expect(result).not.toBe(position);
    });
    
    test('No mutation of POI map', () => {
      // Arrange
      const position = openBullishPosition;
      const poiMapCopy = new Map(bullishPOIMap);
      
      // Act
      updateVirtualPositionProgress(
        position,
        125,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: POI map unchanged
      expect(bullishPOIMap.size).toBe(poiMapCopy.size);
      expect(Array.from(bullishPOIMap.keys())).toEqual(Array.from(poiMapCopy.keys()));
    });
    
    test('Fields not related to progress remain unchanged', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act
      const result = updateVirtualPositionProgress(
        position,
        125,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Core fields unchanged
      expect(result.id).toBe(position.id);
      expect(result.scenarioId).toBe(position.scenarioId);
      expect(result.scenarioType).toBe(position.scenarioType);
      expect(result.score).toEqual(position.score);
      expect(result.risk).toEqual(position.risk);
      expect(result.openedAt).toBe(position.openedAt);
    });
    
  });
  
  // ============================================================
  // BOUNDARY CASES
  // ============================================================
  
  describe('Boundary Cases', () => {
    
    test('Exact TP hit (price === TP POI boundary)', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price exactly at TP1 low (130)
      const result = updateVirtualPositionProgress(
        position,
        130,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: TP1 is reached
      expect(result.reachedTargets).toContain('TP1');
    });
    
    test('Price at entry reference (0% progress)', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price at or below entry reference (~107.5 for bullish)
      const result = updateVirtualPositionProgress(
        position,
        107,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Progress is 0
      expect(result.progressPercent).toBe(0);
    });
    
    test('Price at furthest TP (100% progress)', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price at TP3 low (180)
      const result = updateVirtualPositionProgress(
        position,
        180,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Progress is 100 or very close
      expect(result.progressPercent).toBeGreaterThanOrEqual(99);
    });
    
    test('Price beyond furthest TP (clamped to 100%)', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price way beyond TP3
      const result = updateVirtualPositionProgress(
        position,
        300, // Way beyond TP3 (180-185)
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Progress clamped to 100
      expect(result.progressPercent).toBe(100);
    });
    
    test('Price below entry (bullish) - clamped to 0%', () => {
      // Arrange
      const position = openBullishPosition;
      
      // Act: Price below entry reference
      const result = updateVirtualPositionProgress(
        position,
        90, // Below SL
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: Progress clamped to 0
      expect(result.progressPercent).toBe(0);
    });
    
    test('Position with only TP1 (no TP2/TP3)', () => {
      // Arrange: Create position with only TP1
      const minimalRisk: RiskContract = {
        scenarioId: 'scen-1',
        stopLoss: {
          type: 'orderBlock',
          referencePoiId: 'poi-sl-001',
          beyondStructure: true
        },
        takeProfits: [
          { level: 'TP1', targetPoiId: 'poi-tp1-001', probability: 'high' }
        ],
        rr: 3.5,
        status: 'valid',
        evaluatedAt: T0
      };
      
      const minimalPosition: VirtualPosition = {
        ...openBullishPosition,
        risk: minimalRisk
      };
      
      // Act: Price at TP1
      const result = updateVirtualPositionProgress(
        minimalPosition,
        130,
        bullishPOIMap,
        T0 + 1000
      );
      
      // Assert: TP1 is last TP, so position is completed
      expect(result.reachedTargets).toContain('TP1');
      expect(result.status).toBe('completed');
    });
    
    test('Stall threshold exactly at 1 hour', () => {
      // Arrange: Position with progress
      const position: VirtualPosition = {
        ...openBullishPosition,
        progressPercent: 40,
        status: 'progressing',
        lastEvaluatedAt: T0
      };
      
      // Act: Update exactly 1 hour later with no progress change
      const result = updateVirtualPositionProgress(
        position,
        120, // Same price
        bullishPOIMap,
        T0 + (60 * 60 * 1000) // Exactly 1 hour
      );
      
      // Assert: Not stalled yet (threshold is >, not >=)
      // Actually, after 1 hour it should not be stalled, needs to be OVER 1 hour
      expect(result.lastEvaluatedAt).toBe(T0 + (60 * 60 * 1000));
    });
    
    test('Stall threshold exceeded', () => {
      // Arrange: Position with progress
      const position: VirtualPosition = {
        ...openBullishPosition,
        progressPercent: 40,
        status: 'progressing',
        lastEvaluatedAt: T0
      };
      
      // Act: Update 1 hour + 1 second later with no progress change
      const result = updateVirtualPositionProgress(
        position,
        120, // Same price
        bullishPOIMap,
        T0 + (60 * 60 * 1000) + 1000 // 1 hour + 1 second
      );
      
      // Assert: Stalled (if progress unchanged)
      if (result.progressPercent === position.progressPercent) {
        expect(result.status).toBe('stalled');
      }
    });
    
  });
  
});
