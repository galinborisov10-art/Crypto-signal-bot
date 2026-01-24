"""
Test ML Feature Schema Validation (BUG H5)
Tests the sanity gate that prevents training/prediction feature mismatch
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml_engine import _validate_ml_features, REQUIRED_ML_FEATURES, VALID_TIMEFRAMES, VALID_SIGNAL_TYPES


def test_1_valid_schema_passes():
    """Test 1: Valid schema passes validation"""
    print("\n" + "="*60)
    print("TEST 1: Valid Schema Passes Validation")
    print("="*60)
    
    valid_analysis = {
        'rsi': 65.5,
        'confidence': 75.0,
        'volume_ratio': 1.5,
        'trend_strength': 0.8,
        'volatility': 5.2,
        'timeframe': '4h',
        'signal_type': 'BUY'
    }
    
    is_valid, missing = _validate_ml_features(valid_analysis)
    
    print(f"Analysis: {valid_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == True, "Valid schema should pass validation"
    assert len(missing) == 0, "No features should be missing"
    
    print("✅ PASS: Valid schema accepted")


def test_2_missing_required_feature():
    """Test 2: Missing required feature detected"""
    print("\n" + "="*60)
    print("TEST 2: Missing Required Feature Detected")
    print("="*60)
    
    incomplete_analysis = {
        'rsi': 65.5,
        'confidence': 75.0,
        # 'volume_ratio': missing!
        'trend_strength': 0.8,
        'volatility': 5.2,
        'timeframe': '4h',
        'signal_type': 'BUY'
    }
    
    is_valid, missing = _validate_ml_features(incomplete_analysis)
    
    print(f"Analysis: {incomplete_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == False, "Invalid schema should fail validation"
    assert 'volume_ratio (missing)' in missing, "volume_ratio should be detected as missing"
    
    print("✅ PASS: Missing feature detected")


def test_3_none_values_rejected():
    """Test 3: None values rejected"""
    print("\n" + "="*60)
    print("TEST 3: None Values Rejected")
    print("="*60)
    
    none_value_analysis = {
        'rsi': 65.5,
        'confidence': None,  # None value!
        'volume_ratio': 1.5,
        'trend_strength': 0.8,
        'volatility': 5.2,
        'timeframe': '4h',
        'signal_type': 'BUY'
    }
    
    is_valid, missing = _validate_ml_features(none_value_analysis)
    
    print(f"Analysis: {none_value_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == False, "None values should fail validation"
    assert 'confidence (None)' in missing, "None value should be detected"
    
    print("✅ PASS: None values rejected")


def test_4_wrong_types_detected():
    """Test 4: Wrong types detected"""
    print("\n" + "="*60)
    print("TEST 4: Wrong Types Detected")
    print("="*60)
    
    wrong_type_analysis = {
        'rsi': 65.5,
        'confidence': 75.0,
        'volume_ratio': "1.5",  # String instead of number!
        'trend_strength': 0.8,
        'volatility': 5.2,
        'timeframe': '4h',
        'signal_type': 'BUY'
    }
    
    is_valid, missing = _validate_ml_features(wrong_type_analysis)
    
    print(f"Analysis: {wrong_type_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == False, "Wrong types should fail validation"
    assert 'volume_ratio (wrong type: str)' in missing, "Wrong type should be detected"
    
    print("✅ PASS: Wrong types detected")


def test_5_invalid_categorical_values():
    """Test 5: Invalid categorical values rejected"""
    print("\n" + "="*60)
    print("TEST 5: Invalid Categorical Values Rejected")
    print("="*60)
    
    # Test invalid timeframe
    invalid_tf_analysis = {
        'rsi': 65.5,
        'confidence': 75.0,
        'volume_ratio': 1.5,
        'trend_strength': 0.8,
        'volatility': 5.2,
        'timeframe': '15m',  # Invalid timeframe!
        'signal_type': 'BUY'
    }
    
    is_valid, missing = _validate_ml_features(invalid_tf_analysis)
    
    print(f"Analysis (invalid timeframe): {invalid_tf_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == False, "Invalid timeframe should fail validation"
    assert 'timeframe (invalid: 15m)' in missing, "Invalid timeframe should be detected"
    
    # Test invalid signal_type
    invalid_signal_analysis = {
        'rsi': 65.5,
        'confidence': 75.0,
        'volume_ratio': 1.5,
        'trend_strength': 0.8,
        'volatility': 5.2,
        'timeframe': '4h',
        'signal_type': 'MAYBE_BUY'  # Invalid signal type!
    }
    
    is_valid, missing = _validate_ml_features(invalid_signal_analysis)
    
    print(f"\nAnalysis (invalid signal_type): {invalid_signal_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == False, "Invalid signal_type should fail validation"
    assert 'signal_type (invalid: MAYBE_BUY)' in missing, "Invalid signal_type should be detected"
    
    print("✅ PASS: Invalid categorical values rejected")


def test_6_multiple_errors_reported():
    """Test 6: Multiple errors reported"""
    print("\n" + "="*60)
    print("TEST 6: Multiple Errors Reported")
    print("="*60)
    
    multi_error_analysis = {
        'rsi': None,  # Error 1: None value
        'confidence': 75.0,
        # 'volume_ratio': missing!  # Error 2: Missing
        'trend_strength': "high",  # Error 3: Wrong type
        'volatility': 5.2,
        'timeframe': '15m',  # Error 4: Invalid categorical
        'signal_type': 'BUY'
    }
    
    is_valid, missing = _validate_ml_features(multi_error_analysis)
    
    print(f"Analysis: {multi_error_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    print(f"Number of errors: {len(missing)}")
    
    assert is_valid == False, "Multiple errors should fail validation"
    assert len(missing) >= 3, f"Should detect at least 3 errors, found {len(missing)}"
    
    print("✅ PASS: Multiple errors reported correctly")


def test_7_empty_analysis_rejected():
    """Test 7: Empty analysis rejected"""
    print("\n" + "="*60)
    print("TEST 7: Empty Analysis Rejected")
    print("="*60)
    
    empty_analysis = {}
    
    is_valid, missing = _validate_ml_features(empty_analysis)
    
    print(f"Analysis: {empty_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    print(f"Number of missing: {len(missing)}")
    
    assert is_valid == False, "Empty analysis should fail validation"
    assert len(missing) == len(REQUIRED_ML_FEATURES), "All features should be reported as missing"
    
    print("✅ PASS: Empty analysis rejected")


def run_all_tests():
    """Run all schema validation tests"""
    print("\n" + "="*70)
    print("ML FEATURE SCHEMA VALIDATION TEST SUITE (BUG H5)")
    print("="*70)
    print("\nTesting sanity gate to prevent training/prediction feature mismatch")
    
    tests = [
        test_1_valid_schema_passes,
        test_2_missing_required_feature,
        test_3_none_values_rejected,
        test_4_wrong_types_detected,
        test_5_invalid_categorical_values,
        test_6_multiple_errors_reported,
        test_7_empty_analysis_rejected
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total: {len(tests)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Schema validation working correctly.")
    else:
        print(f"\n⚠️ {failed} test(s) failed")
    
    print("="*70)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
