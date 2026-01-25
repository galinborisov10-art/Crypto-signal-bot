"""
Test ML Feature Schema Validation (BUG H5)
Tests the sanity gate that prevents training/prediction feature mismatch
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml_engine import _validate_ml_features, REQUIRED_ML_FEATURES


def test_1_valid_schema_passes():
    """Test 1: Valid schema passes validation (ICT-aligned, PR-ML-7)"""
    print("\n" + "="*60)
    print("TEST 1: Valid Schema Passes Validation (ICT-aligned)")
    print("="*60)
    
    valid_analysis = {
        'price_change_pct': 2.5,
        'volume_ratio': 1.5,
        'volatility': 5.2,
        'bb_position': 0.75,
        'ict_confidence': 0.82
    }
    
    is_valid, missing = _validate_ml_features(valid_analysis)
    
    print(f"Analysis: {valid_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == True, "Valid schema should pass validation"
    assert len(missing) == 0, "No features should be missing"
    
    print("✅ PASS: Valid schema accepted")


def test_2_missing_required_feature():
    """Test 2: Missing required feature detected (ICT-aligned, PR-ML-7)"""
    print("\n" + "="*60)
    print("TEST 2: Missing Required Feature Detected")
    print("="*60)
    
    incomplete_analysis = {
        'price_change_pct': 2.5,
        # 'volume_ratio': missing!
        'volatility': 5.2,
        'bb_position': 0.75,
        'ict_confidence': 0.82
    }
    
    is_valid, missing = _validate_ml_features(incomplete_analysis)
    
    print(f"Analysis: {incomplete_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == False, "Invalid schema should fail validation"
    assert 'volume_ratio (missing)' in missing, "volume_ratio should be detected as missing"
    
    print("✅ PASS: Missing feature detected")


def test_3_none_values_rejected():
    """Test 3: None values rejected (ICT-aligned, PR-ML-7)"""
    print("\n" + "="*60)
    print("TEST 3: None Values Rejected")
    print("="*60)
    
    none_value_analysis = {
        'price_change_pct': 2.5,
        'volume_ratio': None,  # None value!
        'volatility': 5.2,
        'bb_position': 0.75,
        'ict_confidence': 0.82
    }
    
    is_valid, missing = _validate_ml_features(none_value_analysis)
    
    print(f"Analysis: {none_value_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == False, "None values should fail validation"
    assert 'volume_ratio (None)' in missing, "None value should be detected"
    
    print("✅ PASS: None values rejected")


def test_4_wrong_types_detected():
    """Test 4: Wrong types detected (ICT-aligned, PR-ML-7)"""
    print("\n" + "="*60)
    print("TEST 4: Wrong Types Detected")
    print("="*60)
    
    wrong_type_analysis = {
        'price_change_pct': 2.5,
        'volume_ratio': "1.5",  # String instead of number!
        'volatility': 5.2,
        'bb_position': 0.75,
        'ict_confidence': 0.82
    }
    
    is_valid, missing = _validate_ml_features(wrong_type_analysis)
    
    print(f"Analysis: {wrong_type_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == False, "Wrong types should fail validation"
    assert 'volume_ratio (wrong type: str)' in missing, "Wrong type should be detected"
    
    print("✅ PASS: Wrong types detected")


def test_5_numeric_ranges_accepted():
    """Test 5: Numeric ranges accepted (no categorical validation in ICT schema, PR-ML-7)"""
    print("\n" + "="*60)
    print("TEST 5: Numeric Ranges Accepted (ICT-aligned)")
    print("="*60)
    
    # Test with various numeric values - all should be accepted
    numeric_range_analysis = {
        'price_change_pct': -10.5,  # Negative value is OK
        'volume_ratio': 0.1,        # Small value is OK
        'volatility': 100.0,        # Large value is OK
        'bb_position': 1.5,         # Value > 1 is OK
        'ict_confidence': 0.95      # High confidence is OK
    }
    
    is_valid, missing = _validate_ml_features(numeric_range_analysis)
    
    print(f"Analysis (various numeric ranges): {numeric_range_analysis}")
    print(f"Valid: {is_valid}")
    print(f"Missing features: {missing}")
    
    assert is_valid == True, "Numeric values of any range should pass (no categorical validation)"
    assert len(missing) == 0, "No features should be reported as invalid"
    
    print("✅ PASS: Numeric ranges accepted (no categorical validation in ICT schema)")


def test_6_multiple_errors_reported():
    """Test 6: Multiple errors reported (ICT-aligned, PR-ML-7)"""
    print("\n" + "="*60)
    print("TEST 6: Multiple Errors Reported")
    print("="*60)
    
    multi_error_analysis = {
        'price_change_pct': None,  # Error 1: None value
        # 'volume_ratio': missing!  # Error 2: Missing
        'volatility': "high",  # Error 3: Wrong type
        'bb_position': 0.75,
        'ict_confidence': 0.82
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
    """Run all schema validation tests (ICT-aligned, PR-ML-7)"""
    print("\n" + "="*70)
    print("ML FEATURE SCHEMA VALIDATION TEST SUITE (ICT-aligned, PR-ML-7)")
    print("="*70)
    print("\nTesting schema validation for ICT-only feature space (5 features)")
    
    tests = [
        test_1_valid_schema_passes,
        test_2_missing_required_feature,
        test_3_none_values_rejected,
        test_4_wrong_types_detected,
        test_5_numeric_ranges_accepted,
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
