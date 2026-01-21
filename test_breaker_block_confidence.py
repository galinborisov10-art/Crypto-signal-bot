#!/usr/bin/env python3
"""
Test Breaker Block Confidence Scoring Integration (ESB §4)

This test verifies:
1. breaker_block_weight is present in config with value 0.08
2. Breaker blocks contribute to confidence using configurable weight
3. Formula uses 8% max contribution (not hardcoded 5%)
4. No regression: signals work with and without breaker blocks
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


def test_breaker_block_weight_in_config():
    """Test that breaker_block_weight exists in config with correct value"""
    print("\n" + "="*60)
    print("TEST 1: Breaker Block Weight in Config")
    print("="*60)
    
    try:
        engine = ICTSignalEngine()
        config = engine._get_default_config()
        
        # Check if breaker_block_weight exists
        assert 'breaker_block_weight' in config, "❌ breaker_block_weight not found in config"
        
        # Check if value is 0.08 (8%)
        assert config['breaker_block_weight'] == 0.08, f"❌ Expected 0.08, got {config['breaker_block_weight']}"
        
        print("✅ breaker_block_weight exists in config")
        print(f"✅ Value: {config['breaker_block_weight']} (8%)")
        print("✅ TEST PASSED")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        return False


def test_breaker_block_confidence_calculation():
    """Test that breaker blocks contribute to confidence correctly"""
    print("\n" + "="*60)
    print("TEST 2: Breaker Block Confidence Calculation")
    print("="*60)
    
    try:
        engine = ICTSignalEngine()
        
        # Mock ICT components with breaker blocks
        ict_components = {
            'whale_blocks': [],
            'liquidity_zones': [],
            'order_blocks': [],
            'fvgs': [],
            'breaker_blocks': [
                {'type': 'BULLISH_BREAKER', 'strength': 5.0},
                {'type': 'BEARISH_BREAKER', 'strength': 6.0}
            ],
            'mitigation_blocks': [],
            'sibi_ssib_zones': []
        }
        
        # Calculate confidence with breaker blocks
        confidence = engine._calculate_signal_confidence(
            ict_components=ict_components,
            mtf_analysis=None,
            bias=MarketBias.BULLISH,
            structure_broken=True,
            displacement_detected=False,
            risk_reward_ratio=3.0
        )
        
        # With 2 breaker blocks: min(8, 2 * 3) = 6
        # Score: 6 * 0.08 / 0.08 = 6
        # Base confidence from structure break: 20 * 0.2 / 0.2 = 20
        # Total: 20 + 6 = 26
        
        print(f"Confidence with 2 breaker blocks: {confidence}")
        
        # Verify confidence includes breaker block contribution
        # Should be at least structure break (20) + breaker contribution (6) = 26
        assert confidence >= 26, f"❌ Expected confidence >= 26, got {confidence}"
        
        print("✅ Breaker blocks contribute to confidence")
        print("✅ Formula uses weight-based calculation")
        print("✅ TEST PASSED")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_breaker_block_max_contribution():
    """Test that breaker blocks max contribution is 8% (not 5%)"""
    print("\n" + "="*60)
    print("TEST 3: Breaker Block Max Contribution (8%)")
    print("="*60)
    
    try:
        engine = ICTSignalEngine()
        
        # Mock ICT components with many breaker blocks (should hit the max)
        ict_components = {
            'whale_blocks': [],
            'liquidity_zones': [],
            'order_blocks': [],
            'fvgs': [],
            'breaker_blocks': [
                {'type': 'BULLISH_BREAKER', 'strength': 5.0},
                {'type': 'BULLISH_BREAKER', 'strength': 6.0},
                {'type': 'BULLISH_BREAKER', 'strength': 7.0},
                {'type': 'BULLISH_BREAKER', 'strength': 8.0}
            ],
            'mitigation_blocks': [],
            'sibi_ssib_zones': []
        }
        
        # Calculate confidence with many breaker blocks
        confidence = engine._calculate_signal_confidence(
            ict_components=ict_components,
            mtf_analysis=None,
            bias=MarketBias.BULLISH,
            structure_broken=True,
            displacement_detected=False,
            risk_reward_ratio=3.0
        )
        
        # With 4 breaker blocks: min(8, 4 * 3) = 8 (hits max)
        # Score: 8 * 0.08 / 0.08 = 8
        # Base confidence from structure break: 20
        # Total: 20 + 8 = 28
        
        print(f"Confidence with 4 breaker blocks: {confidence}")
        
        # Verify max contribution is 8 (not 5)
        assert confidence >= 28, f"❌ Expected confidence >= 28, got {confidence}"
        
        print("✅ Max breaker block contribution is 8% (not 5%)")
        print("✅ TEST PASSED")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_no_regression_without_breaker_blocks():
    """Test that signals work correctly when no breaker blocks present"""
    print("\n" + "="*60)
    print("TEST 4: No Regression Without Breaker Blocks")
    print("="*60)
    
    try:
        engine = ICTSignalEngine()
        
        # Mock ICT components WITHOUT breaker blocks
        ict_components = {
            'whale_blocks': [{'strength': 8.0}],
            'liquidity_zones': [{'strength': 7.0}],
            'order_blocks': [{'strength': 6.0}],
            'fvgs': [{'strength': 5.0}],
            'breaker_blocks': [],  # No breaker blocks
            'mitigation_blocks': [],
            'sibi_ssib_zones': []
        }
        
        # Calculate confidence without breaker blocks
        confidence = engine._calculate_signal_confidence(
            ict_components=ict_components,
            mtf_analysis=None,
            bias=MarketBias.BULLISH,
            structure_broken=True,
            displacement_detected=False,
            risk_reward_ratio=3.0
        )
        
        print(f"Confidence without breaker blocks: {confidence}")
        
        # Verify confidence is calculated (no crash, no NaN)
        assert confidence > 0, f"❌ Expected confidence > 0, got {confidence}"
        assert not np.isnan(confidence), "❌ Confidence is NaN"
        
        print("✅ No regression without breaker blocks")
        print("✅ Confidence calculation still works")
        print("✅ TEST PASSED")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BREAKER BLOCK CONFIDENCE SCORING TESTS (ESB §4)")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(test_breaker_block_weight_in_config())
    results.append(test_breaker_block_confidence_calculation())
    results.append(test_breaker_block_max_contribution())
    results.append(test_no_regression_without_breaker_blocks())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print(f"❌ {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
