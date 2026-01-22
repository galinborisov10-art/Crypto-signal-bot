/**
 * POI Contracts - Phase 4: Strategy Core (Design-First)
 * 
 * Contract/validation logic for Points of Interest.
 * Enforces invariants and business rules without execution or detection logic.
 * 
 * Contract Rules:
 * 1. POI cannot exist without timeframe
 * 2. POI must declare direction bias
 * 3. validUntil must be > validFrom
 * 4. Mitigated POI must not be eligible for entry
 * 5. No support/resistance concepts
 */

import { POI, POIInput, POIType, Timeframe, DirectionBias, PriceRange } from './poi.types';

/**
 * Valid timeframe values for validation
 */
const VALID_TIMEFRAMES: Timeframe[] = ['1m', '5m', '15m', '1h', '4h', '1d'];

/**
 * Valid direction bias values for validation
 */
const VALID_DIRECTION_BIAS: DirectionBias[] = ['bullish', 'bearish', 'neutral'];

/**
 * Validation error for POI construction
 */
export class POIValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'POIValidationError';
  }
}

/**
 * Type guard: Check if a value is a valid POIType
 */
export function isPOIType(value: unknown): value is POIType {
  return Object.values(POIType).includes(value as POIType);
}

/**
 * Type guard: Check if a value is a valid Timeframe
 */
export function isTimeframe(value: unknown): value is Timeframe {
  return typeof value === 'string' && VALID_TIMEFRAMES.includes(value as Timeframe);
}

/**
 * Type guard: Check if a value is a valid DirectionBias
 */
export function isDirectionBias(value: unknown): value is DirectionBias {
  return typeof value === 'string' && VALID_DIRECTION_BIAS.includes(value as DirectionBias);
}

/**
 * Validate price range
 * Ensures low <= high
 */
export function validatePriceRange(priceRange: PriceRange): boolean {
  if (typeof priceRange.low !== 'number' || typeof priceRange.high !== 'number') {
    return false;
  }
  if (!isFinite(priceRange.low) || !isFinite(priceRange.high)) {
    return false;
  }
  if (priceRange.low < 0 || priceRange.high < 0) {
    return false;
  }
  return priceRange.low <= priceRange.high;
}

/**
 * Validate POI time window
 * Contract Rule 3: validUntil must be > validFrom
 */
export function validatePOITimeWindow(validFrom: number, validUntil: number): boolean {
  if (typeof validFrom !== 'number' || typeof validUntil !== 'number') {
    return false;
  }
  if (!isFinite(validFrom) || !isFinite(validUntil)) {
    return false;
  }
  if (validFrom < 0 || validUntil < 0) {
    return false;
  }
  return validUntil > validFrom;
}

/**
 * Validate mitigation state
 * If mitigated is true, mitigationTimestamp should be defined
 */
export function validateMitigationState(mitigated: boolean, mitigationTimestamp?: number): boolean {
  if (typeof mitigated !== 'boolean') {
    return false;
  }
  
  // If mitigated, timestamp should be defined and valid
  if (mitigated) {
    if (mitigationTimestamp === undefined) {
      return false;
    }
    if (typeof mitigationTimestamp !== 'number') {
      return false;
    }
    if (!isFinite(mitigationTimestamp) || mitigationTimestamp < 0) {
      return false;
    }
  }
  
  return true;
}

/**
 * Check if POI is valid (all invariants satisfied)
 * 
 * Contract Rules:
 * 1. POI cannot exist without timeframe
 * 2. POI must declare direction bias
 * 3. validUntil must be > validFrom
 */
export function isPOIValid(poi: POI): boolean {
  // Contract Rule 1: POI cannot exist without timeframe
  if (!isTimeframe(poi.timeframe)) {
    return false;
  }
  
  // Contract Rule 2: POI must declare direction bias
  if (!isDirectionBias(poi.directionBias)) {
    return false;
  }
  
  // Contract Rule 3: validUntil must be > validFrom
  if (!validatePOITimeWindow(poi.validFrom, poi.validUntil)) {
    return false;
  }
  
  // Validate POI type
  if (!isPOIType(poi.type)) {
    return false;
  }
  
  // Validate price range
  if (!validatePriceRange(poi.priceRange)) {
    return false;
  }
  
  // Validate mitigation state
  if (!validateMitigationState(poi.mitigated, poi.mitigationTimestamp)) {
    return false;
  }
  
  // Validate ID exists
  if (!poi.id || typeof poi.id !== 'string' || poi.id.trim() === '') {
    return false;
  }
  
  return true;
}

/**
 * Check if POI is eligible for entry
 * 
 * Contract Rule 4: Mitigated POI must not be eligible for entry
 */
export function isPOIEligibleForEntry(poi: POI): boolean {
  // Must be valid first
  if (!isPOIValid(poi)) {
    return false;
  }
  
  // Contract Rule 4: Mitigated POI cannot be used for entry
  if (poi.mitigated) {
    return false;
  }
  
  return true;
}

/**
 * Factory function to create a validated POI
 * 
 * @throws POIValidationError if validation fails
 */
export function createPOI(data: POIInput): POI {
  // Validate all required fields are present
  if (!data.id || typeof data.id !== 'string' || data.id.trim() === '') {
    throw new POIValidationError('POI id must be a non-empty string');
  }
  
  // Contract Rule 1: POI cannot exist without timeframe
  if (!isTimeframe(data.timeframe)) {
    throw new POIValidationError(`Invalid timeframe: ${data.timeframe}. Must be one of: ${VALID_TIMEFRAMES.join(', ')}`);
  }
  
  // Contract Rule 2: POI must declare direction bias
  if (!isDirectionBias(data.directionBias)) {
    throw new POIValidationError(`Invalid direction bias: ${data.directionBias}. Must be one of: ${VALID_DIRECTION_BIAS.join(', ')}`);
  }
  
  // Validate POI type
  if (!isPOIType(data.type)) {
    throw new POIValidationError(`Invalid POI type: ${data.type}`);
  }
  
  // Validate price range
  if (!validatePriceRange(data.priceRange)) {
    throw new POIValidationError(`Invalid price range: low (${data.priceRange.low}) must be <= high (${data.priceRange.high})`);
  }
  
  // Contract Rule 3: validUntil must be > validFrom
  if (!validatePOITimeWindow(data.validFrom, data.validUntil)) {
    throw new POIValidationError(`Invalid time window: validUntil (${data.validUntil}) must be > validFrom (${data.validFrom})`);
  }
  
  // Validate mitigation state
  if (!validateMitigationState(data.mitigated, data.mitigationTimestamp)) {
    throw new POIValidationError('Invalid mitigation state: mitigated POI must have mitigationTimestamp defined');
  }
  
  // Construct the POI object
  const poi: POI = {
    id: data.id,
    type: data.type,
    timeframe: data.timeframe,
    priceRange: {
      low: data.priceRange.low,
      high: data.priceRange.high
    },
    directionBias: data.directionBias,
    validFrom: data.validFrom,
    validUntil: data.validUntil,
    mitigated: data.mitigated,
    mitigationTimestamp: data.mitigationTimestamp
  };
  
  return poi;
}
