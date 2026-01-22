/**
 * Liquidity Context Domain - Entry Point
 * 
 * Phase 4.2: Strategy Core (Design-First)
 * Pure context + contract layer for time-based POI interpretation
 */

// Type definitions
export {
  LiquidityContext,
  LiquidityContextStatus,
  HTFRelation
} from './liquidityContext.types';

// Contracts and functions
export {
  buildLiquidityContext,
  isLiquidityContextActive,
  isLiquidityContextTradable
} from './liquidityContext.contracts';

// Test fixtures (for testing only)
export {
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
  nonTradableExpiredContext,
  allContextFixtures,
  tradableContexts,
  nonTradableContexts
} from './liquidityContext.fixtures';
