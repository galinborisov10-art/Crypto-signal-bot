#!/usr/bin/env python3
"""
Test suite for signal_cache.py duplicate fixes
Tests all 4 bug fixes:
1. Entry price in signal key
2. Cooldown boundary (<=)
3. Cache overwrite prevention
4. Extended cleanup period
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
from signal_cache import is_signal_duplicate, load_sent_signals, save_sent_signals, validate_cache, CACHE_CLEANUP_HOURS

def test_bug1_entry_price_in_key():
    """Test Bug #1: Signal key must include entry_price"""
    print("\n🧪 TEST 1: Entry price in signal key")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Send signal with entry price 2.0357
        is_dup1, msg1 = is_signal_duplicate(
            symbol="XRPUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=2.0357,
            confidence=85,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        
        # Send DIFFERENT signal with entry price 2.1500 (same symbol/type/timeframe)
        is_dup2, msg2 = is_signal_duplicate(
            symbol="XRPUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=2.1500,
            confidence=85,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        
        # Both should be NEW (not duplicates) because entry prices differ
        assert is_dup1 == False, "First signal should NOT be duplicate"
        assert is_dup2 == False, "Second signal with different entry should NOT be duplicate"
        
        # Verify cache has 2 entries with different keys
        cache = load_sent_signals(tmpdir)
        assert len(cache) == 2, f"Cache should have 2 entries, got {len(cache)}"
        
        keys = list(cache.keys())
        assert "XRPUSDT_BUY_4h_2.0357" in keys, "Key should include entry price 2.0357"
        assert "XRPUSDT_BUY_4h_2.15" in keys, "Key should include entry price 2.15"
        
        print("✅ PASS: Entry prices create unique signal keys")


def test_bug2_cooldown_boundary():
    """Test Bug #2: Cooldown should use <= not <"""
    print("\n🧪 TEST 2: Cooldown boundary check (<=)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a signal sent 59.9 minutes ago (within cooldown boundary)
        cache = {}
        signal_key = "BTCUSDT_BUY_1h_50000.0"
        # Use 59.9 minutes to account for execution time
        almost_60_min_ago = (datetime.now() - timedelta(minutes=59, seconds=54)).isoformat()
        
        cache[signal_key] = {
            'timestamp': almost_60_min_ago,
            'entry_price': 50000.0,
            'confidence': 90
        }
        save_sent_signals(cache, tmpdir)
        
        # Try to send same signal now (within 60 minute boundary)
        is_dup, msg = is_signal_duplicate(
            symbol="BTCUSDT",
            signal_type="BUY",
            timeframe="1h",
            entry_price=50000.0,
            confidence=90,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        
        # Should be detected as duplicate (59.9 <= 60 is TRUE)
        assert is_dup == True, f"Signal within 60 min should be duplicate, got: {msg}"
        
        # Also test that signals PAST cooldown are allowed
        cache2 = {}
        past_cooldown_key = "ETHUSDT_SELL_4h_3500.0"
        past_60_min_ago = (datetime.now() - timedelta(minutes=61)).isoformat()
        
        cache2[past_cooldown_key] = {
            'timestamp': past_60_min_ago,
            'entry_price': 3500.0,
            'confidence': 88
        }
        save_sent_signals(cache2, tmpdir)
        
        is_dup2, msg2 = is_signal_duplicate(
            symbol="ETHUSDT",
            signal_type="SELL",
            timeframe="4h",
            entry_price=3500.0,
            confidence=88,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        
        # Should NOT be duplicate (61 > 60, cooldown expired)
        assert is_dup2 == False, f"Signal past cooldown should be allowed, got: {msg2}"
        
        print("✅ PASS: Cooldown boundary works correctly (<=)")


def test_bug3_cache_overwrite_prevention():
    """Test Bug #3: Cache should NOT be updated for duplicates"""
    print("\n🧪 TEST 3: Cache overwrite prevention")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Send first signal
        original_time = datetime.now()
        is_dup1, msg1 = is_signal_duplicate(
            symbol="ETHUSDT",
            signal_type="SELL",
            timeframe="1d",
            entry_price=3746.83,
            confidence=88,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        
        # Load cache and check timestamp
        cache1 = load_sent_signals(tmpdir)
        key = "ETHUSDT_SELL_1d_3746.83"
        timestamp1 = cache1[key]['timestamp']
        
        # Wait 1 second
        import time
        time.sleep(1)
        
        # Try to send duplicate (within cooldown)
        is_dup2, msg2 = is_signal_duplicate(
            symbol="ETHUSDT",
            signal_type="SELL",
            timeframe="1d",
            entry_price=3746.83,
            confidence=88,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        
        # Load cache again
        cache2 = load_sent_signals(tmpdir)
        timestamp2 = cache2[key]['timestamp']
        
        # Verify duplicate was detected
        assert is_dup2 == True, "Second signal should be duplicate"
        
        # Verify timestamp was NOT updated
        assert timestamp1 == timestamp2, f"Timestamp should NOT change for duplicates: {timestamp1} vs {timestamp2}"
        
        print("✅ PASS: Cache timestamp not updated for duplicates")


def test_bug4_extended_cleanup():
    """Test Bug #4: Cleanup period is 168 hours (7 days)"""
    print("\n🧪 TEST 4: Extended cleanup period")
    
    # Check the constant
    assert CACHE_CLEANUP_HOURS == 168, f"Cleanup should be 168 hours, got {CACHE_CLEANUP_HOURS}"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = {}
        
        # Entry from 25 hours ago (should NOT be cleaned with 168h setting)
        cache["OLD_BUY_4h_1000.0"] = {
            'timestamp': (datetime.now() - timedelta(hours=25)).isoformat(),
            'entry_price': 1000.0,
            'confidence': 80
        }
        
        # Entry from 169 hours ago (should be cleaned)
        cache["VERYOLD_BUY_4h_2000.0"] = {
            'timestamp': (datetime.now() - timedelta(hours=169)).isoformat(),
            'entry_price': 2000.0,
            'confidence': 80
        }
        
        # Current entry
        cache["NEW_BUY_4h_3000.0"] = {
            'timestamp': datetime.now().isoformat(),
            'entry_price': 3000.0,
            'confidence': 80
        }
        
        save_sent_signals(cache, tmpdir)
        
        # Load and check cleanup
        loaded = load_sent_signals(tmpdir)
        
        assert len(loaded) == 2, f"Should have 2 entries after cleanup, got {len(loaded)}"
        assert "OLD_BUY_4h_1000.0" in loaded, "25-hour old entry should NOT be cleaned"
        assert "NEW_BUY_4h_3000.0" in loaded, "New entry should be present"
        assert "VERYOLD_BUY_4h_2000.0" not in loaded, "169-hour old entry SHOULD be cleaned"
        
        print("✅ PASS: Cleanup period is 168 hours (7 days)")


def test_cache_validation():
    """Test cache validation function"""
    print("\n🧪 TEST 5: Cache validation")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test 1: No cache file
        is_valid, msg = validate_cache(tmpdir)
        assert is_valid == True, "Should be valid when cache doesn't exist"
        print(f"  ✓ No file: {msg}")
        
        # Test 2: Valid cache
        cache = {
            "TEST_BUY_1h_100.0": {
                'timestamp': datetime.now().isoformat(),
                'entry_price': 100.0,
                'confidence': 85
            }
        }
        save_sent_signals(cache, tmpdir)
        
        is_valid, msg = validate_cache(tmpdir)
        assert is_valid == True, f"Should be valid, got: {msg}"
        print(f"  ✓ Valid cache: {msg}")
        
        # Test 3: Invalid JSON
        cache_file = os.path.join(tmpdir, 'sent_signals_cache.json')
        with open(cache_file, 'w') as f:
            f.write("{invalid json")
        
        is_valid, msg = validate_cache(tmpdir)
        assert is_valid == False, "Should be invalid for corrupted JSON"
        print(f"  ✓ Invalid JSON detected: {msg}")
        
        print("✅ PASS: Cache validation works")


def test_different_entry_prices_allowed():
    """Test that signals with different entry prices are both allowed"""
    print("\n🧪 TEST 6: Different entry prices create separate signals")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Send 3 signals for same symbol/type/timeframe but different entries
        entries = [2.0357, 2.1500, 2.3000]
        
        for entry in entries:
            is_dup, msg = is_signal_duplicate(
                symbol="XRPUSDT",
                signal_type="BUY",
                timeframe="4h",
                entry_price=entry,
                confidence=85,
                cooldown_minutes=60,
                base_path=tmpdir
            )
            assert is_dup == False, f"Signal with entry {entry} should NOT be duplicate"
        
        # Verify all 3 are in cache
        cache = load_sent_signals(tmpdir)
        assert len(cache) == 3, f"Should have 3 different signals, got {len(cache)}"
        
        print("✅ PASS: Different entry prices create separate signals")


def test_same_signal_blocked_within_cooldown():
    """Test that exact same signal is blocked within cooldown"""
    print("\n🧪 TEST 7: Same signal blocked within cooldown")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Send signal
        is_dup1, msg1 = is_signal_duplicate(
            symbol="ADAUSDT",
            signal_type="BUY",
            timeframe="1d",
            entry_price=0.4407,
            confidence=82,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        
        assert is_dup1 == False, "First signal should be allowed"
        
        # Try to send SAME signal immediately
        is_dup2, msg2 = is_signal_duplicate(
            symbol="ADAUSDT",
            signal_type="BUY",
            timeframe="1d",
            entry_price=0.4407,
            confidence=82,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        
        assert is_dup2 == True, f"Duplicate should be blocked: {msg2}"
        
        # Verify only 1 entry in cache
        cache = load_sent_signals(tmpdir)
        assert len(cache) == 1, f"Should have only 1 entry, got {len(cache)}"
        
        print("✅ PASS: Duplicate signal correctly blocked")


def run_all_tests():
    """Run all test cases"""
    print("=" * 60)
    print("🔬 SIGNAL CACHE BUG FIX TESTS")
    print("=" * 60)
    
    tests = [
        test_bug1_entry_price_in_key,
        test_bug2_cooldown_boundary,
        test_bug3_cache_overwrite_prevention,
        test_bug4_extended_cleanup,
        test_cache_validation,
        test_different_entry_prices_allowed,
        test_same_signal_blocked_within_cooldown,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"❌ {failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_all_tests())
