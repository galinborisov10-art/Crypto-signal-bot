/**
 * POI Test Fixtures - Phase 4: Strategy Core (Design-First)
 * 
 * Reusable test data for POI testing.
 * Provides valid and invalid POI examples for various test scenarios.
 */

import { POI, POIInput, POIType } from './poi.types';

/**
 * Valid bullish POI - Order Block
 */
export const validBullishPOI: POI = {
  id: 'poi-bullish-ob-001',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: {
    low: 42000,
    high: 42500
  },
  directionBias: 'bullish',
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000, // +24 hours
  mitigated: false
};

/**
 * Valid bearish POI - Fair Value Gap
 */
export const validBearishPOI: POI = {
  id: 'poi-bearish-fvg-001',
  type: POIType.FairValueGap,
  timeframe: '1h',
  priceRange: {
    low: 41500,
    high: 41800
  },
  directionBias: 'bearish',
  validFrom: Date.now(),
  validUntil: Date.now() + 43200000, // +12 hours
  mitigated: false
};

/**
 * Valid neutral POI - Accumulation zone
 */
export const validNeutralPOI: POI = {
  id: 'poi-neutral-acc-001',
  type: POIType.Accumulation,
  timeframe: '1d',
  priceRange: {
    low: 40000,
    high: 40500
  },
  directionBias: 'neutral',
  validFrom: Date.now(),
  validUntil: Date.now() + 604800000, // +7 days
  mitigated: false
};

/**
 * Mitigated POI - Should not be eligible for entry
 */
export const mitigatedPOI: POI = {
  id: 'poi-mitigated-bb-001',
  type: POIType.BreakerBlock,
  timeframe: '15m',
  priceRange: {
    low: 42200,
    high: 42300
  },
  directionBias: 'bullish',
  validFrom: Date.now() - 7200000, // -2 hours
  validUntil: Date.now() + 3600000, // +1 hour
  mitigated: true,
  mitigationTimestamp: Date.now() - 1800000 // -30 minutes
};

/**
 * Valid POI - Buy Side Liquidity
 */
export const validBuySideLiquidityPOI: POI = {
  id: 'poi-bsl-001',
  type: POIType.BuySideLiquidity,
  timeframe: '1h',
  priceRange: {
    low: 43000,
    high: 43100
  },
  directionBias: 'bullish',
  validFrom: Date.now(),
  validUntil: Date.now() + 21600000, // +6 hours
  mitigated: false
};

/**
 * Valid POI - Sell Side Liquidity
 */
export const validSellSideLiquidityPOI: POI = {
  id: 'poi-ssl-001',
  type: POIType.SellSideLiquidity,
  timeframe: '4h',
  priceRange: {
    low: 41000,
    high: 41200
  },
  directionBias: 'bearish',
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000, // +24 hours
  mitigated: false
};

/**
 * Invalid POI - Missing timeframe
 */
export const invalidPOI_MissingTimeframe: Partial<POI> = {
  id: 'poi-invalid-001',
  type: POIType.OrderBlock,
  // timeframe is missing
  priceRange: {
    low: 42000,
    high: 42500
  },
  directionBias: 'bullish',
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000,
  mitigated: false
};

/**
 * Invalid POI - Invalid time window (validUntil <= validFrom)
 */
export const invalidPOI_InvalidTimeWindow: POIInput = {
  id: 'poi-invalid-002',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: {
    low: 42000,
    high: 42500
  },
  directionBias: 'bullish',
  validFrom: Date.now(),
  validUntil: Date.now() - 3600000, // Invalid: before validFrom
  mitigated: false
};

/**
 * Invalid POI - Invalid price range (low > high)
 */
export const invalidPOI_InvalidPriceRange: POIInput = {
  id: 'poi-invalid-003',
  type: POIType.FairValueGap,
  timeframe: '1h',
  priceRange: {
    low: 42500,
    high: 42000 // Invalid: low > high
  },
  directionBias: 'bearish',
  validFrom: Date.now(),
  validUntil: Date.now() + 43200000,
  mitigated: false
};

/**
 * Invalid POI - Missing direction bias
 */
export const invalidPOI_MissingDirectionBias: Partial<POI> = {
  id: 'poi-invalid-004',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: {
    low: 42000,
    high: 42500
  },
  // directionBias is missing
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000,
  mitigated: false
};

/**
 * Invalid POI - Mitigated without timestamp
 */
export const invalidPOI_MitigatedWithoutTimestamp: POIInput = {
  id: 'poi-invalid-005',
  type: POIType.BreakerBlock,
  timeframe: '15m',
  priceRange: {
    low: 42200,
    high: 42300
  },
  directionBias: 'bullish',
  validFrom: Date.now() - 7200000,
  validUntil: Date.now() + 3600000,
  mitigated: true
  // mitigationTimestamp is missing but mitigated is true
};

/**
 * Invalid POI - Invalid timeframe
 */
export const invalidPOI_InvalidTimeframe: POIInput = {
  id: 'poi-invalid-006',
  type: POIType.OrderBlock,
  timeframe: '30m' as any, // Invalid timeframe
  priceRange: {
    low: 42000,
    high: 42500
  },
  directionBias: 'bullish',
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000,
  mitigated: false
};

/**
 * Invalid POI - Invalid direction bias
 */
export const invalidPOI_InvalidDirectionBias: POIInput = {
  id: 'poi-invalid-007',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: {
    low: 42000,
    high: 42500
  },
  directionBias: 'sideways' as any, // Invalid direction bias
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000,
  mitigated: false
};

/**
 * Invalid POI - Empty ID
 */
export const invalidPOI_EmptyID: POIInput = {
  id: '',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: {
    low: 42000,
    high: 42500
  },
  directionBias: 'bullish',
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000,
  mitigated: false
};

/**
 * Invalid POI - Negative price
 */
export const invalidPOI_NegativePrice: POIInput = {
  id: 'poi-invalid-009',
  type: POIType.OrderBlock,
  timeframe: '4h',
  priceRange: {
    low: -100,
    high: 42500
  },
  directionBias: 'bullish',
  validFrom: Date.now(),
  validUntil: Date.now() + 86400000,
  mitigated: false
};

/**
 * Collection of all valid POI fixtures
 */
export const validPOIs: POI[] = [
  validBullishPOI,
  validBearishPOI,
  validNeutralPOI,
  validBuySideLiquidityPOI,
  validSellSideLiquidityPOI
];

/**
 * Collection of all invalid POI fixtures
 */
export const invalidPOIs: POIInput[] = [
  invalidPOI_InvalidTimeWindow,
  invalidPOI_InvalidPriceRange,
  invalidPOI_MitigatedWithoutTimestamp,
  invalidPOI_InvalidTimeframe,
  invalidPOI_InvalidDirectionBias,
  invalidPOI_EmptyID,
  invalidPOI_NegativePrice
];
