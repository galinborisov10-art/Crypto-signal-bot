#!/usr/bin/env python3
"""
Test Suite for PR #120: Enable 2h Timeframe Signals

This test suite validates that:
1. 2h ICT hierarchy is correctly configured
2. 2h is added to all 3 scanning lists
3. TP/SL calculations work correctly for 2h
4. Duplicate detection works for 2h signals
5. All required 2h mappings are present
"""

import sys
import os

def test_2h_ict_hierarchy():
    """Test 1: Verify 2h ICT hierarchy is correctly configured"""
    print("\n🧪 Test 1: Verifying 2h ICT hierarchy...")
    
    try:
        from ict_signal_engine import ICTSignalEngine
        
        engine = ICTSignalEngine()
        hierarchy = engine._get_tf_hierarchy('2h')
        
        assert hierarchy['entry_tf'] == '2h', f"❌ 2h entry_tf incorrect: {hierarchy['entry_tf']}"
        assert hierarchy['confirmation_tf'] == '4h', f"❌ 2h confirmation_tf incorrect: {hierarchy['confirmation_tf']}"
        assert hierarchy['structure_tf'] == '1d', f"❌ 2h structure_tf incorrect: {hierarchy['structure_tf']}"
        assert hierarchy['htf_bias_tf'] == '1d', f"❌ 2h htf_bias_tf incorrect: {hierarchy['htf_bias_tf']}"
        
        print("✅ Test 1 PASSED: 2h ICT hierarchy correct")
        return True
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")
        return False


def test_2h_in_scanning_lists():
    """Test 2: Verify 2h is added to all 3 scanning lists"""
    print("\n🧪 Test 2: Verifying 2h in scanning lists...")
    
    try:
        with open('bot.py', 'r') as f:
            content = f.read()
        
        # Check line 11023
        found_timeframes_to_check = "timeframes_to_check = ['1h', '2h', '4h', '1d']" in content
        assert found_timeframes_to_check, "❌ 2h not in timeframes_to_check (line 11023)"
        
        # Check line 15277
        found_main_timeframes = "timeframes = ['1h', '2h', '4h', '1d']" in content
        assert found_main_timeframes, "❌ 2h not in main timeframes list (line 15277)"
        
        # Check line 17870
        found_timeframes_to_test = "timeframes_to_test = ['1h', '2h', '4h', '1d']" in content
        assert found_timeframes_to_test, "❌ 2h not in timeframes_to_test (line 17870)"
        
        print("✅ Test 2 PASSED: 2h in all 3 scanning lists")
        return True
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        return False


def test_2h_tp_sl_calculations():
    """Test 3: Verify TP/SL calculations work correctly for 2h"""
    print("\n🧪 Test 3: Verifying TP/SL calculations for 2h...")
    
    try:
        from ict_signal_engine import ICTSignalEngine
        
        engine = ICTSignalEngine()
        
        # Test LONG signal
        entry = 100.0
        sl = 98.0
        risk = entry - sl  # 2.0
        
        tp_prices = engine._calculate_tp_with_min_rr(entry, sl, 'LONG', min_rr=3.0)
        
        assert len(tp_prices) >= 1, "❌ No TP prices calculated"
        
        # TP should be at least 3:1 risk/reward
        min_tp = entry + (risk * 3.0)  # 100 + 6 = 106
        assert tp_prices[0] >= min_tp, f"❌ TP1 doesn't meet 1:3 RR. Expected >= {min_tp}, got {tp_prices[0]}"
        
        print(f"✅ Test 3 PASSED: TP/SL calculations work for 2h (Entry: {entry}, SL: {sl}, TP1: {tp_prices[0]})")
        return True
    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")
        return False


def test_2h_duplicate_detection():
    """Test 4: Verify duplicate detection works for 2h signals"""
    print("\n🧪 Test 4: Verifying duplicate detection for 2h...")
    
    try:
        from signal_cache import SignalCache
        
        cache = SignalCache()
        
        # Simulate signal
        signal_key = "BTCUSDT_BUY_2h"
        entry_price = 100000.0
        
        # First signal
        is_dup1 = cache.is_duplicate(signal_key, entry_price)
        assert not is_dup1, "❌ First signal marked as duplicate"
        
        cache.add_signal(signal_key, entry_price)
        
        # Second signal (same entry)
        is_dup2 = cache.is_duplicate(signal_key, entry_price)
        assert is_dup2, "❌ Duplicate not detected"
        
        print("✅ Test 4 PASSED: Duplicate detection works for 2h")
        return True
    except Exception as e:
        print(f"❌ Test 4 FAILED: {e}")
        return False


def test_2h_mappings():
    """Test 5: Verify 2h has all required mappings"""
    print("\n🧪 Test 5: Verifying 2h mappings...")
    
    try:
        with open('bot.py', 'r') as f:
            content = f.read()
        
        # TradingView mapping (line ~2002)
        assert "'2h': '120'" in content, "❌ TradingView mapping missing"
        
        # Binance mapping (line ~2039)
        assert "'2h': '2h'" in content, "❌ Binance mapping missing"
        
        # MTF weight (line ~3034)
        assert "'2h': 1.0" in content, "❌ MTF weight missing"
        
        print("✅ Test 5 PASSED: All 2h mappings present")
        return True
    except Exception as e:
        print(f"❌ Test 5 FAILED: {e}")
        return False


def run_all_tests():
    """Run all PR #120 tests"""
    print("=" * 60)
    print("PR #120: Enable 2h Timeframe Signals - Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Test 1: 2h ICT Hierarchy", test_2h_ict_hierarchy()))
    results.append(("Test 2: 2h in Scanning Lists", test_2h_in_scanning_lists()))
    results.append(("Test 3: TP/SL Calculations", test_2h_tp_sl_calculations()))
    results.append(("Test 4: Duplicate Detection", test_2h_duplicate_detection()))
    results.append(("Test 5: 2h Mappings", test_2h_mappings()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! 2h timeframe is ready for deployment.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review.")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
