/**
 * POI Type System - Phase 4: Strategy Core (Design-First)
 * 
 * Defines Points of Interest (POI) as first-class domain objects.
 * POI represent liquidity-based contexts, NOT support/resistance lines.
 * 
 * This file contains ONLY type definitions - no logic, detection, or execution.
 */

/**
 * Valid timeframes for POI analysis
 * 
 * NOTE:
 * Timeframe hierarchy and ordering are intentionally NOT modeled here.
 * HTF/LTF semantics are introduced in Phase 4.2 (Liquidity Context Layer).
 */
export type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h' | '1d';

/**
 * Strict enumeration of POI types
 * Each type represents a liquidity-based context in the market
 */
export enum POIType {
  SellSideLiquidity = 'SellSideLiquidity',
  BuySideLiquidity = 'BuySideLiquidity',
  PreviousHigh = 'PreviousHigh',
  PreviousLow = 'PreviousLow',
  OrderBlock = 'OrderBlock',
  FairValueGap = 'FairValueGap',
  BreakerBlock = 'BreakerBlock',
  Accumulation = 'Accumulation',
  Distribution = 'Distribution'
}

/**
 * Direction bias for POI
 */
export type DirectionBias = 'bullish' | 'bearish' | 'neutral';

/**
 * Price range for a POI zone
 */
export interface PriceRange {
  low: number;
  high: number;
}

/**
 * Core POI data model
 * 
 * A Point of Interest represents a significant liquidity-based zone
 * in the market that may influence future price action.
 */
export interface POI {
  /** Unique identifier for the POI */
  id: string;
  
  /** Type of POI from the strict enumeration */
  type: POIType;
  
  /** Timeframe on which this POI was identified */
  timeframe: Timeframe;
  
  /** Price range defining the POI zone */
  priceRange: PriceRange;
  
  /** Market direction bias associated with this POI */
  directionBias: DirectionBias;
  
  /** Unix timestamp (milliseconds) when this POI becomes valid */
  validFrom: number;
  
  /** Unix timestamp (milliseconds) when this POI expires */
  validUntil: number;
  
  /** Whether this POI has been mitigated (price has reacted to it) */
  mitigated: boolean;
  
  /** Unix timestamp (milliseconds) when mitigation occurred, if applicable */
  mitigationTimestamp?: number;
}

/**
 * Input data for creating a POI
 * Used by factory functions to construct validated POI instances
 */
export interface POIInput {
  id: string;
  type: POIType;
  timeframe: Timeframe;
  priceRange: PriceRange;
  directionBias: DirectionBias;
  validFrom: number;
  validUntil: number;
  mitigated: boolean;
  mitigationTimestamp?: number;
}
