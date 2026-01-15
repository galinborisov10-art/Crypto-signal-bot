#!/usr/bin/env python3
"""
Unit tests for Ultra-Simple Entry-Based Deduplication (PR #118)
Tests the simplified is_signal_duplicate() function with 1.5% entry threshold
"""

import os
import sys
import tempfile
from signal_cache import is_signal_duplicate, ENTRY_THRESHOLD_PCT

def test_first_signal_allowed():
    """First signal for symbol/direction/timeframe is allowed"""
    print("\n🧪 TEST 1: First signal allowed")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        is_dup, msg = is_signal_duplicate("BTCUSDT", "BUY", "4h", 94000, 85, base_path=tmpdir)
        assert is_dup == False, f"First signal should be allowed, got: {msg}"
        assert "First signal" in msg, f"Message should mention 'First signal', got: {msg}"
        print(f"   ✅ PASS: {msg}")


def test_same_entry_blocked():
    """Same entry price is blocked as duplicate"""
    print("\n🧪 TEST 2: Same entry blocked")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # First signal
        is_dup1, msg1 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 94000, 85, base_path=tmpdir)
        assert is_dup1 == False, "First signal should be allowed"
        
        # Same entry - should be blocked
        is_dup2, msg2 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 94000, 85, base_path=tmpdir)
        assert is_dup2 == True, f"Same entry should be blocked, got: {msg2}"
        assert "0.00%" in msg2, f"Message should show 0.00% difference, got: {msg2}"
        print(f"   ✅ PASS: Duplicate blocked (0.00% difference)")


def test_small_entry_diff_blocked():
    """Entry difference <1.5% is blocked"""
    print("\n🧪 TEST 3: Small entry difference blocked (<1.5%)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # First signal
        is_dup1, msg1 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 94000, 85, base_path=tmpdir)
        assert is_dup1 == False, "First signal should be allowed"
        
        # Second signal with +1.0% difference (94000 -> 94940)
        is_dup2, msg2 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 94940, 85, base_path=tmpdir)
        assert is_dup2 == True, f"Entry diff <1.5% should be blocked, got: {msg2}"
        assert "1.00%" in msg2, f"Message should show 1.00% difference, got: {msg2}"
        print(f"   ✅ PASS: 1.0% difference blocked")


def test_significant_entry_diff_allowed():
    """Entry difference >=1.5% is allowed"""
    print("\n🧪 TEST 4: Significant entry difference allowed (>=1.5%)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # First signal
        is_dup1, msg1 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 94000, 85, base_path=tmpdir)
        assert is_dup1 == False, "First signal should be allowed"
        
        # Second signal with +1.60% difference (94000 -> 95504)
        is_dup2, msg2 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 95504, 85, base_path=tmpdir)
        assert is_dup2 == False, f"Entry diff >=1.5% should be allowed, got: {msg2}"
        # Allow for slight floating point variations
        assert ("1.60%" in msg2 or "1.59%" in msg2), f"Message should show ~1.60% difference, got: {msg2}"
        print(f"   ✅ PASS: 1.60% difference allowed")


def test_different_direction_allowed():
    """Different direction (BUY vs SELL) is allowed"""
    print("\n🧪 TEST 5: Different direction allowed")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # BUY signal
        is_dup1, msg1 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 94000, 85, base_path=tmpdir)
        assert is_dup1 == False, "BUY signal should be allowed"
        
        # SELL signal (different direction, same entry)
        is_dup2, msg2 = is_signal_duplicate("BTCUSDT", "SELL", "4h", 94000, 85, base_path=tmpdir)
        assert is_dup2 == False, f"Different direction should be allowed, got: {msg2}"
        print(f"   ✅ PASS: Different direction allowed")


def test_different_timeframe_allowed():
    """Different timeframe is allowed"""
    print("\n🧪 TEST 6: Different timeframe allowed")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 4h timeframe
        is_dup1, msg1 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 94000, 85, base_path=tmpdir)
        assert is_dup1 == False, "4h signal should be allowed"
        
        # 1d timeframe (same symbol, direction, entry)
        is_dup2, msg2 = is_signal_duplicate("BTCUSDT", "BUY", "1d", 94000, 85, base_path=tmpdir)
        assert is_dup2 == False, f"Different timeframe should be allowed, got: {msg2}"
        print(f"   ✅ PASS: Different timeframe allowed")


def test_threshold_boundary():
    """Test exact 1.5% boundary"""
    print("\n🧪 TEST 7: Threshold boundary (exactly 1.5%)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # First signal
        is_dup1, msg1 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 94000, 85, base_path=tmpdir)
        assert is_dup1 == False, "First signal should be allowed"
        
        # Second signal with exactly 1.5% difference (94000 -> 95410)
        is_dup2, msg2 = is_signal_duplicate("BTCUSDT", "BUY", "4h", 95410, 85, base_path=tmpdir)
        assert is_dup2 == False, f"Exactly 1.5% should be allowed (>=), got: {msg2}"
        assert "1.50%" in msg2, f"Message should show 1.50% difference, got: {msg2}"
        print(f"   ✅ PASS: Exactly 1.5% boundary allowed")


def test_real_data_xrpusdt():
    """Test with real 14.01 data (XRPUSDT 4h @ $2.0357)"""
    print("\n🧪 TEST 8: Real data - XRPUSDT")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # First signal
        is_dup1, msg1 = is_signal_duplicate("XRPUSDT", "BUY", "4h", 2.0357, 85, base_path=tmpdir)
        assert is_dup1 == False, "First signal should be allowed"
        print(f"   ✓ First XRPUSDT signal allowed")
        
        # Same entry (should be blocked)
        is_dup2, msg2 = is_signal_duplicate("XRPUSDT", "BUY", "4h", 2.0357, 85, base_path=tmpdir)
        assert is_dup2 == True, "Duplicate with same entry should be blocked"
        print(f"   ✓ Duplicate blocked (0.00% diff)")
        
        # Different entry >1.5% (should be allowed)
        # 2.0357 -> 2.0700 = +1.68%
        is_dup3, msg3 = is_signal_duplicate("XRPUSDT", "BUY", "4h", 2.0700, 85, base_path=tmpdir)
        assert is_dup3 == False, f"Entry diff >1.5% should be allowed, got: {msg3}"
        print(f"   ✓ New entry allowed (1.68% diff)")
        print(f"   ✅ PASS: Real XRPUSDT data test passed")


def test_negative_price_change():
    """Test that negative price changes also work"""
    print("\n🧪 TEST 9: Negative price changes")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # First signal at higher price
        is_dup1, msg1 = is_signal_duplicate("ETHUSDT", "SELL", "1h", 4000, 88, base_path=tmpdir)
        assert is_dup1 == False, "First signal should be allowed"
        
        # Second signal with -2.0% difference (4000 -> 3920)
        is_dup2, msg2 = is_signal_duplicate("ETHUSDT", "SELL", "1h", 3920, 88, base_path=tmpdir)
        assert is_dup2 == False, f"Negative 2.0% diff should be allowed, got: {msg2}"
        assert "2.00%" in msg2, f"Message should show 2.00% difference, got: {msg2}"
        print(f"   ✅ PASS: Negative price change handled correctly")


def test_multiple_symbols():
    """Test that different symbols don't interfere"""
    print("\n🧪 TEST 10: Multiple symbols")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Different symbols, same price
        symbols = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]
        
        for symbol in symbols:
            is_dup, msg = is_signal_duplicate(symbol, "BUY", "4h", 1000, 85, base_path=tmpdir)
            assert is_dup == False, f"{symbol} should be allowed (different symbol)"
        
        print(f"   ✅ PASS: All 3 symbols allowed with same entry price")


def test_cooldown_parameter_ignored():
    """Test that cooldown_minutes parameter is ignored (backward compatibility)"""
    print("\n🧪 TEST 11: Cooldown parameter ignored")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # First signal with cooldown=60
        is_dup1, msg1 = is_signal_duplicate("SOLUSDT", "BUY", "1d", 100, 80, 
                                            cooldown_minutes=60, base_path=tmpdir)
        assert is_dup1 == False, "First signal should be allowed"
        
        # Immediately send duplicate with cooldown=1 (should still be blocked by entry price)
        is_dup2, msg2 = is_signal_duplicate("SOLUSDT", "BUY", "1d", 100, 80, 
                                            cooldown_minutes=1, base_path=tmpdir)
        assert is_dup2 == True, "Duplicate should be blocked regardless of cooldown parameter"
        
        print(f"   ✅ PASS: Cooldown parameter correctly ignored")


def run_all_tests():
    """Run all test cases"""
    print("=" * 70)
    print("🔬 ULTRA-SIMPLE ENTRY-BASED DEDUPLICATION TESTS (PR #118)")
    print("=" * 70)
    print(f"\n📊 Configuration: ENTRY_THRESHOLD_PCT = {ENTRY_THRESHOLD_PCT}%")
    
    tests = [
        test_first_signal_allowed,
        test_same_entry_blocked,
        test_small_entry_diff_blocked,
        test_significant_entry_diff_allowed,
        test_different_direction_allowed,
        test_different_timeframe_allowed,
        test_threshold_boundary,
        test_real_data_xrpusdt,
        test_negative_price_change,
        test_multiple_symbols,
        test_cooldown_parameter_ignored,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"   ❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
        print("\n🎯 Key Validations:")
        print(f"   ✓ Entry threshold: {ENTRY_THRESHOLD_PCT}%")
        print(f"   ✓ First signals always allowed")
        print(f"   ✓ Entry diff <{ENTRY_THRESHOLD_PCT}% blocked")
        print(f"   ✓ Entry diff >={ENTRY_THRESHOLD_PCT}% allowed")
        print(f"   ✓ Different directions/timeframes allowed")
        print(f"   ✓ Real data scenarios validated")
        return 0
    else:
        print(f"\n❌ {failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
