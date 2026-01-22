/**
 * Confluence Scoring Domain - Entry Point
 * 
 * Phase 4.4: Confluence Scoring Engine (Design-First)
 * Pure evaluation layer for Entry Scenario confluence quality
 * 
 * This module provides deterministic, replay-safe scoring of Entry Scenarios
 * based on their optional confluence factors. It evaluates structural quality
 * without making trading decisions.
 * 
 * Key Principles:
 * - Scoring evaluates quality, NOT tradability
 * - High confidence ≠ signal
 * - Confidence = quality, NOT permission
 * - Pure, deterministic, replay-safe
 */

// Type definitions
export {
  ConfluenceFactor,
  ConfluenceWeights,
  DampenerImpact,
  ConfluenceBreakdown,
  ConfluenceScore,
  ScoringResult
} from './confluenceScore.types';

// Contracts and functions
export {
  evaluateConfluenceScore
} from './confluenceScore.contracts';

// Test fixtures (for testing only)
export {
  testWeights,
  equalWeights,
  orderBlockHeavyWeights,
  minimalDampenerWeights,
  strongDampenerWeights,
  zeroWeights,
  allConfluencesPresent,
  someConfluencesPresent,
  noConfluences,
  withNewsRisk,
  onlyOrderBlock,
  onlyFairValueGap,
  onlyBreakerBlock,
  onlyNewsRisk,
  mixedWithNewsRisk,
  T0,
  T1,
  T2
} from './confluenceScore.fixtures';
