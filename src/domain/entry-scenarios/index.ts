/**
 * Entry Scenarios Domain - Entry Point
 * 
 * Phase 4.3: Entry Scenario Core (Design-First)
 * Pure data + contract layer for ICT Entry Scenarios
 * 
 * Entry Scenarios represent structural market ideas, NOT trade signals.
 */

// Type definitions
export {
  EntryScenario,
  EntryScenarioType,
  EntryScenarioStatus,
  RequiredGates,
  OptionalConfluences
} from './entryScenario.types';

// Contracts and functions
export {
  buildEntryScenario,
  isScenarioForming,
  isScenarioValid,
  isScenarioInvalidated,
  invalidateOnContextChange,
  InvalidationResult
} from './entryScenario.contracts';

// Test fixtures (for testing only)
export {
  T0,
  allGatesTrue,
  someGatesFalse,
  allGatesFalse,
  onlyHTFAligned,
  onlyLiquidityEvent,
  onlyStructuralConfirmation,
  allConfluencesPresent,
  noConfluences,
  mixedConfluences,
  onlyOrderBlock,
  onlyFairValueGap,
  highNewsRisk,
  formingScenario,
  validScenario,
  invalidatedScenario,
  validScenarioNoConfluences,
  formingScenarioAllConfluences,
  allScenarioTypes,
  allScenarioStates
} from './entryScenario.fixtures';
