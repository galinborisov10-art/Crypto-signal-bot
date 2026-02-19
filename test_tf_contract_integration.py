"""
Test script to verify Timeframe Contract integration
Tests that the centralized TF hierarchy is working correctly
"""

import sys
import logging
from timeframe_contract import (
    TimeframeContract,
    SignalMode,
    TimeframeDebugLogger
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

def test_manual_hierarchies():
    """Test all manual signal timeframe hierarchies"""
    print("\n" + "=" * 70)
    print("TEST 1: MANUAL SIGNAL HIERARCHIES")
    print("=" * 70)
    
    expected_hierarchies = {
        '15m': {'signal': '15m', 'conf': '30m', 'struct': '1h', 'htf': '1h'},
        '30m': {'signal': '30m', 'conf': '1h', 'struct': '2h', 'htf': '2h'},
        '1h': {'signal': '1h', 'conf': '2h', 'struct': '4h', 'htf': '4h'},
        '2h': {'signal': '2h', 'conf': '4h', 'struct': '1d', 'htf': '1d'},
        '4h': {'signal': '4h', 'conf': '1d', 'struct': '1d', 'htf': '1d'},
        '1d': {'signal': '1d', 'conf': '1d', 'struct': '1d', 'htf': '1d'},
    }
    
    all_passed = True
    for tf, expected in expected_hierarchies.items():
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.MANUAL)
        
        if not hierarchy:
            print(f"❌ FAILED: No hierarchy returned for {tf}")
            all_passed = False
            continue
        
        # Check each timeframe
        checks = [
            (hierarchy.signal_tf, expected['signal'], 'Signal TF'),
            (hierarchy.confirmation_tf, expected['conf'], 'Confirmation TF'),
            (hierarchy.structure_tf, expected['struct'], 'Structure TF'),
            (hierarchy.htf_bias_tf, expected['htf'], 'HTF Bias TF'),
        ]
        
        tf_passed = True
        for actual, expected_val, name in checks:
            if actual != expected_val:
                print(f"❌ FAILED: {tf} {name}: expected {expected_val}, got {actual}")
                tf_passed = False
                all_passed = False
        
        if tf_passed:
            print(f"✅ PASSED: {tf} hierarchy correct")
    
    return all_passed


def test_automatic_hierarchies():
    """Test all automatic signal timeframe hierarchies"""
    print("\n" + "=" * 70)
    print("TEST 2: AUTOMATIC SIGNAL HIERARCHIES")
    print("=" * 70)
    
    expected_hierarchies = {
        '1h': {'signal': '1h', 'conf': '2h', 'struct': '4h', 'htf': '4h'},
        '2h': {'signal': '2h', 'conf': '4h', 'struct': '1d', 'htf': '1d'},
        '4h': {'signal': '4h', 'conf': '1d', 'struct': '1d', 'htf': '1d'},
        '1d': {'signal': '1d', 'conf': '1d', 'struct': '1d', 'htf': '1d'},
    }
    
    all_passed = True
    for tf, expected in expected_hierarchies.items():
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.AUTOMATIC)
        
        if not hierarchy:
            print(f"❌ FAILED: No hierarchy returned for {tf}")
            all_passed = False
            continue
        
        # Check each timeframe
        checks = [
            (hierarchy.signal_tf, expected['signal'], 'Signal TF'),
            (hierarchy.confirmation_tf, expected['conf'], 'Confirmation TF'),
            (hierarchy.structure_tf, expected['struct'], 'Structure TF'),
            (hierarchy.htf_bias_tf, expected['htf'], 'HTF Bias TF'),
        ]
        
        tf_passed = True
        for actual, expected_val, name in checks:
            if actual != expected_val:
                print(f"❌ FAILED: {tf} {name}: expected {expected_val}, got {actual}")
                tf_passed = False
                all_passed = False
        
        if tf_passed:
            print(f"✅ PASSED: {tf} automatic hierarchy correct")
    
    return all_passed


def test_unsupported_timeframes():
    """Test that unsupported timeframes are rejected"""
    print("\n" + "=" * 70)
    print("TEST 3: UNSUPPORTED TIMEFRAMES")
    print("=" * 70)
    
    all_passed = True
    
    # Test unsupported manual timeframes
    unsupported_manual = ['5m', '3h', '1w']
    for tf in unsupported_manual:
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.MANUAL)
        if hierarchy is not None:
            print(f"❌ FAILED: {tf} should not be supported for MANUAL mode")
            all_passed = False
        else:
            print(f"✅ PASSED: {tf} correctly rejected for MANUAL mode")
    
    # Test unsupported automatic timeframes (15m, 30m)
    unsupported_auto = ['15m', '30m', '5m']
    for tf in unsupported_auto:
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.AUTOMATIC)
        if hierarchy is not None:
            print(f"❌ FAILED: {tf} should not be supported for AUTOMATIC mode")
            all_passed = False
        else:
            print(f"✅ PASSED: {tf} correctly rejected for AUTOMATIC mode")
    
    return all_passed


def test_component_validation():
    """Test component timeframe validation"""
    print("\n" + "=" * 70)
    print("TEST 4: COMPONENT TIMEFRAME VALIDATION")
    print("=" * 70)
    
    all_passed = True
    
    # Test valid component
    is_valid, error = TimeframeContract.validate_component_timeframe(
        component_tf="1h",
        expected_tf="1h",
        component_name="Order Block"
    )
    
    if is_valid and error is None:
        print("✅ PASSED: Valid component correctly validated")
    else:
        print(f"❌ FAILED: Valid component rejected: {error}")
        all_passed = False
    
    # Test invalid component
    is_valid, error = TimeframeContract.validate_component_timeframe(
        component_tf="4h",
        expected_tf="1h",
        component_name="Order Block"
    )
    
    if not is_valid and error is not None:
        print("✅ PASSED: Invalid component correctly rejected")
    else:
        print("❌ FAILED: Invalid component not detected")
        all_passed = False
    
    # Test case insensitivity
    is_valid, error = TimeframeContract.validate_component_timeframe(
        component_tf="1H",
        expected_tf="1h",
        component_name="FVG"
    )
    
    if is_valid and error is None:
        print("✅ PASSED: Case insensitivity works correctly")
    else:
        print(f"❌ FAILED: Case insensitivity failed: {error}")
        all_passed = False
    
    return all_passed


def test_debug_logger():
    """Test debug logger functions"""
    print("\n" + "=" * 70)
    print("TEST 5: DEBUG LOGGER FUNCTIONALITY")
    print("=" * 70)
    
    try:
        # Test hierarchy logging
        hierarchy = TimeframeContract.get_hierarchy("1h", SignalMode.MANUAL)
        if hierarchy:
            TimeframeDebugLogger.log_hierarchy_usage(hierarchy, "BTCUSDT")
            print("✅ PASSED: Hierarchy logging works")
        
        # Test component logging
        TimeframeDebugLogger.log_component_source("Order Blocks", "1h", 5)
        print("✅ PASSED: Component source logging works")
        
        # Test scoring logging
        TimeframeDebugLogger.log_scoring_timeframe("1h", "PULLBACK")
        print("✅ PASSED: Scoring timeframe logging works")
        
        # Test bias logging
        TimeframeDebugLogger.log_bias_timeframe("4h", "BULLISH")
        print("✅ PASSED: Bias timeframe logging works")
        
        # Test validation error logging
        TimeframeDebugLogger.log_component_validation_error(
            "Order Block", "4h", "1h", "Wrong timeframe"
        )
        print("✅ PASSED: Validation error logging works")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: Debug logger error: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 70)
    print("TIMEFRAME CONTRACT INTEGRATION TESTS")
    print("=" * 70)
    
    results = {
        "Manual Hierarchies": test_manual_hierarchies(),
        "Automatic Hierarchies": test_automatic_hierarchies(),
        "Unsupported Timeframes": test_unsupported_timeframes(),
        "Component Validation": test_component_validation(),
        "Debug Logger": test_debug_logger(),
    }
    
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Timeframe Contract is working correctly.")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED! Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
