"""Test unified ICT analysis for ALL timeframes"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from ict_signal_engine import ICTSignalEngine, MarketBias

def create_sample_df(periods=100):
    """Create sample data for testing"""
    dates = pd.date_range(start='2025-01-01', periods=periods, freq='1H')
    base_price = 50000
    
    # Generate price data with some volatility
    np.random.seed(42)
    prices = []
    current = base_price
    
    for i in range(periods):
        change = np.random.randn() * 100
        current += change
        prices.append(current)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 50) for p in prices],
        'low': [p - abs(np.random.randn() * 50) for p in prices],
        'close': [p + np.random.randn() * 30 for p in prices],
        'volume': [1000000 + np.random.randn() * 200000 for _ in prices]
    })
    
    return df

def test_all_timeframes():
    """Test унифициран анализ за ВСИЧКИ TFs (1w до 1m)"""
    print("\n🧪 Testing: Unified ICT Analysis for ALL Timeframes")
    print("=" * 60)
    
    engine = ICTSignalEngine()
    df = create_sample_df()
    
    supported_timeframes = ['1w', '1d', '4h', '3h', '2h', '1h', '30m', '15m', '5m', '1m']
    
    results = {}
    for tf in supported_timeframes:
        print(f"\n📊 Testing timeframe: {tf}")
        try:
            signal = engine.generate_signal(df, 'BTCUSDT', tf)
            if signal:
                print(f"  ✅ Signal generated for {tf}")
                print(f"     Entry: {signal.entry_price:.2f}")
                print(f"     SL: {signal.sl_price:.2f}")
                print(f"     TP1: {signal.tp_prices[0]:.2f}")
                print(f"     RR: {signal.risk_reward_ratio:.2f}")
                results[tf] = 'PASS'
                
                # Validate mandatory elements
                assert signal.entry_price > 0, f"Entry price invalid for {tf}"
                assert signal.sl_price > 0, f"SL price invalid for {tf}"
                assert len(signal.tp_prices) >= 1, f"No TP prices for {tf}"
            else:
                print(f"  ⏭️  No signal for {tf} (conditions not met)")
                results[tf] = 'NO_SIGNAL'
        except Exception as e:
            print(f"  ❌ Error for {tf}: {e}")
            results[tf] = f'ERROR: {str(e)[:50]}'
    
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY:")
    for tf, result in results.items():
        status = "✅" if result == 'PASS' else "⏭️" if result == 'NO_SIGNAL' else "❌"
        print(f"  {status} {tf}: {result}")
    
    passed = sum(1 for r in results.values() if r == 'PASS')
    total = len(supported_timeframes)
    print(f"\n✅ Test completed: {passed}/{total} timeframes generated signals")
    
    return all(r in ['PASS', 'NO_SIGNAL'] for r in results.values())

def test_sl_validation():
    """Test SL validation за BULLISH/BEARISH"""
    print("\n🧪 Testing: SL Validation")
    print("=" * 60)
    
    engine = ICTSignalEngine()
    df = create_sample_df()
    
    signal = engine.generate_signal(df, 'BTCUSDT', '1h')
    
    if signal and signal.order_blocks:
        ob = signal.order_blocks[0]
        ob_bottom = ob.get('zone_low', ob.get('bottom', 0))
        ob_top = ob.get('zone_high', ob.get('top', 0))
        
        print(f"Signal Type: {signal.signal_type.value}")
        print(f"Entry: {signal.entry_price:.2f}")
        print(f"SL: {signal.sl_price:.2f}")
        print(f"OB Range: [{ob_bottom:.2f}, {ob_top:.2f}]")
        
        if signal.signal_type.value in ['BUY', 'STRONG_BUY']:
            # BULLISH: SL < OB bottom
            if signal.sl_price < ob_bottom:
                print(f"✅ BULLISH SL validation: SL ({signal.sl_price:.2f}) < OB bottom ({ob_bottom:.2f})")
                return True
            else:
                print(f"❌ BULLISH SL validation failed: SL should be < OB bottom")
                return False
        elif signal.signal_type.value in ['SELL', 'STRONG_SELL']:
            # BEARISH: SL > OB top
            if signal.sl_price > ob_top:
                print(f"✅ BEARISH SL validation: SL ({signal.sl_price:.2f}) > OB top ({ob_top:.2f})")
                return True
            else:
                print(f"❌ BEARISH SL validation failed: SL should be > OB top")
                return False
    else:
        print("⏭️  No signal with order blocks generated")
        return True

def test_rr_guarantee():
    """Test RR ≥ 3.0 за всички сигнали"""
    print("\n🧪 Testing: RR ≥ 3.0 Guarantee")
    print("=" * 60)
    
    engine = ICTSignalEngine()
    df = create_sample_df()
    
    # Test multiple times to ensure consistency
    min_rr = 3.0
    test_count = 5
    results = []
    
    for i in range(test_count):
        df_test = create_sample_df(periods=100 + i * 10)
        signal = engine.generate_signal(df_test, 'BTCUSDT', '1h')
        
        if signal:
            risk = abs(signal.entry_price - signal.sl_price)
            reward = abs(signal.tp_prices[0] - signal.entry_price)
            rr = reward / risk if risk > 0 else 0
            
            print(f"Test {i+1}: RR = {rr:.2f}")
            print(f"  Entry: {signal.entry_price:.2f}")
            print(f"  SL: {signal.sl_price:.2f}")
            print(f"  TP1: {signal.tp_prices[0]:.2f}")
            print(f"  Risk: {risk:.2f}, Reward: {reward:.2f}")
            
            if rr >= min_rr:
                print(f"  ✅ RR {rr:.2f} >= {min_rr}")
                results.append(True)
            else:
                print(f"  ❌ RR {rr:.2f} < {min_rr}")
                results.append(False)
        else:
            print(f"Test {i+1}: ⏭️  No signal generated")
    
    if not results:
        print("⏭️  No signals generated for RR testing")
        return True
    
    passed = sum(results)
    total = len(results)
    print(f"\n✅ RR Test: {passed}/{total} signals have RR ≥ {min_rr}")
    
    return all(results)

def test_unified_sequence():
    """Test 12-step unified sequence"""
    print("\n🧪 Testing: 12-Step Unified Sequence")
    print("=" * 60)
    
    engine = ICTSignalEngine()
    df = create_sample_df(periods=150)
    
    # Test with MTF data
    mtf_data = {
        '1d': create_sample_df(periods=50),
        '4h': create_sample_df(periods=100),
        '1h': df
    }
    
    signal = engine.generate_signal(df, 'BTCUSDT', '1h', mtf_data=mtf_data)
    
    if signal:
        print("✅ Signal generated with MTF data")
        print(f"  HTF Bias: {signal.htf_bias}")
        print(f"  MTF Structure: {signal.mtf_structure}")
        print(f"  Confidence: {signal.confidence:.1f}%")
        print(f"  RR: {signal.risk_reward_ratio:.2f}")
        
        # Verify mandatory elements
        assert signal.entry_price > 0
        assert signal.sl_price > 0
        assert len(signal.tp_prices) >= 1
        assert signal.risk_reward_ratio >= 3.0
        
        print("✅ All mandatory elements present")
        return True
    else:
        print("⏭️  No signal generated (conditions not met)")
        return True

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🎯 UNIFIED ICT ANALYSIS TESTS")
    print("=" * 60)
    
    all_passed = True
    
    # Run all tests
    test_results = {
        "All Timeframes": test_all_timeframes(),
        "SL Validation": test_sl_validation(),
        "RR Guarantee": test_rr_guarantee(),
        "Unified Sequence": test_unified_sequence()
    }
    
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS:")
    print("=" * 60)
    
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    all_passed = all(test_results.values())
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED!")
    
    print("=" * 60)
