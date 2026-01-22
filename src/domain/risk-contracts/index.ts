/**
 * Risk Contracts Domain - Entry Point
 * 
 * Phase 4.5: SL/TP Contracts (Design-First)
 * Pure data + contract layer for Risk Contracts
 * 
 * Risk Contracts define structural risk acceptability, NOT trade execution.
 */

// Type definitions
export {
  StopLossContract,
  TakeProfitContract,
  RiskContract,
  RiskPOIs,
  RiskInvalidationReason
} from './riskContract.types';

// Contracts and functions
export {
  buildRiskContract,
  isRiskContractValid,
  isRiskContractInvalid
} from './riskContract.contracts';

// Test fixtures (for testing only)
export {
  T0,
  bullishEntryPOI,
  bearishEntryPOI,
  validBullishSLPOI,
  validBearishSLPOI,
  largeBullishSLPOI,
  validBullishTP1POI,
  validBullishTP2POI,
  validBullishTP3POI,
  nearBullishTP1POI,
  validBearishTP1POI,
  validBearishTP2POI,
  validBearishTP3POI,
  invalidSLTypePOI,
  invalidBullishSLPositionPOI,
  validBullishRiskPOIs,
  validBearishRiskPOIs,
  noValidStopRiskPOIs,
  noValidTargetsRiskPOIs,
  lowRRRiskPOIs,
  invalidSLTypeRiskPOIs,
  invalidSLPositionRiskPOIs,
  validBullishScenario,
  validBearishScenario,
  formingScenario,
  validConfluenceScore,
  validBullishRiskContract,
  invalidRiskContract_NoStop,
  invalidRiskContract_NoTargets,
  invalidRiskContract_LowRR,
  invalidRiskContract_ScenarioNotValid
} from './riskContract.fixtures';
