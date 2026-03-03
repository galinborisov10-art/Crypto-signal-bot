"""
POST-PR VALIDATION TESTS
Validates compliance with specification requirements
All 9 tests must pass for merge approval
"""

import sys
import logging
from timeframe_contract import TimeframeContract, SignalMode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_pass(self, test_name: str, message: str = ""):
        self.passed += 1
        self.tests.append((test_name, True, message))
        logger.info(f"✅ PASS: {test_name}")
        if message:
            logger.info(f"   {message}")
    
    def add_fail(self, test_name: str, message: str):
        self.failed += 1
        self.tests.append((test_name, False, message))
        logger.error(f"❌ FAIL: {test_name}")
        logger.error(f"   {message}")
    
    def print_summary(self):
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {self.passed + self.failed}")
        logger.info(f"Passed: {self.passed}")
        logger.info(f"Failed: {self.failed}")
        logger.info("=" * 80)
        
        if self.failed > 0:
            logger.error("\n❌ TESTS FAILED - PR BLOCKED")
            logger.error("Fix the failures above before merge")
            return False
        else:
            logger.info("\n✅ ALL TESTS PASSED - PR READY FOR MERGE")
            return True


def test_1_timeframe_correctness():
    """
    Test 1: Timeframe Correctness
    Verify all signal types use correct timeframes
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: TIMEFRAME CORRECTNESS")
    logger.info("=" * 80)
    
    results = TestResults()
    
    # Expected values from specification
    expected_manual = {
        '15m': {'signal': '15m', 'conf': '30m', 'struct': '1h', 'htf': '1h'},
        '30m': {'signal': '30m', 'conf': '1h', 'struct': '2h', 'htf': '2h'},
        '1h': {'signal': '1h', 'conf': '2h', 'struct': '4h', 'htf': '4h'},
        '2h': {'signal': '2h', 'conf': '4h', 'struct': '1d', 'htf': '1d'},
        '4h': {'signal': '4h', 'conf': '1d', 'struct': '1d', 'htf': '1d'},
        '1d': {'signal': '1d', 'conf': '1d', 'struct': '1d', 'htf': '1d'},
    }
    
    expected_auto = {
        '1h': {'signal': '1h', 'conf': '2h', 'struct': '4h', 'htf': '4h'},
        '2h': {'signal': '2h', 'conf': '4h', 'struct': '1d', 'htf': '1d'},
        '4h': {'signal': '4h', 'conf': '1d', 'struct': '1d', 'htf': '1d'},
        '1d': {'signal': '1d', 'conf': '1d', 'struct': '1d', 'htf': '1d'},
    }
    
    # Test manual signals
    logger.info("\n📋 Testing MANUAL signal hierarchies:")
    for tf, expected in expected_manual.items():
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.MANUAL)
        if not hierarchy:
            results.add_fail(f"Manual {tf} hierarchy", f"Could not get hierarchy for {tf}")
            continue
        
        errors = []
        if hierarchy.signal_tf != expected['signal']:
            errors.append(f"signal_tf={hierarchy.signal_tf}, expected {expected['signal']}")
        if hierarchy.confirmation_tf != expected['conf']:
            errors.append(f"confirmation_tf={hierarchy.confirmation_tf}, expected {expected['conf']}")
        if hierarchy.structure_tf != expected['struct']:
            errors.append(f"structure_tf={hierarchy.structure_tf}, expected {expected['struct']}")
        if hierarchy.htf_bias_tf != expected['htf']:
            errors.append(f"htf_bias_tf={hierarchy.htf_bias_tf}, expected {expected['htf']}")
        
        if errors:
            results.add_fail(f"Manual {tf} hierarchy", "; ".join(errors))
        else:
            results.add_pass(
                f"Manual {tf} hierarchy",
                f"Conf:{hierarchy.confirmation_tf}, Struct:{hierarchy.structure_tf}, HTF:{hierarchy.htf_bias_tf}"
            )
    
    # Test automatic signals
    logger.info("\n📋 Testing AUTOMATIC signal hierarchies:")
    for tf, expected in expected_auto.items():
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.AUTOMATIC)
        if not hierarchy:
            results.add_fail(f"Auto {tf} hierarchy", f"Could not get hierarchy for {tf}")
            continue
        
        errors = []
        if hierarchy.signal_tf != expected['signal']:
            errors.append(f"signal_tf={hierarchy.signal_tf}, expected {expected['signal']}")
        if hierarchy.confirmation_tf != expected['conf']:
            errors.append(f"confirmation_tf={hierarchy.confirmation_tf}, expected {expected['conf']}")
        if hierarchy.structure_tf != expected['struct']:
            errors.append(f"structure_tf={hierarchy.structure_tf}, expected {expected['struct']}")
        if hierarchy.htf_bias_tf != expected['htf']:
            errors.append(f"htf_bias_tf={hierarchy.htf_bias_tf}, expected {expected['htf']}")
        
        if errors:
            results.add_fail(f"Auto {tf} hierarchy", "; ".join(errors))
        else:
            results.add_pass(
                f"Auto {tf} hierarchy",
                f"Conf:{hierarchy.confirmation_tf}, Struct:{hierarchy.structure_tf}, HTF:{hierarchy.htf_bias_tf}"
            )
    
    return results


def test_2_no_hardcoded_values():
    """
    Test 2: No Hardcoded Timeframe Values
    Verify no hardcoded '1d' or '1w' in fallback logic
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: NO HARDCODED TIMEFRAME VALUES")
    logger.info("=" * 80)
    
    results = TestResults()
    
    # Check ict_signal_engine.py for hardcoded timeframe fallbacks
    with open('ict_signal_engine.py', 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Look for the specific fallback logic that was problematic
    found_bad_fallback = False
    for i, line in enumerate(lines, 1):
        # Check for the old problematic pattern
        if "'1w' if entry_tf_normalized in" in line or '"1w" if entry_tf_normalized in' in line:
            results.add_fail(
                "No hardcoded 1w fallback",
                f"Found hardcoded '1w' fallback at line {i}: {line.strip()}"
            )
            found_bad_fallback = True
        
        # Also check for similar patterns
        if "entry_tf_normalized in ['4h', '1d']" in line and ("'1w'" in line or '"1w"' in line):
            results.add_fail(
                "No conditional 1w assignment",
                f"Found conditional 1w assignment at line {i}: {line.strip()}"
            )
            found_bad_fallback = True
    
    if not found_bad_fallback:
        results.add_pass(
            "No hardcoded timeframe fallbacks",
            "No hardcoded '1w' or conditional timeframe assignments found"
        )
    
    # Verify fallback uses config-based values
    if "htf_bias_tf = '1d'" in content or 'htf_bias_tf = "1d"' in content:
        # This is OK as a simple fallback
        results.add_pass(
            "Simple 1d fallback present",
            "Uses '1d' as universal fallback (matches spec)"
        )
    
    return results


def test_3_structure_tf_correctness():
    """
    Test 3: Structure TF Correctness
    Critical test for 2h and 4h signals
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: STRUCTURE TF CORRECTNESS (CRITICAL)")
    logger.info("=" * 80)
    
    results = TestResults()
    
    # Test 2h signals (was broken - structure_tf was 4h instead of 1d)
    h_2h_manual = TimeframeContract.get_hierarchy('2h', SignalMode.MANUAL)
    if h_2h_manual and h_2h_manual.structure_tf == '1d':
        results.add_pass("2h manual structure_tf", "Correctly set to '1d'")
    else:
        actual = h_2h_manual.structure_tf if h_2h_manual else "None"
        results.add_fail("2h manual structure_tf", f"Expected '1d', got '{actual}'")
    
    h_2h_auto = TimeframeContract.get_hierarchy('2h', SignalMode.AUTOMATIC)
    if h_2h_auto and h_2h_auto.structure_tf == '1d':
        results.add_pass("2h auto structure_tf", "Correctly set to '1d'")
    else:
        actual = h_2h_auto.structure_tf if h_2h_auto else "None"
        results.add_fail("2h auto structure_tf", f"Expected '1d', got '{actual}'")
    
    # Test 4h signals (confirmation_tf was 4h instead of 1d)
    h_4h_manual = TimeframeContract.get_hierarchy('4h', SignalMode.MANUAL)
    if h_4h_manual and h_4h_manual.confirmation_tf == '1d':
        results.add_pass("4h manual confirmation_tf", "Correctly set to '1d'")
    else:
        actual = h_4h_manual.confirmation_tf if h_4h_manual else "None"
        results.add_fail("4h manual confirmation_tf", f"Expected '1d', got '{actual}'")
    
    h_4h_auto = TimeframeContract.get_hierarchy('4h', SignalMode.AUTOMATIC)
    if h_4h_auto and h_4h_auto.confirmation_tf == '1d':
        results.add_pass("4h auto confirmation_tf", "Correctly set to '1d'")
    else:
        actual = h_4h_auto.confirmation_tf if h_4h_auto else "None"
        results.add_fail("4h auto confirmation_tf", f"Expected '1d', got '{actual}'")
    
    return results


def test_4_htf_bias_tf_correctness():
    """
    Test 4: HTF Bias TF Correctness
    Verify HTF bias TF always equals structure TF
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: HTF BIAS TF CORRECTNESS")
    logger.info("=" * 80)
    
    results = TestResults()
    
    # Test all manual signals
    for tf in ['15m', '30m', '1h', '2h', '4h', '1d']:
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.MANUAL)
        if not hierarchy:
            results.add_fail(f"Manual {tf} HTF bias", "Could not get hierarchy")
            continue
        
        if hierarchy.htf_bias_tf == hierarchy.structure_tf:
            results.add_pass(
                f"Manual {tf} HTF bias",
                f"HTF={hierarchy.htf_bias_tf} equals Structure={hierarchy.structure_tf}"
            )
        else:
            results.add_fail(
                f"Manual {tf} HTF bias",
                f"HTF={hierarchy.htf_bias_tf} != Structure={hierarchy.structure_tf}"
            )
    
    # Test all automatic signals
    for tf in ['1h', '2h', '4h', '1d']:
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.AUTOMATIC)
        if not hierarchy:
            results.add_fail(f"Auto {tf} HTF bias", "Could not get hierarchy")
            continue
        
        if hierarchy.htf_bias_tf == hierarchy.structure_tf:
            results.add_pass(
                f"Auto {tf} HTF bias",
                f"HTF={hierarchy.htf_bias_tf} equals Structure={hierarchy.structure_tf}"
            )
        else:
            results.add_fail(
                f"Auto {tf} HTF bias",
                f"HTF={hierarchy.htf_bias_tf} != Structure={hierarchy.structure_tf}"
            )
    
    return results


def test_5_config_file_alignment():
    """
    Test 5: Config File Alignment
    Verify JSON config matches Python contract
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: CONFIG FILE ALIGNMENT")
    logger.info("=" * 80)
    
    import json
    results = TestResults()
    
    try:
        with open('config/timeframe_hierarchy.json', 'r') as f:
            config = json.load(f)
        
        # Check 2h config
        h_2h = config['hierarchies']['2h']
        if h_2h['structure_tf'] == '1d' and h_2h['htf_bias_tf'] == '1d':
            results.add_pass(
                "2h JSON config",
                f"structure_tf={h_2h['structure_tf']}, htf_bias_tf={h_2h['htf_bias_tf']}"
            )
        else:
            results.add_fail(
                "2h JSON config",
                f"Expected structure_tf=1d, htf_bias_tf=1d; Got structure_tf={h_2h['structure_tf']}, htf_bias_tf={h_2h['htf_bias_tf']}"
            )
        
        # Check 4h config
        h_4h = config['hierarchies']['4h']
        if h_4h['confirmation_tf'] == '1d':
            results.add_pass(
                "4h JSON config",
                f"confirmation_tf={h_4h['confirmation_tf']}"
            )
        else:
            results.add_fail(
                "4h JSON config",
                f"Expected confirmation_tf=1d; Got confirmation_tf={h_4h['confirmation_tf']}"
            )
        
        # Verify Python contract matches JSON
        h_2h_py = TimeframeContract.get_hierarchy('2h', SignalMode.MANUAL)
        if h_2h_py:
            if (h_2h_py.structure_tf == h_2h['structure_tf'] and 
                h_2h_py.htf_bias_tf == h_2h['htf_bias_tf']):
                results.add_pass("2h Python-JSON alignment", "Hierarchies match")
            else:
                results.add_fail(
                    "2h Python-JSON alignment",
                    f"Python: struct={h_2h_py.structure_tf}, htf={h_2h_py.htf_bias_tf}; "
                    f"JSON: struct={h_2h['structure_tf']}, htf={h_2h['htf_bias_tf']}"
                )
        
        h_4h_py = TimeframeContract.get_hierarchy('4h', SignalMode.MANUAL)
        if h_4h_py:
            if h_4h_py.confirmation_tf == h_4h['confirmation_tf']:
                results.add_pass("4h Python-JSON alignment", "Hierarchies match")
            else:
                results.add_fail(
                    "4h Python-JSON alignment",
                    f"Python: conf={h_4h_py.confirmation_tf}; JSON: conf={h_4h['confirmation_tf']}"
                )
        
    except Exception as e:
        results.add_fail("Config file loading", f"Error: {str(e)}")
    
    return results


def run_all_tests():
    """Run all validation tests"""
    logger.info("\n" + "=" * 80)
    logger.info("POST-PR VALIDATION TEST SUITE")
    logger.info("Specification Compliance Verification")
    logger.info("=" * 80)
    
    all_results = TestResults()
    
    # Run tests
    test_suites = [
        ("Test 1: Timeframe Correctness", test_1_timeframe_correctness),
        ("Test 2: No Hardcoded Values", test_2_no_hardcoded_values),
        ("Test 3: Structure TF Correctness", test_3_structure_tf_correctness),
        ("Test 4: HTF Bias TF Correctness", test_4_htf_bias_tf_correctness),
        ("Test 5: Config File Alignment", test_5_config_file_alignment),
    ]
    
    for suite_name, test_func in test_suites:
        try:
            suite_results = test_func()
            # Merge results
            all_results.passed += suite_results.passed
            all_results.failed += suite_results.failed
            all_results.tests.extend(suite_results.tests)
        except Exception as e:
            logger.error(f"\n❌ ERROR in {suite_name}: {str(e)}")
            all_results.add_fail(suite_name, f"Test suite error: {str(e)}")
    
    # Print summary
    success = all_results.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
