/**
 * POI Invariant Tests - Phase 4: Strategy Core (Design-First)
 * 
 * Comprehensive tests for POI contract invariants.
 * Tests are semantic, not performance-based.
 * 
 * Test Coverage:
 * 1. Invalid POI construction
 * 2. Validity window semantics
 * 3. Mitigation rules
 * 4. Semantic correctness
 */

import {
  createPOI,
  isPOIValid,
  isPOIEligibleForEntry,
  validatePOITimeWindow,
  validatePriceRange,
  validateMitigationState,
  isPOIType,
  isTimeframe,
  isDirectionBias,
  POIValidationError
} from './poi.contracts';

import { POIType } from './poi.types';

import {
  validBullishPOI,
  validBearishPOI,
  mitigatedPOI,
  invalidPOI_InvalidTimeWindow,
  invalidPOI_InvalidPriceRange,
  invalidPOI_MitigatedWithoutTimestamp,
  invalidPOI_InvalidTimeframe,
  invalidPOI_InvalidDirectionBias,
  invalidPOI_EmptyID,
  invalidPOI_NegativePrice,
  validPOIs,
  invalidPOIs
} from './poi.fixtures';

describe('POI Invariant Tests - Phase 4', () => {
  
  describe('1. Invalid POI Construction', () => {
    
    test('should reject POI with missing timeframe', () => {
      expect(() => createPOI({
        id: 'test-001',
        type: POIType.OrderBlock,
        timeframe: undefined as any,
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: Date.now(),
        validUntil: Date.now() + 86400000,
        mitigated: false
      })).toThrow(POIValidationError);
    });
    
    test('should reject POI with invalid timeframe', () => {
      expect(() => createPOI(invalidPOI_InvalidTimeframe)).toThrow(POIValidationError);
      expect(() => createPOI(invalidPOI_InvalidTimeframe)).toThrow(/Invalid timeframe/);
    });
    
    test('should reject POI with missing direction bias', () => {
      expect(() => createPOI({
        id: 'test-002',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: undefined as any,
        validFrom: Date.now(),
        validUntil: Date.now() + 86400000,
        mitigated: false
      })).toThrow(POIValidationError);
    });
    
    test('should reject POI with invalid direction bias', () => {
      expect(() => createPOI(invalidPOI_InvalidDirectionBias)).toThrow(POIValidationError);
      expect(() => createPOI(invalidPOI_InvalidDirectionBias)).toThrow(/Invalid direction bias/);
    });
    
    test('should reject POI with invalid price range (low > high)', () => {
      expect(() => createPOI(invalidPOI_InvalidPriceRange)).toThrow(POIValidationError);
      expect(() => createPOI(invalidPOI_InvalidPriceRange)).toThrow(/Invalid price range/);
    });
    
    test('should reject POI with negative prices', () => {
      expect(() => createPOI(invalidPOI_NegativePrice)).toThrow(POIValidationError);
    });
    
    test('should reject POI with empty ID', () => {
      expect(() => createPOI(invalidPOI_EmptyID)).toThrow(POIValidationError);
      expect(() => createPOI(invalidPOI_EmptyID)).toThrow(/id must be a non-empty string/);
    });
    
    test('should reject POI with invalid POI type', () => {
      expect(() => createPOI({
        id: 'test-003',
        type: 'InvalidType' as any,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: Date.now(),
        validUntil: Date.now() + 86400000,
        mitigated: false
      })).toThrow(POIValidationError);
    });
  });
  
  describe('2. Validity Window Semantics', () => {
    
    test('should enforce validUntil > validFrom', () => {
      const validFrom = Date.now();
      const validUntil = validFrom - 1000; // Invalid: before validFrom
      
      expect(validatePOITimeWindow(validFrom, validUntil)).toBe(false);
    });
    
    test('should reject POI with validUntil <= validFrom', () => {
      expect(() => createPOI(invalidPOI_InvalidTimeWindow)).toThrow(POIValidationError);
      expect(() => createPOI(invalidPOI_InvalidTimeWindow)).toThrow(/Invalid time window/);
    });
    
    test('should accept POI with validUntil > validFrom', () => {
      const validFrom = Date.now();
      const validUntil = validFrom + 86400000;
      
      expect(validatePOITimeWindow(validFrom, validUntil)).toBe(true);
    });
    
    test('should reject POI with equal validFrom and validUntil', () => {
      const timestamp = Date.now();
      
      expect(validatePOITimeWindow(timestamp, timestamp)).toBe(false);
    });
    
    test('should reject POI with negative timestamps', () => {
      expect(validatePOITimeWindow(-1000, 5000)).toBe(false);
      expect(validatePOITimeWindow(1000, -5000)).toBe(false);
    });
    
    test('should reject POI with non-finite timestamps', () => {
      expect(validatePOITimeWindow(Infinity, Date.now())).toBe(false);
      expect(validatePOITimeWindow(Date.now(), Infinity)).toBe(false);
      expect(validatePOITimeWindow(NaN, Date.now())).toBe(false);
    });
  });
  
  describe('3. Mitigation Rules', () => {
    
    test('should reject mitigated POI without mitigationTimestamp', () => {
      expect(() => createPOI(invalidPOI_MitigatedWithoutTimestamp)).toThrow(POIValidationError);
      expect(() => createPOI(invalidPOI_MitigatedWithoutTimestamp)).toThrow(/Invalid mitigation state/);
    });
    
    test('should validate mitigation state correctly', () => {
      // Not mitigated - timestamp not required
      expect(validateMitigationState(false, undefined)).toBe(true);
      
      // Mitigated - timestamp required
      expect(validateMitigationState(true, Date.now())).toBe(true);
      expect(validateMitigationState(true, undefined)).toBe(false);
    });
    
    test('mitigated POI should not be eligible for entry', () => {
      expect(isPOIEligibleForEntry(mitigatedPOI)).toBe(false);
    });
    
    test('non-mitigated POI should be eligible for entry', () => {
      expect(isPOIEligibleForEntry(validBullishPOI)).toBe(true);
      expect(isPOIEligibleForEntry(validBearishPOI)).toBe(true);
    });
    
    test('should accept POI with mitigated=true and valid timestamp', () => {
      const poi = createPOI({
        id: 'test-mitigated-001',
        type: POIType.BreakerBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: Date.now() - 7200000,
        validUntil: Date.now() + 3600000,
        mitigated: true,
        mitigationTimestamp: Date.now()
      });
      
      expect(poi.mitigated).toBe(true);
      expect(poi.mitigationTimestamp).toBeDefined();
      expect(isPOIValid(poi)).toBe(true);
      expect(isPOIEligibleForEntry(poi)).toBe(false);
    });
  });
  
  describe('4. Semantic Correctness', () => {
    
    test('should validate POI type from enum', () => {
      Object.values(POIType).forEach(type => {
        expect(isPOIType(type)).toBe(true);
      });
      
      expect(isPOIType('InvalidType')).toBe(false);
      expect(isPOIType(undefined)).toBe(false);
      expect(isPOIType(null)).toBe(false);
    });
    
    test('should validate all valid POI types', () => {
      const validTypes = [
        POIType.SellSideLiquidity,
        POIType.BuySideLiquidity,
        POIType.PreviousHigh,
        POIType.PreviousLow,
        POIType.OrderBlock,
        POIType.FairValueGap,
        POIType.BreakerBlock,
        POIType.Accumulation,
        POIType.Distribution
      ];
      
      validTypes.forEach(type => {
        expect(isPOIType(type)).toBe(true);
      });
    });
    
    test('should validate timeframe from allowed list', () => {
      const validTimeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];
      
      validTimeframes.forEach(tf => {
        expect(isTimeframe(tf)).toBe(true);
      });
      
      expect(isTimeframe('30m')).toBe(false);
      expect(isTimeframe('2h')).toBe(false);
      expect(isTimeframe('invalid')).toBe(false);
    });
    
    test('should validate direction bias', () => {
      expect(isDirectionBias('bullish')).toBe(true);
      expect(isDirectionBias('bearish')).toBe(true);
      expect(isDirectionBias('neutral')).toBe(true);
      
      expect(isDirectionBias('sideways')).toBe(false);
      expect(isDirectionBias('up')).toBe(false);
      expect(isDirectionBias(undefined)).toBe(false);
    });
    
    test('should validate price range (low <= high)', () => {
      expect(validatePriceRange({ low: 42000, high: 42500 })).toBe(true);
      expect(validatePriceRange({ low: 42000, high: 42000 })).toBe(true);
      expect(validatePriceRange({ low: 42500, high: 42000 })).toBe(false);
    });
    
    test('should reject price range with negative values', () => {
      expect(validatePriceRange({ low: -100, high: 42500 })).toBe(false);
      expect(validatePriceRange({ low: 42000, high: -100 })).toBe(false);
    });
    
    test('should reject price range with non-finite values', () => {
      expect(validatePriceRange({ low: Infinity, high: 42500 })).toBe(false);
      expect(validatePriceRange({ low: 42000, high: NaN })).toBe(false);
    });
    
    test('should validate all valid POI fixtures', () => {
      validPOIs.forEach(poi => {
        expect(isPOIValid(poi)).toBe(true);
      });
    });
    
    test('should reject all invalid POI fixtures', () => {
      invalidPOIs.forEach(invalidPOI => {
        expect(() => createPOI(invalidPOI)).toThrow(POIValidationError);
      });
    });
  });
  
  describe('5. Contract Rules Enforcement', () => {
    
    test('Contract Rule 1: POI cannot exist without timeframe', () => {
      expect(() => createPOI({
        id: 'test-rule1',
        type: POIType.OrderBlock,
        timeframe: '' as any,
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: Date.now(),
        validUntil: Date.now() + 86400000,
        mitigated: false
      })).toThrow(POIValidationError);
    });
    
    test('Contract Rule 2: POI must declare direction bias', () => {
      expect(() => createPOI({
        id: 'test-rule2',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: '' as any,
        validFrom: Date.now(),
        validUntil: Date.now() + 86400000,
        mitigated: false
      })).toThrow(POIValidationError);
    });
    
    test('Contract Rule 3: validUntil must be > validFrom', () => {
      const now = Date.now();
      expect(() => createPOI({
        id: 'test-rule3',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: now,
        validUntil: now - 1000,
        mitigated: false
      })).toThrow(POIValidationError);
    });
    
    test('Contract Rule 4: Mitigated POI must not be eligible for entry', () => {
      const mitigatedTestPOI = createPOI({
        id: 'test-rule4',
        type: POIType.BreakerBlock,
        timeframe: '1h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: Date.now() - 7200000,
        validUntil: Date.now() + 3600000,
        mitigated: true,
        mitigationTimestamp: Date.now()
      });
      
      expect(isPOIEligibleForEntry(mitigatedTestPOI)).toBe(false);
    });
    
    test('Contract Rule 5: No support/resistance concepts', () => {
      // Verify enum does not contain support/resistance
      const enumValues = Object.values(POIType);
      const hasSupport = enumValues.some(v => v.toLowerCase().includes('support'));
      const hasResistance = enumValues.some(v => v.toLowerCase().includes('resistance'));
      
      expect(hasSupport).toBe(false);
      expect(hasResistance).toBe(false);
    });
  });
  
  describe('6. Valid POI Creation', () => {
    
    test('should create valid bullish POI', () => {
      const poi = createPOI({
        id: 'test-valid-bullish',
        type: POIType.OrderBlock,
        timeframe: '4h',
        priceRange: { low: 42000, high: 42500 },
        directionBias: 'bullish',
        validFrom: Date.now(),
        validUntil: Date.now() + 86400000,
        mitigated: false
      });
      
      expect(poi.id).toBe('test-valid-bullish');
      expect(poi.type).toBe(POIType.OrderBlock);
      expect(poi.directionBias).toBe('bullish');
      expect(isPOIValid(poi)).toBe(true);
      expect(isPOIEligibleForEntry(poi)).toBe(true);
    });
    
    test('should create valid bearish POI', () => {
      const poi = createPOI({
        id: 'test-valid-bearish',
        type: POIType.FairValueGap,
        timeframe: '1h',
        priceRange: { low: 41500, high: 41800 },
        directionBias: 'bearish',
        validFrom: Date.now(),
        validUntil: Date.now() + 43200000,
        mitigated: false
      });
      
      expect(poi.directionBias).toBe('bearish');
      expect(isPOIValid(poi)).toBe(true);
      expect(isPOIEligibleForEntry(poi)).toBe(true);
    });
    
    test('should create valid neutral POI', () => {
      const poi = createPOI({
        id: 'test-valid-neutral',
        type: POIType.Accumulation,
        timeframe: '1d',
        priceRange: { low: 40000, high: 40500 },
        directionBias: 'neutral',
        validFrom: Date.now(),
        validUntil: Date.now() + 604800000,
        mitigated: false
      });
      
      expect(poi.directionBias).toBe('neutral');
      expect(isPOIValid(poi)).toBe(true);
      expect(isPOIEligibleForEntry(poi)).toBe(true);
    });
  });
  
  describe('7. POI Type Coverage', () => {
    
    test('should support all POI types', () => {
      const poiTypes = [
        POIType.SellSideLiquidity,
        POIType.BuySideLiquidity,
        POIType.PreviousHigh,
        POIType.PreviousLow,
        POIType.OrderBlock,
        POIType.FairValueGap,
        POIType.BreakerBlock,
        POIType.Accumulation,
        POIType.Distribution
      ];
      
      poiTypes.forEach(type => {
        const poi = createPOI({
          id: `test-${type}`,
          type: type,
          timeframe: '1h',
          priceRange: { low: 42000, high: 42500 },
          directionBias: 'neutral',
          validFrom: Date.now(),
          validUntil: Date.now() + 86400000,
          mitigated: false
        });
        
        expect(poi.type).toBe(type);
        expect(isPOIValid(poi)).toBe(true);
      });
    });
  });
});
