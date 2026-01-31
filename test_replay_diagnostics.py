"""
Test script for Phase 2B: Replay Diagnostics
Tests the replay functionality without requiring full bot setup
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_replay_cache():
    """Test ReplayCache class"""
    print("=" * 60)
    print("TEST 1: ReplayCache - Save and Load Signals")
    print("=" * 60)
    
    try:
        from diagnostics import ReplayCache, SignalSnapshot
        
        # Create cache instance
        cache = ReplayCache()
        
        # Clear any existing cache
        cache.clear_cache()
        print("✅ Cache cleared")
        
        # Create mock klines data
        timestamps = pd.date_range(start='2024-01-01', periods=100, freq='15min')
        klines = pd.DataFrame({
            'open': np.random.uniform(40000, 45000, 100),
            'high': np.random.uniform(40000, 45000, 100),
            'low': np.random.uniform(40000, 45000, 100),
            'close': np.random.uniform(40000, 45000, 100),
            'volume': np.random.uniform(1000, 5000, 100)
        }, index=timestamps)
        
        # Create mock signal data
        signal_data = {
            'symbol': 'BTCUSDT',
            'timeframe': '15m',
            'signal_type': 'LONG',
            'direction': 'BUY',
            'entry_price': 45000.0,
            'stop_loss': 44500.0,
            'take_profit': [45500.0, 46000.0],
            'confidence': 75,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save signal
        result = cache.save_signal(signal_data, klines)
        print(f"✅ Signal saved: {result}")
        
        # Load signals
        signals = cache.load_signals()
        print(f"✅ Signals loaded: {len(signals)} signals")
        
        if signals:
            snapshot = signals[0]
            print(f"   - Symbol: {snapshot.symbol}")
            print(f"   - Timeframe: {snapshot.timeframe}")
            print(f"   - Hash: {snapshot.signal_hash}")
            print(f"   - Klines: {len(snapshot.klines_snapshot)} rows")
        
        # Test rotation - add 11 signals (should keep only 10)
        for i in range(11):
            signal_data['timestamp'] = datetime.now().isoformat()
            signal_data['signal_type'] = f"SIGNAL_{i}"
            cache.save_signal(signal_data, klines)
        
        signals = cache.load_signals()
        print(f"✅ After adding 11 more: {len(signals)} signals (should be 10 due to rotation)")
        
        # Get signal count
        count = cache.get_signal_count()
        print(f"✅ Signal count: {count}")
        
        # Clear cache
        cache.clear_cache()
        count = cache.get_signal_count()
        print(f"✅ After clear: {count} signals")
        
        print("\n✅ TEST 1 PASSED: ReplayCache works correctly\n")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_signal_comparison():
    """Test signal comparison logic"""
    print("=" * 60)
    print("TEST 2: Signal Comparison Logic")
    print("=" * 60)
    
    try:
        from diagnostics import ReplayEngine, ReplayCache
        
        cache = ReplayCache()
        engine = ReplayEngine(cache)
        
        # Test 1: Identical signals
        original = {
            'signal_type': 'LONG',
            'direction': 'BUY',
            'entry_price': 45000.0,
            'stop_loss': 44500.0,
            'take_profit': [45500.0, 46000.0],
            'confidence': 75
        }
        
        replayed = original.copy()
        
        result = engine.compare_signals(original, replayed)
        print(f"Test 1 - Identical signals: {result['summary']}")
        assert result['match'] == True, "Should match identical signals"
        print("✅ Passed: Identical signals match")
        
        # Test 2: Different signal type
        replayed = original.copy()
        replayed['signal_type'] = 'SHORT'
        
        result = engine.compare_signals(original, replayed)
        print(f"Test 2 - Different type: {result['summary']}")
        assert result['match'] == False, "Should detect type difference"
        assert 'signal_type' in result['diffs'], "Should list signal_type as diff"
        print("✅ Passed: Detects signal type difference")
        
        # Test 3: Price within tolerance (0.01%)
        replayed = original.copy()
        replayed['entry_price'] = 45000.0 + (45000.0 * 0.00005)  # 0.005% difference
        
        result = engine.compare_signals(original, replayed)
        print(f"Test 3 - Within tolerance: {result['summary']}")
        assert result['match'] == True, "Should match within tolerance"
        print("✅ Passed: Accepts prices within 0.01% tolerance")
        
        # Test 4: Price outside tolerance
        replayed = original.copy()
        replayed['entry_price'] = 45000.0 + (45000.0 * 0.0002)  # 0.02% difference
        
        result = engine.compare_signals(original, replayed)
        print(f"Test 4 - Outside tolerance: {result['summary']}")
        assert result['match'] == False, "Should detect price difference"
        assert 'entry_delta' in result['diffs'], "Should list entry_delta as diff"
        print("✅ Passed: Detects prices outside 0.01% tolerance")
        
        # Test 5: Different TP arrays
        replayed = original.copy()
        replayed['take_profit'] = [45500.0, 46000.0, 46500.0]  # Extra TP
        
        result = engine.compare_signals(original, replayed)
        print(f"Test 5 - Different TP array: {result['summary']}")
        assert result['match'] == False, "Should detect TP array difference"
        assert 'tp_delta' in result['diffs'], "Should list tp_delta as diff"
        print("✅ Passed: Detects TP array differences")
        
        print("\n✅ TEST 2 PASSED: Signal comparison works correctly\n")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_capture_function():
    """Test non-blocking capture function"""
    print("=" * 60)
    print("TEST 3: Non-Blocking Signal Capture")
    print("=" * 60)
    
    try:
        from diagnostics import capture_signal_for_replay, ReplayCache
        
        # Clear cache
        cache = ReplayCache()
        cache.clear_cache()
        
        # Create mock data
        timestamps = pd.date_range(start='2024-01-01', periods=50, freq='1h')
        klines = pd.DataFrame({
            'open': np.random.uniform(40000, 45000, 50),
            'high': np.random.uniform(40000, 45000, 50),
            'low': np.random.uniform(40000, 45000, 50),
            'close': np.random.uniform(40000, 45000, 50),
            'volume': np.random.uniform(1000, 5000, 50)
        }, index=timestamps)
        
        signal_data = {
            'symbol': 'ETHUSDT',
            'timeframe': '1h',
            'signal_type': 'SHORT',
            'direction': 'SELL',
            'entry_price': 3000.0,
            'stop_loss': 3050.0,
            'take_profit': [2950.0, 2900.0],
            'confidence': 80,
            'timestamp': datetime.now().isoformat()
        }
        
        # Capture signal (should not raise exception)
        capture_signal_for_replay(signal_data, klines)
        print("✅ Capture completed without blocking")
        
        # Verify signal was saved
        signals = cache.load_signals()
        assert len(signals) == 1, "Should have saved 1 signal"
        print(f"✅ Signal saved: {signals[0].symbol} {signals[0].timeframe}")
        
        # Test with invalid data (should not crash)
        capture_signal_for_replay(None, None)
        print("✅ Gracefully handles invalid data")
        
        # Test with empty DataFrame
        capture_signal_for_replay(signal_data, pd.DataFrame())
        print("✅ Gracefully handles empty DataFrame")
        
        print("\n✅ TEST 3 PASSED: Non-blocking capture works correctly\n")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_cache_file_format():
    """Test replay_cache.json file format"""
    print("=" * 60)
    print("TEST 4: Cache File Format")
    print("=" * 60)
    
    try:
        from diagnostics import ReplayCache
        import json
        
        cache = ReplayCache()
        cache.clear_cache()
        
        # Create and save a signal
        timestamps = pd.date_range(start='2024-01-01', periods=10, freq='5min')
        klines = pd.DataFrame({
            'open': [45000.0] * 10,
            'high': [45100.0] * 10,
            'low': [44900.0] * 10,
            'close': [45050.0] * 10,
            'volume': [1234.5] * 10
        }, index=timestamps)
        
        signal_data = {
            'symbol': 'BTCUSDT',
            'timeframe': '5m',
            'signal_type': 'LONG',
            'direction': 'BUY',
            'entry_price': 45050.0,
            'stop_loss': 44800.0,
            'take_profit': [45300.0, 45500.0],
            'confidence': 75,
            'timestamp': '2026-01-31T10:30:00Z'
        }
        
        cache.save_signal(signal_data, klines)
        
        # Read and validate JSON structure
        cache_file = Path("replay_cache.json")
        assert cache_file.exists(), "Cache file should exist"
        print(f"✅ Cache file created: {cache_file}")
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Validate structure
        assert 'signals' in cache_data, "Should have 'signals' key"
        assert 'metadata' in cache_data, "Should have 'metadata' key"
        print("✅ Cache file has correct top-level structure")
        
        # Validate metadata
        metadata = cache_data['metadata']
        assert metadata['max_signals'] == 10, "Should have max_signals = 10"
        assert metadata['max_klines'] == 100, "Should have max_klines = 100"
        assert metadata['version'] == "1.0", "Should have version 1.0"
        print("✅ Metadata is correct")
        
        # Validate signal structure
        signals = cache_data['signals']
        assert len(signals) == 1, "Should have 1 signal"
        
        sig = signals[0]
        assert 'timestamp' in sig, "Signal should have timestamp"
        assert 'symbol' in sig, "Signal should have symbol"
        assert 'timeframe' in sig, "Signal should have timeframe"
        assert 'klines_snapshot' in sig, "Signal should have klines_snapshot"
        assert 'original_signal' in sig, "Signal should have original_signal"
        assert 'signal_hash' in sig, "Signal should have signal_hash"
        print("✅ Signal structure is correct")
        
        # Validate klines snapshot
        klines_snap = sig['klines_snapshot']
        assert len(klines_snap) == 10, "Should have 10 klines rows"
        assert len(klines_snap[0]) == 6, "Each kline should have 6 values (OHLCV + timestamp)"
        print(f"✅ Klines snapshot is correct: {len(klines_snap)} rows")
        
        print("\n✅ TEST 4 PASSED: Cache file format is correct\n")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PHASE 2B: REPLAY DIAGNOSTICS TEST SUITE")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("ReplayCache", test_replay_cache()))
    results.append(("Signal Comparison", test_signal_comparison()))
    results.append(("Non-Blocking Capture", test_capture_function()))
    results.append(("Cache File Format", test_cache_file_format()))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Phase 2B implementation is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
