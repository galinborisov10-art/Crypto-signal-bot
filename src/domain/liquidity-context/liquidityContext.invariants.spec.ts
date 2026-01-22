/**
 * Liquidity Context Invariants Tests - Phase 4.2: Liquidity Context Layer
 * 
 * Comprehensive invariant tests for Liquidity Context behavior.
 * Tests are semantic and implementation-agnostic.
 * 
 * Test Coverage:
 * 1. Validity Scenarios (active, invalid, expired, mitigated)
 * 2. HTF/LTF Scenarios (aligned, counter, neutral, undefined)
 * 3. Determinism & Immutability
 * 4. Guard Functions
 */

import { POIType, createPOI } from '../poi';
import {
  buildLiquidityContext,
  isLiquidityContextActive,
  isLiquidityContextTradable
} from './liquidityContext.contracts';

/**
 * Fixed reference timestamp for deterministic testing
 * Value: November 14, 2023 22:13:20 GMT
 */
const T0 = 1700000000000;

describe('Liquidity Context - Invariant Tests', () => {
  
  // ==============================================================
  // VALIDITY SCENARIOS
  // ==============================================================
  
  describe('Validity Scenarios', () => {
    
    test('Valid POI within time window and unmitigated → status = active', () => {
      // Arrange: Create a valid POI
      const poi = createPOI({
        id: 'poi-test-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000, // +24 hours
        mitigated: false
      });

      // Act: Build context at T0 (within validity window)
      const context = buildLiquidityContext(poi, T0);

      // Assert
      expect(context.status).toBe('active');
      expect(context.isWithinValidityWindow).toBe(true);
    });

    test('POI evaluated before validFrom → status = invalid', () => {
      // Arrange: Create a POI with validity starting at T0
      const poi = createPOI({
        id: 'poi-test-002',
        type: POIType.FairValueGap,
        timeframe: '1h',
        priceRange: { low: 41500, high: 41800 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 43200000, // +12 hours
        mitigated: false
      });

      // Act: Evaluate before validFrom
      const evaluatedAt = T0 - 3600000; // -1 hour
      const context = buildLiquidityContext(poi, evaluatedAt);

      // Assert
      expect(context.status).toBe('invalid');
      expect(context.isWithinValidityWindow).toBe(false);
    });

    test('POI evaluated after validUntil → status = expired', () => {
      // Arrange: Create a POI with validity ending at T0 + 12 hours
      const poi = createPOI({
        id: 'poi-test-003',
        type: POIType.BreakerBlock,
        timeframe: '15m',
        priceRange: { low: 42200, high: 42300 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 43200000, // +12 hours
        mitigated: false
      });

      // Act: Evaluate after validUntil
      const evaluatedAt = T0 + 86400000; // +24 hours
      const context = buildLiquidityContext(poi, evaluatedAt);

      // Assert
      expect(context.status).toBe('expired');
      expect(context.isWithinValidityWindow).toBe(false);
    });

    test('Mitigated POI → status = mitigated', () => {
      // Arrange: Create a mitigated POI
      const poi = createPOI({
        id: 'poi-test-004',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0 - 7200000, // -2 hours
        validUntil: T0 + 3600000, // +1 hour
        mitigated: true,
        mitigationTimestamp: T0 - 1800000 // -30 minutes
      });

      // Act: Evaluate within validity window
      const context = buildLiquidityContext(poi, T0);

      // Assert
      expect(context.status).toBe('mitigated');
      expect(context.isWithinValidityWindow).toBe(true);
    });

    test('POI at exact validFrom boundary → status = active', () => {
      // Arrange
      const poi = createPOI({
        id: 'poi-test-005',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });

      // Act: Evaluate exactly at validFrom
      const context = buildLiquidityContext(poi, T0);

      // Assert
      expect(context.status).toBe('active');
      expect(context.isWithinValidityWindow).toBe(true);
    });

    test('POI at exact validUntil boundary → status = active', () => {
      // Arrange
      const validUntil = T0 + 86400000;
      const poi = createPOI({
        id: 'poi-test-006',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil,
        mitigated: false
      });

      // Act: Evaluate exactly at validUntil
      const context = buildLiquidityContext(poi, validUntil);

      // Assert
      expect(context.status).toBe('active');
      expect(context.isWithinValidityWindow).toBe(true);
    });

    test('POI one millisecond after validUntil → status = expired', () => {
      // Arrange
      const validUntil = T0 + 86400000;
      const poi = createPOI({
        id: 'poi-test-007',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil,
        mitigated: false
      });

      // Act: Evaluate one millisecond after validUntil
      const context = buildLiquidityContext(poi, validUntil + 1);

      // Assert
      expect(context.status).toBe('expired');
      expect(context.isWithinValidityWindow).toBe(false);
    });
  });

  // ==============================================================
  // HTF/LTF SCENARIOS
  // ==============================================================

  describe('HTF/LTF Scenarios', () => {

    test('Bullish LTF + Bullish HTF → htfRelation = aligned', () => {
      // Arrange: Bullish LTF POI
      const ltfPOI = createPOI({
        id: 'poi-ltf-001',
        type: POIType.OrderBlock,
        timeframe: '15m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });

      // Arrange: Bullish HTF POI
      const htfPOI = createPOI({
        id: 'poi-htf-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 172800000,
        mitigated: false
      });

      // Act
      const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

      // Assert
      expect(context.htfRelation).toBe('aligned');
    });

    test('Bullish LTF + Bearish HTF → htfRelation = counter', () => {
      // Arrange: Bullish LTF POI
      const ltfPOI = createPOI({
        id: 'poi-ltf-002',
        type: POIType.OrderBlock,
        timeframe: '15m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });

      // Arrange: Bearish HTF POI
      const htfPOI = createPOI({
        id: 'poi-htf-002',
        type: POIType.FairValueGap,
        timeframe: '4h',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 172800000,
        mitigated: false
      });

      // Act
      const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

      // Assert
      expect(context.htfRelation).toBe('counter');
    });

    test('Bearish LTF + Bullish HTF → htfRelation = counter', () => {
      // Arrange: Bearish LTF POI
      const ltfPOI = createPOI({
        id: 'poi-ltf-003',
        type: POIType.FairValueGap,
        timeframe: '5m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });

      // Arrange: Bullish HTF POI
      const htfPOI = createPOI({
        id: 'poi-htf-003',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 172800000,
        mitigated: false
      });

      // Act
      const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

      // Assert
      expect(context.htfRelation).toBe('counter');
    });

    test('Bearish LTF + Bearish HTF → htfRelation = aligned', () => {
      // Arrange: Bearish LTF POI
      const ltfPOI = createPOI({
        id: 'poi-ltf-004',
        type: POIType.FairValueGap,
        timeframe: '5m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });

      // Arrange: Bearish HTF POI
      const htfPOI = createPOI({
        id: 'poi-htf-004',
        type: POIType.FairValueGap,
        timeframe: '1h',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bearish',
        validFrom: T0,
        validUntil: T0 + 172800000,
        mitigated: false
      });

      // Act
      const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

      // Assert
      expect(context.htfRelation).toBe('aligned');
    });

    test('Neutral LTF + Bullish HTF → htfRelation = neutral', () => {
      // Arrange: Neutral LTF POI
      const ltfPOI = createPOI({
        id: 'poi-ltf-005',
        type: POIType.Accumulation,
        timeframe: '1d',
        priceRange: { low: 40000, high: 40500 },
        directionBias: 'neutral',
        validFrom: T0,
        validUntil: T0 + 604800000,
        mitigated: false
      });

      // Arrange: Bullish HTF POI
      const htfPOI = createPOI({
        id: 'poi-htf-005',
        type: POIType.OrderBlock,
        timeframe: '1d',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 604800000,
        mitigated: false
      });

      // Act
      const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

      // Assert
      expect(context.htfRelation).toBe('neutral');
    });

    test('Bullish LTF + Neutral HTF → htfRelation = neutral', () => {
      // Arrange: Bullish LTF POI
      const ltfPOI = createPOI({
        id: 'poi-ltf-006',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });

      // Arrange: Neutral HTF POI
      const htfPOI = createPOI({
        id: 'poi-htf-006',
        type: POIType.Accumulation,
        timeframe: '4h',
        priceRange: { low: 40000, high: 40500 },
        directionBias: 'neutral',
        validFrom: T0,
        validUntil: T0 + 604800000,
        mitigated: false
      });

      // Act
      const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

      // Assert
      expect(context.htfRelation).toBe('neutral');
    });

    test('Neutral LTF + Neutral HTF → htfRelation = neutral', () => {
      // Arrange: Neutral LTF POI
      const ltfPOI = createPOI({
        id: 'poi-ltf-007',
        type: POIType.Accumulation,
        timeframe: '1h',
        priceRange: { low: 40000, high: 40500 },
        directionBias: 'neutral',
        validFrom: T0,
        validUntil: T0 + 604800000,
        mitigated: false
      });

      // Arrange: Neutral HTF POI
      const htfPOI = createPOI({
        id: 'poi-htf-007',
        type: POIType.Distribution,
        timeframe: '4h',
        priceRange: { low: 40500, high: 41000 },
        directionBias: 'neutral',
        validFrom: T0,
        validUntil: T0 + 604800000,
        mitigated: false
      });

      // Act
      const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

      // Assert
      expect(context.htfRelation).toBe('neutral');
    });

    test('No HTF provided → htfRelation = undefined', () => {
      // Arrange: LTF POI only
      const ltfPOI = createPOI({
        id: 'poi-ltf-008',
        type: POIType.OrderBlock,
        timeframe: '15m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });

      // Act: Build context without HTF POI
      const context = buildLiquidityContext(ltfPOI, T0);

      // Assert
      expect(context.htfRelation).toBe('undefined');
    });

    test('Non-active contexts have undefined HTF relation (expired)', () => {
      // Arrange: Expired LTF POI
      const ltfPOI = createPOI({
        id: 'poi-ltf-009',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 3600000, // +1 hour
        mitigated: false
      });

      // Arrange: HTF POI with same direction (would be aligned if active)
      const htfPOI = createPOI({
        id: 'poi-htf-009',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 172800000,
        mitigated: false
      });

      // Act: Evaluate after LTF POI expires
      const context = buildLiquidityContext(ltfPOI, T0 + 86400000, htfPOI);

      // Assert
      expect(context.status).toBe('expired');
      expect(context.htfRelation).toBe('undefined'); // HTF relation undefined for non-active
    });

    test('Non-active contexts have undefined HTF relation (mitigated)', () => {
      // Arrange: Mitigated LTF POI
      const ltfPOI = createPOI({
        id: 'poi-ltf-010',
        type: POIType.OrderBlock,
        timeframe: '15m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0 - 7200000,
        validUntil: T0 + 3600000,
        mitigated: true,
        mitigationTimestamp: T0 - 1800000
      });

      // Arrange: HTF POI with same direction (would be aligned if active)
      const htfPOI = createPOI({
        id: 'poi-htf-010',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 172800000,
        mitigated: false
      });

      // Act
      const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

      // Assert
      expect(context.status).toBe('mitigated');
      expect(context.htfRelation).toBe('undefined'); // HTF relation undefined for non-active
    });

    test('Non-active contexts have undefined HTF relation (invalid)', () => {
      // Arrange: Invalid LTF POI (evaluated before validFrom)
      const ltfPOI = createPOI({
        id: 'poi-ltf-011',
        type: POIType.OrderBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });

      // Arrange: HTF POI with same direction (would be aligned if active)
      const htfPOI = createPOI({
        id: 'poi-htf-011',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 172800000,
        mitigated: false
      });

      // Act: Evaluate before LTF POI becomes valid
      const context = buildLiquidityContext(ltfPOI, T0 - 3600000, htfPOI);

      // Assert
      expect(context.status).toBe('invalid');
      expect(context.htfRelation).toBe('undefined'); // HTF relation undefined for non-active
    });
  });

  // ==============================================================
  // DETERMINISM & IMMUTABILITY
  // ==============================================================

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

      const evaluatedAt = T0 + 3600000; // +1 hour

      // Act: Build context multiple times with same inputs
      const context1 = buildLiquidityContext(poi, evaluatedAt);
      const context2 = buildLiquidityContext(poi, evaluatedAt);
      const context3 = buildLiquidityContext(poi, evaluatedAt);

      // Assert: All contexts are identical
      expect(context1).toEqual(context2);
      expect(context2).toEqual(context3);
      expect(context1).toEqual(context3);
    });

    test('Building context does NOT mutate input POI object', () => {
      // Arrange: Create a POI and take a snapshot
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

      // Take a deep copy for comparison
      const poiSnapshot = JSON.parse(JSON.stringify(poi));

      // Act: Build context
      buildLiquidityContext(poi, T0);

      // Assert: POI is unchanged
      expect(poi).toEqual(poiSnapshot);
    });

    test('Building context with HTF does NOT mutate LTF or HTF POI objects', () => {
      // Arrange
      const ltfPOI = createPOI({
        id: 'poi-immutability-ltf-001',
        type: POIType.OrderBlock,
        timeframe: '15m',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 86400000,
        mitigated: false
      });

      const htfPOI = createPOI({
        id: 'poi-immutability-htf-001',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 41500, high: 42000 },
        directionBias: 'bullish',
        validFrom: T0,
        validUntil: T0 + 172800000,
        mitigated: false
      });

      // Take snapshots
      const ltfSnapshot = JSON.parse(JSON.stringify(ltfPOI));
      const htfSnapshot = JSON.parse(JSON.stringify(htfPOI));

      // Act
      buildLiquidityContext(ltfPOI, T0, htfPOI);

      // Assert: Neither POI is mutated
      expect(ltfPOI).toEqual(ltfSnapshot);
      expect(htfPOI).toEqual(htfSnapshot);
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

      const fixedTimestamp = T0 + 7200000; // +2 hours

      // Act: Build context at different times (simulated)
      const context1 = buildLiquidityContext(poi, fixedTimestamp);
      
      // Simulate time passing (doesn't affect result)
      const context2 = buildLiquidityContext(poi, fixedTimestamp);

      // Assert: Results are identical despite simulated time passage
      expect(context1).toEqual(context2);
      expect(context1.evaluatedAt).toBe(fixedTimestamp);
      expect(context2.evaluatedAt).toBe(fixedTimestamp);
    });

    test('Context contains reference to POI ID, not the POI object', () => {
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

      // Act
      const context = buildLiquidityContext(poi, T0);

      // Assert: Context has poiId, not the POI object
      expect(context.poiId).toBe('poi-reference-001');
      expect((context as any).poi).toBeUndefined();
    });
  });

  // ==============================================================
  // GUARD FUNCTIONS
  // ==============================================================

  describe('Guard Functions', () => {

    describe('isLiquidityContextActive', () => {

      test('Returns true for active contexts', () => {
        // Arrange
        const poi = createPOI({
          id: 'poi-guard-001',
          type: POIType.OrderBlock,
          timeframe: '4h',
          priceRange: { low: 42000, high: 42500 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 86400000,
          mitigated: false
        });

        const context = buildLiquidityContext(poi, T0);

        // Act & Assert
        expect(isLiquidityContextActive(context)).toBe(true);
      });

      test('Returns false for expired contexts', () => {
        // Arrange
        const poi = createPOI({
          id: 'poi-guard-002',
          type: POIType.OrderBlock,
          timeframe: '1h',
          priceRange: { low: 42000, high: 42500 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 3600000,
          mitigated: false
        });

        const context = buildLiquidityContext(poi, T0 + 86400000);

        // Act & Assert
        expect(isLiquidityContextActive(context)).toBe(false);
      });

      test('Returns false for mitigated contexts', () => {
        // Arrange
        const poi = createPOI({
          id: 'poi-guard-003',
          type: POIType.BreakerBlock,
          timeframe: '15m',
          priceRange: { low: 42200, high: 42300 },
          directionBias: 'bullish',
          validFrom: T0 - 7200000,
          validUntil: T0 + 3600000,
          mitigated: true,
          mitigationTimestamp: T0 - 1800000
        });

        const context = buildLiquidityContext(poi, T0);

        // Act & Assert
        expect(isLiquidityContextActive(context)).toBe(false);
      });

      test('Returns false for invalid contexts', () => {
        // Arrange
        const poi = createPOI({
          id: 'poi-guard-004',
          type: POIType.OrderBlock,
          timeframe: '4h',
          priceRange: { low: 42000, high: 42500 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 86400000,
          mitigated: false
        });

        const context = buildLiquidityContext(poi, T0 - 3600000);

        // Act & Assert
        expect(isLiquidityContextActive(context)).toBe(false);
      });
    });

    describe('isLiquidityContextTradable', () => {

      test('Returns true for active + aligned contexts', () => {
        // Arrange: Bullish LTF + Bullish HTF
        const ltfPOI = createPOI({
          id: 'poi-tradable-001',
          type: POIType.OrderBlock,
          timeframe: '15m',
          priceRange: { low: 42000, high: 42500 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 86400000,
          mitigated: false
        });

        const htfPOI = createPOI({
          id: 'poi-tradable-htf-001',
          type: POIType.OrderBlock,
          timeframe: '4h',
          priceRange: { low: 41500, high: 42000 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 172800000,
          mitigated: false
        });

        const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

        // Act & Assert
        expect(isLiquidityContextTradable(context)).toBe(true);
      });

      test('Returns true for active + neutral contexts', () => {
        // Arrange: Neutral LTF + Bullish HTF
        const ltfPOI = createPOI({
          id: 'poi-tradable-002',
          type: POIType.Accumulation,
          timeframe: '1h',
          priceRange: { low: 40000, high: 40500 },
          directionBias: 'neutral',
          validFrom: T0,
          validUntil: T0 + 604800000,
          mitigated: false
        });

        const htfPOI = createPOI({
          id: 'poi-tradable-htf-002',
          type: POIType.OrderBlock,
          timeframe: '4h',
          priceRange: { low: 41500, high: 42000 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 172800000,
          mitigated: false
        });

        const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

        // Act & Assert
        expect(isLiquidityContextTradable(context)).toBe(true);
      });

      test('Returns false for active + counter contexts', () => {
        // Arrange: Bullish LTF + Bearish HTF
        const ltfPOI = createPOI({
          id: 'poi-tradable-003',
          type: POIType.OrderBlock,
          timeframe: '15m',
          priceRange: { low: 42000, high: 42500 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 86400000,
          mitigated: false
        });

        const htfPOI = createPOI({
          id: 'poi-tradable-htf-003',
          type: POIType.FairValueGap,
          timeframe: '4h',
          priceRange: { low: 41500, high: 42000 },
          directionBias: 'bearish',
          validFrom: T0,
          validUntil: T0 + 172800000,
          mitigated: false
        });

        const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

        // Act & Assert
        expect(isLiquidityContextTradable(context)).toBe(false);
      });

      test('Returns false for expired contexts (even if aligned)', () => {
        // Arrange: Expired but aligned
        const ltfPOI = createPOI({
          id: 'poi-tradable-004',
          type: POIType.OrderBlock,
          timeframe: '1h',
          priceRange: { low: 42000, high: 42500 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 3600000,
          mitigated: false
        });

        const htfPOI = createPOI({
          id: 'poi-tradable-htf-004',
          type: POIType.OrderBlock,
          timeframe: '4h',
          priceRange: { low: 41500, high: 42000 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 172800000,
          mitigated: false
        });

        const context = buildLiquidityContext(ltfPOI, T0 + 86400000, htfPOI);

        // Act & Assert
        expect(isLiquidityContextTradable(context)).toBe(false);
      });

      test('Returns false for mitigated contexts (even if aligned)', () => {
        // Arrange: Mitigated but aligned
        const ltfPOI = createPOI({
          id: 'poi-tradable-005',
          type: POIType.BreakerBlock,
          timeframe: '15m',
          priceRange: { low: 42200, high: 42300 },
          directionBias: 'bullish',
          validFrom: T0 - 7200000,
          validUntil: T0 + 3600000,
          mitigated: true,
          mitigationTimestamp: T0 - 1800000
        });

        const htfPOI = createPOI({
          id: 'poi-tradable-htf-005',
          type: POIType.OrderBlock,
          timeframe: '4h',
          priceRange: { low: 41500, high: 42000 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 172800000,
          mitigated: false
        });

        const context = buildLiquidityContext(ltfPOI, T0, htfPOI);

        // Act & Assert
        expect(isLiquidityContextTradable(context)).toBe(false);
      });

      test('Returns false for invalid contexts (even if aligned)', () => {
        // Arrange: Invalid but aligned
        const ltfPOI = createPOI({
          id: 'poi-tradable-006',
          type: POIType.OrderBlock,
          timeframe: '1h',
          priceRange: { low: 42000, high: 42500 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 86400000,
          mitigated: false
        });

        const htfPOI = createPOI({
          id: 'poi-tradable-htf-006',
          type: POIType.OrderBlock,
          timeframe: '4h',
          priceRange: { low: 41500, high: 42000 },
          directionBias: 'bullish',
          validFrom: T0,
          validUntil: T0 + 172800000,
          mitigated: false
        });

        const context = buildLiquidityContext(ltfPOI, T0 - 3600000, htfPOI);

        // Act & Assert
        expect(isLiquidityContextTradable(context)).toBe(false);
      });
    });
  });
});
