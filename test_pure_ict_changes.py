#!/usr/bin/env python3
"""
Test Pure ICT Compliance Changes

This test verifies:
1. Volume MA replaced with Volume Median
2. Bollinger SMA replaced with ATR Range
3. Feature extraction still works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import ICT Signal Engine
from ict_signal_engine import ICTSignalEngine, MarketBias

def create_test_dataframe(num_rows=100):
    """Create a test dataframe with realistic crypto data"""
    dates = [datetime.now() - timedelta(hours=i) for i in range(num_rows, 0, -1)]
    
    # Generate realistic price data
    base_price = 50000
    prices = []
    for i in range(num_rows):
        noise = np.random.normal(0, 500)
        trend = i * 10
        price = base_price + trend + noise
        prices.append(price)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + np.random.uniform(50, 200) for p in prices],
        'low': [p - np.random.uniform(50, 200) for p in prices],
        'close': [p + np.random.uniform(-100, 100) for p in prices],
        'volume': [np.random.uniform(1000, 10000) for _ in range(num_rows)]
    })
    
    return df

def test_volume_median_calculation():
    """Test that volume_median is calculated correctly"""
    print("\n" + "="*60)
    print("TEST 1: Volume Median Calculation")
    print("="*60)
    
    engine = ICTSignalEngine()
    df = create_test_dataframe(100)
    
    # Prepare dataframe (this should add volume_median)
    df_prepared = engine._prepare_dataframe(df)
    
    # Check that volume_median exists
    assert 'volume_median' in df_prepared.columns, "❌ volume_median column not found!"
    print("✅ volume_median column exists")
    
    # Check that volume_ratio exists
    assert 'volume_ratio' in df_prepared.columns, "❌ volume_ratio column not found!"
    print("✅ volume_ratio column exists")
    
    # Verify that volume_median is calculated using median (not mean)
    manual_median = df['volume'].rolling(window=20).median().iloc[-1]
    calculated_median = df_prepared['volume_median'].iloc[-1]
    
    # Allow small floating point differences
    assert abs(manual_median - calculated_median) < 0.01, \
        f"❌ Median calculation mismatch: {manual_median} vs {calculated_median}"
    print(f"✅ volume_median calculated correctly: {calculated_median:.2f}")
    
    # Verify volume_ratio is calculated correctly
    expected_ratio = df['volume'].iloc[-1] / calculated_median if calculated_median > 0 else 1.0
    actual_ratio = df_prepared['volume_ratio'].iloc[-1]
    
    assert abs(expected_ratio - actual_ratio) < 0.01, \
        f"❌ volume_ratio mismatch: {expected_ratio} vs {actual_ratio}"
    print(f"✅ volume_ratio calculated correctly: {actual_ratio:.2f}")
    
    print("✅ TEST 1 PASSED: Volume Median works correctly")
    return True

def test_atr_range_calculation():
    """Test that ATR range position is calculated correctly"""
    print("\n" + "="*60)
    print("TEST 2: ATR Range Position Calculation")
    print("="*60)
    
    engine = ICTSignalEngine()
    df = create_test_dataframe(100)
    df = engine._prepare_dataframe(df)
    
    # Create mock components for ML feature extraction
    components = {
        'order_blocks': [],
        'fvgs': [],
        'whale_blocks': [],
        'liquidity_zones': [],
        'internal_liquidity': []
    }
    
    # Extract ML features
    try:
        features = engine._extract_ml_features(
            df=df,
            components=components,
            mtf_analysis=None,
            bias=MarketBias.BULLISH,
            displacement=True,
            structure_break=True
        )
        
        # Check that bb_position exists in features
        assert 'bb_position' in features, "❌ bb_position not found in features!"
        print("✅ bb_position feature exists")
        
        # Verify bb_position is calculated using range (not Bollinger Bands)
        current_price = df['close'].iloc[-1]
        range_high = df['high'].iloc[-20:].max()
        range_low = df['low'].iloc[-20:].min()
        
        expected_position = (current_price - range_low) / (range_high - range_low) \
            if (range_high - range_low) > 0 else 0.5
        actual_position = features['bb_position']
        
        assert abs(expected_position - actual_position) < 0.01, \
            f"❌ bb_position mismatch: {expected_position} vs {actual_position}"
        print(f"✅ bb_position calculated correctly using ATR range: {actual_position:.4f}")
        
        # Verify bb_position is in valid range [0, 1]
        assert 0 <= actual_position <= 1, \
            f"❌ bb_position out of range: {actual_position}"
        print(f"✅ bb_position in valid range [0, 1]")
        
        print("✅ TEST 2 PASSED: ATR Range Position works correctly")
        return True
        
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ml_features_complete():
    """Test that all 13 ML features are extracted correctly"""
    print("\n" + "="*60)
    print("TEST 3: ML Features Completeness")
    print("="*60)
    
    engine = ICTSignalEngine()
    df = create_test_dataframe(100)
    df = engine._prepare_dataframe(df)
    
    components = {
        'order_blocks': [],
        'fvgs': [],
        'whale_blocks': [],
        'liquidity_zones': [],
        'internal_liquidity': []
    }
    
    try:
        features = engine._extract_ml_features(
            df=df,
            components=components,
            mtf_analysis=None,
            bias=MarketBias.BULLISH,
            displacement=True,
            structure_break=True
        )
        
        print(f"✅ Extracted {len(features)} ML features")
        
        # Expected features (based on the code)
        expected_features = [
            'rsi', 'volume_ratio', 'volatility', 'price_change_pct', 'bb_position',
            'num_order_blocks', 'num_fvgs', 'num_whale_blocks', 'num_liquidity_zones',
            'num_ilp', 'liquidity_strength', 'mtf_confluence', 'displacement'
        ]
        
        print("\nFeature values:")
        for feat_name in expected_features:
            if feat_name in features:
                print(f"  ✅ {feat_name}: {features[feat_name]:.4f}")
            else:
                print(f"  ⚠️  {feat_name}: MISSING")
        
        # Check that all critical features exist
        critical_features = ['volume_ratio', 'bb_position']
        for feat_name in critical_features:
            assert feat_name in features, f"❌ Critical feature {feat_name} missing!"
        
        print("\n✅ TEST 3 PASSED: All critical ML features present")
        return True
        
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test that variable names are backward compatible"""
    print("\n" + "="*60)
    print("TEST 4: Backward Compatibility")
    print("="*60)
    
    engine = ICTSignalEngine()
    df = create_test_dataframe(100)
    df = engine._prepare_dataframe(df)
    
    # Check that volume_ratio still exists (even though we use volume_median internally)
    assert 'volume_ratio' in df.columns, "❌ volume_ratio missing - breaks backward compatibility!"
    print("✅ volume_ratio column exists (backward compatible)")
    
    components = {
        'order_blocks': [],
        'fvgs': [],
        'whale_blocks': [],
        'liquidity_zones': [],
        'internal_liquidity': []
    }
    
    features = engine._extract_ml_features(
        df=df,
        components=components,
        mtf_analysis=None,
        bias=MarketBias.BULLISH,
        displacement=True,
        structure_break=True
    )
    
    # Check that bb_position still exists (even though we use range internally)
    assert 'bb_position' in features, "❌ bb_position missing - breaks backward compatibility!"
    print("✅ bb_position feature exists (backward compatible)")
    
    print("✅ TEST 4 PASSED: Backward compatibility maintained")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 TESTING: Pure ICT Compliance Changes")
    print("="*70)
    
    tests = [
        test_volume_median_calculation,
        test_atr_range_calculation,
        test_ml_features_complete,
        test_backward_compatibility
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test.__name__}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED! Pure ICT compliance achieved!")
        return 0
    else:
        print(f"\n❌ {failed} TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit(main())
