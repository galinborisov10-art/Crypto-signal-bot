/**
 * POI Domain - Entry Point
 * 
 * Phase 4: Strategy Core (Design-First)
 * Pure data + contract layer for Points of Interest
 */

// Type definitions
export {
  POI,
  POIInput,
  POIType,
  Timeframe,
  DirectionBias,
  PriceRange
} from './poi.types';

// Contracts and validation
export {
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

// Test fixtures (for testing only)
export {
  validBullishPOI,
  validBearishPOI,
  validNeutralPOI,
  mitigatedPOI,
  validBuySideLiquidityPOI,
  validSellSideLiquidityPOI,
  validPOIs,
  invalidPOIs
} from './poi.fixtures';
