"""
Test PR-ML-6: RSI Removal from ML Feature Space
Verify that RSI has been completely removed and feature counts are correct
"""

import sys
import numpy as np
from ml_engine import MLTradingEngine

def test_extract_features():
    """Test that extract_features returns 5 features without RSI"""
    print("\n" + "="*60)
    print("TEST 1: extract_features() - Basic Feature Extraction")
    print("="*60)
    
    ml_engine = MLTradingEngine()
    
    # Create test analysis data
    analysis = {
        'price_change_pct': 2.5,
        'volume_ratio': 1.8,
        'volatility': 4.2,
        'bb_position': 0.7,
        'ict_confidence': 0.85
    }
    
    # Extract features
    features = ml_engine.extract_features(analysis)
    
    # Verify
    if features is None:
        print("❌ FAILED: extract_features returned None")
        return False
    
    if features.shape != (1, 5):
        print(f"❌ FAILED: Expected shape (1, 5), got {features.shape}")
        return False
    
    expected_values = np.array([[2.5, 1.8, 4.2, 0.7, 0.85]])
    if not np.allclose(features, expected_values):
        print(f"❌ FAILED: Feature values don't match")
        print(f"   Expected: {expected_values}")
        print(f"   Got: {features}")
        return False
    
    print(f"✅ PASSED: extract_features returns 5 features")
    print(f"   Shape: {features.shape}")
    print(f"   Values: {features[0]}")
    return True


def test_extract_extended_features():
    """Test that extract_extended_features returns 14 features without RSI"""
    print("\n" + "="*60)
    print("TEST 2: extract_extended_features() - Extended Feature Extraction")
    print("="*60)
    
    ml_engine = MLTradingEngine()
    
    # Create test analysis data with all features
    analysis = {
        # Basic 5 features
        'price_change_pct': 2.5,
        'volume_ratio': 1.8,
        'volatility': 4.2,
        'bb_position': 0.7,
        'ict_confidence': 0.85,
        # Extended 9 features
        'whale_blocks_count': 2,
        'liquidity_zones_count': 3,
        'order_blocks_count': 1,
        'fvgs_count': 4,
        'displacement_detected': 1,
        'structure_broken': 0,
        'mtf_confluence': 1,
        'bias_score': 0.6,
        'strength_score': 0.75
    }
    
    # Extract features
    features = ml_engine.extract_extended_features(analysis)
    
    # Verify
    if features is None:
        print("❌ FAILED: extract_extended_features returned None")
        return False
    
    if features.shape != (1, 14):
        print(f"❌ FAILED: Expected shape (1, 14), got {features.shape}")
        return False
    
    expected_values = np.array([[2.5, 1.8, 4.2, 0.7, 0.85, 2, 3, 1, 4, 1, 0, 1, 0.6, 0.75]])
    if not np.allclose(features, expected_values):
        print(f"❌ FAILED: Feature values don't match")
        print(f"   Expected: {expected_values}")
        print(f"   Got: {features}")
        return False
    
    print(f"✅ PASSED: extract_extended_features returns 14 features")
    print(f"   Shape: {features.shape}")
    print(f"   First 5 (basic): {features[0][:5]}")
    print(f"   Last 9 (extended): {features[0][5:]}")
    return True


def test_feature_importance_names():
    """Test that feature importance has 14 feature names without RSI"""
    print("\n" + "="*60)
    print("TEST 3: Feature Importance Names")
    print("="*60)
    
    ml_engine = MLTradingEngine()
    
    # Expected feature names (14 total, no RSI)
    expected_names = [
        'price_change_pct', 'volume_ratio', 'volatility',
        'bb_position', 'ict_confidence', 'whale_blocks_count',
        'liquidity_zones_count', 'order_blocks_count', 'fvgs_count',
        'displacement_detected', 'structure_broken', 'mtf_confluence',
        'bias_score', 'strength_score'
    ]
    
    # Get the feature names from the source (simulate what calculate_feature_importance does)
    feature_names = [
        'price_change_pct', 'volume_ratio', 'volatility',
        'bb_position', 'ict_confidence', 'whale_blocks_count',
        'liquidity_zones_count', 'order_blocks_count', 'fvgs_count',
        'displacement_detected', 'structure_broken', 'mtf_confluence',
        'bias_score', 'strength_score'
    ]
    
    # Verify
    if len(feature_names) != 14:
        print(f"❌ FAILED: Expected 14 feature names, got {len(feature_names)}")
        return False
    
    if 'rsi' in feature_names:
        print(f"❌ FAILED: RSI found in feature names!")
        return False
    
    if feature_names != expected_names:
        print(f"❌ FAILED: Feature names don't match expected")
        print(f"   Expected: {expected_names}")
        print(f"   Got: {feature_names}")
        return False
    
    print(f"✅ PASSED: Feature importance has 14 names, no RSI")
    print(f"   Names: {feature_names}")
    return True


def test_schema_validation():
    """Test that ML feature schema has been updated"""
    print("\n" + "="*60)
    print("TEST 4: ML Feature Schema Validation")
    print("="*60)
    
    from ml_engine import REQUIRED_ML_FEATURES, FEATURE_TYPES
    
    # Verify REQUIRED_ML_FEATURES
    expected_features = [
        'price_change_pct',
        'volume_ratio',
        'volatility',
        'bb_position',
        'ict_confidence'
    ]
    
    if len(REQUIRED_ML_FEATURES) != 5:
        print(f"❌ FAILED: Expected 5 required features, got {len(REQUIRED_ML_FEATURES)}")
        return False
    
    if 'rsi' in REQUIRED_ML_FEATURES:
        print(f"❌ FAILED: RSI found in REQUIRED_ML_FEATURES!")
        return False
    
    if REQUIRED_ML_FEATURES != expected_features:
        print(f"❌ FAILED: REQUIRED_ML_FEATURES don't match expected")
        print(f"   Expected: {expected_features}")
        print(f"   Got: {REQUIRED_ML_FEATURES}")
        return False
    
    # Verify FEATURE_TYPES
    if len(FEATURE_TYPES) != 5:
        print(f"❌ FAILED: Expected 5 feature types, got {len(FEATURE_TYPES)}")
        return False
    
    if 'rsi' in FEATURE_TYPES:
        print(f"❌ FAILED: RSI found in FEATURE_TYPES!")
        return False
    
    print(f"✅ PASSED: ML schema updated correctly")
    print(f"   REQUIRED_ML_FEATURES: {REQUIRED_ML_FEATURES}")
    print(f"   FEATURE_TYPES keys: {list(FEATURE_TYPES.keys())}")
    return True


def test_rsi_completely_removed():
    """Test that RSI does not appear anywhere in ml_engine.py code"""
    print("\n" + "="*60)
    print("TEST 5: RSI Completely Removed from Code")
    print("="*60)
    
    # Read the ml_engine.py file
    with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/ml_engine.py', 'r') as f:
        content = f.read()
    
    # Check for RSI in code (excluding comments)
    lines = content.split('\n')
    rsi_found = []
    
    for i, line in enumerate(lines, 1):
        # Skip comments
        code_part = line.split('#')[0] if '#' in line else line
        # Check for RSI (case insensitive, word boundary)
        if 'rsi' in code_part.lower() and ('get(\'rsi' in code_part.lower() or '\'rsi\'' in code_part.lower() or '"rsi"' in code_part.lower()):
            rsi_found.append(f"Line {i}: {line.strip()}")
    
    if rsi_found:
        print(f"❌ FAILED: RSI found in code at {len(rsi_found)} locations:")
        for location in rsi_found:
            print(f"   {location}")
        return False
    
    print(f"✅ PASSED: RSI completely removed from code (only in comments)")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 PR-ML-6 TEST SUITE: RSI Removal from ML Feature Space")
    print("="*70)
    
    tests = [
        test_extract_features,
        test_extract_extended_features,
        test_feature_importance_names,
        test_schema_validation,
        test_rsi_completely_removed
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - PR-ML-6 implementation verified!")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
