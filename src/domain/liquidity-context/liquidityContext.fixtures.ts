/**
 * Liquidity Context Test Fixtures - Phase 4.2: Liquidity Context Layer
 * 
 * Reusable test data for Liquidity Context testing.
 * Provides various context scenarios for comprehensive testing.
 * 
 * @remarks
 * - `status` is the single source of truth
 * - `isWithinValidityWindow` is derived from status
 * - `htfRelation` is only defined for active contexts
 */

import { LiquidityContext } from './liquidityContext.types';

/**
 * Fixed reference timestamp for deterministic testing.
 * This ensures context fixtures are replay-safe and audit-safe.
 * Value: November 14, 2023 22:13:20 GMT
 */
const T0 = 1700000000000;

/**
 * Active Liquidity Context
 * - Status: active
 * - Within validity window (derived from status)
 * - No HTF relation (undefined)
 */
export const activeLiquidityContext: LiquidityContext = {
  poiId: 'poi-bullish-ob-001',
  timeframe: '4h',
  status: 'active',
  isWithinValidityWindow: true,
  htfRelation: 'undefined',
  evaluatedAt: T0
};

/**
 * Expired Liquidity Context
 * - Status: expired
 * - Outside validity window (derived from status)
 * - HTF relation: undefined (non-active)
 */
export const expiredLiquidityContext: LiquidityContext = {
  poiId: 'poi-bullish-ob-002',
  timeframe: '1h',
  status: 'expired',
  isWithinValidityWindow: false,
  htfRelation: 'undefined',
  evaluatedAt: T0 + 86400000 // +24 hours
};

/**
 * Mitigated Liquidity Context
 * - Status: mitigated
 * - Within validity window (derived from status)
 * - HTF relation: undefined (non-active)
 */
export const mitigatedLiquidityContext: LiquidityContext = {
  poiId: 'poi-mitigated-bb-001',
  timeframe: '15m',
  status: 'mitigated',
  isWithinValidityWindow: true,
  htfRelation: 'undefined',
  evaluatedAt: T0
};

/**
 * Invalid Liquidity Context
 * - Status: invalid
 * - Outside validity window (derived from status)
 * - HTF relation: undefined (non-active)
 */
export const invalidLiquidityContext: LiquidityContext = {
  poiId: 'poi-bullish-ob-003',
  timeframe: '4h',
  status: 'invalid',
  isWithinValidityWindow: false,
  htfRelation: 'undefined',
  evaluatedAt: T0 - 3600000 // -1 hour before validFrom
};

/**
 * HTF Aligned Context
 * - Status: active
 * - Bullish LTF + Bullish HTF
 * - HTF relation: aligned
 */
export const htfAlignedContext: LiquidityContext = {
  poiId: 'poi-bullish-ob-004',
  timeframe: '1h',
  status: 'active',
  isWithinValidityWindow: true,
  htfRelation: 'aligned',
  evaluatedAt: T0
};

/**
 * HTF Counter Context
 * - Status: active
 * - Bullish LTF + Bearish HTF
 * - HTF relation: counter
 */
export const htfCounterContext: LiquidityContext = {
  poiId: 'poi-bullish-ob-005',
  timeframe: '15m',
  status: 'active',
  isWithinValidityWindow: true,
  htfRelation: 'counter',
  evaluatedAt: T0
};

/**
 * HTF Neutral Context
 * - Status: active
 * - Neutral LTF or HTF
 * - HTF relation: neutral
 */
export const htfNeutralContext: LiquidityContext = {
  poiId: 'poi-neutral-acc-001',
  timeframe: '1d',
  status: 'active',
  isWithinValidityWindow: true,
  htfRelation: 'neutral',
  evaluatedAt: T0
};

/**
 * No HTF Context
 * - Status: active
 * - No HTF POI provided
 * - HTF relation: undefined
 */
export const noHTFContext: LiquidityContext = {
  poiId: 'poi-bullish-ob-006',
  timeframe: '5m',
  status: 'active',
  isWithinValidityWindow: true,
  htfRelation: 'undefined',
  evaluatedAt: T0
};

/**
 * Tradable Context (Active + Aligned)
 * - Status: active
 * - HTF relation: aligned
 * - Should be tradable
 */
export const tradableAlignedContext: LiquidityContext = {
  poiId: 'poi-bullish-ob-007',
  timeframe: '4h',
  status: 'active',
  isWithinValidityWindow: true,
  htfRelation: 'aligned',
  evaluatedAt: T0
};

/**
 * Tradable Context (Active + Neutral)
 * - Status: active
 * - HTF relation: neutral
 * - Should be tradable
 */
export const tradableNeutralContext: LiquidityContext = {
  poiId: 'poi-neutral-acc-002',
  timeframe: '1h',
  status: 'active',
  isWithinValidityWindow: true,
  htfRelation: 'neutral',
  evaluatedAt: T0
};

/**
 * Non-Tradable Context (Active + Counter)
 * - Status: active
 * - HTF relation: counter
 * - Should NOT be tradable
 */
export const nonTradableCounterContext: LiquidityContext = {
  poiId: 'poi-bullish-ob-008',
  timeframe: '15m',
  status: 'active',
  isWithinValidityWindow: true,
  htfRelation: 'counter',
  evaluatedAt: T0
};

/**
 * Non-Tradable Context (Expired)
 * - Status: expired
 * - HTF relation: undefined (non-active)
 * - Should NOT be tradable (not active)
 */
export const nonTradableExpiredContext: LiquidityContext = {
  poiId: 'poi-bullish-ob-009',
  timeframe: '1h',
  status: 'expired',
  isWithinValidityWindow: false,
  htfRelation: 'undefined',
  evaluatedAt: T0 + 86400000
};

/**
 * Collection of all context fixtures
 */
export const allContextFixtures: LiquidityContext[] = [
  activeLiquidityContext,
  expiredLiquidityContext,
  mitigatedLiquidityContext,
  invalidLiquidityContext,
  htfAlignedContext,
  htfCounterContext,
  htfNeutralContext,
  noHTFContext,
  tradableAlignedContext,
  tradableNeutralContext,
  nonTradableCounterContext,
  nonTradableExpiredContext
];

/**
 * Collection of tradable contexts
 */
export const tradableContexts: LiquidityContext[] = [
  tradableAlignedContext,
  tradableNeutralContext
];

/**
 * Collection of non-tradable contexts
 */
export const nonTradableContexts: LiquidityContext[] = [
  nonTradableCounterContext,
  nonTradableExpiredContext,
  mitigatedLiquidityContext,
  invalidLiquidityContext
];
