/**
 * Confluence Score Invariant Tests - Phase 4.4: Confluence Scoring Engine
 * 
 * Comprehensive invariant tests for Confluence Scoring behavior.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Determinism & Replay Safety
 * 2. Scoring Correctness
 * 3. Dampener Behavior
 * 4. Normalization Boundaries
 * 5. Validation (non-valid scenarios)
 * 6. Immutability
 * 7. Breakdown Transparency
 */

import { createPOI, POIType } from '../poi';
import { buildLiquidityContext } from '../liquidity-context';
import {
  buildEntryScenario,
  EntryScenarioType,
  allGatesTrue,
  someGatesFalse
} from '../entry-scenarios';
import { evaluateConfluenceScore } from './confluenceScore.contracts';
import {
  testWeights,
  strongDampenerWeights,
  zeroWeights,
  allConfluencesPresent,
  someConfluencesPresent,
  noConfluences,
  withNewsRisk,
  onlyOrderBlock,
  onlyNewsRisk,
  mixedWithNewsRisk,
  T0,
  T1
} from './confluenceScore.fixtures';

describe('Confluence Score - Invariant Tests', () => {
  
  // ============================================================
  // DETERMINISM & REPLAY SAFETY
  // ============================================================
  
  describe('Determinism & Replay Safety', () => {
    
    test('Same input produces identical output (deterministic replay)', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-determinism-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      // Act: Evaluate multiple times with same inputs
      const result1 = evaluateConfluenceScore(scenario, testWeights, T0);
      const result2 = evaluateConfluenceScore(scenario, testWeights, T0);
      const result3 = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert: All results are identical
      expect(result1).toEqual(result2);
      expect(result2).toEqual(result3);
      
      if (result1.success && result2.success && result3.success) {
        expect(result1.score).toEqual(result2.score);
        expect(result2.score).toEqual(result3.score);
      }
    });
    
    test('Fixed evaluatedAt produces consistent results', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-determinism-002',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.BreakerBlockMSS,
        context,
        allGatesTrue,
        someConfluencesPresent,
        T0
      );
      
      const fixedTimestamp = T1;
      
      // Act: Evaluate at different times (simulated) with fixed timestamp
      const result1 = evaluateConfluenceScore(scenario, testWeights, fixedTimestamp);
      const result2 = evaluateConfluenceScore(scenario, testWeights, fixedTimestamp);
      
      // Assert: Results are identical
      expect(result1).toEqual(result2);
      
      if (result1.success && result2.success) {
        expect(result1.score.evaluatedAt).toBe(fixedTimestamp);
        expect(result2.score.evaluatedAt).toBe(fixedTimestamp);
      }
    });
  });
  
  // ============================================================
  // SCORING CORRECTNESS
  // ============================================================
  
  describe('Scoring Correctness', () => {
    
    test('All confluences present produces 100% score (no dampener)', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-scoring-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        // maxPossibleScore = 20 + 15 + 25 + 15 + 25 = 100
        // rawScore = 20 + 15 + 25 + 15 + 25 + 0 (no newsRisk) = 100
        // normalizedScore = (100 / 100) * 100 = 100
        expect(result.score.rawScore).toBe(100);
        expect(result.score.normalizedScore).toBe(100);
        expect(result.score.confidence).toBe(100);
      }
    });
    
    test('No confluences present produces 0% score', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-scoring-002',
        type: POIType.FairValueGap,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.BuySideTakenRejection,
        context,
        allGatesTrue,
        noConfluences,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        // rawScore = 0
        // normalizedScore = (0 / 100) * 100 = 0
        expect(result.score.rawScore).toBe(0);
        expect(result.score.normalizedScore).toBe(0);
        expect(result.score.confidence).toBe(0);
      }
    });
    
    test('Partial confluences produce correct weighted score', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-scoring-003',
        type: POIType.BreakerBlock,
        timeframe: '15m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // someConfluencesPresent: orderBlock + breakerBlock only
      const scenario = buildEntryScenario(
        EntryScenarioType.SellSideSweepOBReaction,
        context,
        allGatesTrue,
        someConfluencesPresent,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        // someConfluencesPresent: { orderBlock: true, breakerBlock: true, ... rest false }
        // rawScore = 20 (orderBlock) + 25 (breakerBlock) = 45
        // maxPossibleScore = 100
        // normalizedScore = (45 / 100) * 100 = 45
        expect(result.score.rawScore).toBe(45);
        expect(result.score.normalizedScore).toBe(45);
        expect(result.score.confidence).toBe(45);
      }
    });
    
    test('confidence === normalizedScore (semantic alias)', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-scoring-004',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        onlyOrderBlock,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        expect(result.score.confidence).toBe(result.score.normalizedScore);
      }
    });
    
    test('All factors shown in contributions (0 for missing)', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-scoring-005',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.BreakerBlockMSS,
        context,
        allGatesTrue,
        onlyOrderBlock,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        const contributions = result.score.breakdown.contributions;
        
        // All 6 factors must be present in contributions
        expect(Object.keys(contributions).length).toBe(6);
        expect(contributions.orderBlock).toBe(20);
        expect(contributions.fairValueGap).toBe(0);
        expect(contributions.breakerBlock).toBe(0);
        expect(contributions.discountPremium).toBe(0);
        expect(contributions.buySellLiquidity).toBe(0);
        expect(contributions.newsRisk).toBe(0);
      }
    });
  });
  
  // ============================================================
  // DAMPENER BEHAVIOR
  // ============================================================
  
  describe('Dampener Behavior', () => {
    
    test('newsRisk === true reduces score (dampener)', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-dampener-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenarioWithoutRisk = buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      const scenarioWithRisk = buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        allGatesTrue,
        withNewsRisk,
        T0
      );
      
      // Act
      const resultWithoutRisk = evaluateConfluenceScore(scenarioWithoutRisk, testWeights, T0);
      const resultWithRisk = evaluateConfluenceScore(scenarioWithRisk, testWeights, T0);
      
      // Assert
      expect(resultWithoutRisk.success).toBe(true);
      expect(resultWithRisk.success).toBe(true);
      
      if (resultWithoutRisk.success && resultWithRisk.success) {
        // Without risk: rawScore = 100, normalizedScore = 100
        // With risk: rawScore = 100 + (-20) = 80, normalizedScore = 80
        expect(resultWithoutRisk.score.normalizedScore).toBe(100);
        expect(resultWithRisk.score.normalizedScore).toBe(80);
        expect(resultWithRisk.score.normalizedScore).toBeLessThan(
          resultWithoutRisk.score.normalizedScore
        );
      }
    });
    
    test('Dampener impact correctly recorded in dampenersApplied', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-dampener-002',
        type: POIType.FairValueGap,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.BuySideTakenRejection,
        context,
        allGatesTrue,
        withNewsRisk,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        const dampeners = result.score.breakdown.dampenersApplied;
        
        expect(dampeners.length).toBe(1);
        expect(dampeners[0]?.factor).toBe('newsRisk');
        expect(dampeners[0]?.impact).toBe(-20);
      }
    });
    
    test('newsRisk does NOT contribute to maxPossibleScore', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-dampener-003',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        // maxPossibleScore = 20 + 15 + 25 + 15 + 25 = 100
        // newsRisk (-20) is NOT included in maxPossibleScore
        const maxPossibleScore = 100;
        const rawScore = result.score.rawScore;
        const normalizedScore = result.score.normalizedScore;
        
        expect(normalizedScore).toBe((rawScore / maxPossibleScore) * 100);
      }
    });
    
    test('No dampeners applied when newsRisk === false', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-dampener-004',
        type: POIType.BreakerBlock,
        timeframe: '15m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.SellSideSweepOBReaction,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        expect(result.score.breakdown.dampenersApplied.length).toBe(0);
      }
    });
  });
  
  // ============================================================
  // NORMALIZATION BOUNDARIES
  // ============================================================
  
  describe('Normalization Boundaries', () => {
    
    test('Score never exceeds 100', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-boundary-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        expect(result.score.normalizedScore).toBeLessThanOrEqual(100);
        expect(result.score.confidence).toBeLessThanOrEqual(100);
      }
    });
    
    test('Score never goes below 0 (even with strong dampener)', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-boundary-002',
        type: POIType.FairValueGap,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.BreakerBlockMSS,
        context,
        allGatesTrue,
        onlyNewsRisk,
        T0
      );
      
      // Act: Strong dampener that could push score negative
      const result = evaluateConfluenceScore(scenario, strongDampenerWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        expect(result.score.normalizedScore).toBeGreaterThanOrEqual(0);
        expect(result.score.confidence).toBeGreaterThanOrEqual(0);
      }
    });
    
    test('Correct clamping behavior', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-boundary-003',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        allGatesTrue,
        mixedWithNewsRisk,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, strongDampenerWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        // Verify clamping: 0 <= score <= 100
        expect(result.score.normalizedScore).toBeGreaterThanOrEqual(0);
        expect(result.score.normalizedScore).toBeLessThanOrEqual(100);
      }
    });
    
    test('Zero weights produce zero score', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-boundary-004',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.BuySideTakenRejection,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, zeroWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        expect(result.score.rawScore).toBe(0);
        expect(result.score.normalizedScore).toBe(0);
        expect(result.score.confidence).toBe(0);
      }
    });
  });
  
  // ============================================================
  // VALIDATION
  // ============================================================
  
  describe('Validation', () => {
    
    test('No scoring for non-valid scenarios (status !== valid)', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-validation-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const formingScenario = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        someGatesFalse, // Not all gates true → forming
        allConfluencesPresent,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(formingScenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(false);
      
      if (!result.success) {
        expect(result.error).toBe('SCENARIO_NOT_VALID');
      }
    });
    
    test('Returns error result for invalid scenarios (no throw)', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-validation-002',
        type: POIType.FairValueGap,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const invalidScenario = buildEntryScenario(
        EntryScenarioType.BreakerBlockMSS,
        context,
        someGatesFalse,
        {},
        T0
      );
      
      // Act & Assert: Should not throw
      expect(() => {
        evaluateConfluenceScore(invalidScenario, testWeights, T0);
      }).not.toThrow();
      
      const result = evaluateConfluenceScore(invalidScenario, testWeights, T0);
      
      expect(result.success).toBe(false);
    });
  });
  
  // ============================================================
  // IMMUTABILITY
  // ============================================================
  
  describe('Immutability', () => {
    
    test('No mutation of input scenario object', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-immutability-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      const scenarioSnapshot = JSON.parse(JSON.stringify(scenario));
      
      // Act
      evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(scenario).toEqual(scenarioSnapshot);
    });
    
    test('No mutation of input weights object', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-immutability-002',
        type: POIType.BreakerBlock,
        timeframe: '15m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.SellSideSweepOBReaction,
        context,
        allGatesTrue,
        someConfluencesPresent,
        T0
      );
      
      const weightsSnapshot = JSON.parse(JSON.stringify(testWeights));
      
      // Act
      evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(testWeights).toEqual(weightsSnapshot);
    });
  });
  
  // ============================================================
  // BREAKDOWN TRANSPARENCY
  // ============================================================
  
  describe('Breakdown Transparency', () => {
    
    test('present array contains all true confluences', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-breakdown-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        const present = result.score.breakdown.present;
        
        expect(present).toContain('orderBlock');
        expect(present).toContain('fairValueGap');
        expect(present).toContain('breakerBlock');
        expect(present).toContain('discountPremium');
        expect(present).toContain('buySellLiquidity');
        expect(present.length).toBe(5); // All except newsRisk
      }
    });
    
    test('missing array contains all false/undefined confluences', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-breakdown-002',
        type: POIType.FairValueGap,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.BuySideTakenRejection,
        context,
        allGatesTrue,
        onlyOrderBlock,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        const missing = result.score.breakdown.missing;
        
        expect(missing).toContain('fairValueGap');
        expect(missing).toContain('breakerBlock');
        expect(missing).toContain('discountPremium');
        expect(missing).toContain('buySellLiquidity');
        expect(missing).toContain('newsRisk');
        expect(missing.length).toBe(5);
      }
    });
    
    test('Full breakdown always present in success case', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-breakdown-003',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.BreakerBlockMSS,
        context,
        allGatesTrue,
        mixedWithNewsRisk,
        T0
      );
      
      // Act
      const result = evaluateConfluenceScore(scenario, testWeights, T0);
      
      // Assert
      expect(result.success).toBe(true);
      
      if (result.success) {
        const breakdown = result.score.breakdown;
        
        expect(breakdown.present).toBeDefined();
        expect(breakdown.missing).toBeDefined();
        expect(breakdown.contributions).toBeDefined();
        expect(breakdown.dampenersApplied).toBeDefined();
        
        expect(Array.isArray(breakdown.present)).toBe(true);
        expect(Array.isArray(breakdown.missing)).toBe(true);
        expect(Array.isArray(breakdown.dampenersApplied)).toBe(true);
        expect(typeof breakdown.contributions).toBe('object');
      }
    });
  });
});
