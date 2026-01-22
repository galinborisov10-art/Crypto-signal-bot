/**
 * Entry Scenario Invariant Tests - Phase 4.3: Entry Scenario Core
 * 
 * Comprehensive invariant tests for Entry Scenario behavior.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Lifecycle Transitions (forming → valid, forming → invalidated, valid → invalidated)
 * 2. Gate Logic (all gates true → valid, some gates false → forming)
 * 3. Confluence Independence (confluences don't gate validity)
 * 4. Determinism & Immutability
 * 5. Invalidation Logic
 */

import { createPOI, POIType } from '../poi';
import { buildLiquidityContext } from '../liquidity-context';
import {
  buildEntryScenario,
  isScenarioForming,
  isScenarioValid,
  isScenarioInvalidated,
  invalidateOnContextChange
} from './entryScenario.contracts';
import {
  EntryScenarioType,
  RequiredGates,
  OptionalConfluences
} from './entryScenario.types';
import {
  T0,
  allGatesTrue,
  someGatesFalse,
  allGatesFalse,
  onlyHTFAligned,
  onlyLiquidityEvent,
  onlyStructuralConfirmation,
  allConfluencesPresent,
  noConfluences,
  formingScenario,
  validScenario,
  invalidatedScenario,
  validScenarioNoConfluences,
  formingScenarioAllConfluences,
  allScenarioTypes
} from './entryScenario.fixtures';

describe('Entry Scenario - Invariant Tests', () => {
  
  // ============================================================
  // LIFECYCLE TRANSITIONS
  // ============================================================
  
  describe('Lifecycle Transitions', () => {
    
    test('forming → valid: When all required gates become true', () => {
      // Arrange: Create a LiquidityContext
      const poi = createPOI({
        id: 'poi-lifecycle-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Act: Build scenario with some gates false (forming)
      const formingGates: RequiredGates = {
        htfBiasAligned: true,
        liquidityEvent: false, // Missing
        structuralConfirmation: true
      };
      
      const scenario1 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        formingGates,
        {},
        T0
      );
      
      // Assert: Scenario is forming
      expect(scenario1.status).toBe('forming');
      expect(isScenarioForming(scenario1)).toBe(true);
      expect(isScenarioValid(scenario1)).toBe(false);
      
      // Act: Build scenario with all gates true (valid)
      const validGates: RequiredGates = {
        htfBiasAligned: true,
        liquidityEvent: true, // Now complete
        structuralConfirmation: true
      };
      
      const scenario2 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        validGates,
        {},
        T0 + 1000
      );
      
      // Assert: Scenario is now valid
      expect(scenario2.status).toBe('valid');
      expect(isScenarioValid(scenario2)).toBe(true);
      expect(isScenarioForming(scenario2)).toBe(false);
    });
    
    test('forming → invalidated: When context becomes non-tradable', () => {
      // Arrange: Create a forming scenario
      const poi = createPOI({
        id: 'poi-lifecycle-002',
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
        someGatesFalse,
        {},
        T0
      );
      
      // Assert: Scenario is forming
      expect(isScenarioForming(scenario)).toBe(true);
      
      // Act: Context becomes expired (non-tradable)
      const expiredContext = buildLiquidityContext(poi, T0 + 90000000);
      
      const invalidationResult = invalidateOnContextChange(scenario, expiredContext);
      
      // Assert: Scenario should be invalidated
      expect(invalidationResult.invalidated).toBe(true);
      expect(invalidationResult.reason).toBe('context_not_tradable');
    });
    
    test('valid → invalidated: When context changes invalidate the scenario', () => {
      // Arrange: Create a valid scenario
      const poi = createPOI({
        id: 'poi-lifecycle-003',
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
        {},
        T0
      );
      
      // Assert: Scenario is valid
      expect(isScenarioValid(scenario)).toBe(true);
      
      // Act: POI becomes mitigated (context becomes non-tradable)
      const mitigatedPOI = createPOI({
        id: 'poi-lifecycle-003',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: true,
        mitigationTimestamp: T0 + 3600000
      });
      
      const mitigatedContext = buildLiquidityContext(mitigatedPOI, T0 + 3600000);
      
      const invalidationResult = invalidateOnContextChange(scenario, mitigatedContext);
      
      // Assert: Scenario should be invalidated
      expect(invalidationResult.invalidated).toBe(true);
      expect(invalidationResult.reason).toBe('context_not_tradable');
    });
    
    test('Scenario can exist without ever becoming valid', () => {
      // Arrange: Create a scenario that never becomes valid
      const poi = createPOI({
        id: 'poi-lifecycle-004',
        type: POIType.FairValueGap,
        timeframe: '15m',
        priceRange: { low: 41500, high: 41800 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 3600000, // 1 hour validity
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Act: Build scenario with gates that never complete
      const scenario = buildEntryScenario(
        EntryScenarioType.BuySideTakenRejection,
        context,
        allGatesFalse,
        {},
        T0
      );
      
      // Assert: Scenario starts forming
      expect(isScenarioForming(scenario)).toBe(true);
      
      // Act: Context expires before scenario becomes valid
      const expiredContext = buildLiquidityContext(poi, T0 + 7200000);
      const invalidationResult = invalidateOnContextChange(scenario, expiredContext);
      
      // Assert: Scenario invalidated without ever being valid
      expect(invalidationResult.invalidated).toBe(true);
      expect(isScenarioValid(scenario)).toBe(false); // Never was valid
    });
  });
  
  // ============================================================
  // GATE LOGIC
  // ============================================================
  
  describe('Gate Logic', () => {
    
    test('All gates true → status = valid', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-gates-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Act
      const scenario = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        {},
        T0
      );
      
      // Assert
      expect(scenario.status).toBe('valid');
      expect(isScenarioValid(scenario)).toBe(true);
    });
    
    test('Some gates false → status = forming', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-gates-002',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Act
      const scenario = buildEntryScenario(
        EntryScenarioType.BreakerBlockMSS,
        context,
        someGatesFalse,
        {},
        T0
      );
      
      // Assert
      expect(scenario.status).toBe('forming');
      expect(isScenarioForming(scenario)).toBe(true);
    });
    
    test('All gates false → status = forming', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-gates-003',
        type: POIType.OrderBlock,
        timeframe: '15m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Act
      const scenario = buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        allGatesFalse,
        {},
        T0
      );
      
      // Assert
      expect(scenario.status).toBe('forming');
      expect(isScenarioForming(scenario)).toBe(true);
    });
    
    test('Each gate checked independently', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-gates-004',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Test only HTF aligned
      const scenario1 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        onlyHTFAligned,
        {},
        T0
      );
      expect(scenario1.status).toBe('forming');
      
      // Test only liquidity event
      const scenario2 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        onlyLiquidityEvent,
        {},
        T0
      );
      expect(scenario2.status).toBe('forming');
      
      // Test only structural confirmation
      const scenario3 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        onlyStructuralConfirmation,
        {},
        T0
      );
      expect(scenario3.status).toBe('forming');
    });
  });
  
  // ============================================================
  // CONFLUENCE INDEPENDENCE
  // ============================================================
  
  describe('Confluence Independence', () => {
    
    test('Optional confluences do NOT gate validity (all gates true, no confluences)', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-confluence-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Act: Build scenario with all gates true but NO confluences
      const scenario = buildEntryScenario(
        EntryScenarioType.BuySideTakenRejection,
        context,
        allGatesTrue,
        noConfluences,
        T0
      );
      
      // Assert: Scenario is valid even without confluences
      expect(scenario.status).toBe('valid');
      expect(isScenarioValid(scenario)).toBe(true);
    });
    
    test('All confluences present but gates false → still forming', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-confluence-002',
        type: POIType.FairValueGap,
        timeframe: '1h',
        priceRange: { low: 41500, high: 41800 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Act: Build scenario with all confluences but some gates false
      const scenario = buildEntryScenario(
        EntryScenarioType.SellSideSweepOBReaction,
        context,
        someGatesFalse,
        allConfluencesPresent,
        T0
      );
      
      // Assert: Scenario is forming despite all confluences
      expect(scenario.status).toBe('forming');
      expect(isScenarioForming(scenario)).toBe(true);
    });
    
    test('Confluences are stored but do not affect status', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-confluence-003',
        type: POIType.BreakerBlock,
        timeframe: '15m',
        priceRange: { low: 42200, high: 42300 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Act: Build two scenarios with same gates but different confluences
      const scenario1 = buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      const scenario2 = buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        allGatesTrue,
        noConfluences,
        T0 + 1
      );
      
      // Assert: Both are valid (same status) but different confluences
      expect(scenario1.status).toBe('valid');
      expect(scenario2.status).toBe('valid');
      expect(scenario1.optionalConfluences).not.toEqual(scenario2.optionalConfluences);
    });
    
    test('Fixture: validScenarioNoConfluences is indeed valid', () => {
      expect(isScenarioValid(validScenarioNoConfluences)).toBe(true);
      expect(Object.keys(validScenarioNoConfluences.optionalConfluences).length).toBe(0);
    });
    
    test('Fixture: formingScenarioAllConfluences is still forming', () => {
      expect(isScenarioForming(formingScenarioAllConfluences)).toBe(true);
      expect(formingScenarioAllConfluences.optionalConfluences.orderBlock).toBe(true);
      expect(formingScenarioAllConfluences.optionalConfluences.fairValueGap).toBe(true);
    });
  });
  
  // ============================================================
  // DETERMINISM & IMMUTABILITY
  // ============================================================
  
  describe('Determinism & Immutability', () => {
    
    test('Same inputs produce identical output (deterministic replay)', () => {
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
      
      // Act: Build scenario multiple times with same inputs
      const scenario1 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      const scenario2 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      const scenario3 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        allConfluencesPresent,
        T0
      );
      
      // Assert: All scenarios are identical
      expect(scenario1).toEqual(scenario2);
      expect(scenario2).toEqual(scenario3);
      expect(scenario1).toEqual(scenario3);
    });
    
    test('Building scenario does NOT mutate LiquidityContext', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-immutability-001',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Take a deep copy for comparison
      const contextSnapshot = JSON.parse(JSON.stringify(context));
      
      // Act: Build scenario
      buildEntryScenario(
        EntryScenarioType.BreakerBlockMSS,
        context,
        allGatesTrue,
        {},
        T0
      );
      
      // Assert: LiquidityContext is unchanged
      expect(context).toEqual(contextSnapshot);
    });
    
    test('Building scenario does NOT mutate input gates or confluences', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-immutability-002',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const gates: RequiredGates = {
        htfBiasAligned: true,
        liquidityEvent: true,
        structuralConfirmation: true
      };
      
      const confluences: OptionalConfluences = {
        orderBlock: true,
        fairValueGap: true
      };
      
      // Take snapshots
      const gatesSnapshot = JSON.parse(JSON.stringify(gates));
      const confluencesSnapshot = JSON.parse(JSON.stringify(confluences));
      
      // Act
      buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        gates,
        confluences,
        T0
      );
      
      // Assert: Input objects are unchanged
      expect(gates).toEqual(gatesSnapshot);
      expect(confluences).toEqual(confluencesSnapshot);
    });
    
    test('Fixed evaluatedAt timestamp produces consistent results', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-determinism-002',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const fixedTimestamp = T0 + 7200000; // +2 hours
      
      // Act: Build scenario at different times (simulated)
      const scenario1 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        {},
        fixedTimestamp
      );
      
      // Simulate time passing (doesn't affect result)
      const scenario2 = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        {},
        fixedTimestamp
      );
      
      // Assert: Results are identical despite simulated time passage
      expect(scenario1).toEqual(scenario2);
      expect(scenario1.evaluatedAt).toBe(fixedTimestamp);
      expect(scenario2.evaluatedAt).toBe(fixedTimestamp);
    });
    
    test('Scenario contains reference to context ID, not context object', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-reference-001',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      // Act
      const scenario = buildEntryScenario(
        EntryScenarioType.BuySideTakenRejection,
        context,
        allGatesTrue,
        {},
        T0
      );
      
      // Assert: Scenario has contextId, not the context object
      expect(scenario.contextId).toBe('poi-reference-001');
      expect((scenario as any).context).toBeUndefined();
      expect((scenario as any).liquidityContext).toBeUndefined();
    });
  });
  
  // ============================================================
  // INVALIDATION LOGIC
  // ============================================================
  
  describe('Invalidation Logic', () => {
    
    test('Scenario invalidated when nextContext becomes non-tradable (expired)', () => {
      // Arrange: Create a valid scenario
      const poi = createPOI({
        id: 'poi-invalidation-001',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 3600000, // 1 hour
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.LiquiditySweepDisplacement,
        context,
        allGatesTrue,
        {},
        T0
      );
      
      // Act: Context becomes expired
      const expiredContext = buildLiquidityContext(poi, T0 + 7200000);
      const result = invalidateOnContextChange(scenario, expiredContext);
      
      // Assert
      expect(result.invalidated).toBe(true);
      expect(result.reason).toBe('context_not_tradable');
    });
    
    test('Scenario invalidated when nextContext becomes non-tradable (mitigated)', () => {
      // Arrange: Create a valid scenario
      const poi = createPOI({
        id: 'poi-invalidation-002',
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
        {},
        T0
      );
      
      // Act: POI becomes mitigated
      const mitigatedPOI = createPOI({
        id: 'poi-invalidation-002',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: true,
        mitigationTimestamp: T0 + 3600000
      });
      
      const mitigatedContext = buildLiquidityContext(mitigatedPOI, T0 + 3600000);
      const result = invalidateOnContextChange(scenario, mitigatedContext);
      
      // Assert
      expect(result.invalidated).toBe(true);
      expect(result.reason).toBe('context_not_tradable');
    });
    
    test('Scenario NOT invalidated when context remains tradable', () => {
      // Arrange: Create a valid scenario
      const poi = createPOI({
        id: 'poi-invalidation-003',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      // Create HTF POI to make context tradable
      const htfPOI = createPOI({
        id: 'poi-htf-invalidation-003',
        type: POIType.OrderBlock,
        timeframe: '1d',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 172800000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0, htfPOI);
      
      const scenario = buildEntryScenario(
        EntryScenarioType.OB_FVG_Discount,
        context,
        allGatesTrue,
        {},
        T0
      );
      
      // Act: Context at a later time but still active and tradable
      const stillActiveContext = buildLiquidityContext(poi, T0 + 3600000, htfPOI);
      const result = invalidateOnContextChange(scenario, stillActiveContext);
      
      // Assert
      expect(result.invalidated).toBe(false);
      expect(result.reason).toBeUndefined();
    });
    
    test('invalidateOnContextChange does NOT mutate scenario or context', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-invalidation-004',
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
        EntryScenarioType.BuySideTakenRejection,
        context,
        allGatesTrue,
        {},
        T0
      );
      
      // Take snapshots
      const scenarioSnapshot = JSON.parse(JSON.stringify(scenario));
      
      // Create next context
      const mitigatedPOI = createPOI({
        id: 'poi-invalidation-004',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: true,
        mitigationTimestamp: T0 + 3600000
      });
      
      const nextContext = buildLiquidityContext(mitigatedPOI, T0 + 3600000);
      const nextContextSnapshot = JSON.parse(JSON.stringify(nextContext));
      
      // Act
      invalidateOnContextChange(scenario, nextContext);
      
      // Assert: Neither scenario nor context is mutated
      expect(scenario).toEqual(scenarioSnapshot);
      expect(nextContext).toEqual(nextContextSnapshot);
    });
  });
  
  // ============================================================
  // SCENARIO TYPE COVERAGE
  // ============================================================
  
  describe('Scenario Type Coverage', () => {
    
    test('All scenario types are supported', () => {
      const poi = createPOI({
        id: 'poi-types-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });
      
      const context = buildLiquidityContext(poi, T0);
      
      const scenarioTypes = [
        EntryScenarioType.LiquiditySweepDisplacement,
        EntryScenarioType.BreakerBlockMSS,
        EntryScenarioType.OB_FVG_Discount,
        EntryScenarioType.BuySideTakenRejection,
        EntryScenarioType.SellSideSweepOBReaction
      ];
      
      scenarioTypes.forEach(type => {
        const scenario = buildEntryScenario(
          type,
          context,
          allGatesTrue,
          {},
          T0
        );
        
        expect(scenario.type).toBe(type);
        expect(scenario.status).toBe('valid');
      });
    });
    
    test('Fixture: allScenarioTypes contains all 5 types', () => {
      expect(allScenarioTypes.length).toBe(5);
      
      const types = allScenarioTypes.map(s => s.type);
      expect(types).toContain(EntryScenarioType.LiquiditySweepDisplacement);
      expect(types).toContain(EntryScenarioType.BreakerBlockMSS);
      expect(types).toContain(EntryScenarioType.OB_FVG_Discount);
      expect(types).toContain(EntryScenarioType.BuySideTakenRejection);
      expect(types).toContain(EntryScenarioType.SellSideSweepOBReaction);
    });
  });
  
  // ============================================================
  // GUARD FUNCTIONS
  // ============================================================
  
  describe('Guard Functions', () => {
    
    test('isScenarioForming returns correct value', () => {
      expect(isScenarioForming(formingScenario)).toBe(true);
      expect(isScenarioForming(validScenario)).toBe(false);
      expect(isScenarioForming(invalidatedScenario)).toBe(false);
    });
    
    test('isScenarioValid returns correct value', () => {
      expect(isScenarioValid(formingScenario)).toBe(false);
      expect(isScenarioValid(validScenario)).toBe(true);
      expect(isScenarioValid(invalidatedScenario)).toBe(false);
    });
    
    test('isScenarioInvalidated returns correct value', () => {
      expect(isScenarioInvalidated(formingScenario)).toBe(false);
      expect(isScenarioInvalidated(validScenario)).toBe(false);
      expect(isScenarioInvalidated(invalidatedScenario)).toBe(true);
    });
  });
});
