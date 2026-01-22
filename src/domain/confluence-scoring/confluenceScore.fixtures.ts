/**
 * Confluence Score Test Fixtures - Phase 4.4: Confluence Scoring Engine
 * 
 * Reusable test fixtures for Confluence Scoring across all scenarios.
 * These fixtures support deterministic, replay-safe testing.
 * 
 * Fixture Categories:
 * 1. Weight Configurations (standard, edge cases)
 * 2. Confluence Combinations (all present, some present, none, with dampeners)
 * 3. Test Scenarios (reusing Phase 4.3 fixtures)
 */

import { OptionalConfluences, T0 } from '../entry-scenarios';
import { ConfluenceWeights } from './confluenceScore.types';

// ============================================================
// WEIGHT CONFIGURATIONS
// ============================================================

/**
 * Standard test weights
 * Balanced configuration with negative newsRisk dampener
 * Sum of positive weights = 100 (for easy percentage calculation)
 */
export const testWeights: ConfluenceWeights = {
  orderBlock: 20,
  fairValueGap: 15,
  breakerBlock: 25,
  discountPremium: 15,
  buySellLiquidity: 25,
  newsRisk: -20 // Dampener
};

/**
 * Equal weights configuration
 * All positive weights equal, newsRisk dampener
 */
export const equalWeights: ConfluenceWeights = {
  orderBlock: 20,
  fairValueGap: 20,
  breakerBlock: 20,
  discountPremium: 20,
  buySellLiquidity: 20,
  newsRisk: -15
};

/**
 * Heavily weighted order blocks
 * Prioritizes order block confluence
 */
export const orderBlockHeavyWeights: ConfluenceWeights = {
  orderBlock: 50,
  fairValueGap: 10,
  breakerBlock: 15,
  discountPremium: 10,
  buySellLiquidity: 15,
  newsRisk: -25
};

/**
 * Minimal dampener
 * Very small newsRisk penalty
 */
export const minimalDampenerWeights: ConfluenceWeights = {
  orderBlock: 25,
  fairValueGap: 25,
  breakerBlock: 25,
  discountPremium: 25,
  buySellLiquidity: 0,
  newsRisk: -5
};

/**
 * Strong dampener
 * Heavy newsRisk penalty
 */
export const strongDampenerWeights: ConfluenceWeights = {
  orderBlock: 20,
  fairValueGap: 20,
  breakerBlock: 20,
  discountPremium: 20,
  buySellLiquidity: 20,
  newsRisk: -50
};

/**
 * Zero weights (edge case)
 * All weights are zero
 */
export const zeroWeights: ConfluenceWeights = {
  orderBlock: 0,
  fairValueGap: 0,
  breakerBlock: 0,
  discountPremium: 0,
  buySellLiquidity: 0,
  newsRisk: 0
};

// ============================================================
// CONFLUENCE COMBINATIONS
// ============================================================

/**
 * All confluences present (no news risk)
 * Perfect score scenario
 */
export const allConfluencesPresent: OptionalConfluences = {
  orderBlock: true,
  fairValueGap: true,
  breakerBlock: true,
  discountPremium: true,
  buySellLiquidity: true,
  newsRisk: false
};

/**
 * Some confluences present
 * Partial confluence scenario
 */
export const someConfluencesPresent: OptionalConfluences = {
  orderBlock: true,
  fairValueGap: false,
  breakerBlock: true,
  discountPremium: false,
  buySellLiquidity: false,
  newsRisk: false
};

/**
 * No confluences present
 * Zero score scenario
 */
export const noConfluences: OptionalConfluences = {};

/**
 * All confluences present WITH news risk
 * High confluence but dampened by risk
 */
export const withNewsRisk: OptionalConfluences = {
  orderBlock: true,
  fairValueGap: true,
  breakerBlock: true,
  discountPremium: true,
  buySellLiquidity: true,
  newsRisk: true // Dampener active
};

/**
 * Only order block present
 * Single confluence scenario
 */
export const onlyOrderBlock: OptionalConfluences = {
  orderBlock: true,
  fairValueGap: false,
  breakerBlock: false,
  discountPremium: false,
  buySellLiquidity: false,
  newsRisk: false
};

/**
 * Only fair value gap present
 * Single confluence scenario
 */
export const onlyFairValueGap: OptionalConfluences = {
  orderBlock: false,
  fairValueGap: true,
  breakerBlock: false,
  discountPremium: false,
  buySellLiquidity: false,
  newsRisk: false
};

/**
 * Only breaker block present
 * Single confluence scenario
 */
export const onlyBreakerBlock: OptionalConfluences = {
  orderBlock: false,
  fairValueGap: false,
  breakerBlock: true,
  discountPremium: false,
  buySellLiquidity: false,
  newsRisk: false
};

/**
 * Only news risk present (no positive confluences)
 * Negative score scenario
 */
export const onlyNewsRisk: OptionalConfluences = {
  orderBlock: false,
  fairValueGap: false,
  breakerBlock: false,
  discountPremium: false,
  buySellLiquidity: false,
  newsRisk: true
};

/**
 * Mixed confluences with news risk
 * Some positive, some missing, with dampener
 */
export const mixedWithNewsRisk: OptionalConfluences = {
  orderBlock: true,
  fairValueGap: false,
  breakerBlock: true,
  discountPremium: true,
  buySellLiquidity: false,
  newsRisk: true
};

// ============================================================
// TIMESTAMPS
// ============================================================

/**
 * Fixed reference timestamp for deterministic testing
 * Reuses T0 from Phase 4.3 for consistency
 */
export { T0 };

/**
 * Later timestamp for multi-temporal tests
 */
export const T1 = T0 + 3600000; // +1 hour

/**
 * Even later timestamp
 */
export const T2 = T0 + 7200000; // +2 hours
