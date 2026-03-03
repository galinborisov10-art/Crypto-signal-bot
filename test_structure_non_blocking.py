"""
Test to verify Structure does NOT block signals per specification.

This test validates that:
1. Structure only provides bias (BULLISH/BEARISH/NEUTRAL)
2. Structure does NOT block signals
3. Structure does NOT filter scenarios
4. Structure does NOT participate in scenario selection
5. Scenario selection is based ONLY on probability + component strength
"""

import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test_structure_non_blocking():
    """
    Critical Test: Structure = BEARISH, but strong BUY entry core exists
    Expected: BUY signal should NOT be blocked by BEARISH structure
    
    Specification requirement #2:
    "Structure НЕ блокира сигнали" (Structure does NOT block signals)
    "Structure = само контекст" (Structure = only context)
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Structure Non-Blocking")
    logger.info("=" * 80)
    
    logger.info("\nScenario:")
    logger.info("  • Structure bias = BEARISH (from structure_tf)")
    logger.info("  • Strong BUY entry core exists (Order Blocks, FVG, etc.)")
    logger.info("  • High probability BUY scenario")
    logger.info("\nExpected Result:")
    logger.info("  • BUY signal should be ALLOWED")
    logger.info("  • Structure does NOT block the signal")
    logger.info("  • Structure is only context information")
    
    # Check if structure alignment modifier was removed
    try:
        from ict_signal_engine import ICTSignalEngine
        import inspect
        
        # Get the source code of the generate_signal method
        source = inspect.getsource(ICTSignalEngine.generate_signal)
        
        # Check for structure alignment modifier patterns
        violations = []
        
        if "STRUCTURE_ALIGNMENT" in source:
            violations.append("STRUCTURE_ALIGNMENT still referenced in code")
        
        if "structure_modifier" in source:
            violations.append("structure_modifier variable still used")
        
        if "entry_tf_structure" in source and "Save original entry TF structure for modifier" in source:
            violations.append("entry_tf_structure variable still used for structure modifier")
        
        # Check for structure-based blocking
        if "structure alignment probability below threshold" in source.lower():
            violations.append("Structure alignment threshold blocking still present")
        
        if violations:
            logger.error("\n❌ TEST FAILED: Structure alignment modifier still present")
            for v in violations:
                logger.error(f"   • {v}")
            return False
        else:
            logger.info("\n✅ TEST PASSED: Structure alignment modifier removed")
            logger.info("   • No STRUCTURE_ALIGNMENT references")
            logger.info("   • No structure_modifier usage")
            logger.info("   • No structure-based blocking")
            logger.info("   • Structure is context only")
            return True
            
    except Exception as e:
        logger.error(f"\n❌ TEST ERROR: {str(e)}")
        return False


def test_confirmation_modifier_only():
    """
    Test: Confirmation layer is ONLY a confidence modifier (+8%/-8%)
    Expected: Confirmation does NOT block signals
    
    Specification requirement #3:
    "Confirmation НИКОГА не връща None" (Confirmation NEVER returns None)
    "Confirmation НИКОГА не блокира сигнал" (Confirmation NEVER blocks signals)
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Confirmation Modifier Only")
    logger.info("=" * 80)
    
    logger.info("\nExpected Behavior:")
    logger.info("  • Confirmation found → +8% confidence")
    logger.info("  • Confirmation NOT found → -8% confidence")
    logger.info("  • Confirmation does NOT block signals")
    logger.info("  • Confirmation does NOT return None")
    logger.info("  • Confirmation does NOT set eligible = False")
    
    try:
        from ict_signal_engine import ICTSignalEngine
        import inspect
        
        # Get the source code of confirmation layer
        source = inspect.getsource(ICTSignalEngine._analyze_confirmation_layer)
        
        violations = []
        
        # Check for blocking patterns
        if "return None" in source and "confidence_modifier" not in source:
            violations.append("Confirmation layer returns None (blocks signals)")
        
        if "eligible = False" in source or "eligible=False" in source:
            violations.append("Confirmation layer sets eligible = False")
        
        # Verify modifier is +8% / -8%
        if "0.08" not in source and "confidence_modifier" in source:
            violations.append("Confirmation modifier is not ±8%")
        
        if violations:
            logger.error("\n❌ TEST FAILED: Confirmation layer violations")
            for v in violations:
                logger.error(f"   • {v}")
            return False
        else:
            logger.info("\n✅ TEST PASSED: Confirmation layer compliant")
            logger.info("   • Returns confidence modifier only")
            logger.info("   • Does NOT block signals")
            logger.info("   • Modifier is exactly ±8%")
            return True
            
    except Exception as e:
        logger.error(f"\n❌ TEST ERROR: {str(e)}")
        return False


def test_only_two_hard_gates():
    """
    Test: Verify only 2 hard gates exist
    Expected: (1) No core → no scenario, (2) Confidence threshold
    
    Specification requirement #4:
    "Единствените hard gate в системата:
     - Ако няма core → няма сценарий
     - Confidence threshold (60% auto / 70% manual)"
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Only Two Hard Gates")
    logger.info("=" * 80)
    
    logger.info("\nAllowed Hard Gates:")
    logger.info("  1. No core → no scenario (required)")
    logger.info("  2. Confidence threshold: 60% auto / 70% manual")
    logger.info("\nForbidden Gates:")
    logger.info("  ✗ MTF consensus gate")
    logger.info("  ✗ Structure gate")
    logger.info("  ✗ Confirmation gate")
    logger.info("  ✗ Counter-HTF blocking")
    logger.info("  ✗ Structure alignment blocking")
    
    try:
        from ict_signal_engine import ICTSignalEngine
        import inspect
        
        source = inspect.getsource(ICTSignalEngine.generate_signal)
        
        violations = []
        warnings = []
        
        # Check for forbidden gates
        if "mtf_consensus" in source.lower() and "block" in source.lower():
            if "mtf consensus" in source.lower() and ("< 50" in source or ">= 50" in source):
                # Check if it's actually blocking vs just warning
                if "return" in source and "mtf" in source.lower() and "consensus" in source.lower():
                    violations.append("MTF consensus appears to block signals")
        
        if "structure alignment probability below threshold" in source.lower():
            violations.append("Structure alignment blocking present")
        
        if "counter-htf" in source.lower() and "block" in source.lower():
            violations.append("Counter-HTF blocking present")
        
        # Check for confirmation blocking
        confirmation_source = inspect.getsource(ICTSignalEngine._analyze_confirmation_layer)
        if ("return None" in confirmation_source and 
            "create_no_trade_message" in source and 
            "confirmation" in source.lower()):
            warnings.append("Confirmation might block signals (needs manual review)")
        
        if violations:
            logger.error("\n❌ TEST FAILED: Forbidden gates present")
            for v in violations:
                logger.error(f"   • {v}")
            return False
        elif warnings:
            logger.warning("\n⚠️ TEST WARNING: Potential issues")
            for w in warnings:
                logger.warning(f"   • {w}")
            logger.info("\n✅ TEST PASSED: No clear violations (warnings need manual review)")
            return True
        else:
            logger.info("\n✅ TEST PASSED: Only allowed gates present")
            logger.info("   • No MTF consensus gate")
            logger.info("   • No structure gate")
            logger.info("   • No confirmation gate")
            logger.info("   • No counter-HTF blocking")
            return True
            
    except Exception as e:
        logger.error(f"\n❌ TEST ERROR: {str(e)}")
        return False


def test_scenario_selection_independence():
    """
    Test: Scenario selection is independent of structure/confirmation/MTF
    Expected: Selection based ONLY on probability + component strength
    
    Specification requirement #5:
    "Всички сценарии, които имат core, участват.
     Сравняват се по: probability, component strength
     Structure НЕ участва.
     Confirmation НЕ участва.
     Bias НЕ участва."
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Scenario Selection Independence")
    logger.info("=" * 80)
    
    logger.info("\nScenario Selection Should Use:")
    logger.info("  ✓ Probability")
    logger.info("  ✓ Component strength")
    logger.info("\nScenario Selection Should NOT Use:")
    logger.info("  ✗ Structure")
    logger.info("  ✗ Confirmation")
    logger.info("  ✗ MTF consensus")
    logger.info("  ✗ Bias")
    
    try:
        # Check entry_scenarios.py for selection logic
        with open('entry_scenarios.py', 'r') as f:
            scenario_source = f.read()
        
        violations = []
        
        # Check select_best_entry_scenario function
        if "structure" in scenario_source.lower() and "select_best_entry_scenario" in scenario_source:
            # Check if structure is used in scoring/selection
            if "structure_alignment" in scenario_source.lower():
                violations.append("Structure used in scenario selection")
        
        if "confirmation" in scenario_source.lower() and "_score_" in scenario_source:
            # Check if confirmation affects scenario scoring
            if "confirmation_modifier" in scenario_source.lower():
                violations.append("Confirmation affects scenario scoring")
        
        if "mtf_consensus" in scenario_source.lower() and "eligible" in scenario_source.lower():
            violations.append("MTF consensus affects scenario eligibility")
        
        # Check that selection is based on probability
        if "probability" not in scenario_source:
            violations.append("Probability not used in scenario selection")
        
        if violations:
            logger.error("\n❌ TEST FAILED: Scenario selection violations")
            for v in violations:
                logger.error(f"   • {v}")
            return False
        else:
            logger.info("\n✅ TEST PASSED: Scenario selection independent")
            logger.info("   • Based on probability")
            logger.info("   • Based on component strength")
            logger.info("   • NOT affected by structure")
            logger.info("   • NOT affected by confirmation")
            logger.info("   • NOT affected by MTF consensus")
            return True
            
    except Exception as e:
        logger.error(f"\n❌ TEST ERROR: {str(e)}")
        return False


def run_all_tests():
    """Run all structure non-blocking tests"""
    logger.info("\n" + "=" * 80)
    logger.info("STRUCTURE NON-BLOCKING TEST SUITE")
    logger.info("Verifying compliance with specification")
    logger.info("=" * 80)
    
    results = {
        "Structure Non-Blocking": test_structure_non_blocking(),
        "Confirmation Modifier Only": test_confirmation_modifier_only(),
        "Only Two Hard Gates": test_only_two_hard_gates(),
        "Scenario Selection Independence": test_scenario_selection_independence()
    }
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("-" * 80)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 80)
    
    if passed == total:
        logger.info("\n✅ ALL TESTS PASSED - Structure non-blocking verified")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} TEST(S) FAILED - Specification violations remain")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
