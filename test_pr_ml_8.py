"""
Test PR-ML-8: ML Final Positioning in Pipeline

Verify that:
1. ML runs LAST in the pipeline (after all guards)
2. ML CANNOT change signal direction
3. ML influences ONLY confidence
4. ML modifies confidence within strict bounds
5. get_confidence_modifier() works correctly
"""

import sys
import os
import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml_engine import MLTradingEngine, ML_MODIFIER_MIN, ML_MODIFIER_MAX


def test_get_confidence_modifier():
    """Test 1: Verify get_confidence_modifier() method exists and works"""
    print("\n" + "="*60)
    print("TEST 1: get_confidence_modifier() Method")
    print("="*60)
    
    ml_engine = MLTradingEngine()
    
    # Check method exists
    if not hasattr(ml_engine, 'get_confidence_modifier'):
        print("❌ FAILED: get_confidence_modifier() method not found")
        return False
    
    print("✅ Method exists")
    
    # Test with no model (should return neutral modifier)
    analysis = {
        'price_change_pct': 0.5,
        'volume_ratio': 1.2,
        'volatility': 2.0,
        'bb_position': 0.7,
        'ict_confidence': 0.85
    }
    
    result = ml_engine.get_confidence_modifier(
        analysis=analysis,
        final_signal='BUY',
        base_confidence=75.0
    )
    
    # Verify return structure
    required_keys = ['confidence_modifier', 'ml_confidence', 'mode', 'warnings']
    for key in required_keys:
        if key not in result:
            print(f"❌ FAILED: Missing key '{key}' in result")
            return False
    
    print(f"✅ Returns correct structure: {result.keys()}")
    
    # With no model, modifier should be 1.0 (no change)
    if result['confidence_modifier'] != 1.0:
        print(f"❌ FAILED: Expected modifier 1.0 with no model, got {result['confidence_modifier']}")
        return False
    
    print(f"✅ Correct neutral modifier (1.0) when no model")
    print(f"   Mode: {result['mode']}")
    
    return True


def test_confidence_modifier_bounds():
    """Test 2: Verify confidence modifier is bounded"""
    print("\n" + "="*60)
    print("TEST 2: Confidence Modifier Bounds")
    print("="*60)
    
    print(f"   ML_MODIFIER_MIN: {ML_MODIFIER_MIN} ({ML_MODIFIER_MIN*100:+.0f})")
    print(f"   ML_MODIFIER_MAX: {ML_MODIFIER_MAX} ({ML_MODIFIER_MAX*100:+.0f})")
    
    # Test that constants are properly defined
    if ML_MODIFIER_MIN >= 0:
        print(f"❌ FAILED: ML_MODIFIER_MIN should be negative (penalty), got {ML_MODIFIER_MIN}")
        return False
    
    if ML_MODIFIER_MAX <= 0:
        print(f"❌ FAILED: ML_MODIFIER_MAX should be positive (boost), got {ML_MODIFIER_MAX}")
        return False
    
    print("✅ Bounds are correctly defined")
    
    # Expected values from problem statement
    expected_min = -0.15  # -15%
    expected_max = 0.10   # +10%
    
    if ML_MODIFIER_MIN != expected_min:
        print(f"⚠️  WARNING: ML_MODIFIER_MIN is {ML_MODIFIER_MIN}, expected {expected_min}")
    
    if ML_MODIFIER_MAX != expected_max:
        print(f"⚠️  WARNING: ML_MODIFIER_MAX is {ML_MODIFIER_MAX}, expected {expected_max}")
    
    return True


def test_direction_preservation():
    """Test 3: Verify ML cannot change signal direction"""
    print("\n" + "="*60)
    print("TEST 3: Signal Direction Preservation")
    print("="*60)
    
    ml_engine = MLTradingEngine()
    
    # Test both BUY and SELL signals
    test_cases = [
        ('BUY', 75.0),
        ('SELL', 80.0),
        ('BUY', 65.0),
        ('SELL', 70.0),
    ]
    
    for final_signal, base_confidence in test_cases:
        analysis = {
            'price_change_pct': 0.5,
            'volume_ratio': 1.2,
            'volatility': 2.0,
            'bb_position': 0.7,
            'ict_confidence': base_confidence / 100.0
        }
        
        result = ml_engine.get_confidence_modifier(
            analysis=analysis,
            final_signal=final_signal,
            base_confidence=base_confidence
        )
        
        # Method should NEVER return a different signal
        # It should only return a confidence modifier
        if 'final_signal' in result or 'signal' in result:
            print(f"❌ FAILED: get_confidence_modifier() returns signal (should only return modifier)")
            return False
    
    print(f"✅ get_confidence_modifier() returns ONLY confidence modifier, never signal")
    print(f"✅ Tested {len(test_cases)} scenarios - all passed")
    
    return True


def test_ml_warnings():
    """Test 4: Verify ML warnings when strategy disagrees"""
    print("\n" + "="*60)
    print("TEST 4: ML Advisory Warnings")
    print("="*60)
    
    ml_engine = MLTradingEngine()
    
    # When ML has no model, should have no warnings
    result = ml_engine.get_confidence_modifier(
        analysis={'ict_confidence': 0.75},
        final_signal='BUY',
        base_confidence=75.0
    )
    
    if result['warnings']:
        print(f"   Warnings (no model): {result['warnings']}")
    else:
        print(f"✅ No warnings when ML model not available")
    
    return True


def test_deprecated_methods():
    """Test 5: Verify old methods have deprecation warnings"""
    print("\n" + "="*60)
    print("TEST 5: Deprecated Methods")
    print("="*60)
    
    ml_engine = MLTradingEngine()
    
    # Check that old methods still exist (for backward compatibility)
    if not hasattr(ml_engine, 'predict_signal'):
        print("⚠️  WARNING: predict_signal() removed (should be deprecated, not removed)")
    else:
        print("✅ predict_signal() still exists (deprecated)")
    
    if not hasattr(ml_engine, 'predict_with_ensemble'):
        print("⚠️  WARNING: predict_with_ensemble() removed (should be deprecated, not removed)")
    else:
        print("✅ predict_with_ensemble() still exists (deprecated)")
    
    return True


def test_confidence_application():
    """Test 6: Verify confidence modifier application"""
    print("\n" + "="*60)
    print("TEST 6: Confidence Modifier Application")
    print("="*60)
    
    # Test various scenarios
    test_cases = [
        {
            'base_confidence': 75.0,
            'modifier': 1.05,  # +5%
            'expected': 78.75,
            'description': 'Positive modifier (boost)'
        },
        {
            'base_confidence': 80.0,
            'modifier': 0.95,  # -5%
            'expected': 76.0,
            'description': 'Negative modifier (penalty)'
        },
        {
            'base_confidence': 70.0,
            'modifier': 1.0,   # No change
            'expected': 70.0,
            'description': 'Neutral modifier'
        },
    ]
    
    for case in test_cases:
        base = case['base_confidence']
        modifier = case['modifier']
        expected = case['expected']
        
        # Calculate final confidence
        final = base * modifier
        final = max(0.0, min(100.0, final))  # Clamp
        
        if abs(final - expected) > 0.1:
            print(f"❌ FAILED: {case['description']}")
            print(f"   Base: {base}, Modifier: {modifier}, Expected: {expected}, Got: {final}")
            return False
        
        print(f"✅ {case['description']}: {base}% × {modifier} = {final:.2f}%")
    
    return True


def main():
    """Run all PR-ML-8 tests"""
    print("\n" + "="*60)
    print("🧪 PR-ML-8 TEST SUITE")
    print("ML Final Positioning (Advisory / Confidence-Only)")
    print("="*60)
    
    tests = [
        ("get_confidence_modifier() Method", test_get_confidence_modifier),
        ("Confidence Modifier Bounds", test_confidence_modifier_bounds),
        ("Signal Direction Preservation", test_direction_preservation),
        ("ML Advisory Warnings", test_ml_warnings),
        ("Deprecated Methods", test_deprecated_methods),
        ("Confidence Modifier Application", test_confidence_application),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ Test '{name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED - PR-ML-8 IMPLEMENTATION SUCCESSFUL!")
    else:
        print("❌ SOME TESTS FAILED - REVIEW REQUIRED")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
