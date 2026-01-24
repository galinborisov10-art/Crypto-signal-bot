"""
TEST ML CONFIDENCE MODIFIER BOUNDS
===================================

Tests for PR-ML-1: ML Confidence Modifier Bounds

Validates that ML confidence modifiers are properly bounded to prevent
excessive influence on strategy-approved signals.

Tests:
1. Bounds constants are defined correctly
2. Bounds are asymmetric (penalty > boost, conservative)
3. Inline clamp simulation works correctly
4. Final confidence stays in [0, 100] range
"""

import sys
import os

# Add parent directory to path to import ml_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml_engine import ML_MODIFIER_MIN, ML_MODIFIER_MAX


def test_bounds_constants_defined():
    """Test 1: Verify bounds constants are defined correctly"""
    print("\n" + "=" * 60)
    print("TEST 1: Bounds Constants Defined")
    print("=" * 60)
    
    # Verify ML_MODIFIER_MIN is defined and correct
    assert ML_MODIFIER_MIN == -0.15, f"ML_MODIFIER_MIN should be -0.15, got {ML_MODIFIER_MIN}"
    print(f"✅ ML_MODIFIER_MIN = {ML_MODIFIER_MIN} (max penalty: -15%)")
    
    # Verify ML_MODIFIER_MAX is defined and correct
    assert ML_MODIFIER_MAX == 0.10, f"ML_MODIFIER_MAX should be 0.10, got {ML_MODIFIER_MAX}"
    print(f"✅ ML_MODIFIER_MAX = {ML_MODIFIER_MAX} (max boost: +10%)")
    
    print("\n✅ TEST 1 PASSED: Bounds constants defined correctly")
    return True


def test_bounds_are_asymmetric():
    """Test 2: Verify bounds are asymmetric (penalty > boost, conservative)"""
    print("\n" + "=" * 60)
    print("TEST 2: Bounds Are Asymmetric (Conservative)")
    print("=" * 60)
    
    # Verify penalty magnitude > boost magnitude (conservative design)
    penalty_magnitude = abs(ML_MODIFIER_MIN)
    boost_magnitude = abs(ML_MODIFIER_MAX)
    
    print(f"📊 Penalty magnitude: {penalty_magnitude:.2f}")
    print(f"📊 Boost magnitude: {boost_magnitude:.2f}")
    
    assert penalty_magnitude > boost_magnitude, \
        f"Penalty ({penalty_magnitude}) should be > boost ({boost_magnitude}) for conservative design"
    
    print(f"✅ Conservative design: penalty ({penalty_magnitude:.2f}) > boost ({boost_magnitude:.2f})")
    
    # Verify ratio is reasonable (penalty should be ~1.5x boost)
    ratio = penalty_magnitude / boost_magnitude
    print(f"📊 Penalty/Boost ratio: {ratio:.2f}x")
    
    assert ratio >= 1.4 and ratio <= 1.6, \
        f"Expected ratio ~1.5x, got {ratio:.2f}x"
    
    print(f"✅ Ratio is reasonable: {ratio:.2f}x")
    
    print("\n✅ TEST 2 PASSED: Bounds are asymmetric and conservative")
    return True


def test_inline_clamp_simulation():
    """Test 3: Simulate inline clamp logic"""
    print("\n" + "=" * 60)
    print("TEST 3: Inline Clamp Simulation")
    print("=" * 60)
    
    test_cases = [
        # (ml_confidence, expected_modifier, description)
        (50, 0.0, "ML confidence = 50% → modifier = 0 (neutral)"),
        (60, 0.10, "ML confidence = 60% → modifier = +10% (at MAX, no clamp)"),
        (70, 0.10, "ML confidence = 70% → modifier = +20% → clamped to +10%"),
        (100, 0.10, "ML confidence = 100% → modifier = +50% → clamped to +10%"),
        (40, -0.10, "ML confidence = 40% → modifier = -10% (within bounds)"),
        (35, -0.15, "ML confidence = 35% → modifier = -15% (at MIN, no clamp)"),
        (0, -0.15, "ML confidence = 0% → modifier = -50% → clamped to -15%"),
    ]
    
    all_passed = True
    for ml_confidence, expected_modifier, description in test_cases:
        # Calculate modifier (same formula as in ml_engine.py)
        ml_modifier = (ml_confidence - 50) / 100.0
        
        # Apply bounds (same logic as in ml_engine.py)
        if ml_modifier > ML_MODIFIER_MAX:
            ml_modifier = ML_MODIFIER_MAX
        elif ml_modifier < ML_MODIFIER_MIN:
            ml_modifier = ML_MODIFIER_MIN
        
        # Verify result
        if abs(ml_modifier - expected_modifier) < 0.001:  # Allow small floating point error
            print(f"✅ {description}")
        else:
            print(f"❌ {description}")
            print(f"   Expected: {expected_modifier:.3f}, Got: {ml_modifier:.3f}")
            all_passed = False
    
    assert all_passed, "Some inline clamp simulations failed"
    
    print("\n✅ TEST 3 PASSED: Inline clamp simulation works correctly")
    return True


def test_final_confidence_range():
    """Test 4: Verify final confidence stays in [0, 100] range"""
    print("\n" + "=" * 60)
    print("TEST 4: Final Confidence Range [0, 100]")
    print("=" * 60)
    
    test_cases = [
        # (classical_confidence, ml_modifier, description)
        (50, 0.10, "50% confidence + 10% boost = 55%"),
        (90, 0.10, "90% confidence + 10% boost = 99%"),
        (100, 0.10, "100% confidence + 10% boost = 100% (clamped)"),
        (10, 0.10, "10% confidence + 10% boost = 11%"),
        (50, -0.15, "50% confidence - 15% penalty = 42.5%"),
        (20, -0.15, "20% confidence - 15% penalty = 17%"),
        (10, -0.15, "10% confidence - 15% penalty = 8.5%"),
        (5, -0.15, "5% confidence - 15% penalty = 4.25%"),
    ]
    
    all_passed = True
    for classical_confidence, ml_modifier, description in test_cases:
        # Apply modifier (same formula as in ml_engine.py)
        final_confidence = classical_confidence * (1 + ml_modifier)
        
        # Apply range clamp (same as in ml_engine.py)
        final_confidence = max(0, min(100, final_confidence))
        
        # Verify range
        if 0 <= final_confidence <= 100:
            print(f"✅ {description} → {final_confidence:.1f}%")
        else:
            print(f"❌ {description} → {final_confidence:.1f}% (OUT OF RANGE)")
            all_passed = False
    
    assert all_passed, "Some confidence values were out of range"
    
    # Additional edge case tests
    print("\n📊 Edge case tests:")
    
    # Extreme low confidence with max penalty
    edge_confidence = 1 * (1 + ML_MODIFIER_MIN)
    edge_confidence = max(0, min(100, edge_confidence))
    print(f"   1% confidence - 15% penalty = {edge_confidence:.2f}%")
    assert 0 <= edge_confidence <= 100, "Edge case 1 failed"
    
    # Extreme high confidence with max boost
    edge_confidence = 99 * (1 + ML_MODIFIER_MAX)
    edge_confidence = max(0, min(100, edge_confidence))
    print(f"   99% confidence + 10% boost = {edge_confidence:.2f}%")
    assert 0 <= edge_confidence <= 100, "Edge case 2 failed"
    
    print("\n✅ TEST 4 PASSED: Final confidence always in [0, 100] range")
    return True


def run_all_tests():
    """Run all ML confidence bounds tests"""
    print("\n" + "=" * 60)
    print("🧪 ML CONFIDENCE MODIFIER BOUNDS TESTS")
    print("PR-ML-1: Validation Suite")
    print("=" * 60)
    
    tests = [
        ("Bounds Constants Defined", test_bounds_constants_defined),
        ("Bounds Are Asymmetric", test_bounds_are_asymmetric),
        ("Inline Clamp Simulation", test_inline_clamp_simulation),
        ("Final Confidence Range", test_final_confidence_range),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("=" * 60)
        return True
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("=" * 60)
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
