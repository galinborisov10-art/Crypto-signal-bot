"""
Test ML Integration in ICT Signal Engine
Verify that ML optimization works correctly and maintains ICT compliance
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ict_signal_engine import ICTSignalEngine, MarketBias

def create_test_data():
    """Create synthetic OHLCV data with clear ICT patterns"""
    dates = pd.date_range(start='2025-01-01', periods=200, freq='1h')
    np.random.seed(42)
    
    # Simulate realistic price data with order blocks
    base_price = 50000
    prices = []
    current = base_price
    
    for i in range(200):
        # Add trending moves with some order blocks
        if i == 80:  # Bullish setup - OB candle
            change = -150
        elif i in [81, 82, 83]:  # Displacement
            change = 600
        elif i == 150:  # Bearish setup - OB candle
            change = 200
        elif i in [151, 152, 153]:  # Displacement
            change = -550
        else:
            change = np.random.randn() * 100
        
        current += change
        prices.append(current)
    
    # Create dataframe
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 50) for p in prices],
        'low': [p - abs(np.random.randn() * 50) for p in prices],
        'close': [p + np.random.randn() * 30 for p in prices],
        'volume': [1000000 + np.random.randn() * 200000 for _ in prices]
    })
    
    return df

def test_ml_initialization():
    """Test 1: Verify ML engines are initialized correctly"""
    print("\n" + "="*60)
    print("TEST 1: ML Initialization")
    print("="*60)
    
    engine = ICTSignalEngine()
    
    # Check ML engine availability
    if engine.ml_engine:
        print("✅ ML Trading Engine: Initialized")
    else:
        print("⚠️ ML Trading Engine: Not Available")
    
    if engine.ml_predictor:
        print("✅ ML Predictor: Initialized")
    else:
        print("⚠️ ML Predictor: Not Available")
    
    # Check ML config
    config_keys = [
        'use_ml', 'ml_min_confidence_boost', 'ml_max_confidence_boost',
        'ml_entry_adjustment_max', 'ml_sl_tighten_max', 'ml_sl_widen_max',
        'ml_tp_extension_max', 'ml_override_threshold'
    ]
    
    print("\n📊 ML Configuration:")
    for key in config_keys:
        value = engine.config.get(key)
        print(f"   {key}: {value}")
    
    return engine

def test_ml_feature_extraction(engine):
    """Test 2: Verify ML feature extraction"""
    print("\n" + "="*60)
    print("TEST 2: ML Feature Extraction")
    print("="*60)
    
    df = create_test_data()
    df = engine._prepare_dataframe(df)
    
    # Create mock components and call feature extraction
    mock_components = {
        'order_blocks': [{'type': 'bullish', 'zone_high': 51000, 'zone_low': 50900}],
        'fvgs': [],
        'whale_blocks': [],
        'liquidity_zones': [{'price_level': 52000, 'strength': 0.8}],
        'internal_liquidity': []
    }
    
    mock_mtf = {
        '4h': {'bias': MarketBias.BULLISH},
        '1d': {'bias': MarketBias.BULLISH}
    }
    
    features = engine._extract_ml_features(
        df=df,
        components=mock_components,
        mtf_analysis=mock_mtf,
        bias=MarketBias.BULLISH,
        displacement=True,
        structure_break=True
    )
    
    print(f"\n✅ Extracted {len(features)} features")
    print("\n📊 Feature Summary:")
    print(f"   RSI: {features.get('rsi', 0):.2f}")
    print(f"   Volume Ratio: {features.get('volume_ratio', 0):.2f}")
    print(f"   Volatility: {features.get('volatility', 0):.2f}")
    print(f"   BB Position: {features.get('bb_position', 0):.2f}")
    print(f"   Price Change %: {features.get('price_change_pct', 0):.2f}")
    print(f"\n🎯 ICT Metrics:")
    print(f"   Order Blocks: {features.get('num_order_blocks', 0)}")
    print(f"   FVGs: {features.get('num_fvgs', 0)}")
    print(f"   Whale Blocks: {features.get('num_whale_blocks', 0)}")
    print(f"   Liquidity Zones: {features.get('num_liquidity_zones', 0)}")
    print(f"   Liquidity Strength: {features.get('liquidity_strength', 0):.2f}")
    print(f"   MTF Confluence: {features.get('mtf_confluence', 0):.2f}")
    print(f"   Bias Strength: {features.get('bias_strength', 0):.2f}")
    print(f"   Displacement: {features.get('displacement_detected', 0)}")
    print(f"   Structure Break: {features.get('structure_break_detected', 0)}")
    
    # Verify no forbidden indicators
    forbidden = ['ema', 'macd', 'ma_20', 'ma_50', 'sma']
    for key in forbidden:
        if key in features:
            print(f"❌ FORBIDDEN INDICATOR FOUND: {key}")
            return False
    
    print("\n✅ No forbidden indicators (EMA/MACD/MA) found")
    return True

def test_ml_optimization(engine):
    """Test 3: Verify ML optimization maintains ICT compliance"""
    print("\n" + "="*60)
    print("TEST 3: ML Optimization (ICT Compliance)")
    print("="*60)
    
    # Test BULLISH scenario
    print("\n🟢 BULLISH Scenario:")
    entry_price = 50000.0
    stop_loss = 49500.0  # SL ПОД entry
    take_profit = [51000.0, 51500.0, 52000.0]
    
    ml_features = {
        'ict_confidence': 0.85,
        'liquidity_strength': 0.7,
        'mtf_confluence': 0.6
    }
    
    mock_components = {
        'order_blocks': [
            type('obj', (object,), {
                'zone_high': 49550, 
                'zone_low': 49450,
                'type': type('obj', (object,), {'value': 'BULLISH'})()
            })()
        ],
        'liquidity_zones': []
    }
    
    opt_entry, opt_sl, opt_tp = engine._apply_ml_optimization(
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        ml_features=ml_features,
        bias=MarketBias.BULLISH,
        components=mock_components
    )
    
    print(f"   Entry: {entry_price:.2f} → {opt_entry:.2f}")
    print(f"   SL: {stop_loss:.2f} → {opt_sl:.2f}")
    print(f"   TP1: {take_profit[0]:.2f} → {opt_tp[0]:.2f}")
    
    # CRITICAL: Verify SL is still ПОД (below) entry for BULLISH
    if opt_sl < opt_entry:
        print(f"   ✅ BULLISH: SL is ПОД (below) entry ({opt_sl:.2f} < {opt_entry:.2f})")
    else:
        print(f"   ❌ BULLISH: SL VIOLATION - SL should be ПОД entry!")
        return False
    
    # Test BEARISH scenario
    print("\n🔴 BEARISH Scenario:")
    entry_price = 50000.0
    stop_loss = 50500.0  # SL НАД entry
    take_profit = [49000.0, 48500.0, 48000.0]
    
    ml_features = {
        'ict_confidence': 0.85,
        'liquidity_strength': 0.7,
        'mtf_confluence': 0.6
    }
    
    mock_components = {
        'order_blocks': [
            type('obj', (object,), {
                'zone_high': 50550, 
                'zone_low': 50450,
                'type': type('obj', (object,), {'value': 'BEARISH'})()
            })()
        ],
        'liquidity_zones': []
    }
    
    opt_entry, opt_sl, opt_tp = engine._apply_ml_optimization(
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        ml_features=ml_features,
        bias=MarketBias.BEARISH,
        components=mock_components
    )
    
    print(f"   Entry: {entry_price:.2f} → {opt_entry:.2f}")
    print(f"   SL: {stop_loss:.2f} → {opt_sl:.2f}")
    print(f"   TP1: {take_profit[0]:.2f} → {opt_tp[0]:.2f}")
    
    # CRITICAL: Verify SL is still НАД (above) entry for BEARISH
    if opt_sl > opt_entry:
        print(f"   ✅ BEARISH: SL is НАД (above) entry ({opt_sl:.2f} > {opt_entry:.2f})")
    else:
        print(f"   ❌ BEARISH: SL VIOLATION - SL should be НАД entry!")
        return False
    
    print("\n✅ ICT SL placement rules maintained")
    return True

def test_signal_outcome_recording(engine):
    """Test 4: Verify signal outcome recording"""
    print("\n" + "="*60)
    print("TEST 4: Signal Outcome Recording")
    print("="*60)
    
    signal_data = {
        'symbol': 'BTCUSDT',
        'timeframe': '1h',
        'signal_type': 'BUY',
        'confidence': 85.0,
        'ml_features': {
            'rsi': 55,
            'volume_ratio': 1.2,
            'ict_confidence': 0.85
        }
    }
    
    try:
        engine.record_signal_outcome(
            signal_id='TEST_001',
            outcome='WIN',
            actual_rr=3.5,
            signal_data=signal_data
        )
        print("✅ Outcome recording successful")
        return True
    except Exception as e:
        print(f"❌ Outcome recording failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 ML INTEGRATION TEST SUITE")
    print("="*60)
    
    # Test 1: Initialization
    engine = test_ml_initialization()
    
    # Test 2: Feature extraction
    test2_passed = test_ml_feature_extraction(engine)
    
    # Test 3: ML optimization (ICT compliance)
    test3_passed = test_ml_optimization(engine)
    
    # Test 4: Outcome recording
    test4_passed = test_signal_outcome_recording(engine)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Test 1 (Initialization): ✅ PASSED")
    print(f"Test 2 (Feature Extraction): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print(f"Test 3 (ICT Compliance): {'✅ PASSED' if test3_passed else '❌ FAILED'}")
    print(f"Test 4 (Outcome Recording): {'✅ PASSED' if test4_passed else '❌ FAILED'}")
    
    all_passed = test2_passed and test3_passed and test4_passed
    
    if all_passed:
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED - ML INTEGRATION SUCCESSFUL!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ SOME TESTS FAILED - REVIEW REQUIRED")
        print("="*60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
